"""
FinStream AI - Risk Assessment & SHAP Explainability Routes
"""

from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, Path, Query

from backend.dependencies import get_api_service
from backend.schemas import (
    ErrorResponse,
    PaginatedRiskResponse,
    RiskAssessmentResponse,
    SHAPExplanationResponse,
)
from backend.services import ApiService

router = APIRouter(prefix="/risks", tags=["Risk Intelligence"])


@router.get(
    "",
    response_model=PaginatedRiskResponse,
    summary="List Risk Assessments",
    description="Retrieves evaluated anomaly risk records with filtering by risk tier (LOW/MEDIUM/HIGH), account, and time range.",
)
def list_risk_assessments(
    limit: int = Query(default=50, ge=1, le=100, description="Page limit (1-100)"),
    offset: int = Query(default=0, ge=0, description="Page offset"),
    risk_level: Optional[str] = Query(default=None, description="Risk tier filter: LOW, MEDIUM, or HIGH"),
    account_id: Optional[str] = Query(default=None, description="Filter by account ID"),
    start_time: Optional[datetime] = Query(default=None, description="Filter records >= start_time (ISO 8601 UTC)"),
    end_time: Optional[datetime] = Query(default=None, description="Filter records <= end_time (ISO 8601 UTC)"),
    service: ApiService = Depends(get_api_service),
) -> PaginatedRiskResponse:
    """List risk assessments endpoint."""
    return service.get_risk_assessments(
        limit=limit,
        offset=offset,
        risk_level=risk_level,
        account_id=account_id,
        start_time=start_time,
        end_time=end_time,
    )


@router.get(
    "/{transaction_id}",
    response_model=RiskAssessmentResponse,
    responses={404: {"model": ErrorResponse, "description": "Risk assessment not found"}},
    summary="Get Risk Assessment for Transaction",
    description="Retrieves the supervised XGBoost probability, Isolation Forest score, and combined hybrid risk level for a transaction.",
)
def get_risk_assessment(
    transaction_id: str = Path(..., description="Unique transaction ID"),
    service: ApiService = Depends(get_api_service),
) -> RiskAssessmentResponse:
    """Single risk assessment lookup endpoint."""
    return service.get_risk_for_transaction(transaction_id=transaction_id)


@router.get(
    "/{transaction_id}/explanations",
    response_model=List[SHAPExplanationResponse],
    responses={404: {"model": ErrorResponse, "description": "Risk assessment not found"}},
    summary="Get SHAP Feature Explanations",
    description="Returns the top ranked local feature attribution factors and directional impact for a transaction.",
)
def get_shap_explanations(
    transaction_id: str = Path(..., description="Unique transaction ID"),
    service: ApiService = Depends(get_api_service),
) -> List[SHAPExplanationResponse]:
    """SHAP explanation breakdown endpoint."""
    return service.get_shap_for_transaction(transaction_id=transaction_id)
