"""
Unit tests for FastAPI health and dependency status endpoints.
"""

import fakeredis
from fastapi.testclient import TestClient
import pytest

from backend.dependencies import get_db_manager_dep, get_redis_repo
from backend.main import create_app
from database.connection import DatabaseManager
from database.redis_client import RedisRepository


@pytest.fixture
def client_fixture():
    """Provides a TestClient with isolated in-memory DB and FakeRedis."""
    db_mgr = DatabaseManager(database_url="sqlite:///:memory:")
    db_mgr.create_all_tables()

    fake_client = fakeredis.FakeRedis(decode_responses=True)
    redis_repo = RedisRepository(client=fake_client)

    app = create_app()
    app.dependency_overrides[get_db_manager_dep] = lambda: db_mgr
    app.dependency_overrides[get_redis_repo] = lambda: redis_repo

    client = TestClient(app)
    yield client, db_mgr, redis_repo
    app.dependency_overrides.clear()
    db_mgr.drop_all_tables()
    fake_client.flushall()


def test_basic_health_endpoint(client_fixture):
    client, _, _ = client_fixture
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "finstream-api"
    assert "timestamp" in data


def test_dependencies_health_available(client_fixture):
    client, _, _ = client_fixture
    response = client.get("/api/v1/health/dependencies")
    assert response.status_code == 200
    data = response.json()
    assert data["api"] == "ok"
    assert data["postgresql"] == "available"
    assert data["redis"] == "available"


def test_dependencies_health_when_redis_unavailable(client_fixture):
    client, db_mgr, _ = client_fixture
    # Provide a disconnected redis client
    app = client.app
    from unittest.mock import MagicMock
    mock_redis = MagicMock(spec=RedisRepository)
    mock_redis.is_available.return_value = False
    app.dependency_overrides[get_redis_repo] = lambda: mock_redis

    response = client.get("/api/v1/health/dependencies")
    assert response.status_code == 200
    data = response.json()
    assert data["api"] == "ok"
    assert data["postgresql"] == "available"
    assert data["redis"] == "unavailable"
