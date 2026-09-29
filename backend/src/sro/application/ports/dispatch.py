from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol

from sro.application.context import RequestContext
from sro.domain.execution.run import Medium, RunId
from sro.domain.shared.identifiers import DeviceId, SkillId


class RunDispatcher(Protocol):
    async def start(
        self,
        ctx: RequestContext,
        *,
        skill_id: SkillId,
        parameters: dict[str, str],
        device_id: DeviceId,
        version: int | None = None,
        authorized_by: bool = False,
        medium: Medium = Medium.NETWORK,
        may_take_focus: bool = False,
    ) -> RunId: ...

    async def start_job(
        self,
        ctx: RequestContext,
        *,
        workflow_id: str,
        device_id: DeviceId | None,
        values: Mapping[str, str],
        allow_focus: bool = False,
    ) -> RunId: ...


class DispatchFailed(Exception):
    code = "dispatch_failed"
