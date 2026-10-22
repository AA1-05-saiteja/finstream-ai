"""
FinStream AI - Database Schema Initializer & Health Check CLI
Provides utilities to create, verify, or reset database tables.
"""

import argparse
import logging
import sys

from database.connection import get_db_manager
from database.redis_client import get_redis_repository

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("init_db")


def main():
    parser = argparse.ArgumentParser(
        description="FinStream AI Database & Redis Management CLI"
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Drop all existing tables before recreating schema (WARNING: Clears data)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check connectivity to PostgreSQL and Redis without modifying schema",
    )
    args = parser.parse_args()

    db_manager = get_db_manager()
    redis_repo = get_redis_repository()

    # 1. Connectivity Check
    pg_ok = db_manager.check_connection()
    redis_ok = redis_repo.is_available()

    logger.info("=== Infrastructure Connectivity ===")
    logger.info("PostgreSQL: %s", "AVAILABLE (Connected)" if pg_ok else "UNAVAILABLE (Disconnected)")
    logger.info("Redis:      %s", "AVAILABLE (Connected)" if redis_ok else "UNAVAILABLE (Disconnected)")

    if args.check:
        if not pg_ok:
            sys.exit(1)
        sys.exit(0)

    if not pg_ok:
        logger.error("Cannot initialize schema: PostgreSQL is not reachable.")
        sys.exit(1)

    if args.reset:
        logger.warning("Reset flag provided. Dropping existing tables...")
        db_manager.drop_all_tables()

    logger.info("Initializing schema (creating tables if not exist)...")
    db_manager.create_all_tables()
    logger.info("Schema initialization complete!")


if __name__ == "__main__":
    main()
