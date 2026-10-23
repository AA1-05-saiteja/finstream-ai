"""
FinStream AI - Kafka Package
Extends __path__ so that kafka-python-ng submodules (producer, consumer, errors, etc.)
and local modules seamlessly resolve without collision across all platforms (Linux, macOS, Windows).
"""

import importlib.util
import site
import sys
import sysconfig
from pathlib import Path

# Add site-packages kafka directory to __path__ dynamically
_site_pkg_candidates = []
try:
    _site_pkg_candidates.extend(site.getsitepackages())
except Exception:
    pass

for key in ("purelib", "platlib"):
    try:
        p = sysconfig.get_path(key)
        if p and p not in _site_pkg_candidates:
            _site_pkg_candidates.append(p)
    except Exception:
        pass

prefix_path = Path(sys.prefix)
for sub in [
    Path("Lib") / "site-packages",
    Path("lib") / f"python{sys.version_info.major}.{sys.version_info.minor}" / "site-packages",
    Path("lib") / f"python{sys.version_info.major}.{sys.version_info.minor}" / "dist-packages",
    Path("lib") / "site-packages",
]:
    p = str(prefix_path / sub)
    if p not in _site_pkg_candidates:
        _site_pkg_candidates.append(p)

for sp in _site_pkg_candidates:
    if not sp:
        continue
    candidate = Path(sp) / "kafka"
    if candidate.exists() and candidate.is_dir() and str(candidate) != str(Path(__file__).parent):
        if str(candidate) not in __path__:
            __path__.insert(0, str(candidate))

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
