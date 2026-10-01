from __future__ import annotations

from collections.abc import Sequence

from sro.domain.shared.prices import Answer, Effort


class Replayed:
    """A recorded model. One answer is given to every ask (a suite that asks once); a list is
    given in order, one per ask, and a turn that asks past its end is an error, not a repeat."""

    def __init__(self, answers: dict[str, object] | Sequence[dict[str, object]] | None) -> None:
        self._one = None if isinstance(answers, Sequence) else answers
        self._queue = list(answers) if isinstance(answers, Sequence) else None

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
        if self._queue is None:
            return Answer(data=self._one)
        if not self._queue:
            return Answer(error="the recording ran out of answers")
        return Answer(data=self._queue.pop(0))
