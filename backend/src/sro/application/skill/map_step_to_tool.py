"""Somebody saying: this click is that tool.

The one part of a skill nobody demonstrates. Induction reads recordings, and a
recording holds gestures and the calls they made -- so a step performed through
a connector is always a decision, and this is where the decision is recorded
with the name of whoever made it.

Why it matters at all: a gesture step can never reach `CLEAN`, so a skill whose
mail half is clicks is assisted forever. Mapping that step onto a tool is what
makes the ladder reachable, which is why the machinery exists (ADR 013) and why
it is worth a screen.
"""

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
    """Point one step of one version at a connector's tool.

    Produces a new version rather than editing the one in front of somebody.
    Every version is appended here -- a repair does it, an induction does it --
    and for the same reason: a version that changed under a reviewer who had
    already read it is a review of something else.
    """

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
            # Read for the refusal alone: a mapping onto a step that is not
            # there would otherwise produce a version identical to the one it
            # came from, and report success.
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
                # The bottom of the ladder, whatever the version it was mapped
                # from had earned. A repair inherits its rung because one
                # locator changed and every value is the one the demonstrations
                # carried; this is a step going through a door nobody has
                # watched it go through. The streak that would let it run
                # unattended has to be earned against the connector, not
                # inherited from the clicks it replaced.
                stage=PromotionStage.RECORDED,
                track_record=TrackRecord(),
                promoted_at=None,
                promoted_by=None,
                promoted_from="",
                demotion_reason=None,
                provenance=replace(
                    source.provenance,
                    # The recordings stay: every other step, and every value
                    # this one sends, still came from them. What changed is how
                    # one step is performed, and `induced_by` is the person who
                    # decided that.
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
        """The connector has to say it has this tool.

        Asked before the version is written rather than at the first run: a
        skill carrying a mapping onto a tool that does not exist looks exactly
        like a working one until somebody fires it, and by then the click it
        replaced has been mapped away.

        Asked as THIS operator, because that is the only person whose grant
        this is: a mapping checked against somebody else's would pass here and
        fail at the first run.
        """
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
    """Every `${name}` in the mapping is a parameter this version has.

    `SkillVersion` checks this too, and would refuse the new version -- but it
    would refuse it as an invariant violation, which reads as a bug in this
    system rather than as a typo in a form somebody just filled in.
    """
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
