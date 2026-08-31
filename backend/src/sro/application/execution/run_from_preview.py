"""Run a skill an operator has just read the preview of.

`_check_runnable` refuses a RECORDED version because "a recorded skill has not
been reviewed by anybody". After the preview it has been: by the operator, on
the exact steps and the exact values, at the screen it will act on, with a stop
button in front of them. ADR 014 makes that argument in full.

Promote and run in one call. Two calls race, and a version promoted by a press
that then failed to start is a version sitting at assisted because somebody
clicked once and walked away.
"""

from __future__ import annotations

from sro.application.context import RequestContext
from sro.application.execution.execute_skill import ExecuteSkill, ExecutionRequest
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.system import Clock
from sro.domain.execution.run import Run
from sro.domain.shared.identifiers import DeviceId, SkillId
from sro.domain.skill.promotion import PromotionStage


class RunFromPreview:
    def __init__(self, uow: UnitOfWork, clock: Clock, execute_skill: ExecuteSkill) -> None:
        self._uow = uow
        self._clock = clock
        self._execute = execute_skill

    async def execute(
        self,
        ctx: RequestContext,
        *,
        skill_id: SkillId,
        parameters: dict[str, str],
        device_id: DeviceId,
        intent: str,
    ) -> Run:
        async with self._uow as uow:
            skill = await uow.skills.get(ctx.tenant_id, skill_id)
            version = skill.latest
            now = self._clock.now()
            promoted = False
            # Only a version that cannot run yet, and only as far as it needs
            # to go. A press on the fifth run is not a fifth promotion, and the
            # rungs above assisted are earned by runs, not by presses --
            # `promote` itself refuses `from_where="preview"` past assisted, so
            # this loop never asks it to.
            #
            # One rung per call: `check_promotion` refuses a jump of more than
            # one, so a version sitting at RECORDED climbs through SHADOW on
            # its way to ASSISTED rather than in a single bound the ladder
            # would reject.
            while version.stage.rung < PromotionStage.ASSISTED.rung:
                version.promote(
                    version.stage.next_stage(),
                    now,
                    ctx.principal_id,
                    # DECISION (task 5): pass True here rather than let a
                    # single-demonstration write refuse this promotion and
                    # dead-end the press.
                    #
                    # `acknowledging_fixed_values` exists because a version
                    # induced from one demonstration was never diffed against
                    # a second one -- nothing tells the values it sends apart
                    # from the values that one run happened to carry, so
                    # promoting it past shadow without anybody having looked
                    # would mean repeating that one run's exact write forever.
                    # The flag is the record that somebody looked.
                    #
                    # For a console promotion (`PromoteSkill`) that somebody is
                    # a named reviewer opening the evidence deliberately, which
                    # is why that caller leaves the flag for them to set and
                    # will not default it to true on their behalf. This press
                    # is a different door onto the very same question. The
                    # same press that is already trusted, this call, to move a
                    # version from a stage that sends nothing to one that sends
                    # real writes -- ASSISTED, the whole subject of ADR 014 --
                    # has already been trusted with the larger claim
                    # ("this version may act for real"). Withholding trust
                    # specifically on "and these particular fixed values are
                    # the ones it will act with" is a strictly narrower claim
                    # than the one just granted by the same press, from the
                    # same operator, over the same version, in the same
                    # instant: the panel showed them the steps and the values
                    # this run is about to send before they pressed, which is
                    # the reading this flag exists to require, not a
                    # substitute for it. Refusing here instead would mean the
                    # commonest shape a freshly induced skill has -- one
                    # demonstration, one write -- dead-ends on its very first
                    # press regardless of what the operator read, which is the
                    # exact failure this task exists to close.
                    acknowledging_fixed_values=True,
                    from_where="preview",
                )
                promoted = True
            if promoted:
                await uow.skills.save(skill)
                await uow.commit()
            # Pinned to the version this call just read and, where needed,
            # promoted. Left to resolve on its own, `ExecuteSkill` would ask
            # for "the latest version" again when it starts -- and a second
            # induction landing between this commit and that lookup would
            # promote one version and run another, silently.
            version_number = version.version

        return await self._execute.execute(
            ctx,
            ExecutionRequest(
                skill_id=skill_id,
                parameters=parameters,
                version=version_number,
                authorized_by=str(ctx.principal_id),
                device_id=device_id,
                intent=intent,
            ),
        )
