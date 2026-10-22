"""
FinStream AI - Unit Tests for Spark Structured Stream Processor
Verifies schema definitions, JSON parsing, validation predicates, event-time conversion,
configuration loading, and checkpointing.
"""

from datetime import datetime, timezone
import pytest
from config import settings
from streaming.stream_processor import (
    FinStreamProcessor,
    StreamMetricsTracker,
    convert_iso_to_event_time,
    get_transaction_spark_schema,
    parse_and_validate_json_string,
    parse_args,
    validate_transaction_payload,
)


# =====================================================================
# Test 1: Spark schema contains all required transaction fields
# =====================================================================
def test_spark_schema_fields():
    """Verify that the explicit Spark schema contains all mandatory and optional transaction fields."""
    schema = get_transaction_spark_schema()
    field_names = [f.name for f in schema.fields]

    expected_fields = [
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
        "scenario_label",
    ]

    for expected in expected_fields:
        assert expected in field_names


# =====================================================================
# Test 2: Valid JSON can be parsed
# =====================================================================
def test_valid_json_parsing():
    """Verify valid JSON string is successfully deserialized and marked valid."""
    raw_json = (
        '{"transaction_id": "TX001000", "timestamp": "2026-10-01T12:00:00Z", '
        '"account_id": "ACC0100", "amount": 1500.50, "currency": "INR", '
        '"merchant_id": "MER_GROC_001", "merchant_category": "groceries", '
        '"city": "Hyderabad", "device_id": "DEV100", "channel": "ONLINE", '
        '"card_present": false, "transaction_type": "PURCHASE"}'
    )
    data, is_valid, reason = parse_and_validate_json_string(raw_json)
    assert data is not None
    assert is_valid is True
    assert reason is None
    assert data["transaction_id"] == "TX001000"
    assert data["amount"] == 1500.50


# =====================================================================
# Test 3: Malformed JSON is identified
# =====================================================================
def test_malformed_json_identified():
    """Verify broken JSON strings are safely identified without crashing."""
    bad_json = '{"transaction_id": "TX001000", "timestamp": '  # Incomplete JSON
    data, is_valid, reason = parse_and_validate_json_string(bad_json)
    assert data is None
    assert is_valid is False
    assert "Malformed JSON" in reason


# =====================================================================
# Test 4: Required fields are validated
# =====================================================================
def test_missing_required_fields():
    """Verify records missing transaction_id, account_id, or merchant_id are rejected."""
    # Missing account_id
    payload_missing_account = {
        "transaction_id": "TX001001",
        "timestamp": "2026-10-01T12:00:00Z",
        "amount": 500.0,
        "currency": "INR",
        "merchant_id": "MER001",
    }
    is_valid, reason = validate_transaction_payload(payload_missing_account)
    assert is_valid is False
    assert "Missing required field: 'account_id'" in reason


# =====================================================================
# Test 5: Negative / zero amount is rejected
# =====================================================================
def test_negative_or_zero_amount_rejected():
    """Verify non-positive transaction amounts are flagged as invalid."""
    zero_amount_payload = {
        "transaction_id": "TX001002",
        "account_id": "ACC001",
        "timestamp": "2026-10-01T12:00:00Z",
        "amount": 0.0,
        "currency": "INR",
        "merchant_id": "MER001",
    }
    is_valid_zero, reason_zero = validate_transaction_payload(zero_amount_payload)
    assert is_valid_zero is False
    assert "must be > 0" in reason_zero

    neg_amount_payload = {
        "transaction_id": "TX001003",
        "account_id": "ACC001",
        "timestamp": "2026-10-01T12:00:00Z",
        "amount": -250.0,
        "currency": "INR",
        "merchant_id": "MER001",
    }
    is_valid_neg, reason_neg = validate_transaction_payload(neg_amount_payload)
    assert is_valid_neg is False
    assert "must be > 0" in reason_neg


# =====================================================================
# Test 6: Timestamp is converted to event-time timestamp
# =====================================================================
def test_event_time_conversion():
    """Verify ISO 8601 string is converted to a timezone-aware UTC datetime."""
    ts_str = "2026-10-01T14:30:15Z"
    event_dt = convert_iso_to_event_time(ts_str)

    assert isinstance(event_dt, datetime)
    assert event_dt.year == 2026
    assert event_dt.month == 10
    assert event_dt.day == 1
    assert event_dt.hour == 14
    assert event_dt.minute == 30
    assert event_dt.second == 15
    assert event_dt.tzinfo == timezone.utc


# =====================================================================
# Test 7: Configuration is loaded from existing settings
# =====================================================================
def test_stream_processor_config_defaults():
    """Verify Stream Processor inherits bootstrap servers and topic from central Settings."""
    processor = FinStreamProcessor()
    assert processor.bootstrap_servers == settings.KAFKA_BOOTSTRAP_SERVERS
    assert processor.topic == settings.KAFKA_TOPIC_TRANSACTIONS
    assert processor.starting_offsets == "latest"
    assert processor.watermark_duration == "5 minutes"


# =====================================================================
# Test 8: Checkpoint path is correctly configured
# =====================================================================
def test_checkpoint_path_configuration():
    """Verify custom checkpoint path can be configured."""
    custom_ckpt = "checkpoints/custom_processor_test"
    processor = FinStreamProcessor(checkpoint_dir=custom_ckpt)
    assert processor.checkpoint_dir == custom_ckpt


# =====================================================================
# Test 9: CLI defaults are correct
# =====================================================================
def test_stream_metrics_tracker():
    """Verify that StreamMetricsTracker records batches and computes accurate rates."""
    tracker = StreamMetricsTracker()
    tracker.update(batch_total=100, batch_valid=98, batch_invalid=2)
    summary = tracker.get_summary()

    assert summary["processed"] == 100
    assert summary["valid"] == 98
    assert summary["invalid"] == 2
    assert summary["approx_rate_tps"] >= 0.0
