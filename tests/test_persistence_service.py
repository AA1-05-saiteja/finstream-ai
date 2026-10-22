"""
Unit tests for PersistenceService coordinating PostgreSQL and Redis.
"""

from datetime import datetime, timezone
import fakeredis
import pytest
from unittest.mock import MagicMock

from database.connection import DatabaseManager
from database.persistence_service import PersistenceService
from database.redis_client import RedisRepository
from database.repositories import PostgresRepository


@pytest.fixture
def persistence_fixture():
    """Provides an isolated PersistenceService with in-memory SQLite and FakeRedis."""
    db_mgr = DatabaseManager(database_url="sqlite:///:memory:")
    db_mgr.create_all_tables()

    fake_client = fakeredis.FakeRedis(decode_responses=True)
    redis_repo = RedisRepository(client=fake_client)

    svc = PersistenceService(db_manager=db_mgr, redis_repo=redis_repo)
    yield svc, db_mgr, redis_repo
    db_mgr.drop_all_tables()
    fake_client.flushall()


def test_persist_evaluated_transaction_success(persistence_fixture):
    svc, db_mgr, redis_repo = persistence_fixture

    evaluation_record = {
        "transaction_id": "TX_EVAL_001",
        "timestamp": "2026-10-01T14:30:00+00:00",
        "account_id": "ACC_999",
        "amount": 45000.0,
        "currency": "INR",
        "merchant_id": "MERCH_88",
        "merchant_category": "JEWELRY",
        "city": "Mumbai",
        "device_id": "DEV_NEW",
        "channel": "NET_BANKING",
        "card_present": False,
        "transaction_type": "TRANSFER",
        "scenario_label": "HIGH_AMOUNT",
        "xgboost_probability": 0.8850,
        "isolation_forest_score": 0.1420,
        "isolation_forest_normalized": 0.7800,
        "hybrid_risk_score": 0.8535,
        "risk_level": "HIGH",
        "top_shap_features": [
            {
                "feature": "amount",
                "feature_value": 45000.0,
                "shap_value": 1.15,
                "absolute_shap_value": 1.15,
                "direction": "increases_anomaly",
                "rank": 1,
            },
            {
                "feature": "velocity_1m",
                "feature_value": 4.0,
                "shap_value": 0.65,
                "absolute_shap_value": 0.65,
                "direction": "increases_anomaly",
                "rank": 2,
            },
        ],
    }

    result = svc.persist_evaluated_transaction(evaluation_record)

    # 1. Check Result Status
    assert result["status"] == "SUCCESS"
    assert result["transaction_id"] == "TX_EVAL_001"
    assert result["postgres_persisted"] is True
    assert result["redis_cached"] is True
    assert result["risk_assessment_id"] is not None

    # 2. Check PostgreSQL Data
    with db_mgr.session_scope() as session:
        repo = PostgresRepository(session)
        tx = repo.get_transaction("TX_EVAL_001")
        assert tx is not None
        assert tx.account_id == "ACC_999"

        risk = repo.get_risk_assessment("TX_EVAL_001", with_shap=True)
        assert risk is not None
        assert risk.risk_level == "HIGH"
        assert len(risk.shap_explanations) == 2
        assert risk.shap_explanations[0].feature_name == "amount"

    # 3. Check Redis Hot State
    cached_risk = redis_repo.get_risk_assessment("TX_EVAL_001")
    assert cached_risk is not None
    assert cached_risk["risk_level"] == "HIGH"

    cached_acc = redis_repo.get_account_latest_risk("ACC_999")
    assert cached_acc is not None
    assert cached_acc["hybrid_risk_score"] == 0.8535


def test_persist_missing_transaction_id_fails(persistence_fixture):
    svc, _, _ = persistence_fixture
    result = svc.persist_evaluated_transaction({"account_id": "ACC_EMPTY"})
    assert result["status"] == "FAILED"
    assert result["postgres_persisted"] is False


def test_redis_failure_does_not_abort_postgres_persistence(persistence_fixture):
    svc, db_mgr, _ = persistence_fixture

    # Mock redis to raise error
    mock_redis = MagicMock(spec=RedisRepository)
    mock_redis.store_risk_assessment.side_effect = Exception("Redis Connection Refused")
    mock_redis.store_account_latest_risk.side_effect = Exception("Redis Connection Refused")
    mock_redis.store_transaction.side_effect = Exception("Redis Connection Refused")
    svc.redis_repo = mock_redis

    evaluation_record = {
        "transaction_id": "TX_REDIS_FAIL",
        "timestamp": datetime.now(timezone.utc),
        "account_id": "ACC_111",
        "amount": 500.0,
        "merchant_id": "M",
        "merchant_category": "GROCERY",
        "city": "Pune",
        "device_id": "D",
        "channel": "UPI",
        "xgboost_probability": 0.05,
        "isolation_forest_score": -0.05,
        "isolation_forest_normalized": 0.20,
        "hybrid_risk_score": 0.095,
        "risk_level": "LOW",
    }

    result = svc.persist_evaluated_transaction(evaluation_record)

    # PostgreSQL must still succeed even if Redis failed
    assert result["status"] == "SUCCESS"
    assert result["postgres_persisted"] is True
    assert result["redis_cached"] is False

    with db_mgr.session_scope() as session:
        repo = PostgresRepository(session)
        tx = repo.get_transaction("TX_REDIS_FAIL")
        assert tx is not None


def test_batch_persistence(persistence_fixture):
    svc, db_mgr, _ = persistence_fixture

    records = [
        {
            "transaction_id": f"TX_BATCH_{i}",
            "timestamp": datetime.now(timezone.utc),
            "account_id": f"ACC_B_{i}",
            "amount": 100.0 * (i + 1),
            "merchant_id": "M",
            "merchant_category": "RETAIL",
            "city": "Hyderabad",
            "device_id": "D",
            "channel": "UPI",
            "xgboost_probability": 0.1,
            "isolation_forest_score": 0.0,
            "isolation_forest_normalized": 0.1,
            "hybrid_risk_score": 0.1,
            "risk_level": "LOW",
        }
        for i in range(5)
    ]

    results = svc.persist_batch(records)
    assert len(results) == 5
    assert all(r["status"] == "SUCCESS" for r in results)

    with db_mgr.session_scope() as session:
        repo = PostgresRepository(session)
        txs = repo.get_recent_transactions(limit=10)
        assert len(txs) == 5
