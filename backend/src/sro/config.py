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

    ui_debugger_url: str = ""
    """CDP endpoint of a browser the executor may drive for L2.

    Empty by default, and an empty value is not a degraded mode: a run that
    would have escalated records that there was no browser rather than
    pretending the step was impossible."""
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

    capture_video: bool = True
    """Screencast the demonstration. Encoded as it arrives, so a long session
    costs disk rather than memory."""

    capture_video_fps: int = 2
    """Frames per second for the session video.

    Sampled with screenshots rather than a screencast: a screencast would take
    the live view away from the operator (Chrome allows one consumer per page).
    """

    capture_redact_secret_values: bool = True
    """Remove credential values at the point of capture.

    The single exception to keeping everything. A password is not evidence of
    what happened; it is a key to the customer's system. Turning this off makes
    the evidence store a credential store -- do not, without a decision that says
    who is accountable for it.
    """

    vault_path: str = "./.sro-vault"
    vault_key: str | None = None
    """Fernet key for the file vault. Without it the vault refuses to start
    rather than writing plaintext. Generate one with `make vault-key`."""

    transcription_enabled: bool = False
    """Narration transcription is optional. Default binding is NullTranscriber."""

    gemini_api_key: str = ""
    """Without it every model-backed adapter stays unbound and the system runs
    exactly as it does today -- deliberately, for deployments that may not send
    a customer's screen or a customer's words to a hosted model."""

    gemini_transcription_model: str = "gemini-2.5-flash"
    gemini_embedding_model: str = "gemini-embedding-001"

    knowledge_embeddings_enabled: bool = False
    """Embeddings order what a structured filter already chose. Off by default:
    retrieval works without them, and turning them on sends the knowledge base's
    titles to a hosted model."""


@lru_cache
def get_settings() -> Settings:
    return Settings()
