"""
FinStream AI - End-to-End Pipeline Execution Engine
Integrates Generator -> Feature Engineering -> ML Inference -> SHAP -> Persistence -> WebSocket.
Measures precise per-stage latencies, throughput, and data consistency.
"""

import asyncio
from datetime import datetime, timezone
import logging
import time
from typing import Any, Dict, List, Optional
import numpy as np

from backend.event_service import EventService, get_event_service
from database.connection import DatabaseManager, get_db_manager
from database.persistence_service import PersistenceService
from database.redis_client import RedisRepository, get_redis_repository
from features.feature_definitions import ALL_ENGINEERED_FEATURE_COLUMNS
from models.predict import ModelInferenceEngine, load_inference_engine
from producer.transaction_generator import TransactionGenerator
from streaming.feature_engineering import RealTimeFeatureEngine

logger = logging.getLogger("pipeline_runner")


class PipelineMetricsTracker:
    """Tracks latency percentiles and throughput for pipeline runs."""

    def __init__(self):
        self.feature_latencies: List[float] = []
        self.ml_latencies: List[float] = []
        self.persistence_latencies: List[float] = []
        self.ws_latencies: List[float] = []
        self.e2e_latencies: List[float] = []
        self.processed_records: List[Dict[str, Any]] = []
        self.start_time: float = 0.0
        self.end_time: float = 0.0

    def compute_summary(self) -> Dict[str, Any]:
        """Calculates throughput and latency percentiles (P50, P95, P99, Max)."""
        duration = max(self.end_time - self.start_time, 0.0001)
        count = len(self.e2e_latencies)

        def calc_stats(data: List[float]) -> Dict[str, float]:
            if not data:
                return {"p50_ms": 0.0, "p95_ms": 0.0, "p99_ms": 0.0, "max_ms": 0.0, "mean_ms": 0.0}
            arr = np.array(data) * 1000.0  # convert to ms
            return {
                "p50_ms": round(float(np.percentile(arr, 50)), 2),
                "p95_ms": round(float(np.percentile(arr, 95)), 2),
                "p99_ms": round(float(np.percentile(arr, 99)), 2),
                "max_ms": round(float(np.max(arr)), 2),
                "mean_ms": round(float(np.mean(arr)), 2),
            }

        return {
            "total_transactions": count,
            "duration_seconds": round(duration, 3),
            "throughput_tps": round(count / duration, 2),
            "e2e_latency": calc_stats(self.e2e_latencies),
            "feature_latency": calc_stats(self.feature_latencies),
            "ml_inference_latency": calc_stats(self.ml_latencies),
            "persistence_latency": calc_stats(self.persistence_latencies),
            "websocket_latency": calc_stats(self.ws_latencies),
        }


class EndToEndPipelineRunner:
    """
    Coordinates the full streaming lifecycle in a single deterministic, benchmarkable pipeline.
    """

    def __init__(
        self,
        db_manager: Optional[DatabaseManager] = None,
        redis_repo: Optional[RedisRepository] = None,
        inference_engine: Optional[ModelInferenceEngine] = None,
        event_service: Optional[EventService] = None,
    ):
        self.db_manager = db_manager or get_db_manager()
        self.redis_repo = redis_repo or get_redis_repository()
        self.inference_engine = inference_engine or load_inference_engine()
        self.persistence_service = PersistenceService(
            db_manager=self.db_manager,
            redis_repo=self.redis_repo,
        )
        self.event_service = event_service or get_event_service()
        self.feature_engine = RealTimeFeatureEngine()

    def process_single_transaction(
        self,
        transaction_dict: Dict[str, Any],
        explain: bool = True,
    ) -> Dict[str, Any]:
        """
        Executes single transaction through:
        Feature Extraction -> Dual ML -> SHAP -> Persistence -> Return Scored Record.
        """
        t0 = time.perf_counter()

        # 1. Feature Engineering
        t_feat_start = time.perf_counter()
        enriched = self.feature_engine.enrich_transaction(transaction_dict)
        t_feat_end = time.perf_counter()

        # 2. Dual ML Inference & SHAP
        t_ml_start = time.perf_counter()
        prediction = self.inference_engine.predict_single(
            enriched,
            explain=explain,
            top_n_shap=5,
        )
        t_ml_end = time.perf_counter()

        full_record = {**enriched, **prediction}

        # 3. PostgreSQL & Redis Persistence
        t_persist_start = time.perf_counter()
        persist_res = self.persistence_service.persist_evaluated_transaction(full_record)
        t_persist_end = time.perf_counter()

        # 4. WebSocket Event Delivery
        t_ws_start = time.perf_counter()
        delivered = 0
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        if loop and loop.is_running():
            asyncio.create_task(self.event_service.broadcast_risk_assessed(full_record))
            delivered = 1
        else:
            delivered = asyncio.run(self.event_service.broadcast_risk_assessed(full_record))
        t_ws_end = time.perf_counter()

        t_end = time.perf_counter()

        return {
            "record": full_record,
            "persistence_status": persist_res["status"],
            "websocket_delivered": delivered,
            "timings": {
                "t_feature": t_feat_end - t_feat_start,
                "t_ml": t_ml_end - t_ml_start,
                "t_persistence": t_persist_end - t_persist_start,
                "t_websocket": t_ws_end - t_ws_start,
                "t_e2e": t_end - t0,
            },
        }

    def run_benchmark(
        self,
        num_transactions: int = 100,
        scenario: str = "mixed",
        seed: int = 42,
        explain: bool = True,
    ) -> Dict[str, Any]:
        """
        Executes a controlled, reproducible benchmark run over N transactions.
        """
        generator = TransactionGenerator(
            rate=1000.0,
            scenario=scenario,
            seed=seed,
        )

        tracker = PipelineMetricsTracker()
        self.feature_engine.reset()
        tracker.start_time = time.perf_counter()

        count = 0
        for tx in generator.stream_transactions():
            tx_dict = tx.to_clean_dict()
            res = self.process_single_transaction(tx_dict, explain=explain)
            tracker.processed_records.append(res["record"])

            timings = res["timings"]
            tracker.feature_latencies.append(timings["t_feature"])
            tracker.ml_latencies.append(timings["t_ml"])
            tracker.persistence_latencies.append(timings["t_persistence"])
            tracker.ws_latencies.append(timings["t_websocket"])
            tracker.e2e_latencies.append(timings["t_e2e"])

            count += 1
            if count >= num_transactions:
                break

        tracker.end_time = time.perf_counter()
        return tracker.compute_summary()
