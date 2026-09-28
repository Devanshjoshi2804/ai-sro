from __future__ import annotations

from sro.application.ports.interpretation import Reading


class NoInterpreter:
    @property
    def available(self) -> bool:
        return False

    async def read(self, evidence: str) -> Reading:
        return Reading(caveat="no interpreter is configured")
