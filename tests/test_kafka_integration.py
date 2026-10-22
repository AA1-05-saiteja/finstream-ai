"""
FinStream AI - Kafka Producer-to-Consumer End-to-End Pipeline Tests
Simulates message publishing, consumption, schema verification, loss checking,
and duplicate prevention.
"""

from collections import deque
from unittest.mock import MagicMock
import pytest
from kafka import FinStreamKafkaConsumer
from producer.kafka_producer import FinStreamKafkaProducer
from producer.scenario_generator import ScenarioGenerator
from producer.account_profiles import AccountPool


def test_end_to_end_pipeline_simulation():
    """
    Simulates end-to-end flow:
    Generator -> Producer -> Topic Buffer -> Consumer -> Validated Record
    Verifies that all generated transactions are successfully consumed with 0 loss and 0 duplicates.
    """
    # 1. Setup mock Kafka broker buffer
    topic_buffer = deque()

    mock_producer_instance = MagicMock()

    def mock_send(topic, key, value):
        topic_buffer.append({"key": key, "value": value})
        mock_future = MagicMock()
        return mock_future

    mock_producer_instance.send.side_effect = mock_send

    # 2. Initialize Producer
    producer = FinStreamKafkaProducer(
        topic="transactions",
        producer_instance=mock_producer_instance,
    )

    # 3. Generate 20 synthetic transactions
    pool = AccountPool(size=20, seed=42)
    generator = ScenarioGenerator(pool, seed=42)
    generated_txs = [generator.generate_normal() for _ in range(20)]

    produced_ids = []
    for tx in generated_txs:
        success = producer.publish_transaction(tx)
        assert success is True
        produced_ids.append(tx.transaction_id)

    # Verify produced count
    assert len(produced_ids) == 20
    assert len(topic_buffer) == 20

    # 4. Simulate Consumer reading from topic buffer
    mock_consumer_instance = MagicMock()
    # Mock iterator yielding buffer messages as mock Kafka ConsumerRecords
    mock_records = []
    import json
    for item in topic_buffer:
        record = MagicMock()
        record.value = json.dumps(item["value"]).encode("utf-8")
        record.key = item["key"].encode("utf-8")
        mock_records.append(record)

    mock_consumer_instance.__iter__.return_value = mock_records

    consumer = FinStreamKafkaConsumer(
        topic="transactions",
        consumer_instance=mock_consumer_instance,
    )

    consumed_txs = list(consumer.consume_stream())
    consumed_ids = [tx.transaction_id for tx in consumed_txs]

    # 5. Check Loss and Duplicates
    missing = set(produced_ids) - set(consumed_ids)
    duplicates = len(consumed_ids) - len(set(consumed_ids))

    assert len(generated_txs) == 20
    assert len(produced_ids) == 20
    assert len(consumed_ids) == 20
    assert len(missing) == 0
    assert duplicates == 0
    assert consumed_ids == produced_ids
