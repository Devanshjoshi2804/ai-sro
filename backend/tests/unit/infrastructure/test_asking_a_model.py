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
from sro.infrastructure.gemini.asker import K_TRIES, GeminiAsker
from sro.infrastructure.gemini.metered import Meter, metered_client
from tests.unit.fakes import FakeAsker, FakeClock, FakeUnitOfWork

# The one assertion here that mypy makes and pytest cannot: the real asker
# still satisfies the port every use case and every fake is written against.
# `client` sidesteps the google.genai import, so this costs nothing at import
# time and fails the type gate the moment the two signatures part.
_PORT: Asker = GeminiAsker(client=object())


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
    answer = await GeminiAsker(client=client).ask(
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
    answer = await GeminiAsker(client=client).ask(
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
    asker = GeminiAsker(client=client)

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
    asker = GeminiAsker(client=client)

    answer = await asker.ask(
        model="gemini-3.8-flash", instructions="i", evidence="e", schema={"type": "object"}
    )

    assert answer.data is None
    assert answer.error and not answer.unreachable
    assert answer.in_tokens == 10


async def test_gemini_asker_reports_non_json_text_as_an_error() -> None:
    usage = SimpleNamespace(prompt_token_count=10, candidates_token_count=5)
    response = SimpleNamespace(text="not json", usage_metadata=usage)
    client, _ = _fake_client(lambda: response)
    asker = GeminiAsker(client=client)

    answer = await asker.ask(
        model="gemini-3.8-flash", instructions="i", evidence="e", schema={"type": "object"}
    )

    assert answer.data is None
    assert answer.error and not answer.unreachable
    assert answer.in_tokens == 10
    assert answer.out_tokens == 5


async def test_gemini_asker_flags_unpriced_when_usage_metadata_is_missing() -> None:
    response = SimpleNamespace(text="{}", usage_metadata=None)
    client, _ = _fake_client(lambda: response)
    asker = GeminiAsker(client=client)

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
    asker = GeminiAsker(client=client)

    answer = await asker.ask(
        model="gemini-3.8-flash", instructions="i", evidence="e", schema={"type": "object"}
    )

    assert answer.unpriced is True


async def test_gemini_asker_flags_unpriced_for_an_unknown_model() -> None:
    usage = SimpleNamespace(prompt_token_count=10, candidates_token_count=5)
    response = SimpleNamespace(text="{}", usage_metadata=usage)
    client, _ = _fake_client(lambda: response)
    asker = GeminiAsker(client=client)

    answer = await asker.ask(
        model="gemini-9-imaginary", instructions="i", evidence="e", schema={"type": "object"}
    )

    assert answer.unpriced is True
    assert answer.cost_usd == 0.0


async def test_gemini_asker_survives_the_client_raising() -> None:
    def _raise() -> Any:
        raise RuntimeError("network is down")

    client, _ = _fake_client(_raise)
    asker = GeminiAsker(client=client)

    answer = await asker.ask(
        model="gemini-3.8-flash", instructions="i", evidence="e", schema={"type": "object"}
    )

    assert answer.data is None
    assert answer.error and answer.unreachable
    assert answer.in_tokens == 0
    assert answer.cost_usd == 0.0


async def test_a_call_that_never_returned_does_not_claim_to_be_free() -> None:
    """We cannot tell whether it was billed before it failed, so the cost
    figure is not to be trusted -- which is what `unpriced` means."""

    def _raise() -> Any:
        raise RuntimeError("network is down")

    client, _ = _fake_client(_raise)
    asker = GeminiAsker(client=client)

    answer = await asker.ask(
        model="gemini-3.8-flash", instructions="i", evidence="e", schema={"type": "object"}
    )

    assert answer.error
    assert answer.unpriced is True
    assert answer.cost_usd == 0.0


@pytest.fixture(autouse=True)
def _no_waiting(monkeypatch: pytest.MonkeyPatch) -> None:
    """The backoff is real and this suite must not sit through it. Patched at
    the module the asker reads it from, so the retry COUNT is still exercised
    -- only the waiting is skipped."""
    monkeypatch.setattr("sro.infrastructure.gemini.asker.K_BACKOFF_S", 0.0)


class _Flaky:
    """Fails with the given exception `times` times, then answers."""

    def __init__(self, problem: Exception, times: int, answer: Any) -> None:
        self.problem, self.left, self.answer = problem, times, answer
        self.calls = 0

    def __call__(self) -> Any:
        self.calls += 1
        if self.left > 0:
            self.left -= 1
            raise self.problem
        return self.answer


def _server_error(code: int) -> Exception:
    """What the SDK raises when the far end gives up: an exception carrying an
    HTTP `code`. Read off `code` rather than by class name, so this test does
    not pin the SDK's own naming."""
    problem = RuntimeError(f"{code} DEADLINE_EXCEEDED")
    problem.code = code
    return problem


async def test_a_server_that_gave_up_is_asked_again() -> None:
    """Two of three real mining passes over acme's 555 gestures died on a 504
    DEADLINE_EXCEEDED from Google's backend on a 154,200-token prompt -- not a
    client timeout, which raises `httpx.ReadTimeout`, but the far end giving up
    on a large request. A mining prompt is two orders of magnitude bigger than
    a reading prompt, so it lands there and almost never on a reading."""
    usage = SimpleNamespace(prompt_token_count=10, candidates_token_count=5)
    good = SimpleNamespace(text=json.dumps({"act": "typed a code"}), usage_metadata=usage)
    flaky = _Flaky(_server_error(504), times=2, answer=good)
    client, _ = _fake_client(flaky)
    asker = GeminiAsker(client=client)

    answer = await asker.ask(
        model="gemini-3.8-flash", instructions="i", evidence="e", schema={"type": "object"}
    )

    assert flaky.calls == 3
    assert answer.data == {"act": "typed a code"}
    assert answer.error is None
    assert answer.unpriced is False


async def test_a_refusal_this_deployment_earned_is_not_asked_again() -> None:
    """A 4xx is this deployment being wrong -- a bad schema, a revoked key, a
    quota -- and asking again spends money to be told the same thing. 429 is
    deliberately in that group: it is the quota speaking, and hammering it is
    how a rate limit becomes a ban."""
    for code in (400, 403, 429):
        flaky = _Flaky(_server_error(code), times=99, answer=None)
        client, _ = _fake_client(flaky)
        asker = GeminiAsker(client=client)

        answer = await asker.ask(
            model="gemini-3.8-flash", instructions="i", evidence="e", schema={"type": "object"}
        )

        assert flaky.calls == 1, f"{code} should not be retried"
        assert answer.error
        assert answer.unpriced is True


async def test_a_server_that_never_comes_back_is_recorded_as_failed_not_retried_forever() -> None:
    flaky = _Flaky(_server_error(503), times=99, answer=None)
    client, _ = _fake_client(flaky)
    asker = GeminiAsker(client=client)

    answer = await asker.ask(
        model="gemini-3.8-flash", instructions="i", evidence="e", schema={"type": "object"}
    )

    assert flaky.calls == K_TRIES
    assert answer.error
    # Still unpriced: an attempt may have been billed before it failed, and
    # three attempts means three chances of that.
    assert answer.unpriced is True


async def test_gemini_asker_ask_really_routes_through_build_config() -> None:
    """The seam a future edit must not be able to slip grounding past."""
    usage = SimpleNamespace(prompt_token_count=1, candidates_token_count=1)
    response = SimpleNamespace(text="{}", usage_metadata=usage)
    client, models = _fake_client(lambda: response)
    asker = GeminiAsker(client=client)

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
    asker = GeminiAsker(client=client)

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
    asker = GeminiAsker(client=client)

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

    asker = GeminiAsker(client=_Client())
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


def test_a_real_client_is_built_with_a_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    """The SDK's own default is no timeout, and no timeout is not a duration.

    Measured: one call whose socket stayed ESTABLISHED but never answered held
    a reading pass for 19 hours, having read nothing. `sro.cli.read_cron` runs
    that pass nightly with nobody watching, so the ceiling is the difference
    between one lost gesture and one lost night.
    """
    from google import genai

    built: dict[str, Any] = {}

    def _client(**kwargs: Any) -> object:
        built.update(kwargs)
        return SimpleNamespace(aio=SimpleNamespace(models=object()))

    monkeypatch.setattr(genai, "Client", _client)
    metered_client("k", Meter(FakeUnitOfWork, clock=FakeClock(), cap_usd=-1.0), timeout_ms=90_000)

    options = built.get("http_options")
    assert options is not None, "the client was built with no http_options at all"
    assert options.timeout == 90_000


# -- a truncated answer is a level to lower, not a failure to report ----------
#
# `maxOutputTokens` is a hard ceiling on thinking AND answer together -- Google
# says so in as many words -- and 65,536 is the model's own limit rather than a
# setting. There is no thinking budget on Gemini 3.x. So the only remedy is to
# think less, and the pass may as well do it itself.
#
# Measured on the deployment 2026-09-21: the same 158,193-token window that
# spent all 65,536 tokens thinking at `medium` and answered nothing answered at
# `low` in 10,757 tokens for $0.16, and kept a job. Without this the pass cost
# $0.36 and yielded nothing.


def _cut_off() -> Any:
    return SimpleNamespace(
        text='{"workflows": [{"title": "Create Work Ar',
        usage_metadata=SimpleNamespace(prompt_token_count=100, candidates_token_count=65536),
        candidates=[SimpleNamespace(finish_reason=SimpleNamespace(name="MAX_TOKENS"))],
    )


def _answered() -> Any:
    return SimpleNamespace(
        text=json.dumps({"workflows": []}),
        usage_metadata=SimpleNamespace(prompt_token_count=100, candidates_token_count=20),
    )


async def test_an_answer_cut_off_by_the_ceiling_is_asked_again_thinking_less() -> None:
    answers = iter([_cut_off(), _answered()])
    client, models = _fake_client(lambda: next(answers))

    answer = await GeminiAsker(client=client).ask(
        model="gemini-3.8-flash",
        instructions="i",
        evidence="e",
        schema={"type": "object"},
        effort="medium",
    )

    assert answer.data == {"workflows": []}, "it gave up on a call it could have finished"
    assert models.last_config.thinking_config.thinking_level.value.lower() == "low"
    # Both calls were billed -- the first said nothing and was charged for it --
    # so the row carries the sum rather than only the answer that arrived.
    assert answer.in_tokens == 200
    assert answer.out_tokens == 65556
    assert answer.cost_usd == pytest.approx(
        price("gemini-3.8-flash", 100, 65536) + price("gemini-3.8-flash", 100, 20)
    ), "the pass that had to ask twice was charged for one call"
    assert answer.error is None


async def test_it_asks_again_once_and_not_forever() -> None:
    """A second ceiling is a window too big for this model at any level it can
    step down to from here, and the row should say so rather than the process
    spending the tenant's day finding out."""
    client, _ = _fake_client(_cut_off)

    answer = await GeminiAsker(client=client).ask(
        model="gemini-3.8-flash",
        instructions="i",
        evidence="e",
        schema={"type": "object"},
        effort="medium",
    )

    assert answer.error and answer.error.startswith("truncated:")
    assert answer.out_tokens == 131072, "both attempts are on the bill"


async def test_a_call_that_named_no_level_has_none_to_lower() -> None:
    """Most callers. Nothing here invents a level for a caller that did not
    ask for one -- that would change what every other door sends."""
    calls = []

    def _once() -> Any:
        calls.append(1)
        return _cut_off()

    client, _ = _fake_client(_once)

    answer = await GeminiAsker(client=client).ask(
        model="gemini-3.8-flash", instructions="i", evidence="e", schema={"type": "object"}
    )

    assert len(calls) == 1
    assert answer.error and answer.error.startswith("truncated:")


async def test_a_call_already_thinking_as_little_as_it_can_is_not_asked_again() -> None:
    calls = []

    def _once() -> Any:
        calls.append(1)
        return _cut_off()

    client, _ = _fake_client(_once)

    await GeminiAsker(client=client).ask(
        model="gemini-3.8-flash",
        instructions="i",
        evidence="e",
        schema={"type": "object"},
        effort="minimal",
    )

    assert len(calls) == 1, "there is no level below minimal"
