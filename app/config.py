# app/config.py
from pydantic_settings import BaseSettings
from pydantic import Field, ValidationError


class Settings(BaseSettings):
    db_dsn: str = "sqlite+aiosqlite:///./dev.db"
    jwt_secret: str = "dev-secret"
    log_level: str = "INFO"

    class Config:
        env_prefix = ""
        case_sensitive = False
        env_file = ".env"


settings = Settings()

from pydantic_settings import BaseSettings
from pydantic import Field, ValidationError


class Settings(BaseSettings):
    # Database DSN
    # SQLite used for local development. Example: sqlite+aiosqlite:///./dev.db
    db_dsn: str = Field(
        "sqlite+aiosqlite:///./dev.db",
        description="SQLite database connection string"
    )

    # JWT Security
    jwt_secret: str = Field(
        "dev-secret",
        description="JWT signing secret used for token validation"
    )

    # Token expiry control (in hours)
    jwt_exp_hours: int = Field(
        6,
        description="JWT token expiry in hours"
    )

    # Logging configuration
    log_level: str = Field(
        "INFO",
        description="Logging level for application (INFO, DEBUG, ERROR)"
    )

    # Cache TTL for dynamic tenants (in seconds)
    tenant_cache_ttl: int = Field(
        300,
        description="Time-to-live for tenant cache; allows dynamic tenant validation"
    )

    class Config:
        env_file = ".env"        # Read environment variables from file if available
        case_sensitive = False   # Allow case-insensitive environment keys


try:
    # Load settings safely
    # If something goes wrong (e.g., invalid type in env), a clear startup error is raised.
    settings = Settings()
except ValidationError as e:
    # Error Handling: Config validation failure
    # Fail fast and show what configuration key is invalid.
    raise RuntimeError(f"Invalid configuration: {e}")