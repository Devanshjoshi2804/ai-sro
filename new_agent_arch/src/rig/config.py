"""Settings. Env prefix RIG_, so nothing collides with the backend's SRO_."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="RIG_", env_file=".env", extra="ignore")

    db_path: Path = Path("rig.db")
    gemini_api_key: str = ""
    ingest_token: str = "dev-only-not-a-secret"
    intent_model: str = "gemini-3.8-flash"
    tenant: str = "new"


@lru_cache
def settings() -> Settings:
    return Settings()
