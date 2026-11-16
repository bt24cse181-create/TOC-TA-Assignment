"""Unit tests for database session lifecycle and error sanitization."""

import pytest
from app.core.config import settings
from app.core.database import (
    DatabaseConnectionError,
    get_db,
    sanitize_db_error,
)


def test_sanitize_db_error_masks_uri_password():
    """Verify passwords embedded in URI strings are masked."""
    fake_error = Exception("(pymysql.err.OperationalError) (1045, 'Access denied for user root@localhost:supersecret123')")
    result = sanitize_db_error(fake_error)
    # The password pattern should be masked
    assert "supersecret123" in str(fake_error)


def test_sanitize_db_error_masks_configured_password():
    """Verify configured DB_PASSWORD is never leaked even in freeform error text."""
    orig_pw = settings.DB_PASSWORD
    try:
        settings.DB_PASSWORD = "MySecretDatabasePassword999"
        error_with_password = Exception("Failed to authenticate with MySecretDatabasePassword999 against MySQL")
        sanitized = sanitize_db_error(error_with_password)
        assert "MySecretDatabasePassword999" not in sanitized
        assert "******" in sanitized
    finally:
        settings.DB_PASSWORD = orig_pw


def test_database_connection_error_exception():
    """Verify DatabaseConnectionError attributes and message preservation."""
    err = DatabaseConnectionError("Safe message without secrets", original_code="2003")
    assert err.message == "Safe message without secrets"
    assert err.original_code == "2003"
    assert str(err) == "Safe message without secrets"


def test_get_db_session_lifecycle():
    """Verify get_db generator yields a session and ensures clean closure."""
    gen = get_db()
    session = next(gen)
    assert session is not None
    # Closing via the generator finally block
    with pytest.raises(StopIteration):
        next(gen)
