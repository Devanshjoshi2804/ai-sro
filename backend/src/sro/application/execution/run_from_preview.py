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
from sro.domain.execution.run import Medium, Run
from sro.domain.shared.identifiers import DeviceId, SkillId
from sro.domain.skill.promotion import PromotionStage


class RunFromPreview:
    def __init__(self, uow: UnitOfWork, clock: Clock, execute_skill: ExecuteSkill) -> None:
        self._uow = uow
        self._clock = clock
        self._execute = execute_skill

    async def begin(
        self,
        ctx: RequestContext,
        *,
        skill_id: SkillId,
        parameters: dict[str, str],
        device_id: DeviceId,
        intent: str,
    ) -> Run:
        """Promote what needs it and write the run row. Nothing has stepped yet.

        Split from `execute` for the same reason `ExecuteSkill` itself is
        split: this is always a device run -- the panel's whole premise is the
        operator's own tab -- and `run_skill`'s device path answers before the
        run finishes so the id exists for `/runs/{id}/stream` and
        `/runs/{id}/stop` while it is still running. A caller that returned
        only once the run was over would have promised a stop button the
        operator could never reach in time to use it.
        """
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
                    # DECISION (task 5, amended after review; see ADR 014's
                    # "Consequences", which this comment now matches): pass
                    # True here rather than let a single-demonstration write
                    # refuse this promotion and dead-end the press.
                    #
                    # `acknowledging_fixed_values` exists because a version
                    # induced from one demonstration was never diffed against
                    # a second one -- nothing tells the values it sends apart
                    # from the values that one run happened to carry, so
                    # promoting it past shadow without anybody having looked
                    # would mean repeating that one run's exact write forever.
                    # The flag is the record that somebody looked.
                    #
                    # This is NOT the same claim the press already makes to
                    # reach ASSISTED at all, and the first version of this
                    # comment was wrong to say so: the preview shows
                    # `SkillStep.intent`, the resolved value of each
                    # *parameter*, and the starting tab -- a closed list. A
                    # value this flag guards is, by definition, not a
                    # parameter: one demonstration means nothing was diffed, so
                    # nothing told a value that varies apart from one that is
                    # simply constant, and it is exactly those constants --
                    # never surfaced as a parameter, never a line on the
                    # preview -- that the flag is about. The two sets of values
                    # do not overlap; reading one is not reading the other.
                    #
                    # Setting it is therefore an accepted residual risk, not a
                    # closed one, taken on the same terms ADR 014 already
                    # accepts one for: it documents its own gap ("What the
                    # operator did not read") and closes it the same way every
                    # other run's unread surprises are closed -- not by the
                    # preview, but by `run.wrong_because`, read before anything
                    # else `judge` reads, and `DEMOTE_AFTER_FAILURES` pulling
                    # the version back down after three. A write sent on a
                    # fixed value nobody actually read is exactly the surprise
                    # that backstop exists for. The alternative -- refuse and
                    # dead-end the commonest shape a freshly induced skill has,
                    # one demonstration and one write, on its very first press
                    # -- is the failure this task exists to close, so the risk
                    # is accepted rather than the feature.
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

        return await self._execute.begin(
            ctx,
            ExecutionRequest(
                skill_id=skill_id,
                parameters=parameters,
                version=version_number,
                authorized_by=str(ctx.principal_id),
                device_id=device_id,
                intent=intent,
                # UI, not the NETWORK default: this run acts in the tab the
                # preview named (`starts_on`), which is the entire load-bearing
                # claim ADR 014 makes -- the operator read what would happen on
                # the screen in front of them. A NETWORK replay would send the
                # same calls invisibly, which is a different, undisclosed thing
                # from what the preview described and the operator agreed to.
                medium=Medium.UI,
                # True, deliberately: `run_skill`'s own field doc says a
                # console run "somebody just asked for" may bring the tab
                # forward, and a scheduled one may not, because the caller is
                # the only one who knows whether a person is watching. Here the
                # caller knows for certain -- this run exists only because an
                # operator is looking at the panel right now, mid-task, with
                # ADR 014's stop button already promised to them. Leaving this
                # False would drive their own tab in front of them without
                # bringing it up to show them, which defeats the one thing this
                # feature is for.
                may_take_focus=True,
            ),
        )

    async def execute(
        self,
        ctx: RequestContext,
        *,
        skill_id: SkillId,
        parameters: dict[str, str],
        device_id: DeviceId,
        intent: str,
    ) -> Run:
        """Promote, start and see the run through, in one call.

        For a caller that does not need to stream it -- the durable path, and
        most of this file's own tests -- mirroring `ExecuteSkill.execute`,
        which is exactly `begin` then `resume`. The HTTP router does not use
        this: it calls `begin` directly and hands the result to the same
        background pursuit `run_skill` spawns for its device path, so the
        caller gets the run id back before the run is over.
        """
        run = await self.begin(
            ctx, skill_id=skill_id, parameters=parameters, device_id=device_id, intent=intent
        )
        return await self._execute.resume(ctx, run)
