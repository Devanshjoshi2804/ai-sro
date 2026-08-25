"""No interpreter. A single demonstration still becomes a skill.

What is lost is the narrative and the proposed parameters -- the calls, which
are the part that actually runs, are captured either way. And candidates keep
their derived titles and get no join suggestions, which is a duller list rather
than a broken one.
"""

from __future__ import annotations

from sro.application.ports.interpretation import Judgement, Reading, TaskName


class NoInterpreter:
    @property
    def available(self) -> bool:
        return False

    async def read(self, evidence: str) -> Reading:
        return Reading(caveat="no interpreter is configured")

    async def name_task(self, evidence: str) -> TaskName:
        """Nothing, so the derived title stands. A deployment that may not call
        a hosted model still mines, still offers candidates, still teaches."""
        return TaskName()

    async def judge_join(self, kind: str, first: str, second: str) -> Judgement:
        return Judgement()
