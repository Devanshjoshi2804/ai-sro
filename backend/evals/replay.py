from __future__ import annotations

from sro.domain.shared.prices import Answer, Effort


class Replayed:
    def __init__(self, answer: dict[str, object] | None) -> None:
        self._answer = answer

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
        return Answer(data=self._answer)
