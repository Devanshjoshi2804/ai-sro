from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
from datetime import datetime

from sro.application.context import RequestContext
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.system import Clock
from sro.application.ports.tools import ToolCaller, ToolsUnavailable
from sro.domain.shared.errors import InvariantViolation, NotFound
from sro.domain.shared.identifiers import PrincipalId, SkillId, TenantId
from sro.domain.skill.plan import ToolPlan
from sro.domain.skill.promotion import PromotionStage
from sro.domain.skill.skill import SkillVersion
from sro.domain.skill.template import Template
from sro.domain.skill.track_record import TrackRecord


@dataclass(frozen=True, slots=True)
class Mapped:
    skill_id: SkillId
    version: int
    step_index: int


class MapStepToTool:
    def __init__(self, uow: UnitOfWork, clock: Clock, tools: ToolCaller | None = None) -> None:
        self._uow = uow
        self._clock = clock
        self._tools = tools

    async def execute(
        self,
        ctx: RequestContext,
        *,
        skill_id: SkillId,
        version: int,
        step_index: int,
        server: str,
        tool: str,
        arguments: Mapping[str, str],
        writes: bool,
    ) -> Mapped:
        now = self._clock.now()

        await self._refuse_unless_offered(ctx.tenant_id, ctx.principal_id, server, tool)

        async with self._uow as uow:
            skill = await uow.skills.get(ctx.tenant_id, skill_id)
            source = skill.version(version)
            _refuse_unless_present(source, step_index)

            plan = ToolPlan(
                server=server,
                tool=tool,
                arguments=tuple((name, Template(value)) for name, value in arguments.items()),
                writes=writes,
            )
            _refuse_unless_declared(source, plan)

            fresh = replace(
                source,
                version=skill.next_version_number(),
                steps=tuple(
                    replace(each, tool_plan=plan) if each.index == step_index else each
                    for each in source.steps
                ),
                stage=PromotionStage.RECORDED,
                track_record=TrackRecord(),
                promoted_at=None,
                promoted_by=None,
                promoted_from="",
                demotion_reason=None,
                provenance=replace(
                    source.provenance,
                    induced_at=now,
                    induced_by=ctx.principal_id,
                    note=_note(source, step_index, plan, at=now),
                ),
            )
            skill.add_version(fresh)
            await uow.skills.save(skill)
            await uow.commit()

        return Mapped(skill_id=skill_id, version=fresh.version, step_index=step_index)

    async def _refuse_unless_offered(
        self, tenant_id: TenantId, principal_id: PrincipalId, server: str, tool: str
    ) -> None:
        if self._tools is None or not self._tools.available:
            raise InvariantViolation(
                "no connector is configured, so there is no tool to map this step onto"
            )
        try:
            offered = await self._tools.list_tools(tenant_id, principal_id, server)
        except ToolsUnavailable as gone:
            raise InvariantViolation(str(gone)) from gone
        if tool not in {each.name for each in offered}:
            raise InvariantViolation(
                f"{server} offers no tool called {tool}. It offers: "
                + (", ".join(sorted(each.name for each in offered)) or "nothing")
            )


def _refuse_unless_present(version: SkillVersion, index: int) -> None:
    if not any(step.index == index for step in version.steps):
        raise NotFound(f"version {version.version} has no step {index}")


def _refuse_unless_declared(version: SkillVersion, plan: ToolPlan) -> None:
    declared = {parameter.name for parameter in version.parameters}
    missing = sorted(plan.placeholders - declared)
    if missing:
        raise InvariantViolation("this skill has no parameter called " + ", ".join(missing))


def _note(version: SkillVersion, index: int, plan: ToolPlan, *, at: datetime) -> str:
    was = "a gesture" if _clicked(version, index) else "a call"
    return (
        f"step {index} was {was} and is now {plan.tool} on {plan.server}, "
        f"mapped on {at.date().isoformat()}"
    )


def _clicked(version: SkillVersion, index: int) -> bool:
    for step in version.steps:
        if step.index == index:
            return step.network_plan is None
    return False


__all__ = ["MapStepToTool", "Mapped"]
