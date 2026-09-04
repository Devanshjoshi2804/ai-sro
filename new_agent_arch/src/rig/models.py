"""Gemini, with structured output and a bill.

Every call records its tokens and what they cost. A model call with no cost row
is a model call nobody can defend at the end of the month.

Search grounding is never enabled: it voids zero data retention (thirty days of
storage, no opt-out), and this process reads live customer payloads.
"""

import asyncio
import json
from dataclasses import dataclass
from typing import Any, Protocol

# Dollars per million tokens, (input, output).
PRICES: dict[str, tuple[float, float]] = {
    "gemini-3.8-flash": (0.75, 3.75),  # introductory, to 2026-12-31
    "gemini-3-flash": (0.50, 3.00),
    "gemini-3.1-flash-lite": (0.25, 1.50),
    "gemini-3.1-pro": (2.00, 12.00),  # doubles to (4, 18) above 200K
}

LONG_PROMPT_TOKENS = 200_000

# Above a 200K-token prompt, Gemini 3.1 Pro's rates double.
LONG_PROMPT_PRICES: dict[str, tuple[float, float]] = {
    "gemini-3.1-pro": (4.00, 18.00),
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


@dataclass(frozen=True, slots=True)
class Answer:
    data: dict[str, Any] | None = None
    in_tokens: int = 0
    out_tokens: int = 0
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
        effort: str | None = None,
    ) -> Answer: ...


def build_config(*, schema: dict[str, Any], effort: str | None = None) -> Any:
    """The config every call uses. No tools, ever — see the module docstring."""
    from google.genai import types

    return types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=schema,
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
        effort: str | None = None,
    ) -> Answer:
        from google.genai import types

        parts: list[Any] = [instructions, evidence]
        if image is not None:
            parts.append(types.Part.from_bytes(data=image, mime_type="image/png"))

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
        usage_missing = raw_in is None or raw_out is None
        in_tokens = raw_in or 0
        out_tokens = raw_out or 0
        unpriced = usage_missing or not is_priced(model)
        cost = price(model, in_tokens, out_tokens)

        if response.text is None:
            # The SDK returns None rather than raising when a call is blocked or
            # comes back with no candidates. Parsing that as "{}" would file a
            # refusal as a confident empty answer.
            return Answer(
                in_tokens=in_tokens,
                out_tokens=out_tokens,
                cost_usd=cost,
                unpriced=unpriced,
                error="the model returned no text (blocked, or no candidates)",
            )

        try:
            data = json.loads(response.text)
        except ValueError as problem:
            return Answer(
                in_tokens=in_tokens,
                out_tokens=out_tokens,
                cost_usd=cost,
                unpriced=unpriced,
                error=f"not json: {problem}",
            )

        return Answer(
            data=data,
            in_tokens=in_tokens,
            out_tokens=out_tokens,
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
        effort: str | None = None,
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
                "effort": effort,
            }
        )
        if not self.answers:
            return Answer(error="the fake ran out of answers")
        return self.answers.pop(0)
