"""
FinStream AI - Transactions API Routes
"""

from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, Path, Query

from backend.dependencies import get_api_service
from backend.schemas import (
    DashboardStatsResponse,
    ErrorResponse,
    PaginatedTransactionResponse,
    SimulateRequest,
    SimulateResponse,
    TransactionDetailResponse,
)
from backend.services import ApiService

router = APIRouter(prefix="/transactions", tags=["Transactions"])


@router.get(
    "/stats/summary",
    response_model=DashboardStatsResponse,
    summary="Get Dashboard Statistics",
    description="Retrieves live platform counters (Total, Low, Medium, High risk) and recent scored transactions.",
)
def get_dashboard_statistics(
    service: ApiService = Depends(get_api_service),
) -> DashboardStatsResponse:
    """Dashboard statistics and recent activity feed."""
    return service.get_dashboard_stats()


@router.post(
    "/simulate",
    response_model=SimulateResponse,
    summary="Simulate and Score Transaction",
    description="Simulates a synthetic scenario (normal, high_amount, velocity_spike, high_risk) or custom transaction through the live ML pipeline.",
)
def simulate_transaction(
    payload: SimulateRequest,
    service: ApiService = Depends(get_api_service),
) -> SimulateResponse:
    """Simulate and evaluate transaction endpoint."""
    return service.simulate_transaction(req=payload)



@router.get(
    "",
    response_model=PaginatedTransactionResponse,
    summary="List Transactions",
    description="Retrieves a paginated list of historical transactions with optional filtering.",
)
def list_transactions(
    limit: int = Query(default=50, ge=1, le=100, description="Page limit (1-100)"),
    offset: int = Query(default=0, ge=0, description="Page offset"),
    account_id: Optional[str] = Query(default=None, description="Filter by account ID"),
    start_time: Optional[datetime] = Query(default=None, description="Filter events >= start_time (ISO 8601 UTC)"),
    end_time: Optional[datetime] = Query(default=None, description="Filter events <= end_time (ISO 8601 UTC)"),
    service: ApiService = Depends(get_api_service),
) -> PaginatedTransactionResponse:
    """List transactions endpoint."""
    return service.get_transactions(
        limit=limit,
        offset=offset,
        account_id=account_id,
        start_time=start_time,
        end_time=end_time,
    )


@router.get(
    "/{transaction_id}",
    response_model=TransactionDetailResponse,
    responses={404: {"model": ErrorResponse, "description": "Transaction not found"}},
    summary="Get Transaction Details",
    description="Retrieves full transaction metadata, evaluated risk scores, and SHAP explainability attributions.",
)
def get_transaction(
    transaction_id: str = Path(..., description="Unique transaction ID (e.g. TX000001)"),
    service: ApiService = Depends(get_api_service),
) -> TransactionDetailResponse:
    """Single transaction lookup endpoint."""
    return service.get_transaction_detail(transaction_id=transaction_id)
