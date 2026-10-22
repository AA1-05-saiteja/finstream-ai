"""
FinStream AI - Health & Dependency Status Routes
"""

from fastapi import APIRouter, Depends

from backend.dependencies import get_db_manager_dep, get_redis_repo
from backend.schemas import DependencyHealthResponse, HealthResponse
from database.connection import DatabaseManager
from database.redis_client import RedisRepository

router = APIRouter(prefix="/health", tags=["System Health"])


@router.get(
    "",
    response_model=HealthResponse,
    summary="API Health Status",
    description="Returns the basic operational health status of the FinStream AI API.",
)
def get_health() -> HealthResponse:
    """Basic health check endpoint."""
    return HealthResponse()


@router.get(
    "/dependencies",
    response_model=DependencyHealthResponse,
    summary="Infrastructure Dependencies Health",
    description="Reports the live connectivity status of PostgreSQL and Redis backing services.",
)
def get_dependencies_health(
    db_mgr: DatabaseManager = Depends(get_db_manager_dep),
    redis_repo: RedisRepository = Depends(get_redis_repo),
) -> DependencyHealthResponse:
    """Dependency-aware infrastructure health check endpoint."""
    pg_ok = db_mgr.check_connection()
    redis_ok = redis_repo.is_available()
    return DependencyHealthResponse(
        api="ok",
        postgresql="available" if pg_ok else "unavailable",
        redis="available" if redis_ok else "unavailable",
    )
