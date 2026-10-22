"""
FinStream AI - Unit Tests for Real-Time Feature Engineering Engine
Validates sliding window aggregations, velocity features, spending deviations,
device switching flags, and per-account isolation.
"""

from datetime import datetime, timedelta, timezone
import pytest
from features.feature_definitions import ALL_ENGINEERED_FEATURE_COLUMNS
from streaming.feature_engineering import AccountSlidingWindowState, RealTimeFeatureEngine


@pytest.fixture
def clean_engine():
    engine = RealTimeFeatureEngine()
    engine.reset()
    return engine


def test_single_transaction_feature_extraction(clean_engine):
    """Verify single transaction extracts all 23 defined feature columns."""
    tx = {
        "transaction_id": "TX001001",
        "timestamp": "2026-10-01T12:00:00Z",
        "account_id": "ACC0001",
        "amount": 1200.0,
        "currency": "INR",
        "merchant_id": "MER001",
        "merchant_category": "groceries",
        "city": "Hyderabad",
        "device_id": "DEV001",
        "channel": "POS",
    }
    features = clean_engine.extract_features(tx)

    for col in ALL_ENGINEERED_FEATURE_COLUMNS:
        assert col in features, f"Missing feature column '{col}'"

    assert features["amount"] == 1200.0
    assert features["transaction_count_1m"] == 1
    assert features["transaction_count_5m"] == 1
    assert features["transaction_count_1h"] == 1
    assert features["total_amount_1h"] == 1200.0
    assert features["average_amount_1h"] == 1200.0
    assert features["known_device_flag"] == 1
    assert features["new_city_flag"] == 0


def test_velocity_and_spending_sliding_windows(clean_engine):
    """Verify rapid transactions increment 1m/5m/1h velocities and aggregate spending."""
    base_time = datetime(2026, 10, 1, 12, 0, 0, tzinfo=timezone.utc)

    # 1. First transaction
    tx1 = {
        "transaction_id": "TX001",
        "timestamp": base_time.isoformat(),
        "account_id": "ACC0002",
        "amount": 1000.0,
        "merchant_id": "MER001",
        "merchant_category": "groceries",
        "city": "Bengaluru",
        "device_id": "DEV001",
        "channel": "ONLINE",
    }
    f1 = clean_engine.extract_features(tx1)
    assert f1["transaction_count_1m"] == 1
    assert f1["total_amount_1h"] == 1000.0

    # 2. Second transaction 10 seconds later
    tx2 = {
        "transaction_id": "TX002",
        "timestamp": (base_time + timedelta(seconds=10)).isoformat(),
        "account_id": "ACC0002",
        "amount": 2000.0,
        "merchant_id": "MER002",
        "merchant_category": "electronics",
        "city": "Bengaluru",
        "device_id": "DEV001",
        "channel": "ONLINE",
    }
    f2 = clean_engine.extract_features(tx2)
    assert f2["transaction_count_1m"] == 2
    assert f2["total_amount_5m"] == 3000.0
    assert f2["average_amount_5m"] == 1500.0
    assert f2["maximum_amount_1h"] == 2000.0
    assert f2["minimum_amount_1h"] == 1000.0

    # 3. Third transaction 2 minutes later (outside 1m window, within 5m window)
    tx3 = {
        "transaction_id": "TX003",
        "timestamp": (base_time + timedelta(minutes=2)).isoformat(),
        "account_id": "ACC0002",
        "amount": 3000.0,
        "merchant_id": "MER001",
        "merchant_category": "groceries",
        "city": "Bengaluru",
        "device_id": "DEV001",
        "channel": "ONLINE",
    }
    f3 = clean_engine.extract_features(tx3)
    # Inside 1 minute: only tx3
    assert f3["transaction_count_1m"] == 1
    # Inside 5 minutes: tx1, tx2, tx3
    assert f3["transaction_count_5m"] == 3
    assert f3["total_amount_5m"] == 6000.0
    assert f3["average_amount_5m"] == 2000.0


def test_window_pruning_after_one_hour(clean_engine):
    """Verify events older than 1 hour are pruned from rolling aggregates."""
    base_time = datetime(2026, 10, 1, 10, 0, 0, tzinfo=timezone.utc)

    # Event 1 at 10:00:00
    tx1 = {
        "transaction_id": "TX010",
        "timestamp": base_time.isoformat(),
        "account_id": "ACC0003",
        "amount": 5000.0,
        "merchant_id": "MER001",
        "city": "Mumbai",
        "device_id": "DEV001",
        "channel": "POS",
    }
    clean_engine.extract_features(tx1)

    # Event 2 at 11:05:00 (65 minutes later)
    tx2 = {
        "transaction_id": "TX011",
        "timestamp": (base_time + timedelta(minutes=65)).isoformat(),
        "account_id": "ACC0003",
        "amount": 1000.0,
        "merchant_id": "MER001",
        "city": "Mumbai",
        "device_id": "DEV001",
        "channel": "POS",
    }
    f2 = clean_engine.extract_features(tx2)

    # Event 1 should have pruned out of the 1-hour window
    assert f2["transaction_count_1h"] == 1
    assert f2["total_amount_1h"] == 1000.0
    assert f2["average_amount_1h"] == 1000.0


def test_new_device_and_new_city_flags(clean_engine):
    """Verify known_device_flag and new_city_flag reflect account history."""
    base_time = datetime(2026, 10, 1, 12, 0, 0, tzinfo=timezone.utc)

    # Initial transaction: registered device DEV10, city Delhi
    tx1 = {
        "transaction_id": "TX101",
        "timestamp": base_time.isoformat(),
        "account_id": "ACC0004",
        "amount": 800.0,
        "merchant_id": "MER001",
        "city": "Delhi",
        "device_id": "DEV10",
        "channel": "MOBILE",
    }
    f1 = clean_engine.extract_features(tx1)
    assert f1["known_device_flag"] == 1
    assert f1["new_city_flag"] == 0

    # Second transaction: brand new device DEV99, and distant city Chennai
    tx2 = {
        "transaction_id": "TX102",
        "timestamp": (base_time + timedelta(minutes=5)).isoformat(),
        "account_id": "ACC0004",
        "amount": 9500.0,
        "merchant_id": "MER002",
        "city": "Chennai",
        "device_id": "DEV99",
        "channel": "ONLINE",
    }
    f2 = clean_engine.extract_features(tx2)
    assert f2["known_device_flag"] == 0  # Unseen device flag
    assert f2["new_city_flag"] == 1      # New city flag
    assert f2["unique_device_count_1h"] == 2
    assert f2["unique_city_count_1h"] == 2


def test_account_state_isolation(clean_engine):
    """Verify that multiple accounts maintain isolated independent sliding windows."""
    base_time = datetime(2026, 10, 1, 12, 0, 0, tzinfo=timezone.utc)

    tx_a = {
        "transaction_id": "TX_A1",
        "timestamp": base_time.isoformat(),
        "account_id": "ACC_A",
        "amount": 500.0,
        "merchant_id": "MER01",
        "city": "Pune",
        "device_id": "DEV_A",
        "channel": "POS",
    }
    tx_b = {
        "transaction_id": "TX_B1",
        "timestamp": base_time.isoformat(),
        "account_id": "ACC_B",
        "amount": 50000.0,
        "merchant_id": "MER02",
        "city": "Kolkata",
        "device_id": "DEV_B",
        "channel": "ONLINE",
    }

    fa = clean_engine.extract_features(tx_a)
    fb = clean_engine.extract_features(tx_b)

    assert fa["total_amount_1h"] == 500.0
    assert fb["total_amount_1h"] == 50000.0
    assert fa["transaction_count_1h"] == 1
    assert fb["transaction_count_1h"] == 1
