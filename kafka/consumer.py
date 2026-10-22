"""
FinStream AI - Apache Kafka Transaction Consumer
Consumes raw synthetic transaction events from the 'transactions' topic,
deserializes JSON payloads, and validates schema integrity.
"""

import argparse
import json
import logging
import sys
import time
from pathlib import Path
from typing import Callable, Iterator, Optional

# Ensure project root is in sys.path
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from kafka import KafkaConsumer
from kafka.errors import KafkaError, NoBrokersAvailable
from pydantic import ValidationError

from config import settings
from producer.transaction_models import Transaction

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("kafka_consumer")


class FinStreamKafkaConsumer:
    """
    Kafka Consumer that subscribes to the 'transactions' topic,
    validates incoming JSON messages against the Transaction Pydantic model,
    and forwards clean records.
    """

    def __init__(
        self,
        bootstrap_servers: Optional[str] = None,
        topic: Optional[str] = None,
        group_id: Optional[str] = None,
        auto_offset_reset: str = "latest",
        consumer_instance: Optional[KafkaConsumer] = None,
    ):
        self.bootstrap_servers = bootstrap_servers or settings.KAFKA_BOOTSTRAP_SERVERS
        self.topic = topic or settings.KAFKA_TOPIC_TRANSACTIONS
        self.group_id = group_id or settings.KAFKA_CONSUMER_GROUP
        self.auto_offset_reset = auto_offset_reset
        self.consumer = consumer_instance

        self.total_received = 0
        self.valid_count = 0
        self.malformed_count = 0
        self.running = False

        if self.consumer is None:
            self._init_consumer()

    def _init_consumer(self) -> None:
        """Initializes Kafka consumer connection with validation."""
        try:
            logger.info("Connecting to Kafka broker at %s...", self.bootstrap_servers)
            self.consumer = KafkaConsumer(
                self.topic,
                bootstrap_servers=self.bootstrap_servers,
                group_id=self.group_id,
                auto_offset_reset=self.auto_offset_reset,
                enable_auto_commit=True,
                auto_commit_interval_ms=1000,
                consumer_timeout_ms=1000,  # 1s poll timeout to allow responsive loop exits
                value_deserializer=lambda m: m,  # Raw bytes, handled in process loop
            )
            logger.info(
                "Successfully subscribed to topic '%s' (Group: %s, Offset: %s)",
                self.topic,
                self.group_id,
                self.auto_offset_reset,
            )
        except (NoBrokersAvailable, KafkaError, Exception) as exc:
            logger.error(
                "ERROR: Unable to connect to Kafka at %s.\n"
                "Please verify that the Docker Kafka service is running (e.g., 'docker compose up -d').\n"
                "Details: %s",
                self.bootstrap_servers,
                str(exc),
            )
            self.consumer = None
            raise ConnectionError(
                f"Failed to establish connection to Kafka at {self.bootstrap_servers}"
            ) from exc

    def deserialize_and_validate(self, raw_bytes: bytes) -> Optional[Transaction]:
        """
        Deserializes JSON bytes and validates against Transaction model.
        Returns Transaction if valid, None if malformed.
        """
        self.total_received += 1
        try:
            payload_str = raw_bytes.decode("utf-8")
            data = json.loads(payload_str)
            tx = Transaction(**data)
            self.valid_count += 1
            return tx
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            self.malformed_count += 1
            logger.warning("Malformed message (JSON decode error): %s", str(exc))
            return None
        except ValidationError as exc:
            self.malformed_count += 1
            logger.warning("Schema validation error on received message: %s", str(exc))
            return None
        except Exception as exc:
            self.malformed_count += 1
            logger.error("Unexpected error parsing message payload: %s", str(exc))
            return None

    def consume_stream(
        self,
        max_messages: Optional[int] = None,
        callback: Optional[Callable[[Transaction], None]] = None,
    ) -> Iterator[Transaction]:
        """
        Consumes messages from topic and yields validated Transaction objects.
        """
        if not self.consumer:
            raise RuntimeError("Kafka consumer is not initialized.")

        self.running = True
        try:
            for message in self.consumer:
                if not self.running:
                    break

                tx = self.deserialize_and_validate(message.value)
                if tx:
                    if callback:
                        callback(tx)
                    yield tx

                if max_messages and self.valid_count >= max_messages:
                    self.running = False
                    break
        except KeyboardInterrupt:
            logger.info("Interrupt received in consumer stream.")
        finally:
            self.running = False

    def close(self) -> None:
        """Closes Kafka consumer connection."""
        if self.consumer:
            logger.info("Closing Kafka consumer...")
            self.consumer.close()
            logger.info(
                "Consumer closed. Summary: Received %d, Valid: %d, Malformed: %d",
                self.total_received,
                self.valid_count,
                self.malformed_count,
            )

    def run(self, max_messages: Optional[int] = None) -> int:
        """
        Runs consumer continuously or up to max_messages, logging formatted transactions.
        """
        logger.info(
            "Starting FinStream Kafka Consumer (Topic: %s, Group: %s)...",
            self.topic,
            self.group_id,
        )
        start_time = time.time()

        try:
            for tx in self.consume_stream(max_messages=max_messages):
                # Print clean, standardized transaction summary
                print(
                    f"Received transaction: {tx.transaction_id} | {tx.account_id} | "
                    f"INR {tx.amount:,.2f} | {tx.city} | {tx.channel.value} | LOW/UNSCORED"
                )
        except KeyboardInterrupt:
            logger.info("Consumer stopped by user.")
        finally:
            self.close()
            elapsed = time.time() - start_time
            logger.info(
                "Session finished in %.2fs. Total Received: %d, Valid: %d, Malformed: %d",
                elapsed,
                self.total_received,
                self.valid_count,
                self.malformed_count,
            )

        return self.valid_count


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="FinStream AI Apache Kafka Transaction Consumer",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--topic",
        type=str,
        default=settings.KAFKA_TOPIC_TRANSACTIONS,
        help="Kafka topic to consume from",
    )
    parser.add_argument(
        "--group",
        type=str,
        default=settings.KAFKA_CONSUMER_GROUP,
        help="Kafka consumer group ID",
    )
    parser.add_argument(
        "--bootstrap-servers",
        type=str,
        default=settings.KAFKA_BOOTSTRAP_SERVERS,
        help="Kafka bootstrap servers connection string",
    )
    parser.add_argument(
        "--from-beginning",
        action="store_true",
        help="Consume from earliest offset instead of latest",
    )
    parser.add_argument(
        "--max-messages",
        type=int,
        default=None,
        help="Maximum valid messages to consume before exiting",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    auto_offset = "earliest" if args.from_beginning else "latest"
    try:
        consumer = FinStreamKafkaConsumer(
            bootstrap_servers=args.bootstrap_servers,
            topic=args.topic,
            group_id=args.group,
            auto_offset_reset=auto_offset,
        )
        consumer.run(max_messages=args.max_messages)
    except ConnectionError:
        sys.exit(1)


if __name__ == "__main__":
    main()
