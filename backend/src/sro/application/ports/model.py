from __future__ import annotations

from typing import Protocol

from sro.domain.shared.prices import Answer, Effort


class Asker(Protocol):
    async def ask(
        self,
        *,
        model: str,
        instructions: str,
        evidence: str,
        schema: dict[str, object],
        image: bytes | None = None,
        images: tuple[bytes, ...] = (),
        effort: Effort | None = None,
    ) -> Answer: ...


class AskerUnavailable(Exception):
    code = "no_model"


def asker_or_refuse(asker: Asker | None) -> Asker:
    if asker is None:
        raise AskerUnavailable(
            "no model is configured: set gemini_api_key and interpretation_enabled"
        )
    return asker
