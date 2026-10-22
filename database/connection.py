"""
FinStream AI - Database Connection & Session Management
Provides thread-safe connection pooling, session lifecycle management, and schema operations.
"""

from contextlib import contextmanager
import logging
from typing import Generator, Optional
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from config import get_settings
from database.models import Base

logger = logging.getLogger("database_connection")


class DatabaseManager:
    """
    Manages SQLAlchemy engine lifecycle and session factories.
    Supports PostgreSQL production connections and SQLite in-memory engines for isolated testing.
    """

    def __init__(self, database_url: Optional[str] = None, echo: bool = False):
        settings = get_settings()
        raw_url = database_url or settings.DATABASE_URL
        if raw_url.startswith("postgresql://"):
            raw_url = raw_url.replace("postgresql://", "postgresql+psycopg2://", 1)
        self.database_url = raw_url
        self.echo = echo
        self._engine: Optional[Engine] = None
        self._session_factory: Optional[sessionmaker] = None

    @property
    def engine(self) -> Engine:
        """Lazily initializes and returns the SQLAlchemy Engine."""
        if self._engine is None:
            connect_args = {}
            # Handle SQLite vs PostgreSQL specific parameters
            if self.database_url.startswith("sqlite"):
                from sqlalchemy.pool import StaticPool
                connect_args["check_same_thread"] = False
                self._engine = create_engine(
                    self.database_url,
                    echo=self.echo,
                    connect_args=connect_args,
                    poolclass=StaticPool,
                )
            else:
                connect_args["connect_timeout"] = 3
                self._engine = create_engine(
                    self.database_url,
                    echo=self.echo,
                    connect_args=connect_args,
                    pool_size=10,
                    max_overflow=20,
                    pool_pre_ping=True,
                    pool_timeout=5,
                )
            logger.info("SQLAlchemy engine initialized for %s", self._engine.url.render_as_string(hide_password=True))
        return self._engine

    @property
    def session_factory(self) -> sessionmaker:
        """Returns the configured sessionmaker."""
        if self._session_factory is None:
            self._session_factory = sessionmaker(
                bind=self.engine,
                autocommit=False,
                autoflush=False,
                expire_on_commit=False,
            )
        return self._session_factory

    def get_session(self) -> Session:
        """Creates and returns a new Session instance."""
        return self.session_factory()

    @contextmanager
    def session_scope(self) -> Generator[Session, None, None]:
        """
        Transactional context manager for database operations.
        Automatically commits on success and rolls back on failure.
        """
        session = self.get_session()
        try:
            yield session
            session.commit()
        except Exception as exc:
            session.rollback()
            logger.error("Transaction rolled back due to error: %s", exc)
            raise
        finally:
            session.close()

    def create_all_tables(self) -> None:
        """Creates all defined tables in the database."""
        logger.info("Creating database tables...")
        Base.metadata.create_all(bind=self.engine)
        logger.info("Database tables created successfully.")

    def drop_all_tables(self) -> None:
        """Drops all tables from the database (development/test use only)."""
        logger.warning("Dropping all database tables...")
        Base.metadata.drop_all(bind=self.engine)
        logger.info("All database tables dropped.")

    def check_connection(self) -> bool:
        """
        Tests database connectivity quickly with non-blocking socket probe.
        Returns True if database is reachable, False otherwise.
        """
        if self.database_url.startswith("sqlite"):
            return True
        import socket
        host = self.engine.url.host or "localhost"
        port = self.engine.url.port or 5432
        try:
            sock = socket.create_connection((host, port), timeout=0.5)
            sock.close()
        except Exception as exc:
            logger.warning("Database socket probe failed (%s:%s): %s", host, port, exc)
            return False

        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except (OperationalError, SQLAlchemyError, Exception) as exc:
            logger.warning("Database connection check failed: %s", exc)
            return False


# Default Singleton Manager
_default_db_manager: Optional[DatabaseManager] = None


def get_db_manager(database_url: Optional[str] = None) -> DatabaseManager:
    """Returns the application DatabaseManager instance."""
    global _default_db_manager
    if database_url is not None:
        return DatabaseManager(database_url=database_url)
    if _default_db_manager is None:
        mgr = DatabaseManager()
        if not mgr.check_connection():
            logger.warning("Configured database is unreachable. Falling back to SQLite for zero-install execution.")
            mgr = DatabaseManager(database_url="sqlite:///./finstream.db")
            mgr.create_all_tables()
        _default_db_manager = mgr
    return _default_db_manager


def get_db_session() -> Generator[Session, None, None]:
    """Dependency helper to yield a managed database session."""
    manager = get_db_manager()
    with manager.session_scope() as session:
        yield session
