"""
FinStream AI - Unit Tests for Kafka Producer
Validates serialization, partition keying, delivery callbacks, and error handling.
"""

from unittest.mock import MagicMock, patch
import json
import pytest
from producer.kafka_producer import FinStreamKafkaProducer
from producer.transaction_models import Channel, Transaction, TransactionType


@pytest.fixture
def sample_transaction() -> Transaction:
    return Transaction(
        transaction_id="TX000501",
        timestamp="2026-10-01T12:00:00Z",
        account_id="ACC0501",
        amount=2500.50,
        currency="INR",
        merchant_id="MER_ELEC_001",
        merchant_category="electronics",
        city="Hyderabad",
        device_id="DEV5501",
        channel=Channel.ONLINE,
        card_present=False,
        transaction_type=TransactionType.PURCHASE,
    )


def test_producer_topic_and_config():
    """Verify producer uses configured topic and bootstrap servers."""
    mock_kp = MagicMock()
    producer = FinStreamKafkaProducer(
        bootstrap_servers="localhost:9092",
        topic="custom_transactions",
        producer_instance=mock_kp,
    )
    assert producer.topic == "custom_transactions"
    assert producer.bootstrap_servers == "localhost:9092"
    assert producer.producer is mock_kp


def test_producer_message_key_and_payload(sample_transaction):
    """Verify transaction is published with account_id key and clean dictionary payload."""
    mock_kp = MagicMock()
    mock_future = MagicMock()
    mock_kp.send.return_value = mock_future

    producer = FinStreamKafkaProducer(
        topic="transactions",
        producer_instance=mock_kp,
    )

    success = producer.publish_transaction(sample_transaction)
    assert success is True

    # Verify send was called with topic, key=account_id, value=dict
    mock_kp.send.assert_called_once()
    call_args = mock_kp.send.call_args[1]
    assert call_args["topic"] == "transactions"
    assert call_args["key"] == "ACC0501"
    assert call_args["value"]["transaction_id"] == "TX000501"
    assert call_args["value"]["amount"] == 2500.50


def test_producer_delivery_callbacks():
    """Verify delivery success and error callbacks update counters appropriately."""
    mock_kp = MagicMock()
    producer = FinStreamKafkaProducer(producer_instance=mock_kp)

    mock_metadata = MagicMock()
    mock_metadata.topic = "transactions"
    mock_metadata.partition = 1
    mock_metadata.offset = 42

    # Simulate success callback
    producer._on_delivery_success(mock_metadata, tx_id="TX000501")
    assert producer.delivered_count == 1
    assert producer.failed_count == 0

    # Simulate error callback
    producer._on_delivery_error(Exception("Broker timeout"), tx_id="TX000502")
    assert producer.delivered_count == 1
    assert producer.failed_count == 1


def test_producer_unreachable_broker_raises_connection_error():
    """Verify clear ConnectionError is raised when broker cannot be reached."""
    with patch("producer.kafka_producer.KafkaProducer") as mock_kafka_constructor:
        from kafka.errors import NoBrokersAvailable
        mock_kafka_constructor.side_effect = NoBrokersAvailable()

        with pytest.raises(ConnectionError) as exc_info:
            FinStreamKafkaProducer(bootstrap_servers="nonexistent:9092")

        assert "Failed to establish connection to Kafka" in str(exc_info.value)
