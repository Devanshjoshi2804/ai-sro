"""Asking Gemini for structured output, and paying for the answer.

Every call records its tokens and what they cost, names a cut-off answer as
cut off rather than as malformed, and never enables search grounding. The
named lock lives here too: it is what stops one loop's lock from being handed
to the next one.
"""

from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace
from typing import Any

import pytest

from sro.application.ports.model import Asker
from sro.application.shared.locks import one_at_a_time
from sro.domain.shared.prices import Answer, price
from sro.infrastructure.gemini.asker import GeminiAsker
from tests.unit.fakes import FakeAsker

# The one assertion here that mypy makes and pytest cannot: the real asker
# still satisfies the port every use case and every fake is written against.
# `client` sidesteps the google.genai import, so this costs nothing at import
# time and fails the type gate the moment the two signatures part.
_PORT: Asker = GeminiAsker(api_key="", client=object())


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
    from sro.infrastructure.gemini.asker import build_config

    config = build_config(schema={"type": "object"})

    assert getattr(config, "tools", None) is None
    assert config.response_mime_type == "application/json"


def test_the_request_config_lets_the_model_finish_a_whole_day() -> None:
    """A mining pass over 387 gestures came back cut mid-string under the
    default ceiling: $1.16 for nothing."""
    from sro.infrastructure.gemini.asker import K_MAX_OUTPUT_TOKENS, build_config

    assert K_MAX_OUTPUT_TOKENS >= 65536
    assert build_config(schema={"type": "object"}).max_output_tokens == K_MAX_OUTPUT_TOKENS


async def test_gemini_asker_names_a_cut_off_answer_rather_than_calling_it_not_json() -> None:
    from sro.infrastructure.gemini.asker import K_MAX_OUTPUT_TOKENS

    usage = SimpleNamespace(prompt_token_count=10, candidates_token_count=65536)
    cut = SimpleNamespace(
        text='{"workflows": [{"title": "Create Work Ar',
        usage_metadata=usage,
        candidates=[SimpleNamespace(finish_reason=SimpleNamespace(name="MAX_TOKENS"))],
    )
    client, _ = _fake_client(lambda: cut)
    answer = await GeminiAsker(api_key="unused", client=client).ask(
        model="gemini-3.1-pro-preview", instructions="i", evidence="e", schema={"type": "object"}
    )
    assert answer.data is None
    assert answer.error and answer.error.startswith("truncated:"), answer.error
    assert str(K_MAX_OUTPUT_TOKENS) in answer.error and "65536 tokens" in answer.error
    assert answer.cost_usd > 0 and answer.unpriced is False, "it was billed, and the bill stands"
    # The same broken text with an ordinary finish is still "not json".
    stopped = SimpleNamespace(
        text='{"workflows": [{"title": "Create Work Ar',
        usage_metadata=usage,
        candidates=[SimpleNamespace(finish_reason="STOP")],
    )
    client, _ = _fake_client(lambda: stopped)
    answer = await GeminiAsker(api_key="unused", client=client).ask(
        model="gemini-3.1-pro-preview", instructions="i", evidence="e", schema={"type": "object"}
    )
    assert answer.error and answer.error.startswith("not json:")


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

    from sro.infrastructure.gemini.asker import build_config

    config = build_config(schema={"type": "object"}, effort="high")

    # The SDK coerces the string to its own enum, whose value is "HIGH".
    assert config.thinking_config.thinking_level == types.ThinkingLevel.HIGH
    assert not getattr(config, "tools", None)


def test_no_effort_builds_no_thinking_config() -> None:
    from sro.infrastructure.gemini.asker import build_config

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
    K_EFFORT exists to spend them, and is what makes them worth reading."""

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


def test_a_lock_belongs_to_the_loop_that_asked_for_it() -> None:
    """`_reading` and `_mining` were module-level `asyncio.Lock()`s, so they
    bound to whichever event loop first awaited them and every loop after that
    got `Lock is bound to a different event loop`. Latent in production, not
    just under a test runner: any process that restarts its loop hits it, and
    so does any sharded or reordered CI run.
    """

    async def taken() -> asyncio.Lock:
        async with one_at_a_time("mining") as _:
            pass
        return one_at_a_time("mining")

    first, second = asyncio.run(taken()), asyncio.run(taken())

    assert first is not second


def test_one_loop_gets_one_lock_per_name() -> None:
    """A fresh lock per call would exclude nothing at all, which is the way
    this fix fails silently rather than loudly."""

    async def within_one_loop() -> tuple[bool, bool]:
        return (
            one_at_a_time("mining") is one_at_a_time("mining"),
            one_at_a_time("mining") is one_at_a_time("reading"),
        )

    same_name, different_names = asyncio.run(within_one_loop())

    assert same_name
    assert not different_names


def test_the_lock_still_excludes() -> None:
    """The property the lock exists for: the second pass waits."""

    order: list[str] = []

    async def pass_(name: str, hold: float) -> None:
        async with one_at_a_time("mining"):
            order.append(f"{name} in")
            await asyncio.sleep(hold)
            order.append(f"{name} out")

    async def both() -> None:
        await asyncio.gather(pass_("a", 0.01), pass_("b", 0))

    asyncio.run(both())

    assert order == ["a in", "a out", "b in", "b out"]
