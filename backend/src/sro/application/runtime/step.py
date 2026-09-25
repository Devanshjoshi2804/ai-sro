from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field
from typing import Literal, Protocol

from sro.application.context import RequestContext
from sro.application.ports.page import SessionRef
from sro.domain.execution.account import Lease
from sro.domain.execution.compose import Adding
from sro.domain.execution.lanes import Lane, StepResult
from sro.domain.execution.learned_step import LearnedStep
from sro.domain.execution.verified_writes import VerifiedWrite
from sro.domain.observation.gesture import Gesture
from sro.domain.shared.errors import DomainError
from sro.domain.shared.identifiers import PrincipalId, TenantId
from sro.domain.skill.workflow import Step, Workflow


@dataclass(frozen=True, slots=True)
class Held:
    lease: Lease
    target_id: str
    session: SessionRef


class NeedsAPerson(DomainError):
    code = "needs_a_person"

    def __init__(
        self, question: str, *, kind: Literal["password", "value", "step", "code"] = "step"
    ) -> None:
        super().__init__(question)
        self.question = question
        self.kind = kind


class WaitingForAPerson(NeedsAPerson):
    def __init__(self, question: str, *, held: Held) -> None:
        super().__init__(question, kind="code")
        self.held = held


class Stopped(DomainError):
    code = "stopped"


async def _nothing() -> None:
    return None


@dataclass(frozen=True, slots=True)
class LaneContext:
    tenant_id: TenantId
    principal_id: PrincipalId
    workflow: Workflow
    by_id: Mapping[str, Gesture]
    learned: Mapping[int, LearnedStep]
    ledger: tuple[VerifiedWrite, ...]
    held: Held | None
    stop: asyncio.Event
    secret: str | None = field(default=None, repr=False)
    thread: str = ""
    about_to_write: Callable[[], Awaitable[None]] = _nothing
    reauthed: bool = False
    adding: Mapping[int, Adding] = field(default_factory=dict)

    @property
    def ctx(self) -> RequestContext:
        return RequestContext(tenant_id=self.tenant_id, principal_id=self.principal_id)

    def check_stop(self) -> None:
        if self.stop.is_set():
            raise Stopped("stopped by the operator")

    @classmethod
    def for_sign_in(
        cls,
        ctx: RequestContext,
        job: Workflow,
        by_id: Mapping[str, Gesture],
        held: Held | None,
        *,
        secret: str | None = None,
    ) -> LaneContext:
        return cls(
            tenant_id=ctx.tenant_id,
            principal_id=ctx.principal_id,
            workflow=job,
            by_id=by_id,
            learned={},
            ledger=(),
            held=held,
            stop=asyncio.Event(),
            secret=secret,
        )


class StepLane(Protocol):
    lane: Lane

    async def execute(
        self, step: Step, values: Mapping[str, str], ctx: LaneContext
    ) -> StepResult: ...
