"""
FinStream AI - PostgreSQL Repositories
Data access abstraction layer for Transactions, Risk Assessments, and SHAP Explanations.
"""

from datetime import datetime, timezone
from decimal import Decimal
import logging
from typing import Any, Dict, List, Optional
from sqlalchemy import desc, select
from sqlalchemy.orm import Session, joinedload

from database.models import (
    RiskAssessmentModel,
    ShapExplanationModel,
    TransactionModel,
)

logger = logging.getLogger("postgres_repository")


class PostgresRepository:
    """
    Repository providing clean CRUD and query operations for PostgreSQL.
    Accepts an active SQLAlchemy Session.
    """

    def __init__(self, session: Session):
        self.session = session

    def save_transaction(self, tx_data: Dict[str, Any]) -> TransactionModel:
        """
        Saves a transaction record idempotently.
        If transaction_id already exists, returns the existing record.
        """
        tx_id = str(tx_data["transaction_id"])
        existing = self.get_transaction(tx_id)
        if existing:
            logger.debug("Transaction %s already exists in database (idempotent no-op)", tx_id)
            return existing

        # Parse timestamp safely
        ts = tx_data.get("timestamp")
        if isinstance(ts, str):
            ts_dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        elif isinstance(ts, datetime):
            ts_dt = ts
        else:
            ts_dt = datetime.now(timezone.utc)

        amount_val = Decimal(str(tx_data.get("amount", 0.0)))

        tx = TransactionModel(
            transaction_id=tx_id,
            timestamp=ts_dt,
            account_id=str(tx_data.get("account_id", "")),
            amount=amount_val,
            currency=str(tx_data.get("currency", "INR")),
            merchant_id=str(tx_data.get("merchant_id", "")),
            merchant_category=str(tx_data.get("merchant_category", "")),
            city=str(tx_data.get("city", "")),
            device_id=str(tx_data.get("device_id", "")),
            channel=str(tx_data.get("channel", "UPI")),
            card_present=bool(tx_data.get("card_present", True)),
            transaction_type=str(tx_data.get("transaction_type", "PURCHASE")),
            scenario_label=str(tx_data.get("scenario_label", "NORMAL")),
        )
        self.session.add(tx)
        self.session.flush()
        logger.info("Persisted transaction %s for account %s", tx_id, tx.account_id)
        return tx

    def save_risk_assessment(self, risk_data: Dict[str, Any]) -> RiskAssessmentModel:
        """
        Saves or updates a risk assessment record linked to transaction_id.
        """
        tx_id = str(risk_data["transaction_id"])
        existing = self.get_risk_assessment(tx_id)
        if existing:
            # Update existing assessment
            existing.xgboost_probability = float(risk_data["xgboost_probability"])
            existing.isolation_forest_score = float(risk_data["isolation_forest_score"])
            existing.isolation_forest_normalized = float(risk_data["isolation_forest_normalized"])
            existing.hybrid_risk_score = float(risk_data["hybrid_risk_score"])
            existing.risk_level = str(risk_data["risk_level"])
            self.session.flush()
            logger.info("Updated risk assessment for transaction %s (Level: %s)", tx_id, existing.risk_level)
            return existing

        assessment = RiskAssessmentModel(
            transaction_id=tx_id,
            xgboost_probability=float(risk_data["xgboost_probability"]),
            isolation_forest_score=float(risk_data["isolation_forest_score"]),
            isolation_forest_normalized=float(risk_data["isolation_forest_normalized"]),
            hybrid_risk_score=float(risk_data["hybrid_risk_score"]),
            risk_level=str(risk_data["risk_level"]),
        )
        self.session.add(assessment)
        self.session.flush()
        logger.info(
            "Persisted risk assessment for transaction %s (Score: %.4f, Level: %s)",
            tx_id,
            assessment.hybrid_risk_score,
            assessment.risk_level,
        )
        return assessment

    def save_shap_explanations(
        self,
        risk_assessment_id: int,
        shap_list: List[Dict[str, Any]],
    ) -> List[ShapExplanationModel]:
        """
        Saves ranked SHAP feature attribution explanations for a risk assessment.
        """
        if not shap_list:
            return []

        explanations: List[ShapExplanationModel] = []
        for idx, item in enumerate(shap_list, start=1):
            feature_name = str(item.get("feature", item.get("feature_name", "")))
            feat_val = float(item.get("feature_value", 0.0))
            shap_val = float(item.get("shap_value", 0.0))
            abs_shap = float(item.get("absolute_shap_value", abs(shap_val)))
            direction = str(item.get("direction", "neutral"))
            rank_val = int(item.get("rank", idx))

            explanation = ShapExplanationModel(
                risk_assessment_id=risk_assessment_id,
                feature_name=feature_name,
                feature_value=feat_val,
                shap_value=shap_val,
                absolute_shap_value=abs_shap,
                direction=direction,
                rank=rank_val,
            )
            self.session.add(explanation)
            explanations.append(explanation)

        self.session.flush()
        logger.debug("Persisted %d SHAP explanations for assessment ID %d", len(explanations), risk_assessment_id)
        return explanations

    def get_transaction(self, transaction_id: str) -> Optional[TransactionModel]:
        """Retrieves a single transaction by unique transaction_id."""
        stmt = select(TransactionModel).where(TransactionModel.transaction_id == transaction_id)
        return self.session.execute(stmt).scalars().first()

    def get_risk_assessment(
        self,
        transaction_id: str,
        with_shap: bool = True,
    ) -> Optional[RiskAssessmentModel]:
        """Retrieves a risk assessment by transaction_id with optional eagerly loaded SHAP explanations."""
        stmt = select(RiskAssessmentModel).where(RiskAssessmentModel.transaction_id == transaction_id)
        if with_shap:
            stmt = stmt.options(joinedload(RiskAssessmentModel.shap_explanations))
        return self.session.execute(stmt).unique().scalars().first()

    def get_recent_transactions(
        self,
        limit: int = 50,
        offset: int = 0,
        account_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[TransactionModel]:
        """Retrieves transactions ordered by event timestamp descending with pagination and filters."""
        stmt = select(TransactionModel)
        if account_id:
            stmt = stmt.where(TransactionModel.account_id == account_id)
        if start_time:
            stmt = stmt.where(TransactionModel.timestamp >= start_time)
        if end_time:
            stmt = stmt.where(TransactionModel.timestamp <= end_time)
        stmt = stmt.order_by(desc(TransactionModel.timestamp)).offset(offset).limit(limit)
        return list(self.session.execute(stmt).scalars().all())

    def count_transactions(
        self,
        account_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> int:
        """Returns total count of transactions matching filter criteria."""
        from sqlalchemy import func
        stmt = select(func.count(TransactionModel.id))
        if account_id:
            stmt = stmt.where(TransactionModel.account_id == account_id)
        if start_time:
            stmt = stmt.where(TransactionModel.timestamp >= start_time)
        if end_time:
            stmt = stmt.where(TransactionModel.timestamp <= end_time)
        return int(self.session.execute(stmt).scalar() or 0)

    def get_recent_risk_assessments(
        self,
        limit: int = 50,
        offset: int = 0,
        risk_level: Optional[str] = None,
        account_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        with_shap: bool = True,
    ) -> List[RiskAssessmentModel]:
        """Retrieves most recent risk assessments, optionally filtered by risk level, account, or time range."""
        stmt = select(RiskAssessmentModel)
        if account_id or start_time or end_time:
            stmt = stmt.join(RiskAssessmentModel.transaction)
            if account_id:
                stmt = stmt.where(TransactionModel.account_id == account_id)
            if start_time:
                stmt = stmt.where(TransactionModel.timestamp >= start_time)
            if end_time:
                stmt = stmt.where(TransactionModel.timestamp <= end_time)
        if risk_level:
            stmt = stmt.where(RiskAssessmentModel.risk_level == risk_level.upper())
        if with_shap:
            stmt = stmt.options(joinedload(RiskAssessmentModel.shap_explanations))
        stmt = stmt.order_by(desc(RiskAssessmentModel.created_at)).offset(offset).limit(limit)
        return list(self.session.execute(stmt).unique().scalars().all())

    def count_risk_assessments(
        self,
        risk_level: Optional[str] = None,
        account_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> int:
        """Returns total count of risk assessments matching filter criteria."""
        from sqlalchemy import func
        stmt = select(func.count(RiskAssessmentModel.id))
        if account_id or start_time or end_time:
            stmt = stmt.join(RiskAssessmentModel.transaction)
            if account_id:
                stmt = stmt.where(TransactionModel.account_id == account_id)
            if start_time:
                stmt = stmt.where(TransactionModel.timestamp >= start_time)
            if end_time:
                stmt = stmt.where(TransactionModel.timestamp <= end_time)
        if risk_level:
            stmt = stmt.where(RiskAssessmentModel.risk_level == risk_level.upper())
        return int(self.session.execute(stmt).scalar() or 0)

    def get_latest_risk_for_account(
        self,
        account_id: str,
        with_shap: bool = True,
    ) -> Optional[RiskAssessmentModel]:
        """Retrieves the latest risk assessment for an account by joining transactions."""
        stmt = (
            select(RiskAssessmentModel)
            .join(RiskAssessmentModel.transaction)
            .where(TransactionModel.account_id == account_id)
            .order_by(desc(TransactionModel.timestamp))
        )
        if with_shap:
            stmt = stmt.options(joinedload(RiskAssessmentModel.shap_explanations))
        return self.session.execute(stmt).unique().scalars().first()

    def get_shap_explanations(self, risk_assessment_id: int) -> List[ShapExplanationModel]:
        """Retrieves SHAP explanations for a given risk assessment ID ordered by rank."""
        stmt = (
            select(ShapExplanationModel)
            .where(ShapExplanationModel.risk_assessment_id == risk_assessment_id)
            .order_by(ShapExplanationModel.rank)
        )
        return list(self.session.execute(stmt).scalars().all())
