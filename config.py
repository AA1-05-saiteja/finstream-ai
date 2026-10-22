"""
FinStream AI - Central Configuration Module
Provides typed and validated application configuration loaded from environment
variables and optional .env files.
"""

from functools import lru_cache
from pathlib import Path
from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    APP_NAME: str = "FinStream AI"

    # Kafka
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"
    KAFKA_TOPIC_TRANSACTIONS: str = "transactions"
    KAFKA_TOPIC_ALERTS: str = "transaction_alerts"
    KAFKA_CONSUMER_GROUP: str = "finstream-stream-processors"
    KAFKA_AUTO_OFFSET_RESET: str = "latest"

    # Generator
    GENERATOR_RATE_TPS: int = 5
    GENERATOR_SUSPICIOUS_PROBABILITY: float = 0.08
    GENERATOR_ACCOUNTS_POOL: int = 200
    GENERATOR_MERCHANTS_POOL: int = 50
    GENERATOR_DEVICES_POOL: int = 300

    # PostgreSQL
    POSTGRES_USER: str = "finstream_user"
    POSTGRES_PASSWORD: str = "finstream_password"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "finstream_db"
    DATABASE_URL: str = (
        "postgresql+psycopg2://finstream_user:finstream_password@localhost:5432/finstream_db"
    )

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str = ""
    REDIS_TRANSACTION_TTL_SECONDS: int = 3600
    REDIS_RISK_TTL_SECONDS: int = 86400

    # Backend API
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    # Machine Learning & Risk Thresholds
    MODEL_DIR: str = "models/saved"
    RISK_THRESHOLD_LOW: float = 0.30
    RISK_THRESHOLD_HIGH: float = 0.70
    XGBOOST_MODEL_PATH: str = "models/saved/xgboost_model.joblib"
    ISOLATION_FOREST_PATH: str = "models/saved/isolation_forest.joblib"
    SCALER_PATH: str = "models/saved/scaler.joblib"
    FEATURE_COLUMNS_PATH: str = "models/saved/feature_columns.json"

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


@lru_cache()
def get_settings() -> Settings:
    """Returns a cached instance of application settings."""
    return Settings()


# Default module-level instance for easy access
settings = get_settings()
