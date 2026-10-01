"""Which model an eval run asks: the recorded one, another Gemini, or an OpenRouter model."""

from __future__ import annotations

import pytest
from evals.models import OpenRouterAsker, Overridden, chosen

from sro.domain.shared.prices import Answer


class _Spy:
    def __init__(self) -> None:
        self.seen: dict[str, object] = {}

    async def ask(self, **kwargs: object) -> Answer:
        self.seen = kwargs
        return Answer(data={"ok": True})


async def test_another_model_and_thinking_level_reach_the_wrapped_asker() -> None:
    spy = _Spy()
    asker = chosen(spy, provider="gemini", model="gemini-3.7-flash", thinking="low")

    assert isinstance(asker, Overridden)
    await asker.ask(
        model="gemini-3.8-flash", instructions="i", evidence="e", schema={}, effort=None
    )
    assert spy.seen["model"] == "gemini-3.7-flash" and spy.seen["effort"] == "low"


async def test_thinking_default_means_the_models_own_default() -> None:
    spy = _Spy()
    asker = chosen(spy, provider="gemini", model=None, thinking="default")

    assert asker is not None
    await asker.ask(model="m", instructions="i", evidence="e", schema={}, effort="low")
    assert spy.seen["effort"] is None and spy.seen["model"] == "m"


def test_nothing_chosen_is_the_recorded_asker() -> None:
    spy = _Spy()
    assert chosen(spy, provider="gemini", model=None, thinking=None) is spy


def test_openrouter_needs_a_model_and_a_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    with pytest.raises(SystemExit):
        chosen(None, provider="openrouter", model="qwen/qwen3.8-flash", thinking=None)
    monkeypatch.setenv("OPENROUTER_API_KEY", "k")
    assert isinstance(
        chosen(None, provider="openrouter", model="qwen/qwen3.8-flash", thinking=None),
        OpenRouterAsker,
    )


def test_openai_strict_schema_requires_every_key_and_allows_null_for_the_optional_ones() -> None:
    from evals.models import strict

    schema = {
        "type": "object",
        "properties": {"action": {"type": "string"}, "text": {"type": "string"}},
        "required": ["action"],
    }

    out = strict(schema)

    assert out["required"] == ["action", "text"] and out["additionalProperties"] is False
    assert out["properties"]["action"]["type"] == "string"
    assert out["properties"]["text"]["type"] == ["string", "null"]
    assert schema["required"] == ["action"]  # the original is not touched
