"""
FinStream AI - Unit Tests for Kafka Consumer
Validates message deserialization, schema validation, malformed payload resilience, and configuration.
"""

from unittest.mock import MagicMock, patch
import json
import pytest
from kafka import FinStreamKafkaConsumer
from producer.transaction_models import Channel, Transaction


def test_consumer_configuration():
    """Verify consumer parameters are properly configured."""
    mock_kc = MagicMock()
    consumer = FinStreamKafkaConsumer(
        bootstrap_servers="localhost:9092",
        topic="transactions",
        group_id="test_group",
        auto_offset_reset="earliest",
        consumer_instance=mock_kc,
    )
    assert consumer.topic == "transactions"
    assert consumer.group_id == "test_group"
    assert consumer.auto_offset_reset == "earliest"


def test_consumer_valid_message_deserialization():
    """Verify valid JSON payload is deserialized into Transaction model."""
    mock_kc = MagicMock()
    consumer = FinStreamKafkaConsumer(consumer_instance=mock_kc)

    raw_payload = json.dumps({
        "transaction_id": "TX000999",
        "timestamp": "2026-10-01T12:00:00Z",
        "account_id": "ACC0999",
        "amount": 1800.0,
        "currency": "INR",
        "merchant_id": "MER_DINE_001",
        "merchant_category": "dining",
        "city": "Mumbai",
        "device_id": "DEV9999",
        "channel": "POS",
        "card_present": True,
        "transaction_type": "PURCHASE",
    }).encode("utf-8")

    tx = consumer.deserialize_and_validate(raw_payload)
    assert tx is not None
    assert tx.transaction_id == "TX000999"
    assert tx.amount == 1800.0
    assert tx.city == "Mumbai"
    assert consumer.valid_count == 1
    assert consumer.malformed_count == 0


def test_consumer_malformed_json_handling():
    """Verify invalid JSON bytes do not raise uncaught exceptions and increment malformed counter."""
    mock_kc = MagicMock()
    consumer = FinStreamKafkaConsumer(consumer_instance=mock_kc)

    bad_payload = b"NOT_A_VALID_JSON_STRING"
    tx = consumer.deserialize_and_validate(bad_payload)
    assert tx is None
    assert consumer.malformed_count == 1
    assert consumer.valid_count == 0


def test_consumer_schema_validation_failure():
    """Verify missing required fields or invalid values are rejected safely."""
    mock_kc = MagicMock()
    consumer = FinStreamKafkaConsumer(consumer_instance=mock_kc)

    invalid_schema_payload = json.dumps({
        "transaction_id": "TX000111",
        # Missing amount and timestamp
        "account_id": "ACC0111",
    }).encode("utf-8")

    tx = consumer.deserialize_and_validate(invalid_schema_payload)
    assert tx is None
    assert consumer.malformed_count == 1


def test_consumer_unreachable_broker_raises_connection_error():
    """Verify connection failure to Kafka broker raises clear ConnectionError."""
    with patch("kafka.consumer.KafkaConsumer") as mock_kc_constructor:
        from kafka.errors import NoBrokersAvailable
        mock_kc_constructor.side_effect = NoBrokersAvailable()

        with pytest.raises(ConnectionError) as exc_info:
            FinStreamKafkaConsumer(bootstrap_servers="nonexistent:9092")

        assert "Failed to establish connection to Kafka" in str(exc_info.value)
