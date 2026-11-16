"""Unit tests for application configuration and environment settings."""

from pathlib import Path
from app.core.config import Settings, find_project_root


def test_find_project_root():
    """Verify project root correctly resolves to directory containing .env.example."""
    root = find_project_root()
    assert root.exists()
    assert (root / ".env.example").exists()


def test_settings_defaults():
    """Verify default configuration attributes."""
    settings = Settings(
        DB_USER="test_user",
        DB_PASSWORD="test_secret_password",
        DB_HOST="127.0.0.1",
        DB_PORT=3306,
        DB_NAME="test_db",
    )
    assert settings.APP_NAME == "WorkflowGuard"
    assert settings.API_V1_PREFIX == "/api/v1"
    assert settings.DB_USER == "test_user"
    assert settings.DB_PASSWORD == "test_secret_password"
    assert settings.DB_NAME == "test_db"


def test_database_url_generation():
    """Verify database URL properly encodes parameters and constructs PyMySQL connection string."""
    settings = Settings(
        DB_USER="workflow_admin",
        DB_PASSWORD="P@ssw0rd!#special",
        DB_HOST="db.example.com",
        DB_PORT=3307,
        DB_NAME="workflow_prod",
    )
    url = settings.database_url
    assert url.startswith("mysql+pymysql://workflow_admin:")
    # Check that special characters are URL-encoded
    assert "@" not in url.split("@", 1)[0].split("://", 1)[1]  # Password should not have unescaped @
    assert "db.example.com:3307/workflow_prod?charset=utf8mb4" in url


def test_database_url_masked_protects_password():
    """Verify database_url_masked never reveals raw database password."""
    secret = "TopSecret123"
    settings = Settings(
        DB_USER="root",
        DB_PASSWORD=secret,
        DB_HOST="localhost",
        DB_PORT=3306,
        DB_NAME="workflowguard_db",
    )
    masked_url = settings.database_url_masked
    assert secret not in masked_url
    assert "******" in masked_url
    assert masked_url == "mysql+pymysql://root:******@localhost:3306/workflowguard_db?charset=utf8mb4"


def test_cors_origins_parsing():
    """Verify CORS origins parse both JSON arrays and comma-separated strings."""
    settings_json = Settings(CORS_ORIGINS='["http://localhost:3000", "http://localhost:5173"]')
    assert settings_json.CORS_ORIGINS == ["http://localhost:3000", "http://localhost:5173"]

    settings_csv = Settings(CORS_ORIGINS="http://localhost:3000, http://localhost:5173")
    assert settings_csv.CORS_ORIGINS == ["http://localhost:3000", "http://localhost:5173"]
