"""Settings. Env prefix RIG_, so nothing collides with the backend's SRO_."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="RIG_", env_file=".env", extra="ignore")

    db_path: Path = Path("rig.db")
    gemini_api_key: str = ""
    anthropic_api_key: str = ""
    """Only the bake-off asks Anthropic. Empty is the ordinary state: the
    rig runs on Gemini, and a key here buys a comparison, not a dependency."""

    ingest_token: str = "dev-only-not-a-secret"
    intent_model: str = "gemini-3.8-flash"
    mine_model: str = "gemini-3.1-pro-preview"
    tenant: str = "new"

    daily_usd_cap: float = 5.0
    """What one day of model calls may cost before the rig stops asking:
    readings, mining passes, runs and the chat door, summed.

    read_on_ingest bills per gesture as capture arrives, so an unattended run
    spends whatever the operator's day produces. On the measured evidence that
    is about $0.37 per 81-gesture day, but the whole point of watching every tab
    is that a day is thousands, and nothing here knew what the ceiling was. A
    pass or a run is a bigger call than a reading, and the cap that saw only
    readings let a day of those through untouched.

    A cap that stops asking is honest in a way a cap that stops CAPTURE is not:
    the evidence still arrives and is still stored, so raising this tomorrow
    reads what today declined. Over the cap, `/v1/mine`, `/v1/chat` and
    `POST /v1/runs` answer 429 and say how much of what. Zero disables the
    asking entirely; a negative value means no cap, which is what a deliberate
    one-off measurement wants. A run already going finishes on its own budget."""

    plan_model: str = "gemini-3.8-flash"
    """Plans one command per step. Small models match frontier ones at this
    class of inference; a clean step never touches the expensive one."""

    rescue_model: str = "gemini-3.1-pro-preview"
    """Retries a step once, with both screenshots and the failure. Only a step
    that surprised the planner costs what surprises cost."""

    command_deadline_s: float = 20.0


@lru_cache
def settings() -> Settings:
    return Settings()
