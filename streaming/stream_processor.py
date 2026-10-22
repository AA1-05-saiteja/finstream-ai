"""
FinStream AI - Apache Spark Structured Streaming Processor
Ingests real-time transactions from Kafka, parses JSON payloads with strict schema validation,
extracts event-time timestamps, applies watermarking, and sinks validated streams.
"""

import argparse
import json
import logging
import os
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

# Ensure project root is in sys.path
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("stream_processor")

# Lazy PySpark imports
try:
    from pyspark.sql import DataFrame, SparkSession
    from pyspark.sql.functions import col, from_json, to_timestamp, when, lit
    from pyspark.sql.types import (
        BooleanType,
        DoubleType,
        StringType,
        StructField,
        StructType,
        TimestampType,
    )
    PYSPARK_AVAILABLE = True
except ImportError:
    PYSPARK_AVAILABLE = False


def get_transaction_spark_schema() -> Any:
    """
    Returns the explicit Spark StructType schema corresponding to the Phase 2
    Pydantic Transaction model.
    """
    if not PYSPARK_AVAILABLE:
        raise RuntimeError("PySpark is not installed or available.")

    return StructType([
        StructField("transaction_id", StringType(), False),
        StructField("timestamp", StringType(), False),
        StructField("account_id", StringType(), False),
        StructField("amount", DoubleType(), False),
        StructField("currency", StringType(), False),
        StructField("merchant_id", StringType(), False),
        StructField("merchant_category", StringType(), True),
        StructField("city", StringType(), True),
        StructField("device_id", StringType(), True),
        StructField("channel", StringType(), True),
        StructField("card_present", BooleanType(), True),
        StructField("transaction_type", StringType(), True),
        StructField("scenario_label", StringType(), True),
    ])


def validate_transaction_payload(data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Validates a raw transaction dictionary against required business constraints.
    Returns (is_valid, reason_if_invalid).
    """
    if not isinstance(data, dict):
        return False, "Payload is not a JSON object"

    required_fields = ["transaction_id", "account_id", "timestamp", "amount", "currency", "merchant_id"]
    for field in required_fields:
        if field not in data or data[field] is None:
            return False, f"Missing required field: '{field}'"

    # Amount validation: must be strictly > 0
    try:
        amount_val = float(data["amount"])
        if amount_val <= 0.0:
            return False, f"Invalid transaction amount: {amount_val} (must be > 0)"
    except (ValueError, TypeError):
        return False, f"Non-numeric transaction amount: {data.get('amount')}"

    # Currency validation
    if str(data.get("currency")).strip().upper() != "INR":
        return False, f"Unsupported currency: '{data.get('currency')}' (only 'INR' supported)"

    # Timestamp format validation
    try:
        ts_str = str(data["timestamp"]).replace("Z", "+00:00")
        datetime.fromisoformat(ts_str)
    except Exception as exc:
        return False, f"Invalid ISO 8601 timestamp format: {data.get('timestamp')}"

    return True, None


def parse_and_validate_json_string(raw_str: str) -> Tuple[Optional[Dict[str, Any]], bool, Optional[str]]:
    """
    Parses a raw JSON string and checks schema constraints.
    Returns (parsed_dict, is_valid, error_reason).
    """
    try:
        data = json.loads(raw_str)
    except Exception as exc:
        return None, False, f"Malformed JSON: {str(exc)}"

    is_valid, reason = validate_transaction_payload(data)
    return data, is_valid, reason


def convert_iso_to_event_time(iso_str: str) -> datetime:
    """
    Converts ISO 8601 string timestamp to UTC datetime object representing Event Time.
    """
    clean_str = iso_str.replace("Z", "+00:00")
    dt = datetime.fromisoformat(clean_str)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class StreamMetricsTracker:
    """Tracks streaming micro-batch processing metrics."""

    def __init__(self):
        self.total_processed = 0
        self.valid_count = 0
        self.invalid_count = 0
        self.start_time = time.time()

    def update(self, batch_total: int, batch_valid: int, batch_invalid: int) -> None:
        self.total_processed += batch_total
        self.valid_count += batch_valid
        self.invalid_count += batch_invalid

    def get_summary(self) -> Dict[str, Any]:
        elapsed = max(0.1, time.time() - self.start_time)
        rate = self.total_processed / elapsed
        return {
            "processed": self.total_processed,
            "valid": self.valid_count,
            "invalid": self.invalid_count,
            "elapsed_seconds": round(elapsed, 2),
            "approx_rate_tps": round(rate, 2),
        }

    def log_metrics(self) -> None:
        summary = self.get_summary()
        logger.info(
            "STREAM METRICS | Processed: %d | Valid: %d | Invalid: %d | Rate: %.1f TPS",
            summary["processed"],
            summary["valid"],
            summary["invalid"],
            summary["approx_rate_tps"],
        )


class FinStreamProcessor:
    """
    Spark Structured Streaming processor for FinStream AI.
    Handles Kafka stream consumption, event-time watermarking, and console output.
    """

    def __init__(
        self,
        bootstrap_servers: Optional[str] = None,
        topic: Optional[str] = None,
        checkpoint_dir: str = "checkpoints/stream_processor",
        starting_offsets: str = "latest",
        watermark_duration: str = "5 minutes",
        trigger_interval: str = "2 seconds",
    ):
        self.bootstrap_servers = bootstrap_servers or settings.KAFKA_BOOTSTRAP_SERVERS
        self.topic = topic or settings.KAFKA_TOPIC_TRANSACTIONS
        self.checkpoint_dir = checkpoint_dir
        self.starting_offsets = starting_offsets
        self.watermark_duration = watermark_duration
        self.trigger_interval = trigger_interval

        self.spark: Optional[SparkSession] = None
        self.metrics = StreamMetricsTracker()
        self.active_query = None

    def init_spark_session(self) -> SparkSession:
        """Initializes a local SparkSession with Kafka SQL connector support."""
        if not PYSPARK_AVAILABLE:
            raise RuntimeError("PySpark is not installed.")

        # Check for Java runtime
        if shutil.which("java") is None and "JAVA_HOME" not in os.environ:
            logger.error(
                "ERROR: Java (JVM) is required to run Apache Spark Structured Streaming locally.\n"
                "Please install OpenJDK 11 or 17 and configure JAVA_HOME.\n"
                "In containerized environments, Java is bundled automatically in the Docker image."
            )
            raise EnvironmentError("Java runtime not found on system PATH.")

        logger.info("Initializing SparkSession (FinStream-StreamProcessor)...")
        # Spark 3.5+ kafka dependency package coordinate
        kafka_package = "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.1"

        self.spark = (
            SparkSession.builder.appName("FinStream-StreamProcessor")
            .master("local[*]")
            .config("spark.jars.packages", kafka_package)
            .config("spark.sql.streaming.forceDeleteTempCheckpointLocation", "true")
            .config("spark.sql.shuffle.partitions", "2")
            .getOrCreate()
        )
        self.spark.sparkContext.setLogLevel("WARN")
        logger.info("SparkSession initialized successfully.")
        return self.spark

    def build_streaming_pipeline(self) -> DataFrame:
        """
        Constructs the Structured Streaming DataFrame pipeline:
        Kafka Source -> Extract UTF-8 Value -> JSON Schema Parsing -> Event-Time -> Watermark.
        """
        if not self.spark:
            self.init_spark_session()

        schema = get_transaction_spark_schema()

        # 1. Ingest Kafka Stream
        logger.info(
            "Reading Kafka stream from topic '%s' (broker: %s, offsets: %s)",
            self.topic,
            self.bootstrap_servers,
            self.starting_offsets,
        )
        raw_kafka_df = (
            self.spark.readStream.format("kafka")
            .option("kafka.bootstrap.servers", self.bootstrap_servers)
            .option("subscribe", self.topic)
            .option("startingOffsets", self.starting_offsets)
            .option("failOnDataLoss", "false")
            .load()
        )

        # 2. Extract UTF-8 JSON value & parse with explicit schema
        json_parsed_df = raw_kafka_df.selectExpr("CAST(value AS STRING) as raw_json").select(
            from_json(col("raw_json"), schema).alias("tx"),
            col("raw_json"),
        )

        # 3. Event-Time Conversion & Watermarking
        event_df = json_parsed_df.select(
            col("tx.*"),
            to_timestamp(col("tx.timestamp")).alias("event_time"),
        ).withWatermark("event_time", self.watermark_duration)

        # 4. Schema validation predicates
        is_valid_condition = (
            col("transaction_id").isNotNull()
            & col("account_id").isNotNull()
            & col("event_time").isNotNull()
            & (col("amount") > 0.0)
            & col("merchant_id").isNotNull()
            & (col("currency") == "INR")
        )

        validated_df = event_df.withColumn(
            "is_valid_transaction",
            when(is_valid_condition, lit(True)).otherwise(lit(False)),
        )

        return validated_df

    def start_console_sink(self, validated_df: DataFrame):
        """
        Sinks validated stream to console batches for local development inspection.
        """
        # Ensure checkpoint directory exists
        Path(self.checkpoint_dir).mkdir(parents=True, exist_ok=True)

        logger.info(
            "Starting console sink (Trigger: %s, Checkpoint: %s)...",
            self.trigger_interval,
            self.checkpoint_dir,
        )

        query = (
            validated_df.writeStream.outputMode("append")
            .format("console")
            .option("truncate", "false")
            .option("checkpointLocation", self.checkpoint_dir)
            .trigger(processingTime=self.trigger_interval)
            .start()
        )
        self.active_query = query
        return query

    def run(self) -> None:
        """Runs the stream processing query until interrupted."""
        try:
            validated_df = self.build_streaming_pipeline()
            query = self.start_console_sink(validated_df)
            logger.info("FinStream Spark Stream Processor is active and listening...")
            query.awaitTermination()
        except KeyboardInterrupt:
            logger.info("Interrupt signal received. Stopping streaming query cleanly...")
        except Exception as exc:
            logger.error("Error during stream processing execution: %s", str(exc))
            raise
        finally:
            if self.active_query and self.active_query.isActive:
                self.active_query.stop()
            if self.spark:
                self.spark.stop()
            logger.info("Spark Stream Processor shutdown complete.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="FinStream AI Apache Spark Structured Streaming Processor",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--bootstrap-servers",
        type=str,
        default=settings.KAFKA_BOOTSTRAP_SERVERS,
        help="Kafka bootstrap servers connection string",
    )
    parser.add_argument(
        "--topic",
        type=str,
        default=settings.KAFKA_TOPIC_TRANSACTIONS,
        help="Kafka source topic",
    )
    parser.add_argument(
        "--checkpoint-dir",
        type=str,
        default="checkpoints/stream_processor",
        help="Structured streaming checkpoint location",
    )
    parser.add_argument(
        "--starting-offset",
        type=str,
        default="latest",
        choices=["latest", "earliest"],
        help="Starting Kafka offset for stream ingestion",
    )
    parser.add_argument(
        "--trigger-interval",
        type=str,
        default="2 seconds",
        help="Micro-batch trigger interval duration",
    )
    parser.add_argument(
        "--watermark",
        type=str,
        default="5 minutes",
        help="Event-time watermark duration for handling late arrivals",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    processor = FinStreamProcessor(
        bootstrap_servers=args.bootstrap_servers,
        topic=args.topic,
        checkpoint_dir=args.checkpoint_dir,
        starting_offsets=args.starting_offset,
        watermark_duration=args.watermark,
        trigger_interval=args.trigger_interval,
    )
    try:
        processor.run()
    except (EnvironmentError, ConnectionError):
        sys.exit(1)


if __name__ == "__main__":
    main()
