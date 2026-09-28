from __future__ import annotations

import logging
from collections.abc import Mapping
from dataclasses import replace
from types import MappingProxyType

from sro.application.ports.model import Asker
from sro.domain.prompts.record import Prompt, conforms
from sro.domain.shared.prices import Answer

logger = logging.getLogger(__name__)

_NOTHING: Mapping[str, str] = MappingProxyType({})


async def ask(
    asker: Asker,
    prompt: Prompt,
    *,
    trusted: Mapping[str, object],
    untrusted: Mapping[str, str] = _NOTHING,
    image: bytes | None = None,
    images: tuple[bytes, ...] = (),
    audio: tuple[bytes, str] | None = None,
) -> Answer:
    evidence = prompt.evidence(trusted, untrusted)
    first = await _asked(asker, prompt, prompt.model, evidence, image, images, audio)
    if prompt.fallback_model is None or not _failed(first, prompt.unit):
        return first
    logger.warning(
        "%s v%s: %s failed (%s); asking %s",
        prompt.name,
        prompt.version,
        prompt.model,
        _why(first),
        prompt.fallback_model,
    )
    second = await _asked(asker, prompt, prompt.fallback_model, evidence, image, images, audio)
    used = second
    if _failed(second, prompt.unit):
        logger.warning(
            "%s v%s: %s failed too (%s)",
            prompt.name,
            prompt.version,
            prompt.fallback_model,
            _why(second),
        )
        used = first
    return replace(
        used,
        in_tokens=first.in_tokens + second.in_tokens,
        out_tokens=first.out_tokens + second.out_tokens,
        thought_tokens=first.thought_tokens + second.thought_tokens,
        cost_usd=first.cost_usd + second.cost_usd,
        unpriced=first.unpriced or second.unpriced,
        fell_back=True,
        malformed=first.malformed or second.malformed,
    )


def _failed(answer: Answer, unit: str | None) -> bool:
    return answer.data is None or (answer.dropped > 0 and _many(answer.data, unit) == 0)


def _why(answer: Answer) -> str:
    return answer.error or ("no answer" if answer.data is None else "every item was dropped")


async def _asked(
    asker: Asker,
    prompt: Prompt,
    model: str,
    evidence: str,
    image: bytes | None,
    images: tuple[bytes, ...],
    audio: tuple[bytes, str] | None,
) -> Answer:
    answer = await asker.ask(
        model=model,
        instructions=prompt.instructions,
        evidence=evidence,
        schema=dict(prompt.output_schema),
        image=image,
        images=images,
        audio=audio,
        effort=prompt.thinking,
    )
    if answer.data is None:
        return answer
    data = prompt.kept(answer.data)
    dropped = _many(answer.data, prompt.unit) - _many(data, prompt.unit)
    if dropped:
        logger.info(
            "%s v%s: %d item(s) dropped for breaking the schema",
            prompt.name,
            prompt.version,
            dropped,
        )
    if not conforms(data, prompt.output_schema):
        return replace(
            answer,
            data=None,
            dropped=dropped,
            error=answer.error
            or f"{prompt.name} v{prompt.version}: the answer does not match its schema",
            malformed=True,
        )
    return answer if data is answer.data else replace(answer, data=data, dropped=dropped)


def _many(data: dict[str, object], unit: str | None) -> int:
    found = data.get(unit) if unit else None
    return len(found) if isinstance(found, list) else 0
