from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    ENV: str = "development"
    APP_NAME: str = "Sistema Odontologico"

    DATABASE_URL: str = "postgresql+asyncpg://odonto:odonto@localhost:5432/odonto"
    REDIS_URL: str = "redis://localhost:6379/0"

    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    CORS_ORIGINS: list[str] = ["http://localhost:4200"]

    STORAGE_PROVIDER: str = "local"  # local | s3
    STORAGE_LOCAL_PATH: str = "./storage"
    S3_ENDPOINT_URL: str | None = None
    S3_BUCKET: str | None = None
    S3_ACCESS_KEY: str | None = None
    S3_SECRET_KEY: str | None = None
    S3_REGION: str = "us-east-1"

    REFRESH_TOKEN_COOKIE_NAME: str = "refresh_token"
    REFRESH_TOKEN_COOKIE_SECURE: bool = False

    # WhatsApp Cloud API. Absent both of these, messaging falls back to the
    # console provider and every message is recorded as `simulado`.
    WHATSAPP_TOKEN: str | None = None
    WHATSAPP_PHONE_NUMBER_ID: str | None = None
    WHATSAPP_API_VERSION: str = "v21.0"

    # The assistant is OFF unless a key is present. There is no offline
    # fallback that makes something up.
    ANTHROPIC_API_KEY: str | None = None
    AI_MODEL: str = "claude-sonnet-5"
    AI_MAX_TOKENS: int = 1200

    # How long a patient's portal link stays valid.
    PORTAL_LINK_DAYS: int = 30
    PORTAL_BASE_URL: str = "http://localhost:4200" 


@lru_cache
def get_settings() -> Settings:
    return Settings()
