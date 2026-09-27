from pathlib import Path

import pytest
from pydantic import ValidationError

from sro.config import Settings

_RETIRED = (
    "SRO_GEMINI_PLAN_MODEL",
    "SRO_GEMINI_RESCUE_MODEL",
    "SRO_GEMINI_VISION_MODEL",
    "SRO_GEMINI_INTENT_MODEL",
    "SRO_GEMINI_INTERPRETER_MODEL",
    "SRO_GEMINI_TRANSCRIPTION_MODEL",
)


@pytest.mark.parametrize("key", _RETIRED)
def test_a_retired_model_setting_in_the_environment_stops_the_load(
    key: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(key, "gemini-anything")

    with pytest.raises(ValidationError) as refused:
        Settings(_env_file=None)

    assert key in str(refused.value)
    assert "the model now lives on the prompt record" in str(refused.value)


@pytest.mark.parametrize("key", _RETIRED)
def test_a_retired_model_setting_in_the_env_file_stops_the_load(key: str, tmp_path: Path) -> None:
    env = tmp_path / ".env"
    env.write_text(f"{key}=gemini-anything\n", encoding="utf-8")

    with pytest.raises(ValidationError) as refused:
        Settings(_env_file=env)

    assert key in str(refused.value)


def test_the_embedding_model_is_still_a_setting(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SRO_GEMINI_EMBEDDING_MODEL", "gemini-embedding-001")

    assert Settings(_env_file=None).gemini_embedding_model == "gemini-embedding-001"
