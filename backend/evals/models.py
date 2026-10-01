"""Which model an eval run asks: the production asker with another model or thinking level,
or an OpenRouter model. Eval only: nothing here is wired into the product.

`python -m evals run --suite chat --tenant T --model gemini-3.7-flash --thinking low`
`python -m evals run ... --provider openrouter --model qwen/qwen3.8-flash`  (OPENROUTER_API_KEY)

OpenRouter sends the eval's text to a third party. The chat cases are QA test sentences; do not
point this at a tenant's real traffic.
"""

from __future__ import annotations

import asyncio
import json
import os
from typing import Any

import httpx

from sro.application.ports.model import Asker
from sro.domain.shared.prices import Answer, Effort

K_URL = "https://openrouter.ai/api/v1/chat/completions"
K_TIMEOUT_S = 120.0
K_TRIES = 4
K_BACKOFF_S = 4.0
EFFORTS: tuple[str, ...] = ("minimal", "low", "medium", "high")


class Overridden:
    """The wrapped asker, asked for another model and/or another thinking level."""

    def __init__(self, inner: Asker, *, model: str | None, thinking: str | None) -> None:
        self._inner, self._model, self._thinking = inner, model, thinking

    async def ask(self, *, model: str, effort: Effort | None = None, **rest: Any) -> Answer:
        if self._thinking == "default":
            effort = None
        elif self._thinking:
            effort = self._thinking  # type: ignore[assignment]
        return await self._inner.ask(model=self._model or model, effort=effort, **rest)


class OpenRouterAsker:
    """The same contract over OpenRouter's chat completions with a JSON-schema answer."""

    def __init__(self, *, key: str, model: str, thinking: str | None) -> None:
        self._key, self._model, self._thinking = key, model, thinking

    async def ask(
        self,
        *,
        model: str,
        instructions: str,
        evidence: str,
        schema: dict[str, object],
        effort: Effort | None = None,
        **_: Any,
    ) -> Answer:
        body: dict[str, Any] = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": instructions},
                {"role": "user", "content": evidence},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": "answer", "schema": schema},
            },
            "provider": {"require_parameters": True},
            "usage": {"include": True},
        }
        level = self._thinking if self._thinking not in (None, "default") else None
        if level in EFFORTS:
            body["reasoning"] = {"effort": level}
        payload: dict[str, Any] = {}
        for attempt in range(K_TRIES):
            try:
                async with httpx.AsyncClient(timeout=K_TIMEOUT_S) as client:
                    reply = await client.post(
                        K_URL, json=body, headers={"Authorization": f"Bearer {self._key}"}
                    )
                payload = reply.json()
            except (httpx.HTTPError, ValueError) as problem:
                return Answer(error=f"openrouter: {type(problem).__name__}: {problem}")
            code = (payload.get("error") or {}).get("code")
            # A provider that is rate-limited or briefly down is retried; anything else is final.
            if "error" not in payload or code not in (429, 500, 502, 503, 504):
                break
            await asyncio.sleep(K_BACKOFF_S * (attempt + 1))
        if "error" in payload:
            return Answer(error=f"openrouter: {str(payload['error'])[:200]}")
        usage = payload.get("usage") or {}
        spent: dict[str, Any] = dict(  # noqa: C408
            in_tokens=int(usage.get("prompt_tokens") or 0),
            out_tokens=int(usage.get("completion_tokens") or 0),
            cost_usd=float(usage.get("cost") or 0.0),
            thought_tokens=int(
                (usage.get("completion_tokens_details") or {}).get("reasoning_tokens") or 0
            ),
        )
        try:
            text = payload["choices"][0]["message"]["content"] or ""
            data = json.loads(text)
        except (KeyError, IndexError, ValueError):
            return Answer(error="openrouter: the answer was not JSON", **spent)
        return Answer(data=data if isinstance(data, dict) else None, **spent)


def chosen(
    inner: Asker | None, *, provider: str, model: str | None, thinking: str | None
) -> Asker | None:
    if provider == "openrouter":
        key = os.environ.get("OPENROUTER_API_KEY", "")
        if not key or not model:
            raise SystemExit("--provider openrouter needs --model and OPENROUTER_API_KEY")
        return OpenRouterAsker(key=key, model=model, thinking=thinking)
    if inner is not None and (model or thinking):
        return Overridden(inner, model=model, thinking=thinking)
    return inner
