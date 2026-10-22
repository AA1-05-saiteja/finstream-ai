"""
Tests for FinStream AI configuration module.
Verifies default values, environment variable parsing, and type safety.
"""

import os
import pytest
from config import Settings, get_settings


def test_default_settings():
    """Verify default settings values when initialized."""
    settings = Settings()
    assert settings.APP_NAME == "FinStream AI"
    assert settings.KAFKA_BOOTSTRAP_SERVERS == "localhost:9092"
    assert settings.KAFKA_TOPIC_TRANSACTIONS == "transactions"
    assert settings.GENERATOR_RATE_TPS == 5
    assert settings.RISK_THRESHOLD_LOW == 0.30
    assert settings.RISK_THRESHOLD_HIGH == 0.70
    assert "http://localhost:5173" in settings.cors_origins_list
    assert settings.POSTGRES_DB == "finstream_db"
    assert settings.POSTGRES_PORT == 5432
    assert settings.REDIS_PORT == 6379
    assert settings.REDIS_TRANSACTION_TTL_SECONDS == 3600
    assert settings.REDIS_RISK_TTL_SECONDS == 86400


def test_cors_origins_parsing():
    """Verify that comma-separated CORS origins are parsed into a clean list."""
    settings = Settings(CORS_ORIGINS="http://localhost:3000, http://example.com,")
    origins = settings.cors_origins_list
    assert len(origins) == 2
    assert "http://localhost:3000" in origins
    assert "http://example.com" in origins


def test_singleton_get_settings():
    """Verify that get_settings returns a cached instance."""
    s1 = get_settings()
    s2 = get_settings()
    assert s1 is s2

