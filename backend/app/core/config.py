"""Application configuration management using Pydantic Settings.

Loads environment variables from the project root .env file regardless of the
current working directory.
"""

from functools import lru_cache
from pathlib import Path
from typing import List, Union
from urllib.parse import quote_plus

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def find_project_root() -> Path:
    """Locate the project root directory containing .env or .env.example."""
    # backend/app/core/config.py -> parents: [core, app, backend, WorkflowGuard_Project]
    current = Path(__file__).resolve()
    for parent in [current.parents[3], current.parents[2], Path.cwd()]:
        if (parent / ".env").exists() or (parent / ".env.example").exists():
            return parent
    return current.parents[3]


PROJECT_ROOT = find_project_root()
ENV_FILE_PATH = PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    """WorkflowGuard system configuration loaded from environment or .env file."""

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE_PATH),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Application settings
    APP_NAME: str = Field(default="WorkflowGuard", description="Application name")
    APP_ENV: str = Field(default="development", description="Environment: development, test, production")
    APP_DEBUG: bool = Field(default=True, description="Enable debug mode")
    API_V1_PREFIX: str = Field(default="/api/v1", description="API routing prefix")
    SECRET_KEY: str = Field(
        default="change-this-to-a-secure-random-32-byte-hex-string",
        description="Application secret key",
    )

    # Server settings
    SERVER_HOST: str = Field(default="127.0.0.1", description="Server listen host")
    SERVER_PORT: int = Field(default=8000, description="Server listen port")

    # MySQL database configuration
    DB_HOST: str = Field(default="localhost", description="MySQL server host")
    DB_PORT: int = Field(default=3306, description="MySQL server port")
    DB_USER: str = Field(default="root", description="MySQL database username")
    DB_PASSWORD: str = Field(default="", description="MySQL database password")
    DB_NAME: str = Field(default="workflowguard_db", description="MySQL database name")

    # CORS settings
    CORS_ORIGINS: Union[List[str], str] = Field(
        default=["http://localhost:5173", "http://127.0.0.1:5173"],
        description="Allowed CORS origins",
    )

    # ML parameters (Phase 3 placeholder configuration)
    ISOLATION_FOREST_CONTAMINATION: float = Field(default=0.05, description="Contamination factor for Isolation Forest")
    ISOLATION_FOREST_RANDOM_STATE: int = Field(default=42, description="Random seed for reproducibility")

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, value: Union[str, List[str]]) -> List[str]:
        """Parse CORS origins whether provided as a JSON list, comma-separated string, or list."""
        if isinstance(value, str):
            value = value.strip()
            if value.startswith("[") and value.endswith("]"):
                import json

                try:
                    return json.loads(value)
                except Exception:
                    pass
            return [x.strip() for x in value.split(",") if x.strip()]
        return value

    @property
    def database_url(self) -> str:
        """Construct the SQLAlchemy connection URL with safely encoded credentials."""
        encoded_password = quote_plus(self.DB_PASSWORD) if self.DB_PASSWORD else ""
        return (
            f"mysql+pymysql://{self.DB_USER}:{encoded_password}@"
            f"{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?charset=utf8mb4"
        )

    @property
    def database_url_masked(self) -> str:
        """Return the database URL with the password redacted for safe logging/display."""
        return (
            f"mysql+pymysql://{self.DB_USER}:******@"
            f"{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?charset=utf8mb4"
        )


@lru_cache()
def get_settings() -> Settings:
    """Return a cached singleton instance of the Settings object."""
    return Settings()


# Export default settings instance
settings: Settings = get_settings()
