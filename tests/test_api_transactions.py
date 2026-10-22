"""
Unit tests for FastAPI transactions endpoints.
"""

from datetime import datetime, timezone
import fakeredis
from fastapi.testclient import TestClient
import pytest

from backend.dependencies import get_db_manager_dep, get_redis_repo
from backend.main import create_app
from database.connection import DatabaseManager
from database.persistence_service import PersistenceService
from database.redis_client import RedisRepository


@pytest.fixture
def api_test_fixture():
    """Provides TestClient with seeded data in an isolated SQLite instance."""
    db_mgr = DatabaseManager(database_url="sqlite:///:memory:")
    db_mgr.create_all_tables()

    fake_client = fakeredis.FakeRedis(decode_responses=True)
    redis_repo = RedisRepository(client=fake_client)

    svc = PersistenceService(db_manager=db_mgr, redis_repo=redis_repo)

    # Seed 5 sample transactions
    for i in range(1, 6):
        tx_id = f"TX_API_{i:03d}"
        risk_lvl = "HIGH" if i == 1 else ("MEDIUM" if i == 2 else "LOW")
        score = 0.85 if i == 1 else (0.45 if i == 2 else 0.08)
        svc.persist_evaluated_transaction({
            "transaction_id": tx_id,
            "timestamp": f"2026-10-01T12:0{i}:00+00:00",
            "account_id": "ACC_TEST_01" if i <= 3 else "ACC_TEST_02",
            "amount": 1000.0 * i,
            "currency": "INR",
            "merchant_id": f"M_{i}",
            "merchant_category": "RETAIL",
            "city": "Mumbai",
            "device_id": f"D_{i}",
            "channel": "UPI",
            "card_present": True,
            "transaction_type": "PURCHASE",
            "scenario_label": "HIGH_AMOUNT" if i == 1 else "NORMAL",
            "xgboost_probability": score,
            "isolation_forest_score": score - 0.5,
            "isolation_forest_normalized": score,
            "hybrid_risk_score": score,
            "risk_level": risk_lvl,
            "top_shap_features": [
                {
                    "feature": "amount",
                    "feature_value": 1000.0 * i,
                    "shap_value": 0.8,
                    "absolute_shap_value": 0.8,
                    "direction": "increases_anomaly",
                    "rank": 1,
                }
            ] if i == 1 else [],
        })

    app = create_app()
    app.dependency_overrides[get_db_manager_dep] = lambda: db_mgr
    app.dependency_overrides[get_redis_repo] = lambda: redis_repo

    client = TestClient(app)
    yield client, db_mgr, redis_repo
    app.dependency_overrides.clear()
    db_mgr.drop_all_tables()
    fake_client.flushall()


def test_list_transactions_pagination(api_test_fixture):
    client, _, _ = api_test_fixture
    response = client.get("/api/v1/transactions?limit=2&offset=0")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 5
    assert len(data["items"]) == 2
    assert data["limit"] == 2
    assert data["offset"] == 0


def test_list_transactions_account_filter(api_test_fixture):
    client, _, _ = api_test_fixture
    response = client.get("/api/v1/transactions?account_id=ACC_TEST_01")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert len(data["items"]) == 3
    assert all(item["account_id"] == "ACC_TEST_01" for item in data["items"])


def test_get_single_transaction_detail(api_test_fixture):
    client, _, _ = api_test_fixture
    response = client.get("/api/v1/transactions/TX_API_001")
    assert response.status_code == 200
    data = response.json()
    assert data["transaction"]["transaction_id"] == "TX_API_001"
    assert data["risk"]["risk_level"] == "HIGH"
    assert len(data["explanations"]) == 1
    assert data["explanations"][0]["feature"] == "amount"


def test_get_transaction_not_found_returns_404(api_test_fixture):
    client, _, _ = api_test_fixture
    response = client.get("/api/v1/transactions/TX_NON_EXISTENT")
    assert response.status_code == 404
    data = response.json()
    assert data["error"] == "transaction_not_found"
