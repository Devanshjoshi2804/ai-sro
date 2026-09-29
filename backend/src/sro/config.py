from __future__ import annotations

import subprocess
from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from pydantic import Field, field_validator, model_validator
from pydantic.fields import FieldInfo
from pydantic_settings import (
    BaseSettings,
    EnvSettingsSource,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)

RETIRED_MODEL_SETTINGS = frozenset(
    {
        "SRO_GEMINI_PLAN_MODEL",
        "SRO_GEMINI_RESCUE_MODEL",
        "SRO_GEMINI_VISION_MODEL",
        "SRO_GEMINI_INTENT_MODEL",
        "SRO_GEMINI_INTERPRETER_MODEL",
        "SRO_GEMINI_TRANSCRIPTION_MODEL",
    }
)

_RETIRED = "retired_model_settings"


def _git_head() -> str:
    try:
        done = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],  # noqa: S607 - git is on PATH or it is not
            cwd=Path(__file__).parent,
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
        )
    except (OSError, subprocess.SubprocessError):
        return "unknown"
    return done.stdout.strip() or "unknown"


_DEFAULT_PORTS = {"http": "80", "https": "443", "ws": "80", "wss": "443"}
_LOOPBACK = ("127.0.0.1", "localhost", "[::1]")


def _origins_of(url: str) -> set[tuple[str, str]]:
    parsed = urlsplit(url if "//" in url else f"//{url}")
    host = (parsed.hostname or "").lower()
    if not host:
        return set()
    if ":" in host:
        host = f"[{host}]"
    host = host.rstrip(".")
    try:
        port = str(parsed.port) if parsed.port else ""
    except ValueError:
        return set()
    if port and port == _DEFAULT_PORTS.get(parsed.scheme.lower()):
        port = ""
    prefix = parsed.path.rstrip("/") or "/"
    hosts = _LOOPBACK if host in _LOOPBACK else (host,)
    return {(f"{one}:{port}" if port else one, prefix) for one in hosts}


class _RetiredModelSettings(PydanticBaseSettingsSource):
    def __init__(self, settings_cls: type[BaseSettings], *read: EnvSettingsSource) -> None:
        super().__init__(settings_cls)
        self._read = read

    def get_field_value(self, field: FieldInfo, field_name: str) -> tuple[Any, str, bool]:
        return None, field_name, False

    def __call__(self) -> dict[str, Any]:
        found = sorted(
            {
                key.upper()
                for source in self._read
                for key in source.env_vars
                if key.upper() in RETIRED_MODEL_SETTINGS
            }
        )
        return {_RETIRED: found} if found else {}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_prefix="SRO_", env_nested_delimiter="__", extra="ignore"
    )

    environment: str = "local"
    debug: bool = False

    louder_for: str = ""

    revision: str = Field(default_factory=_git_head)

    database_url: str = "postgresql+asyncpg://sro:sro@localhost:5432/sro"

    ui_debugger_url: str = ""

    s3_endpoint_url: str = "http://localhost:9000"
    s3_access_key: str = "sro"
    s3_secret_key: str = "sro-secret"  # noqa: S105 - local MinIO default, overridden by SRO_S3_SECRET_KEY
    s3_bucket: str = "sro-artifacts"

    s3_public_endpoint_url: str | None = None
    s3_region: str = "us-east-1"

    cors_origins: tuple[str, ...] = ()

    mcp_servers: str = ""

    steel_base_url: str = "http://localhost:3010"
    steel_public_base_url: str | None = None

    steel_cdp_url: str = "http://localhost:9223"
    browser_width: int = 1600
    browser_height: int = 1000

    steel_session_timeout_seconds: int = 3600

    steel_urls: dict[str, tuple[tuple[str, str], ...]] = Field(default_factory=dict)
    steel_sessions_per_container: int = 20
    steel_tenants: tuple[str, ...] = ()

    def steel_containers(self, tenant: str) -> tuple[tuple[str, str], ...]:
        return self.steel_urls.get(tenant) or ((self.steel_base_url, self.steel_cdp_url),)

    page_code_path: str = str(
        Path(__file__).resolve().parents[3]
        / "new-chrome-extension"
        / "src"
        / "page"
        / "page-code.js"
    )

    attach_hosts: tuple[str, ...] = ("127.0.0.1", "localhost", "[::1]")

    api_url: str = "http://localhost:8000"

    console_url: str = "http://localhost:3000"

    def our_own_origins(self) -> frozenset[tuple[str, str]]:
        found: set[tuple[str, str]] = set()
        for url in (self.api_url, self.console_url, *self.cors_origins):
            found |= _origins_of(url)
        return frozenset(found)

    temporal_address: str = "localhost:7233"

    temporal_namespace: str = "default"

    otlp_endpoint: str | None = "http://localhost:4318"
    service_name: str = "sro-backend"

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        read = tuple(
            source
            for source in (env_settings, dotenv_settings)
            if isinstance(source, EnvSettingsSource)
        )
        return (
            _RetiredModelSettings(settings_cls, *read),
            init_settings,
            env_settings,
            dotenv_settings,
            file_secret_settings,
        )

    @model_validator(mode="before")
    @classmethod
    def _a_retired_model_setting_is_refused(cls, data: Any) -> Any:
        retired = data.get(_RETIRED) if isinstance(data, dict) else None
        if retired:
            raise ValueError(
                f"{', '.join(retired)} is retired: the model now lives on the prompt record "
                "in sro.domain.prompts. Remove the key; a different model is a prompt change."
            )
        return data

    @field_validator("otlp_endpoint", mode="before")
    @classmethod
    def _blank_otlp_endpoint_is_off(cls, value: str | None) -> str | None:
        return value or None

    inline_body_limit_bytes: int = Field(default=256 * 1024)

    observation_artifact_bytes: int = 8_000_000

    observation_batch_events: int = 5000

    capture_drain_interval_seconds: float = 5.0
    capture_screenshot_per_frame: bool = True

    capture_video: bool = True

    capture_video_fps: int = 2

    capture_redact_secret_values: bool = True

    vault_project: str | None = None

    vault_path: str = "./.sro-vault"
    vault_key: str | None = None

    transcription_enabled: bool = False

    rig_sweep_seconds: float = 60.0

    mail_sweep_seconds: float = 60.0

    mining_window_hours: int = 24

    session_sweep_seconds: float = 600.0

    retention_sweep_seconds: float = 86400.0

    auth_secret: str = ""

    gemini_api_key: str = ""

    gemini_mine_timeout_ms: int = 600_000

    gemini_timeout_ms: int = 120_000

    gemini_read_tail: int = 0

    gemini_read_at_once: int = 8

    daily_usd_cap: float = -1.0

    gemini_embedding_model: str = "gemini-embedding-2"

    interpretation_enabled: bool = False

    vision_enabled: bool = False

    keycloak_realm_url: str = ""

    keycloak_client_id: str = ""

    keycloak_client_secret: str = ""
    knowledge_embeddings_enabled: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
