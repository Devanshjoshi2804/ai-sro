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
    mine_model: str = "gemini-3.1-pro-preview"
    tenant: str = "new"

    daily_usd_cap: float = 5.0
    """What one day of reading may cost before the rig stops asking.

    read_on_ingest bills per gesture as capture arrives, so an unattended run
    spends whatever the operator's day produces. On the measured evidence that
    is about $0.37 per 81-gesture day, but the whole point of watching every tab
    is that a day is thousands, and nothing here knew what the ceiling was.

    A cap that stops reading is honest in a way a cap that stops CAPTURE is not:
    the evidence still arrives and is still stored, so raising this tomorrow
    reads what today declined. Zero disables reading entirely; a negative value
    means no cap, which is what a deliberate one-off measurement wants."""


@lru_cache
def settings() -> Settings:
    return Settings()
