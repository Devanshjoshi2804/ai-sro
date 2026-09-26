from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
from types import MappingProxyType

from sro.application.ports.model import Asker
from sro.domain.prompts.record import Prompt, conforms
from sro.domain.shared.prices import Answer

_NOTHING: Mapping[str, str] = MappingProxyType({})


async def ask(
    asker: Asker,
    prompt: Prompt,
    *,
    trusted: Mapping[str, object],
    untrusted: Mapping[str, str] = _NOTHING,
    image: bytes | None = None,
    images: tuple[bytes, ...] = (),
) -> Answer:
    answer = await asker.ask(
        model=prompt.model,
        instructions=prompt.instructions,
        evidence=prompt.evidence(trusted, untrusted),
        schema=dict(prompt.output_schema),
        image=image,
        images=images,
        effort=prompt.thinking,
    )
    if answer.data is None:
        return answer
    data = prompt.kept(answer.data)
    if not conforms(data, prompt.output_schema):
        return replace(
            answer,
            data=None,
            error=answer.error
            or f"{prompt.name} v{prompt.version}: the answer does not match its schema",
        )
    return answer if data is answer.data else replace(answer, data=data)
