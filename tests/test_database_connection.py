"""
Unit tests for database connection and session management.
"""

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from database.connection import DatabaseManager
from database.models import Base, TransactionModel


@pytest.fixture
def sqlite_db():
    """Provides an isolated SQLite in-memory DatabaseManager."""
    manager = DatabaseManager(database_url="sqlite:///:memory:")
    manager.create_all_tables()
    yield manager
    manager.drop_all_tables()


def test_database_connection_and_table_creation(sqlite_db: DatabaseManager):
    """Verifies that engine connects and creates all required tables."""
    assert sqlite_db.check_connection() is True

    with sqlite_db.engine.connect() as conn:
        # Check table existence in SQLite schema
        result = conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table'")
        ).fetchall()
        table_names = [row[0] for row in result]
        assert "transactions" in table_names
        assert "risk_assessments" in table_names
        assert "shap_explanations" in table_names


def test_session_scope_commit(sqlite_db: DatabaseManager):
    """Verifies that session_scope commits changes upon normal exit."""
    with sqlite_db.session_scope() as session:
        tx = TransactionModel(
            transaction_id="TX_CONN_TEST_1",
            timestamp=pytest.importorskip("datetime").datetime.now(
                pytest.importorskip("datetime").timezone.utc
            ),
            account_id="ACC0001",
            amount=500.0,
            currency="INR",
            merchant_id="MERCH001",
            merchant_category="GROCERY",
            city="Mumbai",
            device_id="DEV001",
            channel="UPI",
            card_present=False,
            transaction_type="PURCHASE",
            scenario_label="NORMAL",
        )
        session.add(tx)

    # In a new session, record should exist
    with sqlite_db.session_scope() as session:
        stored = session.query(TransactionModel).filter_by(transaction_id="TX_CONN_TEST_1").first()
        assert stored is not None
        assert stored.account_id == "ACC0001"


def test_session_scope_rollback_on_exception(sqlite_db: DatabaseManager):
    """Verifies that session_scope rolls back changes when an exception is raised."""
    with pytest.raises(ValueError):
        with sqlite_db.session_scope() as session:
            tx = TransactionModel(
                transaction_id="TX_ROLLBACK_TEST",
                timestamp=pytest.importorskip("datetime").datetime.now(
                    pytest.importorskip("datetime").timezone.utc
                ),
                account_id="ACC0002",
                amount=1000.0,
                currency="INR",
                merchant_id="MERCH002",
                merchant_category="ELECTRONICS",
                city="Delhi",
                device_id="DEV002",
                channel="POS",
                card_present=True,
                transaction_type="PURCHASE",
                scenario_label="NORMAL",
            )
            session.add(tx)
            raise ValueError("Intentional trigger for rollback")

    with sqlite_db.session_scope() as session:
        stored = session.query(TransactionModel).filter_by(transaction_id="TX_ROLLBACK_TEST").first()
        assert stored is None
