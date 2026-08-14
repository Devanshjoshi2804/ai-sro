"""Doing the same taught task to several things at once.

A batch is not a new kind of execution. It is N runs of one skill version, each
with its own idempotency keys, its own audit record and its own verification --
so one item failing tells you nothing about the others, and the failure names
which item it was.

Two rules that keep a batch from being the worst thing in the system:

- **The operator confirms the table, not the sentence.** What the model read out
  of "these six SKUs" is shown as parameter sets before anything is sent, and
  that confirmation is the authorisation each assisted run records.
- **It stops on a system that is failing.** The circuit breaker is checked per
  run, so a batch against a WMS that started answering 500 stops after the third
  rather than sending the remaining forty.
"""

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
    """Why the rest were not attempted. Present when a limit stopped the batch,
    absent when everything was tried."""

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
                # A safety limit, not this item's fault. Everything after it
                # would hit the same wall, so the batch stops and says so.
                done.append(Item(parameters=parameters, refused=str(refusal)))
                return BatchResult(items=tuple(done), stopped_early=str(refusal))
            except NotRunnable as refusal:
                # This item cannot run -- a missing value, usually. The others
                # still can, so the batch carries on.
                done.append(Item(parameters=parameters, refused=str(refusal)))
                continue

            done.append(Item(parameters=parameters, run=run))

        return BatchResult(items=tuple(done))
