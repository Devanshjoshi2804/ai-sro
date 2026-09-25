from __future__ import annotations

from typing import Protocol

from sro.application.context import RequestContext
from sro.domain.execution.run import RunId
from sro.domain.shared.identifiers import SkillId


class DurableExecution(Protocol):
    async def execute_skill(
        self,
        ctx: RequestContext,
        *,
        skill_id: SkillId,
        parameters: dict[str, str],
        version: int | None = None,
        authorized_by: str | None = None,
        medium: str = "network",
        run_id: RunId | None = None,
        wait: bool = True,
    ) -> RunId: ...

    async def start_run(self, ctx: RequestContext, *, run_id: str, budget_s: float) -> None: ...

    async def answer_run(self, run_id: str, question_id: str, value: str) -> None: ...
