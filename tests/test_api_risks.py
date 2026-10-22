"""
Unit tests for FastAPI risk assessments and SHAP explainability endpoints.
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
def risk_api_fixture():
    """Provides seeded TestClient for risk testing."""
    db_mgr = DatabaseManager(database_url="sqlite:///:memory:")
    db_mgr.create_all_tables()

    fake_client = fakeredis.FakeRedis(decode_responses=True)
    redis_repo = RedisRepository(client=fake_client)
    svc = PersistenceService(db_manager=db_mgr, redis_repo=redis_repo)

    # Seed 3 evaluated transactions
    svc.persist_evaluated_transaction({
        "transaction_id": "TX_HIGH_01",
        "timestamp": "2026-10-01T10:00:00+00:00",
        "account_id": "ACC_HIGH",
        "amount": 80000.0,
        "merchant_id": "M1",
        "merchant_category": "LUXURY",
        "city": "Delhi",
        "device_id": "D1",
        "channel": "NET_BANKING",
        "xgboost_probability": 0.92,
        "isolation_forest_score": 0.18,
        "isolation_forest_normalized": 0.84,
        "hybrid_risk_score": 0.896,
        "risk_level": "HIGH",
        "top_shap_features": [
            {
                "feature": "amount",
                "feature_value": 80000.0,
                "shap_value": 1.34,
                "absolute_shap_value": 1.34,
                "direction": "increases_anomaly",
                "rank": 1,
            },
            {
                "feature": "velocity_1m",
                "feature_value": 5.0,
                "shap_value": 0.95,
                "absolute_shap_value": 0.95,
                "direction": "increases_anomaly",
                "rank": 2,
            },
        ],
    })

    svc.persist_evaluated_transaction({
        "transaction_id": "TX_LOW_01",
        "timestamp": "2026-10-01T10:05:00+00:00",
        "account_id": "ACC_LOW",
        "amount": 250.0,
        "merchant_id": "M2",
        "merchant_category": "GROCERY",
        "city": "Mumbai",
        "device_id": "D2",
        "channel": "UPI",
        "xgboost_probability": 0.02,
        "isolation_forest_score": -0.08,
        "isolation_forest_normalized": 0.15,
        "hybrid_risk_score": 0.059,
        "risk_level": "LOW",
        "top_shap_features": [],
    })

    app = create_app()
    app.dependency_overrides[get_db_manager_dep] = lambda: db_mgr
    app.dependency_overrides[get_redis_repo] = lambda: redis_repo

    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()
    db_mgr.drop_all_tables()
    fake_client.flushall()


def test_list_risks_filter_high(risk_api_fixture):
    client = risk_api_fixture
    response = client.get("/api/v1/risks?risk_level=HIGH")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["risk_level"] == "HIGH"
    assert data["items"][0]["transaction_id"] == "TX_HIGH_01"


def test_get_single_risk_assessment(risk_api_fixture):
    client = risk_api_fixture
    response = client.get("/api/v1/risks/TX_HIGH_01")
    assert response.status_code == 200
    data = response.json()
    assert data["transaction_id"] == "TX_HIGH_01"
    assert data["xgboost_probability"] == 0.92
    assert data["risk_level"] == "HIGH"


def test_get_shap_explanations(risk_api_fixture):
    client = risk_api_fixture
    response = client.get("/api/v1/risks/TX_HIGH_01/explanations")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["feature"] == "amount"
    assert data[0]["direction"] == "increases_anomaly"
    assert data[0]["rank"] == 1


def test_get_risk_not_found_returns_404(risk_api_fixture):
    client = risk_api_fixture
    response = client.get("/api/v1/risks/TX_UNKNOWN")
    assert response.status_code == 404
    assert response.json()["error"] == "riskassessment_not_found"
