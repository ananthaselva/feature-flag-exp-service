from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    db_dsn: str = "sqlite+aiosqlite:///./dev.db"
    jwt_secret: str = "dev-secret"
    log_level: str = "INFO"

    class Config:
        env_prefix = ""
        case_sensitive = False
        env_file = ".env"


settings = Settings()
