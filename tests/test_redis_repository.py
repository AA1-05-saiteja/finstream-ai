"""
Unit tests for Redis hot-state repository.
"""

import fakeredis
import pytest

from database.redis_client import RedisRepository


@pytest.fixture
def fake_redis_repo():
    """Provides a RedisRepository powered by in-memory FakeRedis."""
    fake_client = fakeredis.FakeRedis(decode_responses=True)
    repo = RedisRepository(client=fake_client)
    yield repo
    fake_client.flushall()


def test_redis_availability_and_ping(fake_redis_repo: RedisRepository):
    """Verifies that Redis is recognized as available."""
    assert fake_redis_repo.is_available() is True


def test_store_and_retrieve_transaction(fake_redis_repo: RedisRepository):
    """Verifies transaction caching and retrieval."""
    tx_data = {
        "transaction_id": "TX_REDIS_001",
        "account_id": "ACC_001",
        "amount": 2500.0,
        "city": "Chennai",
    }

    stored = fake_redis_repo.store_transaction(tx_data, ttl=60)
    assert stored is True

    cached = fake_redis_repo.get_transaction("TX_REDIS_001")
    assert cached is not None
    assert cached["transaction_id"] == "TX_REDIS_001"
    assert cached["amount"] == 2500.0


def test_store_and_retrieve_risk_assessment(fake_redis_repo: RedisRepository):
    """Verifies compact risk caching."""
    risk_data = {
        "transaction_id": "TX_REDIS_002",
        "account_id": "ACC_002",
        "amount": 75000.0,
        "hybrid_risk_score": 0.8845,
        "risk_level": "HIGH",
        "xgboost_probability": 0.9123,
        "isolation_forest_normalized": 0.8200,
    }

    stored = fake_redis_repo.store_risk_assessment(risk_data, ttl=120)
    assert stored is True

    cached = fake_redis_repo.get_risk_assessment("TX_REDIS_002")
    assert cached is not None
    assert cached["transaction_id"] == "TX_REDIS_002"
    assert cached["risk_level"] == "HIGH"
    assert cached["hybrid_risk_score"] == 0.8845


def test_store_and_retrieve_account_latest_risk(fake_redis_repo: RedisRepository):
    """Verifies account latest risk state caching."""
    snapshot = {
        "transaction_id": "TX_REDIS_003",
        "amount": 120.0,
        "hybrid_risk_score": 0.05,
        "risk_level": "LOW",
    }

    stored = fake_redis_repo.store_account_latest_risk("ACC_007", snapshot)
    assert stored is True

    cached = fake_redis_repo.get_account_latest_risk("ACC_007")
    assert cached is not None
    assert cached["transaction_id"] == "TX_REDIS_003"
    assert cached["risk_level"] == "LOW"


def test_missing_keys_return_none(fake_redis_repo: RedisRepository):
    """Verifies non-existent keys return None cleanly."""
    assert fake_redis_repo.get_transaction("NON_EXISTENT") is None
    assert fake_redis_repo.get_risk_assessment("NON_EXISTENT") is None
    assert fake_redis_repo.get_account_latest_risk("NON_EXISTENT") is None
