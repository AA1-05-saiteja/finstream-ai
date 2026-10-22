"""
Unit tests for FastAPI account endpoints.
"""

import fakeredis
from fastapi.testclient import TestClient
import pytest

from backend.dependencies import get_db_manager_dep, get_redis_repo
from backend.main import create_app
from database.connection import DatabaseManager
from database.persistence_service import PersistenceService
from database.redis_client import RedisRepository


@pytest.fixture
def account_api_fixture():
    db_mgr = DatabaseManager(database_url="sqlite:///:memory:")
    db_mgr.create_all_tables()

    fake_client = fakeredis.FakeRedis(decode_responses=True)
    redis_repo = RedisRepository(client=fake_client)
    svc = PersistenceService(db_manager=db_mgr, redis_repo=redis_repo)

    # 1. Seed account with both PostgreSQL and Redis cache
    svc.persist_evaluated_transaction({
        "transaction_id": "TX_ACC_01",
        "timestamp": "2026-10-01T11:00:00+00:00",
        "account_id": "ACC_CACHED",
        "amount": 500.0,
        "merchant_id": "M1",
        "merchant_category": "FOOD",
        "city": "Hyderabad",
        "device_id": "D1",
        "channel": "UPI",
        "xgboost_probability": 0.05,
        "isolation_forest_score": 0.0,
        "isolation_forest_normalized": 0.20,
        "hybrid_risk_score": 0.095,
        "risk_level": "LOW",
    })

    # 2. Seed account in PostgreSQL only (no Redis cache to test fallback)
    with db_mgr.session_scope() as session:
        from database.repositories import PostgresRepository
        repo = PostgresRepository(session)
        repo.save_transaction({
            "transaction_id": "TX_ACC_PG_ONLY",
            "timestamp": "2026-10-01T11:30:00+00:00",
            "account_id": "ACC_PG_ONLY",
            "amount": 75000.0,
            "merchant_id": "M2",
            "merchant_category": "JEWELRY",
            "city": "Bengaluru",
            "device_id": "D2",
            "channel": "NET_BANKING",
        })
        repo.save_risk_assessment({
            "transaction_id": "TX_ACC_PG_ONLY",
            "xgboost_probability": 0.88,
            "isolation_forest_score": 0.15,
            "isolation_forest_normalized": 0.80,
            "hybrid_risk_score": 0.856,
            "risk_level": "HIGH",
        })

    app = create_app()
    app.dependency_overrides[get_db_manager_dep] = lambda: db_mgr
    app.dependency_overrides[get_redis_repo] = lambda: redis_repo

    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()
    db_mgr.drop_all_tables()
    fake_client.flushall()


def test_get_account_risk_from_redis(account_api_fixture):
    client = account_api_fixture
    response = client.get("/api/v1/accounts/ACC_CACHED/risk")
    assert response.status_code == 200
    data = response.json()
    assert data["account_id"] == "ACC_CACHED"
    assert data["risk_level"] == "LOW"
    assert data["source"] == "redis_hot_state"


def test_get_account_risk_postgres_fallback(account_api_fixture):
    client = account_api_fixture
    response = client.get("/api/v1/accounts/ACC_PG_ONLY/risk")
    assert response.status_code == 200
    data = response.json()
    assert data["account_id"] == "ACC_PG_ONLY"
    assert data["risk_level"] == "HIGH"
    assert data["source"] == "postgres_fallback"


def test_get_account_risk_not_found(account_api_fixture):
    client = account_api_fixture
    response = client.get("/api/v1/accounts/ACC_NON_EXISTENT/risk")
    assert response.status_code == 404
    assert response.json()["error"] == "account_not_found"


def test_get_account_transactions(account_api_fixture):
    client = account_api_fixture
    response = client.get("/api/v1/accounts/ACC_CACHED/transactions")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["account_id"] == "ACC_CACHED"
