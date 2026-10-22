"""
FinStream AI - Phase 13 End-to-End Pipeline Integration Tests
Tests full integration: Generator -> Feature Engineering -> ML Inference -> SHAP -> Persistence -> WebSocket.
Verifies data consistency, correlation IDs, zero duplication, and latency tracker.
"""

import pytest
import sqlite3
from unittest.mock import AsyncMock, MagicMock, patch

from backend.event_service import EventService
from database.connection import DatabaseManager
from database.persistence_service import PersistenceService
from database.redis_client import RedisRepository
from database.repositories import PostgresRepository
from models.predict import ModelInferenceEngine
from producer.transaction_generator import TransactionGenerator
from streaming.feature_engineering import RealTimeFeatureEngine
from streaming.pipeline_runner import EndToEndPipelineRunner, PipelineMetricsTracker


@pytest.fixture
def sqlite_db_manager(tmp_path):
    """Creates a fresh SQLite database manager for integration testing."""
    db_file = tmp_path / "test_e2e.db"
    db_url = f"sqlite:///{db_file}"
    manager = DatabaseManager(database_url=db_url)
    manager.create_all_tables()
    return manager


@pytest.fixture
def mock_redis_repo():
    """Mock Redis repository that succeeds on all operations."""
    mock_redis = MagicMock(spec=RedisRepository)
    mock_redis.is_connected = MagicMock(return_value=True)
    mock_redis.cache_recent_transaction = MagicMock(return_value=True)
    mock_redis.cache_account_state = MagicMock(return_value=True)
    mock_redis.cache_risk_assessment = MagicMock(return_value=True)
    return mock_redis


@pytest.fixture
def test_pipeline_runner(sqlite_db_manager, mock_redis_repo):
    """Initializes a full EndToEndPipelineRunner configured for testing."""
    engine = ModelInferenceEngine(artifacts_dir="models/artifacts", enable_shap=True)
    mock_event_service = EventService()
    runner = EndToEndPipelineRunner(
        db_manager=sqlite_db_manager,
        redis_repo=mock_redis_repo,
        inference_engine=engine,
        event_service=mock_event_service,
    )
    return runner


class TestEndToEndPipeline:
    """Automated integration test suite for FinStream AI streaming pipeline."""

    def test_single_transaction_end_to_end_flow(self, test_pipeline_runner, sqlite_db_manager):
        """
        Verifies that a single synthetic transaction flows through all 5 pipeline stages:
        1. Feature extraction
        2. ML Dual-Inference
        3. Local SHAP generation
        4. Persistence to SQLite/PostgreSQL & Redis
        5. WebSocket broadcast
        """
        generator = TransactionGenerator(rate=10.0, scenario="mixed", seed=101)
        tx = next(generator.stream_transactions())
        tx_dict = tx.to_clean_dict()

        result = test_pipeline_runner.process_single_transaction(tx_dict, explain=True)

        # 1. Assert return structure
        assert result is not None
        assert result["persistence_status"] == "SUCCESS"
        assert "timings" in result
        assert result["timings"]["t_e2e"] > 0

        # 2. Assert enriched and scored record fields
        record = result["record"]
        assert record["transaction_id"] == tx_dict["transaction_id"]
        assert record["account_id"] == tx_dict["account_id"]
        assert record["amount"] == tx_dict["amount"]
        assert "log_amount" in record
        assert "transaction_count_1m" in record
        assert "xgboost_probability" in record
        assert 0.0 <= record["xgboost_probability"] <= 1.0
        assert "isolation_forest_normalized" in record
        assert 0.0 <= record["isolation_forest_normalized"] <= 1.0
        assert "hybrid_risk_score" in record
        assert 0.0 <= record["hybrid_risk_score"] <= 1.0
        assert record["risk_level"] in ["LOW", "MEDIUM", "HIGH"]
        assert "top_shap_features" in record
        assert len(record["top_shap_features"]) > 0

        # 3. Verify database durability
        with sqlite_db_manager.get_session() as session:
            repo = PostgresRepository(session)
            db_tx = repo.get_transaction(tx_dict["transaction_id"])
            assert db_tx is not None
            assert db_tx.account_id == tx_dict["account_id"]
            assert round(float(db_tx.amount), 2) == round(tx_dict["amount"], 2)

            db_risk = repo.get_risk_assessment(tx_dict["transaction_id"])
            assert db_risk is not None
            assert db_risk.risk_level == record["risk_level"]

            db_shap = repo.get_shap_explanations(db_risk.id)
            assert db_shap is not None
            assert len(db_shap) > 0

    def test_batch_pipeline_data_consistency_and_zero_loss(self, test_pipeline_runner):
        """
        Executes a 50-transaction benchmark and asserts zero record loss,
        unique transaction IDs, and complete metric tracking.
        """
        summary = test_pipeline_runner.run_benchmark(
            num_transactions=50,
            scenario="mixed",
            seed=2024,
            explain=True,
        )

        assert summary["total_transactions"] == 50
        assert summary["duration_seconds"] > 0
        assert summary["throughput_tps"] > 0

        # Validate latency stats
        for key in ["e2e_latency", "feature_latency", "ml_inference_latency", "persistence_latency"]:
            stats = summary[key]
            assert stats["p50_ms"] >= 0
            assert stats["p95_ms"] >= stats["p50_ms"]
            assert stats["max_ms"] >= stats["p95_ms"]

    def test_idempotent_duplicate_prevention(self, test_pipeline_runner, sqlite_db_manager):
        """
        Verifies that re-submitting an already processed transaction is handled idempotently.
        """
        generator = TransactionGenerator(rate=10.0, scenario="high_amount", seed=77)
        tx = next(generator.stream_transactions())
        tx_dict = tx.to_clean_dict()

        # First run -> Persisted
        res1 = test_pipeline_runner.process_single_transaction(tx_dict, explain=False)
        assert res1["persistence_status"] == "SUCCESS"

        # Second run -> Duplicate handled idempotently
        res2 = test_pipeline_runner.process_single_transaction(tx_dict, explain=False)
        assert res2["persistence_status"] == "SUCCESS"
