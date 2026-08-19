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
    browser_width: int = 1600
    browser_height: int = 1000
    """The teaching browser's viewport.

    Steel defaults to something small, and this WMS is a dense ExtJS grid: at
    the default the operator is reading a postage stamp, and the accessibility
    tree that gets captured is one of a layout nobody uses.
    """

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

    session_sweep_seconds: float = 600.0
    """How often the keeper looks at the connected systems.

    Not how often it signs in -- that is decided per system from how long its
    sessions have been observed to last. This is only how often the question is
    asked, and asking is a cached read."""

    auth_secret: str = ""
    """The key this deployment signs its own credentials with.

    Unset, every authenticated endpoint answers 503 rather than letting
    anything through: a system that cannot check who is asking must refuse, and
    a default here would be a key every deployment shares. Generate one with
    `make auth-secret`."""

    gemini_api_key: str = ""
    """Without it every model-backed adapter stays unbound and the system runs
    exactly as it does today -- deliberately, for deployments that may not send
    a customer's screen or a customer's words to a hosted model."""

    gemini_transcription_model: str = "gemini-3.7-flash"
    gemini_embedding_model: str = "gemini-embedding-001"

    gemini_vision_model: str = "gemini-3.7-flash"
    """Computer use is native here rather than a separate specialised model.
    Checked against the account rather than assumed: the standalone
    `gemini-2.5-computer-use-preview` still answers, and this one accepts the
    same tool while being the model everything else already uses."""

    gemini_intent_model: str = "gemini-3.7-flash"
    """Chat: reading one sentence, extracting values. An operator is waiting, so
    this is the fast one -- measured at ~2.3s against ~4.8s for the pro model,
    for a job where the answer is checked against the skills that exist anyway."""

    gemini_interpreter_model: str = "gemini-3.1-pro-preview"
    """Reading a demonstration into a workflow, once per induction. Nobody is
    watching the clock, being wrong is expensive and lasting, and the reading is
    what an operator will see for the life of the skill -- so this is the
    reasoning model. It cannot enable computer use, and does not need to."""

    interpretation_enabled: bool = False
    """Reading one demonstration as a workflow sends the captured calls and
    bodies to a hosted model. Same rule as every other egress: a key is not
    consent, so this is its own switch. Off, a single demonstration still
    becomes a skill -- with mechanical step descriptions and no proposed
    parameters."""

    vision_enabled: bool = False

    keycloak_realm_url: str = ""
    """The realm that issues offline tokens for the connected system.

    Empty means no token source: runs authenticate with the session cookies,
    which work and expire on the identity provider's schedule."""

    keycloak_client_id: str = ""

    keycloak_client_secret: str = ""
    """Only for a confidential client. Keycloak answers a public client sent a
    secret, and a confidential one sent none, with the same "Invalid client"
    -- so this is set when the realm says the client is confidential rather
    than guessed at."""
    """The L3 rung sends a screenshot of a customer's live WMS to Google.

    Off by default and separate from the key, like every other egress here. With
    it off, a step whose control has vanished fails with that reason rather than
    quietly reaching for a model."""

    knowledge_embeddings_enabled: bool = False
    """Embeddings order what a structured filter already chose. Off by default:
    retrieval works without them, and turning them on sends the knowledge base's
    titles to a hosted model."""


@lru_cache
def get_settings() -> Settings:
    return Settings()
