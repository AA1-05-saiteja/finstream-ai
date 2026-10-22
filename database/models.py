"""
FinStream AI - Database Models
SQLAlchemy ORM models defining normalized relational tables for Transactions,
Risk Assessments, and SHAP Local Explanations.
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    func,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class TransactionModel(Base):
    """
    Core historical transaction model.
    Stores immutable event details for financial transactions.
    """

    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    transaction_id = Column(
        String(64), unique=True, nullable=False, index=True, doc="Unique synthetic transaction ID"
    )
    timestamp = Column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        doc="Transaction event-time timestamp",
    )
    account_id = Column(
        String(32), nullable=False, index=True, doc="Synthetic account identifier"
    )
    amount = Column(
        Numeric(14, 2), nullable=False, doc="Transaction amount in specified currency"
    )
    currency = Column(
        String(8), default="INR", nullable=False, doc="Currency code (e.g. INR)"
    )
    merchant_id = Column(
        String(32), nullable=False, doc="Synthetic merchant identifier"
    )
    merchant_category = Column(
        String(64), nullable=False, doc="Merchant category vertical"
    )
    city = Column(String(64), nullable=False, doc="Transaction city")
    device_id = Column(String(64), nullable=False, doc="Originating device identifier")
    channel = Column(
        String(32), nullable=False, doc="Payment channel (UPI, POS, NET_BANKING, etc.)"
    )
    card_present = Column(
        Boolean, default=True, nullable=False, doc="Whether physical card was present"
    )
    transaction_type = Column(
        String(32), default="PURCHASE", nullable=False, doc="Transaction type"
    )
    scenario_label = Column(
        String(64), default="NORMAL", nullable=False, doc="Synthetic scenario generator label"
    )
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        doc="Database record insertion timestamp",
    )

    # Relationships
    risk_assessment = relationship(
        "RiskAssessmentModel",
        back_populates="transaction",
        uselist=False,
        cascade="all, delete-orphan",
    )

    def to_dict(self) -> Dict[str, Any]:
        """Converts model instance to JSON-serializable dictionary."""
        return {
            "id": self.id,
            "transaction_id": self.transaction_id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "account_id": self.account_id,
            "amount": float(self.amount) if self.amount is not None else 0.0,
            "currency": self.currency,
            "merchant_id": self.merchant_id,
            "merchant_category": self.merchant_category,
            "city": self.city,
            "device_id": self.device_id,
            "channel": self.channel,
            "card_present": self.card_present,
            "transaction_type": self.transaction_type,
            "scenario_label": self.scenario_label,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class RiskAssessmentModel(Base):
    """
    Risk assessment evaluation model.
    Stores ML model predictions, unsupervised anomaly scores, and hybrid risk metrics.
    """

    __tablename__ = "risk_assessments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    transaction_id = Column(
        String(64),
        ForeignKey("transactions.transaction_id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
        doc="Foreign key reference to transactions.transaction_id",
    )
    xgboost_probability = Column(
        Float, nullable=False, doc="Supervised XGBoost anomaly probability in [0, 1]"
    )
    isolation_forest_score = Column(
        Float, nullable=False, doc="Raw unsupervised Isolation Forest inverted decision score"
    )
    isolation_forest_normalized = Column(
        Float, nullable=False, doc="Normalized Isolation Forest anomaly score in [0, 1]"
    )
    hybrid_risk_score = Column(
        Float, nullable=False, index=True, doc="Weighted hybrid risk score in [0, 1]"
    )
    risk_level = Column(
        String(16),
        nullable=False,
        index=True,
        doc="Categorical risk tier: LOW, MEDIUM, or HIGH",
    )
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        doc="Database evaluation record insertion timestamp",
    )

    # Relationships
    transaction = relationship("TransactionModel", back_populates="risk_assessment")
    shap_explanations = relationship(
        "ShapExplanationModel",
        back_populates="risk_assessment",
        cascade="all, delete-orphan",
        order_by="ShapExplanationModel.rank",
    )

    def to_dict(self, include_shap: bool = True) -> Dict[str, Any]:
        """Converts risk assessment instance to JSON-serializable dictionary."""
        data: Dict[str, Any] = {
            "id": self.id,
            "transaction_id": self.transaction_id,
            "xgboost_probability": round(float(self.xgboost_probability), 4),
            "isolation_forest_score": round(float(self.isolation_forest_score), 4),
            "isolation_forest_normalized": round(float(self.isolation_forest_normalized), 4),
            "hybrid_risk_score": round(float(self.hybrid_risk_score), 4),
            "risk_level": self.risk_level,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        if include_shap and self.shap_explanations:
            data["top_shap_features"] = [exp.to_dict() for exp in self.shap_explanations]
        return data


class ShapExplanationModel(Base):
    """
    SHAP local feature attribution model.
    Stores ranked feature-level contributions explaining why a transaction received its score.
    """

    __tablename__ = "shap_explanations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    risk_assessment_id = Column(
        Integer,
        ForeignKey("risk_assessments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Foreign key reference to risk_assessments.id",
    )
    feature_name = Column(
        String(64), nullable=False, doc="Feature name from the 23-feature space"
    )
    feature_value = Column(
        Float, nullable=False, doc="Observed value of the feature for this transaction"
    )
    shap_value = Column(
        Float, nullable=False, doc="Raw SHAP contribution value (log-odds impact)"
    )
    absolute_shap_value = Column(
        Float, nullable=False, doc="Absolute magnitude of the SHAP contribution"
    )
    direction = Column(
        String(32),
        nullable=False,
        doc="Directional impact: increases_anomaly, decreases_anomaly, or neutral",
    )
    rank = Column(
        Integer, nullable=False, doc="Rank order of importance (1 = top contributor)"
    )
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        doc="Record insertion timestamp",
    )

    # Relationships
    risk_assessment = relationship(
        "RiskAssessmentModel", back_populates="shap_explanations"
    )

    def to_dict(self) -> Dict[str, Any]:
        """Converts SHAP explanation instance to JSON-serializable dictionary."""
        return {
            "id": self.id,
            "feature": self.feature_name,
            "feature_value": round(float(self.feature_value), 4),
            "shap_value": round(float(self.shap_value), 4),
            "absolute_shap_value": round(float(self.absolute_shap_value), 4),
            "direction": self.direction,
            "rank": self.rank,
        }


# Composite Indexes for common dashboard query patterns
Index("idx_transactions_acc_time", TransactionModel.account_id, TransactionModel.timestamp.desc())
Index("idx_risk_level_created", RiskAssessmentModel.risk_level, RiskAssessmentModel.created_at.desc())
