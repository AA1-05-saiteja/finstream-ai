"""
Unit tests for API parameter validation and error handling.
"""

from fastapi.testclient import TestClient
import pytest

from backend.dependencies import get_db_manager_dep, get_redis_repo
from backend.main import create_app
from database.connection import DatabaseManager
from database.redis_client import RedisRepository


@pytest.fixture
def validation_client():
    db_mgr = DatabaseManager(database_url="sqlite:///:memory:")
    db_mgr.create_all_tables()

    app = create_app()
    app.dependency_overrides[get_db_manager_dep] = lambda: db_mgr
    app.dependency_overrides[get_redis_repo] = lambda: RedisRepository(
        client=pytest.importorskip("fakeredis").FakeRedis(decode_responses=True)
    )

    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()
    db_mgr.drop_all_tables()


def test_invalid_risk_level_rejected(validation_client):
    response = validation_client.get("/api/v1/risks?risk_level=CRITICAL_FRAUD")
    assert response.status_code == 422
    data = response.json()
    assert data["error"] == "invalid_request_parameters"


def test_invalid_date_range_rejected(validation_client):
    response = validation_client.get(
        "/api/v1/transactions?start_time=2026-10-02T00:00:00Z&end_time=2026-10-01T00:00:00Z"
    )
    assert response.status_code == 422
    data = response.json()
    assert "start_time must be less than or equal to end_time" in data["message"]


def test_invalid_pagination_limit_rejected(validation_client):
    # Limit exceeds max 100
    response = validation_client.get("/api/v1/transactions?limit=500")
    assert response.status_code == 422

    # Limit less than min 1
    response = validation_client.get("/api/v1/transactions?limit=0")
    assert response.status_code == 422
