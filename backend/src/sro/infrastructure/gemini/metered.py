from __future__ import annotations

import logging
import math
import traceback
from collections.abc import Callable
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

from sro.application.intent.spend import over_cap
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.system import Clock
from sro.application.shared.refusals import OverCap
from sro.domain.shared.identifiers import TenantId
from sro.domain.shared.prices import ModelSpend, is_priced, price
from sro.whose import whose

logger = logging.getLogger(__name__)

K_CHARS_PER_TOKEN = 4

_NOT_THE_CALLER = ("/sro/infrastructure/", "/asyncio/", "contextlib")


class Unattributed(Exception):
    pass


class Meter:
    def __init__(self, uow: Callable[[], UnitOfWork], *, clock: Clock, cap_usd: float) -> None:
        self._uow = uow
        self._clock = clock
        self._cap_usd = cap_usd

    async def check(self, model: str) -> None:
        tenant = _tenant()
        if not tenant:
            logger.error("a %s call from %s was made for no tenant; refused", model, _caller())
            raise Unattributed("a model call was made for no tenant, so no cap or bill sees it")
        if self._cap_usd < 0:
            return
        async with self._uow() as uow:
            why = await over_cap(
                uow, TenantId(tenant), now=self._clock.now(), cap_usd=self._cap_usd
            )
        if why is not None:
            logger.warning("%s: a %s call from %s refused -- %s", tenant, model, _caller(), why)
            raise OverCap(why)

    async def record(
        self,
        *,
        model: str,
        in_tokens: int | None,
        out_tokens: int = 0,
        thought_tokens: int = 0,
    ) -> None:
        tenant = _tenant()
        known = in_tokens is not None
        spent_in, spent_out = in_tokens or 0, out_tokens + thought_tokens
        try:
            async with self._uow() as uow:
                await uow.spend.record(
                    ModelSpend(
                        id=f"spd_{uuid4().hex}",
                        tenant=tenant,
                        model=model,
                        at=self._clock.now(),
                        in_tokens=spent_in,
                        out_tokens=spent_out,
                        thought_tokens=thought_tokens,
                        cost_usd=price(model, spent_in, spent_out),
                        unpriced=not known or not is_priced(model),
                    )
                )
                await uow.commit()
        except Exception:
            logger.exception(
                "%s: a %s call was answered but its spend was not written", tenant, model
            )


class Metered:
    def __init__(self, client: Any, meter: Meter) -> None:
        self._client = client
        self._models = client.aio.models
        self._meter = meter
        self.aio = SimpleNamespace(models=self)

    async def generate_content(self, *, model: str, **rest: Any) -> Any:
        await self._meter.check(model)
        response = await self._models.generate_content(model=model, **rest)
        usage = getattr(response, "usage_metadata", None)
        prompt = getattr(usage, "prompt_token_count", None)
        tools = getattr(usage, "tool_use_prompt_token_count", None) or 0
        await self._meter.record(
            model=model,
            in_tokens=None if prompt is None else prompt + tools,
            out_tokens=getattr(usage, "candidates_token_count", None) or 0,
            thought_tokens=getattr(usage, "thoughts_token_count", None) or 0,
        )
        return response

    async def embed_content(self, *, model: str, contents: Any, **rest: Any) -> Any:
        await self._meter.check(model)
        response = await self._models.embed_content(model=model, contents=contents, **rest)
        sent = sum(len(str(one)) for one in contents)
        await self._meter.record(
            model=model, in_tokens=math.ceil(sent / K_CHARS_PER_TOKEN), out_tokens=0
        )
        return response


def metered_client(api_key: str, meter: Meter, *, timeout_ms: int | None = None) -> Metered:
    from google import genai
    from google.genai import types

    return Metered(
        genai.Client(
            api_key=api_key,
            http_options=None if timeout_ms is None else types.HttpOptions(timeout=timeout_ms),
        ),
        meter,
    )


def _caller() -> str:
    for frame in reversed(traceback.extract_stack()[:-2]):
        if not any(part in frame.filename for part in _NOT_THE_CALLER):
            return f"{Path(frame.filename).stem}.{frame.name}"
    return "unknown"


def _tenant() -> str:
    return str(whose().get("tenant") or "")
