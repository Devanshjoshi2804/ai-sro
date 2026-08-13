"""Runtime configuration. One Settings object, read from the environment."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_prefix="SRO_", env_nested_delimiter="__", extra="ignore"
    )

    environment: str = "local"
    debug: bool = False

    database_url: str = "postgresql+asyncpg://sro:sro@localhost:5432/sro"
    redis_url: str = "redis://localhost:6379/0"

    s3_endpoint_url: str = "http://localhost:9000"
    s3_access_key: str = "sro"
    s3_secret_key: str = "sro-secret"  # noqa: S105 - local MinIO default, overridden by SRO_S3_SECRET_KEY
    s3_bucket: str = "sro-artifacts"
    s3_region: str = "us-east-1"

    steel_base_url: str = "http://localhost:3010"
    steel_cdp_url: str = "http://localhost:9223"
    """Chrome DevTools endpoint Steel publishes. Playwright connects over it."""
    steel_session_timeout_seconds: int = 3600

    temporal_address: str = "localhost:7233"
    temporal_namespace: str = "default"

    otlp_endpoint: str | None = "http://localhost:4318"
    service_name: str = "sro-backend"

    inline_body_limit_bytes: int = Field(default=256 * 1024)
    """Payloads above this go to object storage and the row keeps the URI.
    Nothing is discarded either way -- see docs/11-capture-completeness.md."""

    capture_drain_interval_seconds: float = 5.0
    capture_screenshot_per_frame: bool = True

    transcription_enabled: bool = False
    """Narration transcription is optional. Default binding is NullTranscriber."""


@lru_cache
def get_settings() -> Settings:
    return Settings()
