"""
Unit tests for PostgreSQL Repository layer.
"""

from datetime import datetime, timezone
import pytest

from database.connection import DatabaseManager
from database.repositories import PostgresRepository


@pytest.fixture
def repo_session():
    """Provides a transactional session with in-memory SQLite schema for testing repositories."""
    manager = DatabaseManager(database_url="sqlite:///:memory:")
    manager.create_all_tables()
    session = manager.get_session()
    repo = PostgresRepository(session)
    yield repo, session
    session.close()
    manager.drop_all_tables()


def test_save_and_get_transaction(repo_session):
    repo, session = repo_session
    tx_data = {
        "transaction_id": "TX_TEST_001",
        "timestamp": "2026-10-01T12:00:00+00:00",
        "account_id": "ACC0042",
        "amount": 1499.50,
        "currency": "INR",
        "merchant_id": "MERCH_10",
        "merchant_category": "RETAIL",
        "city": "Bengaluru",
        "device_id": "DEV_ANDROID_99",
        "channel": "UPI",
        "card_present": False,
        "transaction_type": "PURCHASE",
        "scenario_label": "NORMAL",
    }

    model = repo.save_transaction(tx_data)
    session.commit()

    assert model.id is not None
    assert model.transaction_id == "TX_TEST_001"
    assert float(model.amount) == 1499.50

    fetched = repo.get_transaction("TX_TEST_001")
    assert fetched is not None
    assert fetched.account_id == "ACC0042"
    assert fetched.city == "Bengaluru"


def test_duplicate_transaction_idempotency(repo_session):
    repo, session = repo_session
    tx_data = {
        "transaction_id": "TX_TEST_DUP",
        "timestamp": "2026-10-01T12:00:00+00:00",
        "account_id": "ACC0042",
        "amount": 200.0,
        "merchant_id": "M1",
        "merchant_category": "FOOD",
        "city": "Hyderabad",
        "device_id": "D1",
        "channel": "UPI",
    }

    first = repo.save_transaction(tx_data)
    session.commit()

    # Second call should return existing model without error
    second = repo.save_transaction(tx_data)
    session.commit()

    assert first.id == second.id
    assert second.transaction_id == "TX_TEST_DUP"


def test_save_risk_assessment_and_shap_explanations(repo_session):
    repo, session = repo_session
    tx_data = {
        "transaction_id": "TX_TEST_RISK",
        "timestamp": datetime.now(timezone.utc),
        "account_id": "ACC0099",
        "amount": 55000.0,
        "merchant_id": "M2",
        "merchant_category": "LUXURY",
        "city": "Delhi",
        "device_id": "D2",
        "channel": "NET_BANKING",
    }
    repo.save_transaction(tx_data)

    risk_data = {
        "transaction_id": "TX_TEST_RISK",
        "xgboost_probability": 0.85,
        "isolation_forest_score": 0.12,
        "isolation_forest_normalized": 0.75,
        "hybrid_risk_score": 0.82,
        "risk_level": "HIGH",
    }
    risk_model = repo.save_risk_assessment(risk_data)
    session.commit()

    assert risk_model.id is not None
    assert risk_model.risk_level == "HIGH"
    assert risk_model.hybrid_risk_score == 0.82

    # Save SHAP explanations
    shap_list = [
        {
            "feature": "amount",
            "feature_value": 55000.0,
            "shap_value": 1.25,
            "absolute_shap_value": 1.25,
            "direction": "increases_anomaly",
            "rank": 1,
        },
        {
            "feature": "maximum_amount_1h",
            "feature_value": 55000.0,
            "shap_value": 0.95,
            "absolute_shap_value": 0.95,
            "direction": "increases_anomaly",
            "rank": 2,
        },
    ]
    shap_models = repo.save_shap_explanations(risk_model.id, shap_list)
    session.commit()

    assert len(shap_models) == 2
    assert shap_models[0].feature_name == "amount"

    # Fetch risk assessment with eager SHAP
    fetched_risk = repo.get_risk_assessment("TX_TEST_RISK", with_shap=True)
    assert fetched_risk is not None
    assert len(fetched_risk.shap_explanations) == 2
    assert fetched_risk.shap_explanations[0].feature_name == "amount"


def test_get_recent_risk_assessments_filtered(repo_session):
    repo, session = repo_session
    for i, level in enumerate(["LOW", "MEDIUM", "HIGH", "HIGH"]):
        tx_id = f"TX_REC_{i}"
        repo.save_transaction({
            "transaction_id": tx_id,
            "timestamp": datetime.now(timezone.utc),
            "account_id": f"ACC_{i}",
            "amount": 100.0 * (i + 1),
            "merchant_id": "M",
            "merchant_category": "CAT",
            "city": "Pune",
            "device_id": "D",
            "channel": "UPI",
        })
        repo.save_risk_assessment({
            "transaction_id": tx_id,
            "xgboost_probability": 0.1 * i,
            "isolation_forest_score": 0.0,
            "isolation_forest_normalized": 0.1 * i,
            "hybrid_risk_score": 0.1 * i,
            "risk_level": level,
        })
    session.commit()

    high_risks = repo.get_recent_risk_assessments(limit=10, risk_level="HIGH")
    assert len(high_risks) == 2
    assert all(r.risk_level == "HIGH" for r in high_risks)
