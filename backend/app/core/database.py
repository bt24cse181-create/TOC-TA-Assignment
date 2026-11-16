"""SQLAlchemy 2.0 database engine, session factory, and session dependency.

Configures connection pooling and sanitizes database errors to prevent
accidental credential leakage in application logs or responses.
"""

import logging
import re
from typing import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError, OperationalError, SQLAlchemyError
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings

logger = logging.getLogger("workflowguard.database")


class DatabaseConnectionError(Exception):
    """Sanitized exception raised when database connectivity fails."""

    def __init__(self, message: str, original_code: str = ""):
        self.message = message
        self.original_code = original_code
        super().__init__(self.message)


class Base(DeclarativeBase):
    """Base declarative class for all SQLAlchemy ORM models."""

    pass


# Initialize SQLAlchemy 2.0 Engine with robust MySQL connection pooling
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,      # Automatically verify connection health before checkout
    pool_recycle=3600,       # Recycle connections older than 1 hour to prevent MySQL drops
    pool_size=10,            # Steady-state connection pool size
    max_overflow=20,         # Maximum burst overflow connections
    echo=settings.APP_DEBUG, # Echo SQL queries if debug mode is active
    future=True,
)

# Thread-safe session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,
)


def sanitize_db_error(exc: Exception) -> str:
    """Strip passwords and sensitive connection parameters from database error messages."""
    raw = str(exc)
    # Mask password pattern if present in URI format: :password@
    sanitized = re.sub(r":([^:@]+)@", ":******@", raw)
    if settings.DB_PASSWORD:
        sanitized = sanitized.replace(settings.DB_PASSWORD, "******")
    return sanitized


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency yielding an isolated database session.

    Guarantees session cleanup even if unhandled exceptions occur during route
    handling.
    """
    db = SessionLocal()
    try:
        yield db
    except SQLAlchemyError as exc:
        safe_msg = sanitize_db_error(exc)
        logger.error(f"Database error during session execution: {safe_msg}")
        raise
    finally:
        db.close()


def verify_connection() -> dict:
    """Execute a lightweight SELECT 1 check to verify database connectivity.

    Returns diagnostic status information without exposing credentials.
    """
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1")).scalar()
            return {
                "status": "connected" if result == 1 else "unexpected_result",
                "database": settings.DB_NAME,
                "host": settings.DB_HOST,
                "port": settings.DB_PORT,
                "user": settings.DB_USER,
            }
    except OperationalError as exc:
        safe_msg = sanitize_db_error(exc)
        logger.error(f"OperationalError while connecting to database: {safe_msg}")
        raise DatabaseConnectionError(
            message=f"Could not connect to MySQL at {settings.DB_HOST}:{settings.DB_PORT}. Details: {safe_msg}"
        ) from exc
    except DBAPIError as exc:
        safe_msg = sanitize_db_error(exc)
        logger.error(f"DBAPIError: {safe_msg}")
        raise DatabaseConnectionError(
            message=f"Database driver communication error. Details: {safe_msg}"
        ) from exc
    except Exception as exc:
        safe_msg = sanitize_db_error(exc)
        logger.error(f"Unexpected database connection error: {safe_msg}")
        raise DatabaseConnectionError(
            message=f"Unexpected error connecting to database: {safe_msg}"
        ) from exc
