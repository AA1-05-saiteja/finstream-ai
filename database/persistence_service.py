"""
FinStream AI - Persistence Service
Coordinates transactional durability in PostgreSQL and low-latency state caching in Redis.
"""

import logging
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from database.connection import DatabaseManager, get_db_manager
from database.redis_client import RedisRepository, get_redis_repository
from database.repositories import PostgresRepository

logger = logging.getLogger("persistence_service")


class PersistenceService:
    """
    Unified persistence coordinator for evaluated streaming transactions.
    Ensures PostgreSQL acts as the durable system of record while Redis maintains hot state.
    """

    def __init__(
        self,
        db_manager: Optional[DatabaseManager] = None,
        redis_repo: Optional[RedisRepository] = None,
    ):
        self.db_manager = db_manager or get_db_manager()
        self.redis_repo = redis_repo or get_redis_repository()

    def persist_evaluated_transaction(
        self,
        evaluation_record: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Persists a single risk-assessed transaction and its SHAP explanations.

        Flow:
        1. PostgreSQL: Transaction + Risk Assessment + SHAP Explanations in one ACID transaction.
        2. Redis: Caches hot risk state and updates account latest risk snapshot.

        Returns a structured result status dictionary.
        """
        tx_id = str(evaluation_record.get("transaction_id", ""))
        account_id = str(evaluation_record.get("account_id", ""))

        if not tx_id:
            logger.error("Cannot persist evaluation record missing transaction_id")
            return {
                "status": "FAILED",
                "transaction_id": None,
                "postgres_persisted": False,
                "redis_cached": False,
                "error": "Missing transaction_id in evaluation record",
            }

        postgres_persisted = False
        risk_assessment_id: Optional[int] = None
        error_msg: Optional[str] = None

        # 1. Durable PostgreSQL Persistence
        try:
            with self.db_manager.session_scope() as session:
                repo = PostgresRepository(session)

                # Persist Transaction details
                tx_model = repo.save_transaction(evaluation_record)

                # Persist Risk Assessment
                risk_model = repo.save_risk_assessment(evaluation_record)
                risk_assessment_id = risk_model.id

                # Persist SHAP explanations if present
                shap_list = evaluation_record.get("top_shap_features", [])
                if shap_list and risk_assessment_id:
                    repo.save_shap_explanations(risk_assessment_id, shap_list)

            postgres_persisted = True
            logger.info("Successfully persisted transaction %s to PostgreSQL", tx_id)
        except Exception as exc:
            error_msg = f"PostgreSQL persistence error: {exc}"
            logger.error("Failed to persist transaction %s to PostgreSQL: %s", tx_id, exc, exc_info=True)
            return {
                "status": "FAILED",
                "transaction_id": tx_id,
                "postgres_persisted": False,
                "redis_cached": False,
                "error": error_msg,
            }

        # 2. Hot-State Redis Caching
        redis_cached = False
        try:
            # Cache hot risk summary
            r1 = self.redis_repo.store_risk_assessment(evaluation_record)
            # Cache latest account risk state
            r2 = self.redis_repo.store_account_latest_risk(account_id, evaluation_record) if account_id else True
            # Cache transaction payload
            r3 = self.redis_repo.store_transaction(evaluation_record)
            redis_cached = r1 and r2 and r3
            if redis_cached:
                logger.debug("Successfully cached state for transaction %s in Redis", tx_id)
        except Exception as exc:
            logger.warning("Redis caching failed for transaction %s (PostgreSQL persisted): %s", tx_id, exc)

        return {
            "status": "SUCCESS",
            "transaction_id": tx_id,
            "account_id": account_id,
            "risk_assessment_id": risk_assessment_id,
            "hybrid_risk_score": evaluation_record.get("hybrid_risk_score"),
            "risk_level": evaluation_record.get("risk_level"),
            "postgres_persisted": postgres_persisted,
            "redis_cached": redis_cached,
            "error": None,
        }

    def persist_batch(
        self,
        evaluation_records: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Persists a batch of evaluated transactions sequentially.
        """
        results = []
        for record in evaluation_records:
            res = self.persist_evaluated_transaction(record)
            results.append(res)
        return results
