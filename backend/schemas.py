"""
FinStream AI - API Schemas
Pydantic response and query models defining the public REST API contracts.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class TransactionResponse(BaseModel):
    """Public representation of a financial transaction."""

    transaction_id: str = Field(..., description="Unique synthetic transaction ID")
    timestamp: datetime = Field(..., description="Event timestamp (UTC)")
    account_id: str = Field(..., description="Account identifier")
    amount: float = Field(..., description="Transaction amount")
    currency: str = Field(default="INR", description="Currency code")
    merchant_id: str = Field(..., description="Merchant identifier")
    merchant_category: str = Field(..., description="Merchant vertical")
    city: str = Field(..., description="Transaction location")
    device_id: str = Field(..., description="Device ID")
    channel: str = Field(..., description="Payment channel (UPI, POS, NET_BANKING, etc.)")
    card_present: bool = Field(default=True, description="Physical card presence flag")
    transaction_type: str = Field(default="PURCHASE", description="Transaction classification")
    scenario_label: str = Field(default="NORMAL", description="Synthetic scenario label")
    created_at: Optional[datetime] = Field(None, description="Database record insertion time")

    model_config = {"from_attributes": True}


class SHAPExplanationResponse(BaseModel):
    """Local SHAP feature attribution contribution item."""

    feature: str = Field(..., description="Feature name from the 23-feature space")
    feature_value: float = Field(..., description="Observed numerical value for this transaction")
    shap_value: float = Field(..., description="Raw SHAP contribution value (log-odds impact)")
    absolute_shap_value: float = Field(..., description="Absolute magnitude of contribution")
    direction: str = Field(
        ...,
        description="Directional impact: increases_anomaly, decreases_anomaly, or neutral",
    )
    rank: int = Field(..., description="Importance rank (1 = top contributor)")

    model_config = {"from_attributes": True}


class RiskAssessmentResponse(BaseModel):
    """Public representation of ML risk evaluation and anomaly metrics."""

    transaction_id: str = Field(..., description="Linked transaction ID")
    xgboost_probability: float = Field(
        ..., description="Supervised XGBoost anomaly probability in [0, 1]"
    )
    isolation_forest_score: float = Field(
        ..., description="Raw unsupervised Isolation Forest inverted decision score"
    )
    isolation_forest_normalized: float = Field(
        ..., description="Normalized Isolation Forest anomaly score in [0, 1]"
    )
    hybrid_risk_score: float = Field(
        ..., description="Weighted hybrid risk score in [0, 1]"
    )
    risk_level: str = Field(
        ..., description="Categorical risk level: LOW, MEDIUM, or HIGH"
    )
    created_at: Optional[datetime] = Field(None, description="Evaluation timestamp")
    top_shap_features: Optional[List[SHAPExplanationResponse]] = Field(
        default=None, description="Top ranked SHAP explanations if available"
    )

    model_config = {"from_attributes": True}


class TransactionDetailResponse(BaseModel):
    """Comprehensive single-transaction view including transaction data, risk score, and SHAP."""

    transaction: TransactionResponse = Field(..., description="Transaction event data")
    risk: Optional[RiskAssessmentResponse] = Field(
        None, description="Risk assessment metrics if evaluated"
    )
    explanations: List[SHAPExplanationResponse] = Field(
        default_factory=list, description="Ranked SHAP explanation items"
    )


class AccountRiskResponse(BaseModel):
    """Current/latest risk posture snapshot for a financial account."""

    account_id: str = Field(..., description="Account identifier")
    transaction_id: Optional[str] = Field(None, description="Latest transaction ID")
    amount: Optional[float] = Field(None, description="Latest transaction amount")
    hybrid_risk_score: float = Field(..., description="Latest hybrid risk score in [0, 1]")
    risk_level: str = Field(..., description="Latest risk level: LOW, MEDIUM, or HIGH")
    xgboost_probability: Optional[float] = Field(None, description="XGBoost probability")
    isolation_forest_normalized: Optional[float] = Field(
        None, description="Normalized Isolation Forest score"
    )
    source: str = Field(
        default="cache", description="Data origin: 'redis_hot_state' or 'postgres_fallback'"
    )
    timestamp: Optional[str] = Field(None, description="Snapshot timestamp")


class PaginatedTransactionResponse(BaseModel):
    """Paginated list of transactions with metadata."""

    items: List[TransactionResponse] = Field(..., description="Transaction records")
    total: int = Field(..., description="Total matching records count")
    limit: int = Field(..., description="Page size limit")
    offset: int = Field(..., description="Page offset")


class PaginatedRiskResponse(BaseModel):
    """Paginated list of risk assessments with metadata."""

    items: List[RiskAssessmentResponse] = Field(..., description="Risk assessment records")
    total: int = Field(..., description="Total matching records count")
    limit: int = Field(..., description="Page size limit")
    offset: int = Field(..., description="Page offset")


class HealthResponse(BaseModel):
    """Basic API application health report."""

    status: str = Field(default="ok", description="Application status")
    service: str = Field(default="finstream-api", description="Service identifier")
    version: str = Field(default="1.0.0", description="API version")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Health check timestamp (UTC)",
    )


class DependencyHealthResponse(BaseModel):
    """Detailed dependency infrastructure health report."""

    api: str = Field(default="ok", description="API service status")
    postgresql: str = Field(..., description="PostgreSQL database status: 'available' or 'unavailable'")
    redis: str = Field(..., description="Redis cache status: 'available' or 'unavailable'")
    details: Dict[str, Any] = Field(default_factory=dict, description="Diagnostic details")


class ErrorResponse(BaseModel):
    """Standardized API error response."""

    error: str = Field(..., description="Error classification slug")
    message: str = Field(..., description="Human-readable error description")
    detail: Optional[str] = Field(None, description="Extended error context if applicable")


class SimulateRequest(BaseModel):
    """Payload to simulate a synthetic or custom financial transaction."""

    scenario: str = Field(
        default="normal",
        description="Scenario type: normal, high_amount, velocity_spike, high_risk, custom",
    )
    account_id: Optional[str] = Field(default=None, description="Optional account identifier")
    amount: Optional[float] = Field(default=None, description="Optional custom transaction amount")
    merchant_category: Optional[str] = Field(default=None, description="Optional merchant vertical")
    city: Optional[str] = Field(default=None, description="Optional city location")
    channel: Optional[str] = Field(default=None, description="Payment channel (UPI, POS, ONLINE, ATM)")
    device_id: Optional[str] = Field(default=None, description="Optional device identifier")
    card_present: Optional[bool] = Field(default=None, description="Card present flag")
    transaction_type: Optional[str] = Field(default=None, description="Transaction type")


class SimulateResponse(BaseModel):
    """Evaluation output for a simulated transaction."""

    transaction_id: str
    account_id: str
    amount: float
    currency: str = "INR"
    merchant_id: Optional[str] = None
    merchant_category: Optional[str] = None
    city: Optional[str] = None
    device_id: Optional[str] = None
    channel: Optional[str] = None
    card_present: bool = True
    transaction_type: str = "PURCHASE"
    scenario_label: str
    timestamp: str
    hybrid_risk_score: float
    risk_level: str
    xgboost_probability: float
    isolation_forest_normalized: float
    isolation_forest_score: float
    top_shap_features: List[Dict[str, Any]] = Field(default_factory=list)
    features: Dict[str, Any] = Field(default_factory=dict)
    persistence_status: Optional[str] = None
    timings: Dict[str, float] = Field(default_factory=dict)


class DashboardStatsResponse(BaseModel):
    """Aggregated metrics and recent transactions for dashboard display."""

    total_transactions: int
    low_risk_count: int
    medium_risk_count: int
    high_risk_count: int
    avg_risk_score: float
    recent_transactions: List[Dict[str, Any]] = Field(default_factory=list)

