from __future__ import annotations

import asyncio
import json
import logging
import re
from dataclasses import replace
from typing import Any

from sro.application.shared.refusals import OverCap, Unattributed
from sro.domain.shared.prices import Answer, Effort, is_priced, price
from sro.infrastructure.telemetry.otel import doing

logger = logging.getLogger(__name__)

K_MAX_OUTPUT_TOKENS = 65536


LESS_THINKING: dict[Effort, Effort] = {"high": "medium", "medium": "low", "low": "minimal"}


def truncated(response: Any) -> bool:
    candidates = getattr(response, "candidates", None) or []
    reason = getattr(candidates[0], "finish_reason", None) if candidates else None
    name = getattr(reason, "name", None) or (str(reason) if reason is not None else "")
    return "MAX_TOKENS" in name.upper()


def build_config(*, schema: dict[str, object], effort: Effort | None = None) -> Any:
    from google.genai import types

    return types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=dict(schema),
        max_output_tokens=K_MAX_OUTPUT_TOKENS,
        thinking_config=None
        if effort is None
        else types.ThinkingConfig(thinking_level=types.ThinkingLevel(effort)),
    )


K_TRIES = 3

K_BACKOFF_S = 2.0


def _worth_retrying(problem: Exception) -> bool:
    code = getattr(problem, "code", None)
    return isinstance(code, int) and 500 <= code < 600


_THE_KEY = re.compile(r"api[ _]key", re.IGNORECASE)


def _an_outage(problem: Exception) -> bool:
    code = getattr(problem, "code", None)
    # Gemini answers an invalid or expired key with a 400: configuration, not this one prompt.
    return (
        not isinstance(code, int)
        or code >= 500
        or code in (401, 403, 429)
        or (code == 400 and bool(_THE_KEY.search(str(problem))))
    )


class GeminiAsker:
    def __init__(self, *, client: Any) -> None:
        self._client = client

    async def ask(
        self,
        *,
        model: str,
        instructions: str,
        evidence: str,
        schema: dict[str, object],
        image: bytes | None = None,
        images: tuple[bytes, ...] = (),
        audio: tuple[bytes, str] | None = None,
        effort: Effort | None = None,
    ) -> Answer:
        parts = self._parts(instructions, evidence, image, images, audio)
        answer = await self._asked_once(model=model, parts=parts, schema=schema, effort=effort)
        lower = LESS_THINKING.get(effort) if effort is not None else None
        if not answer.truncated or lower is None:
            return answer
        logger.info("the answer hit the output ceiling at %s; asking again at %s", effort, lower)
        again = await self._asked_once(model=model, parts=parts, schema=schema, effort=lower)
        return replace(
            again,
            in_tokens=answer.in_tokens + again.in_tokens,
            out_tokens=answer.out_tokens + again.out_tokens,
            thought_tokens=answer.thought_tokens + again.thought_tokens,
            cost_usd=answer.cost_usd + again.cost_usd,
            unpriced=answer.unpriced or again.unpriced,
        )

    def _parts(
        self,
        instructions: str,
        evidence: str,
        image: bytes | None,
        images: tuple[bytes, ...],
        audio: tuple[bytes, str] | None,
    ) -> list[Any]:
        from google.genai import types

        parts: list[Any] = [part for part in (instructions, evidence) if part]
        if image is not None:
            parts.append(types.Part.from_bytes(data=image, mime_type="image/png"))
        for more in images:
            parts.append(types.Part.from_bytes(data=more, mime_type="image/png"))
        if audio is not None:
            parts.append(types.Part.from_bytes(data=audio[0], mime_type=audio[1]))
        return parts

    async def _asked_once(
        self, *, model: str, parts: list[Any], schema: dict[str, object], effort: Effort | None
    ) -> Answer:
        problem: Exception | None = None
        response = None
        with doing("model.ask") as span:
            span.set_attribute("model", model)
            for attempt in range(K_TRIES):
                try:
                    response = await self._client.aio.models.generate_content(
                        model=model,
                        contents=parts,
                        config=build_config(schema=schema, effort=effort),
                    )
                    problem = None
                    break
                except (OverCap, Unattributed):
                    raise
                except Exception as raised:
                    problem = raised
                    if attempt + 1 >= K_TRIES or not _worth_retrying(raised):
                        break
                    logger.warning(
                        "%s from the model, retrying (%d of %d)",
                        type(raised).__name__,
                        attempt + 2,
                        K_TRIES,
                    )
                    await asyncio.sleep(K_BACKOFF_S * (attempt + 1))
        if problem is not None or response is None:
            return Answer(
                unpriced=True,
                error=f"{type(problem).__name__}: {problem}",
                unreachable=problem is None or _an_outage(problem),
            )

        usage = getattr(response, "usage_metadata", None)
        raw_in = getattr(usage, "prompt_token_count", None)
        raw_out = getattr(usage, "candidates_token_count", None)
        thought_tokens = getattr(usage, "thoughts_token_count", None) or 0
        usage_missing = raw_in is None
        in_tokens = raw_in or 0
        out_tokens = (raw_out or 0) + thought_tokens
        unpriced = usage_missing or not is_priced(model)
        cost = price(model, in_tokens, out_tokens)

        if response.text is None:
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
                truncated=truncated(response),
            )

        return Answer(
            data=data,
            in_tokens=in_tokens,
            out_tokens=out_tokens,
            thought_tokens=thought_tokens,
            cost_usd=cost,
            unpriced=unpriced,
        )
