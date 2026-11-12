from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration read from environment variables (or a local .env file)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://recon:recon@localhost:5432/reconciliation"
    jwt_secret: str = "change-me-to-a-long-random-secret-of-32-bytes-min"
    jwt_algorithm: str = "HS256"
    jwt_ttl_minutes: int = 60
    demo_password: str = "password"


@lru_cache
def get_settings() -> Settings:
    return Settings()
