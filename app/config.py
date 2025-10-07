# app/config.py
from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    # Database DSN
    db_dsn: str = Field(
        default="sqlite+aiosqlite:///./dev.db",
        description="SQLite database connection string"
    )

    # JWT Security
    jwt_secret: str = Field(
        default="dev-secret",
        description="JWT signing secret used for token validation"
    )

    # Token expiry control (in hours)
    jwt_exp_hours: int = Field(
        default=6,
        description="JWT token expiry in hours"
    )

    # Logging configuration
    log_level: str = Field(
        default="INFO",
        description="Logging level for application (INFO, DEBUG, ERROR)"
    )

    # Cache TTL for dynamic tenants (in seconds)
    tenant_cache_ttl: int = Field(
        default=300,
        description="Time-to-live for tenant cache; allows dynamic tenant validation"
    )

    class Config:
        env_file = ".env"
        case_sensitive = False

# Instantiate settings once
settings: Settings = Settings()
