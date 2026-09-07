"""The structured-output port every mined-workflow model call goes through.

The backend's ``IntentParser`` stays for utterances. This is the seam the
reading loop, the mining pass, the planner, the verifier and the chat door
all ask through, and the one place a fake goes in for every test that would
otherwise cost money.
"""

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
