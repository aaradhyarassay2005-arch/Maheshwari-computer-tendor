import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Tender Intelligence Platform"
    ENV: str = "dev"  # dev, test, prod

    # Database Settings
    # Defaulting to local postgres for development
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/tender_db"

    # Qdrant Settings
    QDRANT_URL: Optional[str] = None
    QDRANT_API_KEY: Optional[str] = None
    QDRANT_PATH: Optional[str] = "data/qdrant"

    # LLM Settings
    GEMINI_API_KEY: Optional[str] = None

    # Observability Settings
    ENABLE_METRICS: bool = True
    OTLP_ENDPOINT: str = "http://localhost:4317"
    SENTRY_DSN: Optional[str] = None
    METRICS_USERNAME: Optional[str] = None
    METRICS_PASSWORD: Optional[str] = None

    # Auth Settings
    SECRET_KEY: str = "dev_cryptographic_signing_secret_key_change_me"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7



    # SettingsConfigDict for loading env variables from .env
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
