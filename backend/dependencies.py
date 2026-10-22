"""
FinStream AI - FastAPI Dependency Injection
Defines modular dependency providers for database sessions, repositories, and services.
"""

from typing import Generator
from fastapi import Depends
from sqlalchemy.orm import Session

from backend.services import ApiService
from database.connection import DatabaseManager, get_db_manager
from database.redis_client import RedisRepository, get_redis_repository
from database.repositories import PostgresRepository


def get_db_manager_dep() -> DatabaseManager:
    """Provides the singleton DatabaseManager instance."""
    return get_db_manager()


def get_db_session(
    db_mgr: DatabaseManager = Depends(get_db_manager_dep),
) -> Generator[Session, None, None]:
    """Yields a managed database session for the request lifecycle."""
    with db_mgr.session_scope() as session:
        yield session


def get_postgres_repo(
    session: Session = Depends(get_db_session),
) -> PostgresRepository:
    """Provides PostgresRepository instance bound to the request's active session."""
    return PostgresRepository(session=session)


def get_redis_repo() -> RedisRepository:
    """Provides the Redis repository instance."""
    return get_redis_repository()


def get_api_service(
    pg_repo: PostgresRepository = Depends(get_postgres_repo),
    redis_repo: RedisRepository = Depends(get_redis_repo),
    db_mgr: DatabaseManager = Depends(get_db_manager_dep),
) -> ApiService:
    """Provides the ApiService instance with injected repositories."""
    return ApiService(
        postgres_repo=pg_repo,
        redis_repo=redis_repo,
        db_manager=db_mgr,
    )
