"""
FinStream AI - Kafka Consumer CLI Entrypoint
"""

import importlib.util
from pathlib import Path

_consumer_file = Path(__file__).parent / "consumer.py"
spec = importlib.util.spec_from_file_location("consumer_main", _consumer_file)
if spec and spec.loader:
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if hasattr(mod, "main"):
        mod.main()
