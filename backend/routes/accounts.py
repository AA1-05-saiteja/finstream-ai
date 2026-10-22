"""
FinStream AI - Account Intelligence Routes
"""

from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, Path, Query

from backend.dependencies import get_api_service
from backend.schemas import (
    AccountRiskResponse,
    ErrorResponse,
    PaginatedTransactionResponse,
)
from backend.services import ApiService

router = APIRouter(prefix="/accounts", tags=["Account Intelligence"])


@router.get(
    "/{account_id}/risk",
    response_model=AccountRiskResponse,
    responses={404: {"model": ErrorResponse, "description": "Account not found"}},
    summary="Get Latest Account Risk",
    description="Fetches the current real-time risk posture for an account (Redis hot state with PostgreSQL fallback).",
)
def get_account_risk(
    account_id: str = Path(..., description="Synthetic account ID (e.g. ACC0042)"),
    service: ApiService = Depends(get_api_service),
) -> AccountRiskResponse:
    """Account latest risk evaluation endpoint."""
    return service.get_account_risk(account_id=account_id)


@router.get(
    "/{account_id}/transactions",
    response_model=PaginatedTransactionResponse,
    summary="Get Account Transactions",
    description="Retrieves transaction event history specifically associated with an account ID.",
)
def get_account_transactions(
    account_id: str = Path(..., description="Synthetic account ID"),
    limit: int = Query(default=50, ge=1, le=100, description="Page limit (1-100)"),
    offset: int = Query(default=0, ge=0, description="Page offset"),
    start_time: Optional[datetime] = Query(default=None, description="Filter >= start_time (ISO 8601 UTC)"),
    end_time: Optional[datetime] = Query(default=None, description="Filter <= end_time (ISO 8601 UTC)"),
    service: ApiService = Depends(get_api_service),
) -> PaginatedTransactionResponse:
    """Account transactions history endpoint."""
    return service.get_account_transactions(
        account_id=account_id,
        limit=limit,
        offset=offset,
        start_time=start_time,
        end_time=end_time,
    )
