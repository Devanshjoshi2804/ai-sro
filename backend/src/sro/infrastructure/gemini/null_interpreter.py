from __future__ import annotations

from sro.application.ports.interpretation import Judgement, Reading, TaskName


class NoInterpreter:
    @property
    def available(self) -> bool:
        return False

    async def read(self, evidence: str) -> Reading:
        return Reading(caveat="no interpreter is configured")

    async def name_task(self, evidence: str) -> TaskName:
        return TaskName()

    async def judge_join(self, kind: str, first: str, second: str) -> Judgement:
        return Judgement()
