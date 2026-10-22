"""
FinStream AI - Synthetic Transaction Generator Unit Tests
Covers schema validation, uniqueness, constraints, scenario generation, and deterministic behavior.
"""

import time
import pytest
from pydantic import ValidationError
from producer.account_profiles import AccountPool, INDIAN_CITIES
from producer.scenario_generator import ScenarioGenerator
from producer.transaction_generator import TransactionGenerator
from producer.transaction_models import Channel, MerchantCategory, Transaction, TransactionType


# =====================================================================
# Test 1: Transaction schema validation
# =====================================================================
def test_transaction_schema_validation():
    """Verify that a valid transaction dictionary successfully validates through Pydantic."""
    valid_data = {
        "transaction_id": "TX000100",
        "timestamp": "2026-10-01T12:00:00Z",
        "account_id": "ACC0001",
        "amount": 1500.75,
        "currency": "INR",
        "merchant_id": "MER_GROC_001",
        "merchant_category": "groceries",
        "city": "Hyderabad",
        "device_id": "DEV1234",
        "channel": "POS",
        "card_present": True,
        "transaction_type": "PURCHASE",
    }
    tx = Transaction(**valid_data)
    assert tx.transaction_id == "TX000100"
    assert tx.amount == 1500.75
    assert tx.currency == "INR"
    assert tx.channel == Channel.POS


# =====================================================================
# Test 2: Transaction ID uniqueness
# =====================================================================
def test_transaction_id_uniqueness():
    """Verify that every generated transaction within a session has a strictly unique ID."""
    pool = AccountPool(size=50, seed=42)
    generator = ScenarioGenerator(pool, seed=42)

    tx_ids = set()
    for _ in range(100):
        tx = generator.generate_normal()
        assert tx.transaction_id not in tx_ids
        tx_ids.add(tx.transaction_id)

    assert len(tx_ids) == 100


# =====================================================================
# Test 3: Amount is positive
# =====================================================================
def test_amount_is_strictly_positive():
    """Verify that amount > 0 is enforced and invalid amounts raise ValidationError."""
    with pytest.raises(ValidationError):
        Transaction(
            transaction_id="TX000001",
            timestamp="2026-10-01T12:00:00Z",
            account_id="ACC0001",
            amount=0.0,
            currency="INR",
            merchant_id="MER001",
            merchant_category="groceries",
            city="Hyderabad",
            device_id="DEV001",
            channel="POS",
        )

    with pytest.raises(ValidationError):
        Transaction(
            transaction_id="TX000001",
            timestamp="2026-10-01T12:00:00Z",
            account_id="ACC0001",
            amount=-50.0,
            currency="INR",
            merchant_id="MER001",
            merchant_category="groceries",
            city="Hyderabad",
            device_id="DEV001",
            channel="POS",
        )


# =====================================================================
# Test 4: Required fields exist
# =====================================================================
def test_required_fields_exist_in_clean_dict():
    """Verify that all mandatory fields are present in exported clean dictionaries."""
    pool = AccountPool(size=20, seed=123)
    generator = ScenarioGenerator(pool, seed=123)
    tx = generator.generate_normal()
    tx_dict = tx.to_clean_dict()

    required_keys = {
        "transaction_id",
        "timestamp",
        "account_id",
        "amount",
        "currency",
        "merchant_id",
        "merchant_category",
        "city",
        "device_id",
        "channel",
        "card_present",
        "transaction_type",
    }
    assert required_keys.issubset(set(tx_dict.keys()))


# =====================================================================
# Test 5: Valid channels are generated
# =====================================================================
def test_valid_channels_generated():
    """Verify all generated channels match the Channel enum."""
    pool = AccountPool(size=50, seed=99)
    generator = ScenarioGenerator(pool, seed=99)
    valid_channels = {c.value for c in Channel}

    for _ in range(50):
        tx = generator.generate_normal()
        assert tx.channel.value in valid_channels


# =====================================================================
# Test 6: Valid cities are generated
# =====================================================================
def test_valid_cities_generated():
    """Verify all generated cities belong to the defined Indian cities list."""
    pool = AccountPool(size=50, seed=77)
    generator = ScenarioGenerator(pool, seed=77)

    for _ in range(50):
        tx = generator.generate_normal()
        assert tx.city in INDIAN_CITIES


# =====================================================================
# Test 7: Deterministic generation with a seed
# =====================================================================
def test_deterministic_generation_with_seed():
    """Verify identical seeds produce identical transaction sequences."""
    pool1 = AccountPool(size=30, seed=42)
    gen1 = ScenarioGenerator(pool1, seed=42)

    pool2 = AccountPool(size=30, seed=42)
    gen2 = ScenarioGenerator(pool2, seed=42)

    txs1 = [gen1.generate_normal() for _ in range(10)]
    txs2 = [gen2.generate_normal() for _ in range(10)]

    for t1, t2 in zip(txs1, txs2):
        assert t1.account_id == t2.account_id
        assert t1.amount == t2.amount
        assert t1.merchant_id == t2.merchant_id
        assert t1.city == t2.city
        assert t1.device_id == t2.device_id


# =====================================================================
# Test 8: High-amount suspicious scenario
# =====================================================================
def test_high_amount_scenario_generation():
    """Verify high-amount scenario generates amounts significantly higher than normal."""
    pool = AccountPool(size=20, seed=101)
    generator = ScenarioGenerator(pool, seed=101)

    account = pool.get_account("ACC0001")
    high_tx = generator.generate_high_amount(account=account)

    assert high_tx.scenario_label == "HIGH_AMOUNT"
    assert high_tx.amount >= 65000.0
    assert high_tx.amount > account.avg_amount * 5


# =====================================================================
# Test 9: New-device scenario
# =====================================================================
def test_new_device_scenario_generation():
    """Verify new-device scenario generates a device ID outside known registered devices."""
    pool = AccountPool(size=20, seed=202)
    generator = ScenarioGenerator(pool, seed=202)

    account = pool.get_account("ACC0002")
    known_devices = set(account.known_devices)

    tx = generator.generate_new_device(account=account)
    assert tx.scenario_label == "NEW_DEVICE"
    assert tx.device_id not in known_devices


# =====================================================================
# Test 10: Velocity scenario generates burst for same account
# =====================================================================
def test_velocity_scenario_multiple_transactions():
    """Verify velocity spike creates multiple rapid transactions for the same account."""
    pool = AccountPool(size=20, seed=303)
    generator = ScenarioGenerator(pool, seed=303)

    account = pool.get_account("ACC0003")
    burst = generator.generate_velocity_spike(account=account, count=5)

    assert len(burst) == 5
    for tx in burst:
        assert tx.account_id == "ACC0003"
        assert tx.scenario_label == "VELOCITY_SPIKE"


# =====================================================================
# Test 11: Duration argument terminates correctly
# =====================================================================
def test_duration_termination():
    """Verify that TransactionGenerator terminates after the specified duration."""
    generator = TransactionGenerator(rate=20, num_accounts=20, seed=42)
    start_time = time.time()
    count = generator.run(duration=1.0)
    elapsed = time.time() - start_time

    assert count > 0
    # Elapsed time should be around 1.0 - 1.5 seconds
    assert 0.8 <= elapsed <= 2.5
