"""
FinStream AI - Kafka Package
Extends __path__ so that kafka-python-ng submodules (producer, consumer, errors, etc.)
and local modules seamlessly resolve without collision.
"""

import importlib.util
import sys
from pathlib import Path

# Add site-packages kafka directory to __path__
_site_pkg_kafka = Path(sys.prefix) / "Lib" / "site-packages" / "kafka"
if _site_pkg_kafka.exists():
    __path__.insert(0, str(_site_pkg_kafka))

# Standard kafka-python-ng exports
try:
    from kafka.producer.kafka import KafkaProducer
    from kafka.consumer.group import KafkaConsumer
    import kafka.errors as errors
except Exception:
    pass

# Local FinStream Kafka Consumer export
_local_consumer_file = Path(__file__).parent / "consumer.py"
if _local_consumer_file.exists():
    spec = importlib.util.spec_from_file_location("kafka.finstream_consumer", _local_consumer_file)
    if spec and spec.loader:
        _mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_mod)
        FinStreamKafkaConsumer = getattr(_mod, "FinStreamKafkaConsumer", None)
