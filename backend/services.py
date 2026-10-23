"""
FinStream AI - API Service Layer
Coordinates repository calls, fallback logic, and schema mappings for API routes.
"""

from datetime import datetime, timezone
import logging
import random
from typing import Any, Dict, List, Optional

from backend.exceptions import ResourceNotFoundException, ValidationException
from backend.schemas import (
    AccountRiskResponse,
    DashboardStatsResponse,
    DependencyHealthResponse,
    HealthResponse,
    PaginatedRiskResponse,
    PaginatedTransactionResponse,
    RiskAssessmentResponse,
    SHAPExplanationResponse,
    SimulateRequest,
    SimulateResponse,
    TransactionDetailResponse,
    TransactionResponse,
)
from database.connection import DatabaseManager
from database.redis_client import RedisRepository
from database.repositories import PostgresRepository

logger = logging.getLogger("api_service")

_shared_pipeline_runner = None
_shared_scenario_gen = None


class ApiService:
    """
    Service layer providing business logic for the REST API.
    Interacts with PostgresRepository and RedisRepository without raw SQL in routes.
    """

    def __init__(
        self,
        postgres_repo: PostgresRepository,
        redis_repo: RedisRepository,
        db_manager: Optional[DatabaseManager] = None,
    ):
        self.pg_repo = postgres_repo
        self.redis_repo = redis_repo
        self.db_manager = db_manager

    def get_health(self) -> HealthResponse:
        """Returns API basic health."""
        return HealthResponse()

    def get_dependencies_health(self) -> DependencyHealthResponse:
        """Checks connectivity of backing PostgreSQL and Redis services."""
        pg_ok = False
        if self.db_manager is not None:
            pg_ok = self.db_manager.check_connection()
        else:
            try:
                # Test query via repo session
                self.pg_repo.session.execute(
                    pytest_import_text("SELECT 1") if False else __import__("sqlalchemy").text("SELECT 1")
                )
                pg_ok = True
            except Exception:
                pg_ok = False

        redis_ok = self.redis_repo.is_available()

        return DependencyHealthResponse(
            api="ok",
            postgresql="available" if pg_ok else "unavailable",
            redis="available" if redis_ok else "unavailable",
            details={
                "postgresql_connected": pg_ok,
                "redis_connected": redis_ok,
            },
        )

    def get_transactions(
        self,
        limit: int = 50,
        offset: int = 0,
        account_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> PaginatedTransactionResponse:
        """Retrieves paginated transactions with optional filters."""
        if start_time and end_time and start_time > end_time:
            raise ValidationException("start_time must be less than or equal to end_time")

        tx_models = self.pg_repo.get_recent_transactions(
            limit=limit,
            offset=offset,
            account_id=account_id,
            start_time=start_time,
            end_time=end_time,
        )
        total_count = self.pg_repo.count_transactions(
            account_id=account_id,
            start_time=start_time,
            end_time=end_time,
        )

        items = [TransactionResponse.model_validate(tx.to_dict()) for tx in tx_models]
        return PaginatedTransactionResponse(
            items=items,
            total=total_count,
            limit=limit,
            offset=offset,
        )

    def get_transaction_detail(self, transaction_id: str) -> TransactionDetailResponse:
        """Retrieves comprehensive transaction detail with risk score and SHAP attributions."""
        tx_model = self.pg_repo.get_transaction(transaction_id)
        if not tx_model:
            raise ResourceNotFoundException("Transaction", transaction_id)

        tx_res = TransactionResponse.model_validate(tx_model.to_dict())

        risk_model = self.pg_repo.get_risk_assessment(transaction_id, with_shap=True)
        risk_res: Optional[RiskAssessmentResponse] = None
        explanations: List[SHAPExplanationResponse] = []

        if risk_model:
            risk_dict = risk_model.to_dict(include_shap=False)
            risk_res = RiskAssessmentResponse.model_validate(risk_dict)
            if risk_model.shap_explanations:
                explanations = [
                    SHAPExplanationResponse.model_validate(exp.to_dict())
                    for exp in risk_model.shap_explanations
                ]

        return TransactionDetailResponse(
            transaction=tx_res,
            risk=risk_res,
            explanations=explanations,
        )

    def get_risk_assessments(
        self,
        limit: int = 50,
        offset: int = 0,
        risk_level: Optional[str] = None,
        account_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> PaginatedRiskResponse:
        """Retrieves paginated risk assessments filtered by level, account, or time range."""
        if start_time and end_time and start_time > end_time:
            raise ValidationException("start_time must be less than or equal to end_time")

        if risk_level and risk_level.upper() not in {"LOW", "MEDIUM", "HIGH"}:
            raise ValidationException(f"Invalid risk_level '{risk_level}'. Must be LOW, MEDIUM, or HIGH.")

        risk_models = self.pg_repo.get_recent_risk_assessments(
            limit=limit,
            offset=offset,
            risk_level=risk_level,
            account_id=account_id,
            start_time=start_time,
            end_time=end_time,
            with_shap=True,
        )
        total_count = self.pg_repo.count_risk_assessments(
            risk_level=risk_level,
            account_id=account_id,
            start_time=start_time,
            end_time=end_time,
        )

        items = [
            RiskAssessmentResponse.model_validate(r.to_dict(include_shap=True))
            for r in risk_models
        ]
        return PaginatedRiskResponse(
            items=items,
            total=total_count,
            limit=limit,
            offset=offset,
        )

    def get_risk_for_transaction(self, transaction_id: str) -> RiskAssessmentResponse:
        """Retrieves risk assessment for a specific transaction ID."""
        risk_model = self.pg_repo.get_risk_assessment(transaction_id, with_shap=True)
        if not risk_model:
            raise ResourceNotFoundException("RiskAssessment", transaction_id)
        return RiskAssessmentResponse.model_validate(risk_model.to_dict(include_shap=True))

    def get_shap_for_transaction(self, transaction_id: str) -> List[SHAPExplanationResponse]:
        """Retrieves SHAP explanations for a transaction ID."""
        risk_model = self.pg_repo.get_risk_assessment(transaction_id, with_shap=True)
        if not risk_model:
            raise ResourceNotFoundException("RiskAssessment", transaction_id)
        return [
            SHAPExplanationResponse.model_validate(exp.to_dict())
            for exp in risk_model.shap_explanations
        ]

    def get_account_risk(self, account_id: str) -> AccountRiskResponse:
        """
        Retrieves current risk status for an account.
        Checks Redis hot cache first; falls back to PostgreSQL if cache miss.
        """
        # 1. Try Redis Hot Cache
        try:
            cached = self.redis_repo.get_account_latest_risk(account_id)
            if cached:
                return AccountRiskResponse(
                    account_id=account_id,
                    transaction_id=cached.get("transaction_id"),
                    amount=cached.get("amount"),
                    hybrid_risk_score=float(cached.get("hybrid_risk_score", 0.0)),
                    risk_level=str(cached.get("risk_level", "LOW")),
                    xgboost_probability=cached.get("xgboost_probability"),
                    isolation_forest_normalized=cached.get("isolation_forest_normalized"),
                    source="redis_hot_state",
                    timestamp=cached.get("timestamp"),
                )
        except Exception as exc:
            logger.warning("Redis lookup failed for account %s: %s", account_id, exc)

        # 2. PostgreSQL Fallback
        latest_risk = self.pg_repo.get_latest_risk_for_account(account_id)
        if latest_risk:
            return AccountRiskResponse(
                account_id=account_id,
                transaction_id=latest_risk.transaction_id,
                amount=float(latest_risk.transaction.amount) if latest_risk.transaction else None,
                hybrid_risk_score=float(latest_risk.hybrid_risk_score),
                risk_level=latest_risk.risk_level,
                xgboost_probability=float(latest_risk.xgboost_probability),
                isolation_forest_normalized=float(latest_risk.isolation_forest_normalized),
                source="postgres_fallback",
                timestamp=latest_risk.created_at.isoformat() if latest_risk.created_at else None,
            )

        raise ResourceNotFoundException("Account", account_id)

    def get_account_transactions(
        self,
        account_id: str,
        limit: int = 50,
        offset: int = 0,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> PaginatedTransactionResponse:
        """Retrieves transaction history for a specific account."""
        return self.get_transactions(
            limit=limit,
            offset=offset,
            account_id=account_id,
            start_time=start_time,
            end_time=end_time,
        )

    def get_dashboard_stats(self) -> DashboardStatsResponse:
        """Returns aggregated dashboard KPI counters and recent transactions with risk data."""
        total = self.pg_repo.count_transactions()
        low = self.pg_repo.count_risk_assessments(risk_level="LOW")
        med = self.pg_repo.count_risk_assessments(risk_level="MEDIUM")
        high = self.pg_repo.count_risk_assessments(risk_level="HIGH")

        recent_risks = self.pg_repo.get_recent_risk_assessments(limit=25, with_shap=True)
        recent_list = []
        score_sum = 0.0
        for r in recent_risks:
            score_sum += float(r.hybrid_risk_score)
            tx = r.transaction
            tx_source = getattr(tx, "source", None) or ("LIVE_STREAM" if "LIVE" in r.transaction_id else "SIMULATED")
            tx_info = {
                "transaction_id": r.transaction_id,
                "amount": float(tx.amount) if tx else 0.0,
                "account_id": tx.account_id if tx else "N/A",
                "merchant_category": tx.merchant_category if tx else "N/A",
                "city": tx.city if tx else "N/A",
                "channel": tx.channel if tx else "UPI",
                "timestamp": tx.timestamp.isoformat() if tx and tx.timestamp else (r.created_at.isoformat() if r.created_at else ""),
                "hybrid_risk_score": round(float(r.hybrid_risk_score), 4),
                "risk_level": r.risk_level,
                "xgboost_probability": round(float(r.xgboost_probability), 4),
                "isolation_forest_normalized": round(float(r.isolation_forest_normalized), 4),
                "top_shap_features": [exp.to_dict() for exp in r.shap_explanations] if r.shap_explanations else [],
                "source": tx_source,
            }
            recent_list.append(tx_info)

        avg_score = round(score_sum / len(recent_risks), 4) if recent_risks else 0.0

        return DashboardStatsResponse(
            total_transactions=total,
            low_risk_count=low,
            medium_risk_count=med,
            high_risk_count=high,
            avg_risk_score=avg_score,
            recent_transactions=recent_list,
        )

    def simulate_transaction(self, req: SimulateRequest) -> SimulateResponse:
        """
        Executes a simulated transaction through the full end-to-end pipeline:
        Feature Extraction -> Dual ML (XGBoost + Isolation Forest) -> SHAP -> Persistence -> WebSocket.
        """
        from features.feature_definitions import ALL_ENGINEERED_FEATURE_COLUMNS
        from producer.account_profiles import AccountPool
        from producer.scenario_generator import ScenarioGenerator
        from streaming.pipeline_runner import EndToEndPipelineRunner

        global _shared_pipeline_runner, _shared_scenario_gen
        if _shared_scenario_gen is None:
            pool = AccountPool(size=25, seed=random.randint(1, 99999))
            _shared_scenario_gen = ScenarioGenerator(account_pool=pool)
        self._scenario_gen = _shared_scenario_gen

        scenario = (req.scenario or "normal").lower()
        if _shared_pipeline_runner is None or _shared_pipeline_runner.db_manager != self.db_manager:
            _shared_pipeline_runner = EndToEndPipelineRunner(db_manager=self.db_manager, redis_repo=self.redis_repo)
        runner = _shared_pipeline_runner

        if scenario == "normal":
            tx = self._scenario_gen.generate_normal()
            tx_dict = tx.to_clean_dict()
        elif scenario == "high_amount":
            tx = self._scenario_gen.generate_high_amount()
            tx_dict = tx.to_clean_dict()
        elif scenario == "velocity_spike":
            burst = self._scenario_gen.generate_velocity_spike(count=6)
            for b_tx in burst[:-1]:
                runner.process_single_transaction(b_tx.to_clean_dict(), explain=False)
            tx = burst[-1]
            tx_dict = tx.to_clean_dict()
        elif scenario == "high_risk":
            tx = self._scenario_gen.generate_high_amount()
            tx_dict = tx.to_clean_dict()
            tx_dict["amount"] = max(tx_dict.get("amount", 85000.0), 175000.0)
            tx_dict["device_id"] = f"DEV_ANOMALY_{random.randint(1000, 9999)}"
            tx_dict["merchant_category"] = "LUXURY"
            tx_dict["channel"] = "ONLINE"
            tx_dict["scenario_label"] = "HIGH_RISK_ANOMALY"
        elif scenario == "custom":
            acc_id = req.account_id or f"ACC{random.randint(1, 50):04d}"
            amount = float(req.amount or 1500.0)
            now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            tx_id = f"TX{random.randint(100000, 999999)}"
            cat = req.merchant_category or "GROCERY"
            city = req.city or "Mumbai"
            channel = req.channel or "UPI"
            device_id = req.device_id or f"DEV_{acc_id[-4:]}"
            tx_dict = {
                "transaction_id": tx_id,
                "timestamp": now_iso,
                "account_id": acc_id,
                "amount": amount,
                "currency": "INR",
                "merchant_id": f"MER_{cat[:4]}_{random.randint(10, 99)}",
                "merchant_category": cat,
                "city": city,
                "device_id": device_id,
                "channel": channel,
                "card_present": channel in ["POS", "ATM"],
                "transaction_type": req.transaction_type or ("WITHDRAWAL" if channel == "ATM" else "PURCHASE"),
                "scenario_label": "CUSTOM",
            }
        else:
            tx = self._scenario_gen.generate_normal()
            tx_dict = tx.to_clean_dict()

        # Ensure fresh unique transaction ID so each simulation creates a distinct record
        import time as _pytime
        unique_suffix = f"{int(_pytime.time() * 1000) % 1000000:06d}{random.randint(10, 99)}"
        tx_dict["transaction_id"] = f"TX{unique_suffix}"

        if req.amount is not None:
            tx_dict["amount"] = float(req.amount)
        if req.account_id:
            tx_dict["account_id"] = req.account_id
        if req.city:
            tx_dict["city"] = req.city
        if req.channel:
            tx_dict["channel"] = req.channel

        result = runner.process_single_transaction(tx_dict, explain=True)
        rec = result["record"]

        feat_dict = {k: rec.get(k) for k in ALL_ENGINEERED_FEATURE_COLUMNS if k in rec}

        return SimulateResponse(
            transaction_id=str(rec.get("transaction_id")),
            account_id=str(rec.get("account_id")),
            amount=float(rec.get("amount", 0.0)),
            currency=str(rec.get("currency", "INR")),
            merchant_id=str(rec.get("merchant_id", "")),
            merchant_category=str(rec.get("merchant_category", "")),
            city=str(rec.get("city", "")),
            device_id=str(rec.get("device_id", "")),
            channel=str(rec.get("channel", "")),
            card_present=bool(rec.get("card_present", True)),
            transaction_type=str(rec.get("transaction_type", "PURCHASE")),
            scenario_label=str(rec.get("scenario_label", "NORMAL")),
            timestamp=str(rec.get("timestamp")),
            hybrid_risk_score=float(rec.get("hybrid_risk_score", 0.0)),
            risk_level=str(rec.get("risk_level", "LOW")),
            xgboost_probability=float(rec.get("xgboost_probability", 0.0)),
            isolation_forest_normalized=float(rec.get("isolation_forest_normalized", 0.0)),
            isolation_forest_score=float(rec.get("isolation_forest_score", 0.0)),
            top_shap_features=rec.get("top_shap_features", []),
            features=feat_dict,
            persistence_status=result.get("persistence_status"),
            timings=result.get("timings", {}),
        )
