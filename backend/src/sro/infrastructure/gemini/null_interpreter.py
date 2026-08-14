"""No interpreter. A single demonstration still becomes a skill.

What is lost is the narrative and the proposed parameters -- the calls, which
are the part that actually runs, are captured either way.
"""

from __future__ import annotations

from sro.application.ports.interpretation import Reading


class NoInterpreter:
    @property
    def available(self) -> bool:
        return False

    async def read(self, evidence: str) -> Reading:
        return Reading(caveat="no interpreter is configured")
