"""Gemini, with structured output and a bill.

Every call records its tokens and what they cost. A model call with no cost row
is a model call nobody can defend at the end of the month.

Search grounding is never enabled: it voids zero data retention (thirty days of
storage, no opt-out), and this process reads live customer payloads.
"""

import asyncio
import json
import weakref
from dataclasses import dataclass
from typing import Any, Literal, Protocol

_LOCKS: weakref.WeakKeyDictionary[asyncio.AbstractEventLoop, dict[str, asyncio.Lock]] = (
    weakref.WeakKeyDictionary()
)


def one_at_a_time(name: str) -> asyncio.Lock:
    """The named lock belonging to the running event loop, made on first use.

    A module-level `asyncio.Lock()` binds to whichever loop first touches it and
    raises `Lock is bound to a different event loop` for every loop after --
    which is what `api._reading` and `mine._mining` were, and what broke the
    moment the suite ran in more than one shard. Latent in production
    too: any process that restarts its loop, and any test runner that gives each
    test its own, hits the same wall.

    Keyed weakly, so a finished loop takes its locks with it rather than pinning
    them for the life of the process.
    """
    return _LOCKS.setdefault(asyncio.get_running_loop(), {}).setdefault(name, asyncio.Lock())


# Dollars per million tokens, (input, output).
PRICES: dict[str, tuple[float, float]] = {
    "gemini-3.8-flash": (0.75, 3.75),  # introductory, to 2026-12-31
    "gemini-3-flash": (0.50, 3.00),
    "gemini-3.1-flash-lite": (0.25, 1.50),
    "gemini-3.1-pro": (2.00, 12.00),  # doubles to (4, 18) above 200K
    # A preview is priced like the model it previews. Without these rows a real
    # pass on a preview name records cost_usd 0.0 with unpriced=True -- which is
    # honest, and useless: the measurement run that proved this architecture
    # works billed $1.12 and every row said free. A name missing from this table
    # is the one failure mode `unpriced` cannot fix, because nothing downstream
    # can price a call the table never knew about.
    "gemini-3.1-pro-preview": (2.00, 12.00),
    "gemini-3-flash-preview": (0.50, 3.00),
    "gemini-3.8-flash-preview": (0.75, 3.75),
    # Anthropic, for the bake-off. The rig asks Gemini in production; these
    # rows exist so a comparison run is priced by the same arithmetic as
    # everything else rather than by a spreadsheet nobody committed.
    "claude-haiku-4-5-20251001": (1.00, 5.00),
    "claude-haiku-4.5": (1.00, 5.00),
    "claude-sonnet-5": (2.00, 10.00),
}

LONG_PROMPT_TOKENS = 200_000

# Above a 200K-token prompt, Gemini 3.1 Pro's rates double.
LONG_PROMPT_PRICES: dict[str, tuple[float, float]] = {
    "gemini-3.1-pro": (4.00, 18.00),
    "gemini-3.1-pro-preview": (4.00, 18.00),
}


def price(model: str, in_tokens: int, out_tokens: int) -> float:
    rates = PRICES.get(model)
    if rates is None:
        return 0.0
    if in_tokens > LONG_PROMPT_TOKENS:
        rates = LONG_PROMPT_PRICES.get(model, rates)
    return in_tokens * rates[0] / 1_000_000 + out_tokens * rates[1] / 1_000_000


def is_priced(model: str) -> bool:
    return model in PRICES


# The levels the SDK accepts. Narrowed to a Literal rather than left as str
# because google-genai does not reject an unknown one: ThinkingLevel("nonsense")
# returns a pseudo-member carrying the typo straight to the API on 2.22.0. A
# constant that silently means "model default" is the exact failure wiring
# K_EFFORT was meant to close, one layer down, so mypy catches it instead.
Effort = Literal["minimal", "low", "medium", "high"]


@dataclass(frozen=True, slots=True)
class Answer:
    data: dict[str, Any] | None = None
    in_tokens: int = 0
    out_tokens: int = 0
    # Part of out_tokens for pricing, kept separately so a reader can see how
    # much of the bill was reasoning nobody ever read.
    thought_tokens: int = 0
    cost_usd: float = 0.0
    # True when cost_usd cannot be trusted: the model is missing from PRICES,
    # or the SDK did not give back real usage counts. A $0.00 row and an
    # honestly-unpriced row look the same in cost_usd alone -- this is what
    # tells them apart.
    unpriced: bool = False
    error: str | None = None


class Asker(Protocol):
    async def ask(
        self,
        *,
        model: str,
        instructions: str,
        evidence: str,
        schema: dict[str, Any],
        image: bytes | None = None,
        images: tuple[bytes, ...] = (),
        effort: Effort | None = None,
    ) -> Answer: ...


K_MAX_OUTPUT_TOKENS = 65536
"""What one answer may run to. A mining pass writes every workflow it found,
each step citing gestures by id; a day's worth is thousands of tokens and the
default ceiling cut one off.

Thinking is counted inside this on Gemini, not beside it, and that is a trap
worth knowing: Gemini 3.8 Flash at effort `high` spent 62,913 of the 65,536
thinking about one day of evidence and had 2,609 left to write its answer in --
truncated, three runs out of three, $0.38 each for nothing. A budget cannot fix
it (the API takes a level or a budget, never both, and this model ignores the
budget); the level is the knob, and a model that thinks too much for its own
ceiling needs a lower one. Anthropic bills thinking outside its ceiling and is
unaffected."""


def truncated(response: Any) -> bool:
    """Whether the model stopped because it hit the output ceiling. The SDK
    says so on the candidate's `finish_reason`; compared by name so a fake and
    the enum both read. A cut-off answer is not "not json": it is a page the
    model was not allowed to finish, and the row should say which."""
    candidates = getattr(response, "candidates", None) or []
    reason = getattr(candidates[0], "finish_reason", None) if candidates else None
    name = getattr(reason, "name", None) or (str(reason) if reason is not None else "")
    return "MAX_TOKENS" in name.upper()


def build_config(*, schema: dict[str, Any], effort: Effort | None = None) -> Any:
    """The config every call uses. No tools, ever — see the module docstring."""
    from google.genai import types

    return types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=schema,
        # The most the model may write back. Left to the default, a mining
        # pass over a whole day came back cut mid-string at 17,313 characters
        # and was filed as "not json": $1.16 for nothing, and nothing said
        # why. The models this rig names all write up to this.
        max_output_tokens=K_MAX_OUTPUT_TOKENS,
        # Self-consistency was measured at a 0.4% gain for 20x the cost, so
        # K_SAMPLES is 1 and this is the knob instead. None leaves the model's
        # own default alone, which is what the per-gesture reading wants.
        # ThinkingLevel(...) because the SDK types the field as its own enum,
        # and a plain str fails mypy. It takes "high" case-insensitively.
        thinking_config=None
        if effort is None
        else types.ThinkingConfig(thinking_level=types.ThinkingLevel(effort)),
    )


class GeminiAsker:
    def __init__(self, api_key: str, client: Any | None = None) -> None:
        """`client` is for tests; production passes an api_key and nothing else."""
        if client is not None:
            self._client = client
            return
        from google import genai

        self._client = genai.Client(api_key=api_key)

    async def ask(
        self,
        *,
        model: str,
        instructions: str,
        evidence: str,
        schema: dict[str, Any],
        image: bytes | None = None,
        images: tuple[bytes, ...] = (),
        effort: Effort | None = None,
    ) -> Answer:
        from google.genai import types

        # A falsy instruction would otherwise ship as a leading Part(text=''):
        # benign in the SDK, and rejected by some endpoints. umbrella.py passes
        # instructions="" on every call.
        parts: list[Any] = [part for part in (instructions, evidence) if part]
        if image is not None:
            parts.append(types.Part.from_bytes(data=image, mime_type="image/png"))
        # Further pictures, in the order given: a rescue shows the page as it
        # is now and then the page the failed attempt left behind.
        for more in images:
            parts.append(types.Part.from_bytes(data=more, mime_type="image/png"))

        try:
            response = await self._client.aio.models.generate_content(
                model=model,
                contents=parts,
                config=build_config(schema=schema, effort=effort),
            )
        except Exception as problem:  # noqa: BLE001 -- a rig keeps going; the row records why
            # The call may or may not have been billed before it failed, and we
            # cannot tell -- so the cost figure (0.0 here) is not to be trusted.
            return Answer(unpriced=True, error=f"{type(problem).__name__}: {problem}")

        usage = getattr(response, "usage_metadata", None)
        raw_in = getattr(usage, "prompt_token_count", None)
        raw_out = getattr(usage, "candidates_token_count", None)
        # Thinking tokens are billed at the OUTPUT rate, with no discount tier,
        # and candidates_token_count does not include them -- the SDK carries
        # them separately. Reading only candidates_token_count understated every
        # figure this rig has ever produced, and understated them by more the
        # harder the prompt was. K_EFFORT = "high" exists to spend these, so a
        # short visible answer can carry thousands of billed tokens the bill
        # showed and we did not.
        thought_tokens = getattr(usage, "thoughts_token_count", None) or 0
        usage_missing = raw_in is None or raw_out is None
        in_tokens = raw_in or 0
        # Kept apart in the record and added together for the bill: one number
        # says what the model wrote, the other says what it cost.
        out_tokens = (raw_out or 0) + thought_tokens
        unpriced = usage_missing or not is_priced(model)
        cost = price(model, in_tokens, out_tokens)

        if response.text is None:
            # The SDK returns None rather than raising when a call is blocked or
            # comes back with no candidates. Parsing that as "{}" would file a
            # refusal as a confident empty answer.
            return Answer(
                in_tokens=in_tokens,
                out_tokens=out_tokens,
                thought_tokens=thought_tokens,
                cost_usd=cost,
                unpriced=unpriced,
                error="the model returned no text (blocked, or no candidates)",
            )

        try:
            data = json.loads(response.text)
        except ValueError as problem:
            why = (
                f"truncated: the answer hit the {K_MAX_OUTPUT_TOKENS} output-token ceiling"
                f" after {raw_out or 0} tokens"
                if truncated(response)
                else f"not json: {problem}"
            )
            return Answer(
                in_tokens=in_tokens,
                out_tokens=out_tokens,
                thought_tokens=thought_tokens,
                cost_usd=cost,
                unpriced=unpriced,
                error=why,
            )

        return Answer(
            data=data,
            in_tokens=in_tokens,
            out_tokens=out_tokens,
            thought_tokens=thought_tokens,
            cost_usd=cost,
            unpriced=unpriced,
        )


class FakeAsker:
    """Queued answers, and a record of every question.

    Not a dataclass: it takes *answers positionally, and @dataclass would
    replace this __init__ with a generated one.
    """

    def __init__(self, *answers: Answer) -> None:
        self.answers = list(answers)
        self.asked: list[dict[str, Any]] = []

    async def ask(
        self,
        *,
        model: str,
        instructions: str,
        evidence: str,
        schema: dict[str, Any],
        image: bytes | None = None,
        images: tuple[bytes, ...] = (),
        effort: Effort | None = None,
    ) -> Answer:
        # Yield, because the real thing does. Without a suspension point this
        # double never lets another task interleave, so any test racing two
        # callers with asyncio.gather passes whether or not the code under test
        # actually serialises -- it proves the double, not the code.
        await asyncio.sleep(0)
        self.asked.append(
            {
                "model": model,
                "instructions": instructions,
                "evidence": evidence,
                "schema": schema,
                "image": image,
                "images": images,
                "effort": effort,
            }
        )
        if not self.answers:
            return Answer(error="the fake ran out of answers")
        return self.answers.pop(0)
