import asyncio
import json
from types import SimpleNamespace
from typing import Any

import pytest

from rig.models import PRICES, Answer, FakeAsker, GeminiAsker, price


def test_a_price_is_dollars_per_million_tokens() -> None:
    """Gemini 3.8 Flash: $0.75 in, $3.75 out, introductory to 2026-12-31."""
    assert PRICES["gemini-3.8-flash"] == (0.75, 3.75)

    assert price("gemini-3.8-flash", 1_000_000, 0) == pytest.approx(0.75)
    assert price("gemini-3.8-flash", 0, 1_000_000) == pytest.approx(3.75)
    assert price("gemini-3.8-flash", 1000, 200) == pytest.approx(0.00075 + 0.00075)


def test_an_unknown_model_costs_nothing_and_does_not_raise() -> None:
    """A rig must not fall over because a price list is stale."""
    assert price("gemini-9-imaginary", 1000, 1000) == 0.0


def test_a_long_prompt_doubles_gemini_3_1_pro_rates() -> None:
    """Above 200K input tokens the standard rate no longer applies."""
    under = price("gemini-3.1-pro", 200_000, 0)
    over = price("gemini-3.1-pro", 200_001, 0)

    assert under == pytest.approx(200_000 * 2.00 / 1_000_000)
    assert over == pytest.approx(200_001 * 4.00 / 1_000_000)


async def test_a_fake_asker_records_what_it_was_asked() -> None:
    asker = FakeAsker(Answer(data={"act": "typed a client code"}, in_tokens=10, out_tokens=5))

    answer = await asker.ask(
        model="gemini-3.8-flash",
        instructions="read this",
        evidence="{}",
        schema={"type": "object"},
    )

    assert answer.data == {"act": "typed a client code"}
    assert asker.asked[0]["model"] == "gemini-3.8-flash"


async def test_a_fake_asker_runs_out_and_says_so() -> None:
    asker = FakeAsker()

    answer = await asker.ask(model="m", instructions="i", evidence="e", schema={"type": "object"})

    assert answer.data is None
    assert answer.error


def test_the_request_config_never_enables_search_grounding() -> None:
    """Grounding voids zero data retention: 30-day storage, no opt-out."""
    from rig.models import build_config

    config = build_config(schema={"type": "object"})

    assert getattr(config, "tools", None) is None
    assert config.response_mime_type == "application/json"


class _FakeModels:
    """Stands in for `client.aio.models`: records the config it was sent."""

    def __init__(self, respond: Any) -> None:
        self._respond = respond
        self.last_config: Any = None
        self.last_contents: Any = None

    async def generate_content(self, *, model: str, contents: Any, config: Any) -> Any:
        self.last_config = config
        self.last_contents = contents
        return self._respond()


def _fake_client(respond: Any) -> tuple[Any, _FakeModels]:
    """A `google.genai.Client`-shaped stub. No network, ever."""
    models = _FakeModels(respond)
    return SimpleNamespace(aio=SimpleNamespace(models=models)), models


async def test_gemini_asker_happy_path_parses_data_and_prices_it() -> None:
    usage = SimpleNamespace(prompt_token_count=10, candidates_token_count=5)
    response = SimpleNamespace(text=json.dumps({"act": "typed a code"}), usage_metadata=usage)
    client, _ = _fake_client(lambda: response)
    asker = GeminiAsker(api_key="unused", client=client)

    answer = await asker.ask(
        model="gemini-3.8-flash", instructions="i", evidence="e", schema={"type": "object"}
    )

    assert answer.data == {"act": "typed a code"}
    assert answer.in_tokens == 10
    assert answer.out_tokens == 5
    assert answer.unpriced is False
    assert answer.error is None
    assert answer.cost_usd == pytest.approx(price("gemini-3.8-flash", 10, 5))


async def test_gemini_asker_reports_a_blocked_response_as_an_error() -> None:
    """A blocked call must never be filed as a confident empty answer."""
    usage = SimpleNamespace(prompt_token_count=10, candidates_token_count=0)
    response = SimpleNamespace(text=None, usage_metadata=usage)
    client, _ = _fake_client(lambda: response)
    asker = GeminiAsker(api_key="unused", client=client)

    answer = await asker.ask(
        model="gemini-3.8-flash", instructions="i", evidence="e", schema={"type": "object"}
    )

    assert answer.data is None
    assert answer.error
    assert answer.in_tokens == 10


async def test_gemini_asker_reports_non_json_text_as_an_error() -> None:
    usage = SimpleNamespace(prompt_token_count=10, candidates_token_count=5)
    response = SimpleNamespace(text="not json", usage_metadata=usage)
    client, _ = _fake_client(lambda: response)
    asker = GeminiAsker(api_key="unused", client=client)

    answer = await asker.ask(
        model="gemini-3.8-flash", instructions="i", evidence="e", schema={"type": "object"}
    )

    assert answer.data is None
    assert answer.error
    assert answer.in_tokens == 10
    assert answer.out_tokens == 5


async def test_gemini_asker_flags_unpriced_when_usage_metadata_is_missing() -> None:
    response = SimpleNamespace(text="{}", usage_metadata=None)
    client, _ = _fake_client(lambda: response)
    asker = GeminiAsker(api_key="unused", client=client)

    answer = await asker.ask(
        model="gemini-3.8-flash", instructions="i", evidence="e", schema={"type": "object"}
    )

    assert answer.unpriced is True
    assert answer.in_tokens == 0
    assert answer.out_tokens == 0


async def test_gemini_asker_flags_unpriced_when_usage_counts_are_none() -> None:
    usage = SimpleNamespace(prompt_token_count=None, candidates_token_count=None)
    response = SimpleNamespace(text="{}", usage_metadata=usage)
    client, _ = _fake_client(lambda: response)
    asker = GeminiAsker(api_key="unused", client=client)

    answer = await asker.ask(
        model="gemini-3.8-flash", instructions="i", evidence="e", schema={"type": "object"}
    )

    assert answer.unpriced is True


async def test_gemini_asker_flags_unpriced_for_an_unknown_model() -> None:
    usage = SimpleNamespace(prompt_token_count=10, candidates_token_count=5)
    response = SimpleNamespace(text="{}", usage_metadata=usage)
    client, _ = _fake_client(lambda: response)
    asker = GeminiAsker(api_key="unused", client=client)

    answer = await asker.ask(
        model="gemini-9-imaginary", instructions="i", evidence="e", schema={"type": "object"}
    )

    assert answer.unpriced is True
    assert answer.cost_usd == 0.0


async def test_gemini_asker_survives_the_client_raising() -> None:
    def _raise() -> Any:
        raise RuntimeError("network is down")

    client, _ = _fake_client(_raise)
    asker = GeminiAsker(api_key="unused", client=client)

    answer = await asker.ask(
        model="gemini-3.8-flash", instructions="i", evidence="e", schema={"type": "object"}
    )

    assert answer.data is None
    assert answer.error
    assert answer.in_tokens == 0
    assert answer.cost_usd == 0.0


async def test_a_call_that_never_returned_does_not_claim_to_be_free() -> None:
    """We cannot tell whether it was billed before it failed, so the cost
    figure is not to be trusted -- which is what `unpriced` means."""

    def _raise() -> Any:
        raise RuntimeError("network is down")

    client, _ = _fake_client(_raise)
    asker = GeminiAsker(api_key="unused", client=client)

    answer = await asker.ask(
        model="gemini-3.8-flash", instructions="i", evidence="e", schema={"type": "object"}
    )

    assert answer.error
    assert answer.unpriced is True
    assert answer.cost_usd == 0.0


async def test_gemini_asker_ask_really_routes_through_build_config() -> None:
    """The seam a future edit must not be able to slip grounding past."""
    usage = SimpleNamespace(prompt_token_count=1, candidates_token_count=1)
    response = SimpleNamespace(text="{}", usage_metadata=usage)
    client, models = _fake_client(lambda: response)
    asker = GeminiAsker(api_key="unused", client=client)

    await asker.ask(
        model="gemini-3.8-flash", instructions="i", evidence="e", schema={"type": "object"}
    )

    assert getattr(models.last_config, "tools", None) is None


def test_the_config_carries_the_effort_and_still_no_tools() -> None:
    """Search grounding voids zero-data-retention and this rig reads live
    customer payloads. The effort knob must not smuggle a tool in beside it."""
    from google.genai import types

    from rig.models import build_config

    config = build_config(schema={"type": "object"}, effort="high")

    # The SDK coerces the string to its own enum, whose value is "HIGH".
    assert config.thinking_config.thinking_level == types.ThinkingLevel.HIGH
    assert not getattr(config, "tools", None)


def test_no_effort_builds_no_thinking_config() -> None:
    from rig.models import build_config

    assert build_config(schema={"type": "object"}).thinking_config is None


async def test_gemini_asker_hands_the_effort_to_the_config() -> None:
    from google.genai import types

    usage = SimpleNamespace(prompt_token_count=1, candidates_token_count=1)
    response = SimpleNamespace(text="{}", usage_metadata=usage)
    client, models = _fake_client(lambda: response)
    asker = GeminiAsker(api_key="unused", client=client)

    await asker.ask(
        model="gemini-3.8-flash",
        instructions="i",
        evidence="e",
        schema={"type": "object"},
        effort="low",
    )

    # The level, not just the wire: hardcoding "high" inside GeminiAsker left
    # an is-not-None assertion green.
    assert models.last_config.thinking_config.thinking_level == types.ThinkingLevel.LOW


async def test_an_empty_instruction_is_not_sent_as_an_empty_part() -> None:
    """umbrella.py passes instructions="" on purpose -- the prompt states the
    task at both ends and owns it. That reached the SDK as a leading
    Part(text=''), which some endpoints reject."""
    usage = SimpleNamespace(prompt_token_count=1, candidates_token_count=1)
    response = SimpleNamespace(text="{}", usage_metadata=usage)
    client, models = _fake_client(lambda: response)
    asker = GeminiAsker(api_key="unused", client=client)

    await asker.ask(
        model="gemini-3.8-flash", instructions="", evidence="e", schema={"type": "object"}
    )

    assert models.last_contents == ["e"]


def test_thinking_tokens_are_part_of_the_bill() -> None:
    """Thinking tokens bill at the output rate with no discount, and
    candidates_token_count does not include them -- so reading that field alone
    understated every figure this rig produced, by more the harder the prompt.
    K_EFFORT = "high" exists to spend them."""

    class _Usage:
        prompt_token_count = 1_000
        candidates_token_count = 200
        thoughts_token_count = 5_000

    class _Response:
        text = "{}"
        usage_metadata = _Usage()

    class _Models:
        async def generate_content(self, **_: object) -> _Response:
            return _Response()

    class _Client:
        aio = type("_Aio", (), {"models": _Models()})()

    asker = GeminiAsker(api_key="", client=_Client())
    answer = asyncio.run(
        asker.ask(model="gemini-3.1-pro", instructions="i", evidence="e", schema={})
    )

    assert answer.thought_tokens == 5_000
    assert answer.out_tokens == 5_200
    assert answer.cost_usd == price("gemini-3.1-pro", 1_000, 5_200)
    assert answer.cost_usd > price("gemini-3.1-pro", 1_000, 200)
