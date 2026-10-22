"""
FinStream AI - Apache Kafka Transaction Producer
Streams synthetic financial transaction events into the Kafka 'transactions' topic.
"""

import argparse
import json
import logging
import sys
import time
from typing import Optional
from kafka import KafkaProducer
from kafka.errors import KafkaError, NoBrokersAvailable

from config import settings
from producer.transaction_generator import TransactionGenerator
from producer.transaction_models import Transaction

# Setup logging to stderr
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("kafka_producer")


class FinStreamKafkaProducer:
    """
    Publishes synthetic financial transaction events to Kafka with partition keying
    and delivery callbacks.
    """

    def __init__(
        self,
        bootstrap_servers: Optional[str] = None,
        topic: Optional[str] = None,
        producer_instance: Optional[KafkaProducer] = None,
    ):
        self.bootstrap_servers = bootstrap_servers or settings.KAFKA_BOOTSTRAP_SERVERS
        self.topic = topic or settings.KAFKA_TOPIC_TRANSACTIONS
        self.producer = producer_instance
        self.delivered_count = 0
        self.failed_count = 0

        if self.producer is None:
            self._init_producer()

    def _init_producer(self) -> None:
        """Initializes the Kafka producer with connection validation."""
        try:
            logger.info("Connecting to Kafka broker at %s...", self.bootstrap_servers)
            self.producer = KafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                key_serializer=lambda k: k.encode("utf-8") if isinstance(k, str) else k,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                acks="all",
                retries=3,
                max_block_ms=5000,
            )
            logger.info("Successfully connected to Kafka. Target topic: '%s'", self.topic)
        except (NoBrokersAvailable, KafkaError, Exception) as exc:
            logger.error(
                "ERROR: Unable to connect to Kafka at %s.\n"
                "Please verify that the Docker Kafka service is running (e.g., 'docker compose up -d').\n"
                "Details: %s",
                self.bootstrap_servers,
                str(exc),
            )
            self.producer = None
            raise ConnectionError(
                f"Failed to establish connection to Kafka at {self.bootstrap_servers}"
            ) from exc

    def _on_delivery_success(self, record_metadata, tx_id: str) -> None:
        """Callback triggered on successful broker acknowledgment."""
        self.delivered_count += 1
        logger.debug(
            "SUCCESS: Transaction %s delivered to topic '%s' partition %d offset %d",
            tx_id,
            record_metadata.topic,
            record_metadata.partition,
            record_metadata.offset,
        )

    def _on_delivery_error(self, exc: Exception, tx_id: str) -> None:
        """Callback triggered on broker delivery failure."""
        self.failed_count += 1
        logger.error("ERROR: Failed to deliver transaction %s: %s", tx_id, str(exc))

    def publish_transaction(self, transaction: Transaction) -> bool:
        """
        Publishes a single transaction to Kafka with account_id as the partition key.
        """
        if not self.producer:
            raise RuntimeError("Kafka producer is not connected.")

        tx_id = transaction.transaction_id
        # Key on account_id so events for the same account are routed to the same partition
        key = transaction.account_id
        payload = transaction.to_clean_dict()

        try:
            future = self.producer.send(
                topic=self.topic,
                key=key,
                value=payload,
            )
            future.add_callback(self._on_delivery_success, tx_id=tx_id)
            future.add_errback(self._on_delivery_error, tx_id=tx_id)
            return True
        except Exception as exc:
            self._on_delivery_error(exc, tx_id=tx_id)
            return False

    def flush(self) -> None:
        """Flushes buffered records to the broker."""
        if self.producer:
            self.producer.flush()

    def close(self) -> None:
        """Gracefully closes producer after flushing remaining messages."""
        if self.producer:
            logger.info("Flushing remaining records and closing Kafka producer...")
            self.producer.flush()
            self.producer.close()
            logger.info(
                "Producer closed. Summary: %d acknowledged, %d failed",
                self.delivered_count,
                self.failed_count,
            )

    def run_generator_stream(
        self,
        rate: float = 5.0,
        num_accounts: int = 200,
        scenario: str = "mixed",
        seed: Optional[int] = None,
        duration: Optional[float] = None,
    ) -> int:
        """
        Streams generated transactions into Kafka using the Phase 2 generator.
        """
        generator = TransactionGenerator(
            rate=rate,
            num_accounts=num_accounts,
            scenario=scenario,
            seed=seed,
        )

        logger.info(
            "Starting Kafka Transaction Stream (Rate: %.1f TPS, Scenario: %s, Topic: %s)",
            rate,
            scenario,
            self.topic,
        )

        start_time = time.time()
        produced_count = 0

        try:
            for tx in generator.stream_transactions(duration=duration):
                success = self.publish_transaction(tx)
                if success:
                    produced_count += 1
                    # Log concise stream progress
                    sys.stderr.write(
                        f"\r[PRODUCED] TX: {tx.transaction_id} | Account: {tx.account_id} | "
                        f"Amount: INR {tx.amount:,.2f} | City: {tx.city} | Channel: {tx.channel.value}"
                    )
                    sys.stderr.flush()
        except KeyboardInterrupt:
            logger.info("\nReceived keyboard interrupt. Halting stream...")
        finally:
            sys.stderr.write("\n")
            self.close()
            elapsed = time.time() - start_time
            eff_rate = produced_count / elapsed if elapsed > 0 else 0.0
            logger.info(
                "Stream session ended. Produced: %d, Time: %.2fs, Rate: %.2f TPS",
                produced_count,
                elapsed,
                eff_rate,
            )

        return produced_count


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="FinStream AI Apache Kafka Transaction Producer",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--rate",
        type=float,
        default=float(settings.GENERATOR_RATE_TPS),
        help="Target transactions published per second (TPS)",
    )
    parser.add_argument(
        "--accounts",
        type=int,
        default=settings.GENERATOR_ACCOUNTS_POOL,
        help="Number of synthetic accounts in pool",
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=None,
        help="Stream duration in seconds (omission runs continuously)",
    )
    parser.add_argument(
        "--scenario",
        type=str,
        default="mixed",
        choices=[
            "normal",
            "high_amount",
            "velocity_spike",
            "new_device",
            "unusual_merchant",
            "unusual_location",
            "rapid_device_switching",
            "mixed",
        ],
        help="Synthetic transaction scenario pattern",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Random seed for deterministic reproducibility",
    )
    parser.add_argument(
        "--topic",
        type=str,
        default=settings.KAFKA_TOPIC_TRANSACTIONS,
        help="Target Kafka topic",
    )
    parser.add_argument(
        "--bootstrap-servers",
        type=str,
        default=settings.KAFKA_BOOTSTRAP_SERVERS,
        help="Kafka bootstrap servers connection string",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    try:
        producer = FinStreamKafkaProducer(
            bootstrap_servers=args.bootstrap_servers,
            topic=args.topic,
        )
        producer.run_generator_stream(
            rate=args.rate,
            num_accounts=args.accounts,
            scenario=args.scenario,
            seed=args.seed,
            duration=args.duration,
        )
    except ConnectionError:
        sys.exit(1)


if __name__ == "__main__":
    main()
