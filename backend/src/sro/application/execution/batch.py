from __future__ import annotations

from dataclasses import dataclass

from sro.application.context import RequestContext
from sro.application.execution.execute_skill import (
    ExecuteSkill,
    ExecutionRequest,
    NotRunnable,
    Refused,
)
from sro.domain.execution.run import Medium, Run, RunStatus
from sro.domain.shared.identifiers import SkillId


@dataclass(frozen=True, slots=True)
class Item:
    parameters: dict[str, str]
    run: Run | None = None
    refused: str | None = None

    @property
    def succeeded(self) -> bool:
        return self.run is not None and self.run.status is RunStatus.SUCCEEDED


@dataclass(frozen=True, slots=True)
class BatchResult:
    items: tuple[Item, ...]
    stopped_early: str | None = None

    @property
    def performed(self) -> int:
        return sum(1 for item in self.items if item.succeeded)


class RunBatch:
    def __init__(self, execute: ExecuteSkill) -> None:
        self._execute = execute

    async def execute(
        self,
        ctx: RequestContext,
        *,
        skill_id: SkillId,
        items: tuple[dict[str, str], ...],
        authorized_by: str | None = None,
        version: int | None = None,
        medium: Medium = Medium.NETWORK,
    ) -> BatchResult:
        done: list[Item] = []

        for parameters in items:
            try:
                run = await self._execute.execute(
                    ctx,
                    ExecutionRequest(
                        skill_id=skill_id,
                        parameters=dict(parameters),
                        version=version,
                        authorized_by=authorized_by,
                        medium=medium,
                    ),
                )
            except Refused as refusal:
                done.append(Item(parameters=parameters, refused=str(refusal)))
                return BatchResult(items=tuple(done), stopped_early=str(refusal))
            except NotRunnable as refusal:
                done.append(Item(parameters=parameters, refused=str(refusal)))
                continue

            done.append(Item(parameters=parameters, run=run))

        return BatchResult(items=tuple(done))
