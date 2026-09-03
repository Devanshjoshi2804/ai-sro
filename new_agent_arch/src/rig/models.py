"""Gemini, with structured output and a bill.

Every call records its tokens and what they cost. A model call with no cost row
is a model call nobody can defend at the end of the month.

Search grounding is never enabled: it voids zero data retention (thirty days of
storage, no opt-out), and this process reads live customer payloads.
"""

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


def price(model: str, in_tokens: int, out_tokens: int) -> float:
    rates = PRICES.get(model)
    if rates is None:
        return 0.0
    return in_tokens * rates[0] / 1_000_000 + out_tokens * rates[1] / 1_000_000


@dataclass(frozen=True, slots=True)
class Answer:
    data: dict[str, Any] | None = None
    in_tokens: int = 0
    out_tokens: int = 0
    cost_usd: float = 0.0
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
    ) -> Answer: ...


def build_config(*, schema: dict[str, Any]) -> Any:
    """The config every call uses. No tools, ever — see the module docstring."""
    from google.genai import types

    return types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=schema,
    )


class GeminiAsker:
    def __init__(self, api_key: str) -> None:
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
    ) -> Answer:
        from google.genai import types

        parts: list[Any] = [instructions, evidence]
        if image is not None:
            parts.append(types.Part.from_bytes(data=image, mime_type="image/png"))

        try:
            response = await self._client.aio.models.generate_content(
                model=model,
                contents=parts,
                config=build_config(schema=schema),
            )
        except Exception as problem:  # noqa: BLE001 -- a rig keeps going; the row records why
            return Answer(error=f"{type(problem).__name__}: {problem}")

        usage = getattr(response, "usage_metadata", None)
        in_tokens = getattr(usage, "prompt_token_count", 0) or 0
        out_tokens = getattr(usage, "candidates_token_count", 0) or 0

        try:
            data = json.loads(response.text or "{}")
        except ValueError as problem:
            return Answer(
                in_tokens=in_tokens,
                out_tokens=out_tokens,
                cost_usd=price(model, in_tokens, out_tokens),
                error=f"not json: {problem}",
            )

        return Answer(
            data=data,
            in_tokens=in_tokens,
            out_tokens=out_tokens,
            cost_usd=price(model, in_tokens, out_tokens),
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
    ) -> Answer:
        self.asked.append(
            {
                "model": model,
                "instructions": instructions,
                "evidence": evidence,
                "schema": schema,
                "image": image,
            }
        )
        if not self.answers:
            return Answer(error="the fake ran out of answers")
        return self.answers.pop(0)
