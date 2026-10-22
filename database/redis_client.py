"""
FinStream AI - Redis Cache & Hot State Layer
Provides microsecond-latency state caching for transactions, risk assessments, and account snapshots.
"""

import json
import logging
from typing import Any, Dict, Optional
import redis
from redis.exceptions import ConnectionError, RedisError, TimeoutError

from config import get_settings

logger = logging.getLogger("redis_client")


class RedisRepository:
    """
    Repository for Redis hot-state caching.
    Manages key conventions, TTL policies, and safe fallback on connectivity errors.
    """

    KEY_PREFIX_TX = "finstream:tx:"
    KEY_PREFIX_RISK = "finstream:risk:"
    KEY_PREFIX_ACCOUNT = "finstream:account:"

    def __init__(
        self,
        client: Optional[redis.Redis] = None,
        host: Optional[str] = None,
        port: Optional[int] = None,
        db: Optional[int] = None,
        password: Optional[str] = None,
        transaction_ttl: Optional[int] = None,
        risk_ttl: Optional[int] = None,
    ):
        settings = get_settings()
        self.host = host or settings.REDIS_HOST
        self.port = port or settings.REDIS_PORT
        self.db = db if db is not None else settings.REDIS_DB
        self.password = password if password is not None else (settings.REDIS_PASSWORD or None)
        self.transaction_ttl = transaction_ttl or settings.REDIS_TRANSACTION_TTL_SECONDS
        self.risk_ttl = risk_ttl or settings.REDIS_RISK_TTL_SECONDS

        self._is_custom = client is not None
        if client is not None:
            self._client = client
        else:
            self._client = redis.Redis(
                host=self.host,
                port=self.port,
                db=self.db,
                password=self.password,
                decode_responses=True,
                socket_timeout=0.3,
                socket_connect_timeout=0.3,
                retry_on_timeout=False,
            )

    @property
    def client(self) -> redis.Redis:
        """Returns the underlying Redis client."""
        return self._client

    def is_available(self) -> bool:
        """Checks if Redis instance is reachable and responding."""
        if not self._is_custom:
            import socket
            try:
                sock = socket.create_connection((self.host, self.port), timeout=0.2)
                sock.close()
            except Exception:
                return False
        try:
            return bool(self._client.ping())
        except (ConnectionError, TimeoutError, RedisError, Exception) as exc:
            logger.warning("Redis is currently unavailable: %s", exc)
            return False

    def store_transaction(self, tx_data: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """
        Caches a transaction payload in Redis with TTL.
        """
        if not self.is_available():
            return False
        tx_id = str(tx_data.get("transaction_id", ""))
        if not tx_id:
            return False

        key = f"{self.KEY_PREFIX_TX}{tx_id}"
        ttl_seconds = ttl or self.transaction_ttl
        try:
            payload = json.dumps(tx_data, default=str)
            self._client.set(key, payload, ex=ttl_seconds)
            logger.debug("Cached transaction %s in Redis (TTL: %ds)", tx_id, ttl_seconds)
            return True
        except (RedisError, Exception) as exc:
            logger.warning("Failed to cache transaction %s in Redis: %s", tx_id, exc)
            return False

    def store_risk_assessment(self, risk_data: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """
        Caches compact risk assessment data in Redis with TTL.
        """
        if not self.is_available():
            return False
        tx_id = str(risk_data.get("transaction_id", ""))
        if not tx_id:
            return False

        key = f"{self.KEY_PREFIX_RISK}{tx_id}"
        ttl_seconds = ttl or self.risk_ttl

        # Compact representation for hot cache
        compact_risk = {
            "transaction_id": tx_id,
            "account_id": str(risk_data.get("account_id", "")),
            "amount": float(risk_data.get("amount", 0.0)),
            "hybrid_risk_score": round(float(risk_data.get("hybrid_risk_score", 0.0)), 4),
            "risk_level": str(risk_data.get("risk_level", "LOW")),
            "xgboost_probability": round(float(risk_data.get("xgboost_probability", 0.0)), 4),
            "isolation_forest_normalized": round(float(risk_data.get("isolation_forest_normalized", 0.0)), 4),
            "timestamp": risk_data.get("timestamp"),
        }

        try:
            payload = json.dumps(compact_risk, default=str)
            self._client.set(key, payload, ex=ttl_seconds)
            logger.debug("Cached risk assessment %s in Redis (Score: %.4f)", tx_id, compact_risk["hybrid_risk_score"])
            return True
        except (RedisError, Exception) as exc:
            logger.warning("Failed to cache risk assessment %s in Redis: %s", tx_id, exc)
            return False

    def store_account_latest_risk(
        self,
        account_id: str,
        risk_data: Dict[str, Any],
        ttl: Optional[int] = None,
    ) -> bool:
        """
        Caches the latest risk snapshot for a specific account.
        """
        if not self.is_available():
            return False
        if not account_id:
            return False

        key = f"{self.KEY_PREFIX_ACCOUNT}{account_id}:latest"
        ttl_seconds = ttl or self.risk_ttl
        try:
            payload = json.dumps(risk_data, default=str)
            self._client.set(key, payload, ex=ttl_seconds)
            logger.debug("Updated latest account risk for %s in Redis", account_id)
            return True
        except (RedisError, Exception) as exc:
            logger.warning("Failed to update latest account risk for %s in Redis: %s", account_id, exc)
            return False

    def get_transaction(self, transaction_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves cached transaction payload by transaction_id."""
        key = f"{self.KEY_PREFIX_TX}{transaction_id}"
        try:
            val = self._client.get(key)
            return json.loads(val) if val else None
        except (RedisError, Exception) as exc:
            logger.warning("Failed to retrieve transaction %s from Redis: %s", transaction_id, exc)
            return None

    def get_risk_assessment(self, transaction_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves cached risk assessment by transaction_id."""
        key = f"{self.KEY_PREFIX_RISK}{transaction_id}"
        try:
            val = self._client.get(key)
            return json.loads(val) if val else None
        except (RedisError, Exception) as exc:
            logger.warning("Failed to retrieve risk assessment %s from Redis: %s", transaction_id, exc)
            return None

    def get_account_latest_risk(self, account_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves latest risk evaluation snapshot for an account."""
        key = f"{self.KEY_PREFIX_ACCOUNT}{account_id}:latest"
        try:
            val = self._client.get(key)
            return json.loads(val) if val else None
        except (RedisError, Exception) as exc:
            logger.warning("Failed to retrieve account latest risk for %s from Redis: %s", account_id, exc)
            return None


_default_redis_repo: Optional[RedisRepository] = None


def get_redis_repository(client: Optional[redis.Redis] = None) -> RedisRepository:
    """Returns singleton Redis repository instance."""
    global _default_redis_repo
    if client is not None:
        return RedisRepository(client=client)
    if _default_redis_repo is None:
        _default_redis_repo = RedisRepository()
    return _default_redis_repo
