"""Perform a skill at L1: replay the calls the demonstration produced.

What this is careful about, in order of how much damage the alternative does:

- A mutation is sent at most once per run, and nothing here retries one. The run
  is saved after every step, so a run left RUNNING with N outcomes says exactly
  one thing: step N was in flight, and whether it landed is unknown. That is the
  state a human has to be told about rather than a state a retry may guess at.
- A stage that does not permit writes withholds them rather than skipping them.
  A shadow run produces the full request it would have sent, which is the only
  way to review one before allowing it.
- A step whose headers cannot be resolved does not go out degraded.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass, replace
from datetime import datetime
from urllib.parse import urlsplit

from sro.application.capture.identity import system_named, system_of
from sro.application.context import RequestContext
from sro.application.execution.answer import MAX_ROWS, Answer, merge, read_answer
from sro.application.execution.headers import client_headers, resolve_headers
from sro.application.execution.paging import MOST_PAGES, how_it_pages, next_page
from sro.application.execution.self_heal import HealBudget, Healed, SelfHeal
from sro.application.execution.verify import check, check_on_screen, extract
from sro.application.execution.vision_step import PerformWithVision
from sro.application.knowledge.learn_from_run import LearnFromRun
from sro.application.ports.agent import AgentDrivers
from sro.application.ports.http import HttpCaller, HttpResponse, TargetUnreachable
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.system import Clock, IdFactory
from sro.application.ports.token import TokenRefused, TokenSource
from sro.application.ports.ui import ResolvedLocator, UiDriver, UiUnavailable
from sro.application.ports.vault import CredentialVault
from sro.application.ports.vision import VisionUnavailable
from sro.domain.connection.connection import Connection
from sro.domain.execution.escalation import FailureKind, next_medium
from sro.domain.execution.run import (
    Medium,
    Run,
    RunId,
    RunStatus,
    StepDisposition,
    StepOutcome,
)
from sro.domain.execution.safety import FAILURE_WINDOW, WRITE_WINDOW, RunFact, assess
from sro.domain.execution.verdict import judge
from sro.domain.shared.errors import DomainError
from sro.domain.shared.identifiers import DeviceId, PrincipalId, SkillId
from sro.domain.shared.objective import ObjectiveKey
from sro.domain.skill.assertion import AssertionKind
from sro.domain.skill.parameter import Parameter, ParameterKind
from sro.domain.skill.promotion import PromotionStage
from sro.domain.skill.skill import Skill, SkillStep, SkillVersion

logger = logging.getLogger(__name__)


class NotRunnable(DomainError):
    """The skill cannot be run as asked. Never a partial run: this is raised
    before anything is sent."""

    code = "not_runnable"


async def refuse_if_breaker_is_open(
    uow: UnitOfWork, ctx: RequestContext, system: str, now: datetime
) -> None:
    """Whether anything at all may be driven against this system right now.

    About the system's recent behaviour, not about what is being asked of it, so
    every rung asks it: a replay, and a pursuit working a task out on the screen.
    The pursuit did not, and the rung with no demonstration behind it was the one
    allowed to keep going after the others had been stopped.
    """
    recent = await uow.runs.finished_since(
        ctx.tenant_id, target_system=system, since=now - FAILURE_WINDOW - WRITE_WINDOW
    )
    # Failures somebody has already looked at stop counting. Without this the
    # breaker asks for a person and gives them nothing to do: every run is
    # refused until the window ages out, including the one that would show the
    # fault is already fixed.
    connection = await uow.connections.find_by_system(ctx.tenant_id, system)
    cleared = connection.failures_acknowledged_at if connection else None
    if cleared is not None:
        recent = tuple(run for run in recent if run.ended_at is None or run.ended_at > cleared)
    verdict = assess(tuple(_fact(run) for run in recent), now)
    if not verdict.permitted:
        raise Refused(verdict.reason or "recent runs against this system have failed")


@dataclass(frozen=True, slots=True)
class ExecutionRequest:
    skill_id: SkillId
    parameters: dict[str, str]
    version: int | None = None
    authorized_by: str | None = None

    run_id: RunId | None = None
    """Given by the caller when it has to know the id before the run ends --
    a console streaming the steps as they happen, for instance."""

    device_id: DeviceId | None = None
    """Perform this in the operator's own browser rather than in one of ours.

    Which is how a skill runs against a system this deployment holds no
    credentials for: the request goes out of a page the operator is already
    signed in to. It also means the browser can close, and a run that loses it
    fails rather than being finished somewhere else."""

    medium: Medium = Medium.NETWORK
    """Which rung performs the whole task.

    A choice, not a fallback. Swapping medium mid-run leaves the browser without
    the screen state the earlier steps would have produced, so the task is the
    unit that changes rung, and today a human picks it."""

    may_take_focus: bool = False
    """Whether this run may bring a tab to the front of the operator's browser.

    Somebody watching a run they asked for is not interrupted by their tab
    changing; somebody typing at 3pm while a schedule fires behind them is.
    Default no, so a caller that has not thought about it does not take
    anybody's screen."""


class Refused(DomainError):
    """A safety limit stopped this before anything was sent.

    Separate from NotRunnable, which is about the skill: this is about the
    system's recent behaviour, and the answer is a person rather than a retry.
    """

    code = "refused"


class StartRun:
    """Create the run. Nothing has been sent when this returns."""

    def __init__(self, uow: UnitOfWork, clock: Clock, ids: IdFactory) -> None:
        self._uow = uow
        self._clock = clock
        self._ids = ids

    async def check(self, ctx: RequestContext, request: ExecutionRequest) -> None:
        """Everything ``execute`` would refuse for, without starting anything.

        For a caller that schedules the run somewhere else and answers before it
        begins. Without this, a refusal -- a skill at a stage that may not run, a
        breaker asking for a person -- happened inside the workflow, after the
        request had already answered 201 with a run id for a run that was never
        created. The console then watched that id forever, which is the one
        outcome a breaker exists to prevent.
        """
        async with self._uow as uow:
            await self._may_run(uow, ctx, request, self._clock.now())

    async def _may_run(
        self, uow: UnitOfWork, ctx: RequestContext, request: ExecutionRequest, now: datetime
    ) -> tuple[Skill, SkillVersion]:
        skill = await uow.skills.get(ctx.tenant_id, request.skill_id)
        version = _version_of(skill, request.version)
        _check_runnable(version, request)

        # Checked here because here is where nothing has happened yet. A
        # limit enforced after the first write is a limit that has already
        # been exceeded.
        #
        # Every system it touches, not only the one it is keyed by: a workflow
        # that writes into a second system must be stopped by that system's
        # breaker, and keying alone would hide exactly that.
        for system in version.systems or (skill.objective_key.target_system,):
            await refuse_if_breaker_is_open(uow, ctx, system, now)
        return skill, version

    async def execute(self, ctx: RequestContext, request: ExecutionRequest) -> Run:
        now = self._clock.now()
        async with self._uow as uow:
            skill, version = await self._may_run(uow, ctx, request, now)
            system = skill.objective_key.target_system

            run = Run(
                # Minted by whoever asked, where they need to know it before it
                # finishes: a console cannot stream a run whose id only arrives
                # with the last step.
                id=request.run_id or self._ids.new_run_id(),
                tenant_id=ctx.tenant_id,
                skill_id=skill.id,
                skill_version=version.version,
                stage=version.stage,
                parameters=dict(request.parameters),
                requested_by=ctx.principal_id,
                started_at=now,
                authorized_by=_principal(request.authorized_by),
                medium=request.medium,
                device_id=request.device_id,
                may_take_focus=request.may_take_focus,
                target_system=system,
                systems=version.systems,
                may_change_the_system=version.changes_the_system,
            )
            await uow.runs.add(run)
            await uow.commit()
        return run


class ExecuteStep:
    """One step of one run.

    A step at a time because that is the unit a crash can be resumed at. It is
    also the unit that must not be retried blindly: the caller knows whether the
    step it is asking for has already been recorded, because the run says so.
    """

    def __init__(
        self,
        uow: UnitOfWork,
        http: HttpCaller,
        vault: CredentialVault,
        ui: UiDriver | None = None,
        vision: PerformWithVision | None = None,
        heal: SelfHeal | None = None,
        tokens: TokenSource | None = None,
        agents: AgentDrivers | None = None,
    ) -> None:
        self._uow = uow
        self._http = http
        self._vault = vault
        self._ui = ui
        self._agents = agents
        self._vision = vision
        self._heal_with = heal
        self._tokens = tokens
        self._budgets: dict[str, HealBudget] = {}

    async def execute(self, ctx: RequestContext, *, run_id: RunId, index: int) -> StepOutcome:
        async with self._uow as uow:
            run = await uow.runs.get(ctx.tenant_id, run_id)
            # Read here because a step's credentials depend on which system it
            # is calling, and a workflow's steps do not all call the same one.
            connections = await uow.connections.list_for_tenant(ctx.tenant_id)
            skill = await uow.skills.get(ctx.tenant_id, run.skill_id)

        version = skill.version(run.skill_version)
        if index < len(run.steps):
            return run.steps[index]  # already done; never send it twice

        step = version.steps[index]
        if run.medium is Medium.UI:
            outcome = await self._perform_in_ui(run, step, values=run.values, version=version)
            run.record(outcome)
            async with self._uow as uow:
                await uow.runs.save(run)
                await uow.commit()
            return outcome

        # Every value this step hands forward, not the first: one call can
        # return an id and the code the next call needs alongside it.
        produces = tuple(
            parameter
            for parameter in version.parameters
            if parameter.kind is ParameterKind.DERIVED and parameter.source_step_index == index
        )

        outcome, derived, failure = await self._perform(
            run,
            step,
            values=run.values,
            scope=str(ctx.tenant_id),
            objective=skill.objective_key,
            connections=connections,
            produces=produces,
            parameters=tuple(version.parameters),
        )

        # A session that aged out is not a broken skill, and the run should not
        # need a person to say so. Repair what the target system owns, once,
        # and let the step speak for itself; anything the healer cannot explain
        # is left exactly as it failed.
        healed = await self._heal(ctx, run, skill, step, outcome, failure)
        if healed is not None and not healed.repaired:
            # Diagnosed and not repaired. The diagnosis is the useful half: a
            # step that says "assertion_failed" sends somebody to read the
            # skill, and this one was turned away at a login page by a system
            # nobody is signed into any more.
            outcome = replace(
                outcome,
                detail=f"{healed.because}; {healed.detail}"
                + (f" -- {outcome.detail}" if outcome.detail else ""),
            )
        elif healed is not None and _may_be_retried(step, outcome):
            outcome, derived, failure = await self._perform(
                run,
                step,
                values=run.values,
                scope=str(ctx.tenant_id),
                objective=skill.objective_key,
                connections=connections,
                produces=produces,
            )
            outcome = replace(
                outcome,
                detail=f"{healed.because}; {healed.detail}, then retried"
                + (f" -- {outcome.detail}" if outcome.detail else ""),
            )
        elif healed is not None:
            # Repaired, and deliberately not retried: this step's write reached
            # the application. Sending it again is how one create becomes two.
            outcome = replace(
                outcome,
                detail=f"{healed.because}; {healed.detail}, and not retried because "
                "this step's write may already have landed"
                + (f" -- {outcome.detail}" if outcome.detail else ""),
            )

        if failure is not None:
            outcome = await self._escalate(
                run, step, outcome, failure, values=run.values, version=version
            )
        run.record(outcome)
        for name, value in derived.items():
            run.learn(name, value)

        async with self._uow as uow:
            await uow.runs.save(run)
            await uow.commit()
        return outcome

    async def _heal(
        self,
        ctx: RequestContext,
        run: Run,
        skill: Skill,
        step: SkillStep,
        outcome: StepOutcome,
        failure: FailureKind | None,
    ) -> Healed | None:
        """Ask the healer whether this failure is one the session explains."""
        if self._heal_with is None or (
            outcome.disposition is StepDisposition.PERFORMED and not failure
        ):
            return None
        plan = step.network_plan
        return await self._heal_with.attempt(
            ctx,
            target_system=skill.objective_key.target_system,
            facility=skill.objective_key.facility,
            step_index=step.index,
            mutating=bool(plan and plan.is_mutation),
            budget=self._budget_for(run),
            failure=failure,
            status_code=outcome.status_code,
            missing_headers=_missing_named(outcome.detail),
            endpoint=f"{outcome.method} {urlsplit(outcome.url or '').path}"
            if outcome.url
            else None,
        )

    def _budget_for(self, run: Run) -> HealBudget:
        """One budget per run, so a repair that did not take is not repeated."""
        return self._budgets.setdefault(run.id.value, HealBudget())

    async def _bearer(self, tenant: str, session_scope: str) -> str | None:
        """An access token for this system, if one has been established."""
        if self._tokens is None:
            return None
        system = session_scope.split("/", 1)[0]
        try:
            return await self._tokens.access_token(tenant=tenant, system=system)
        except TokenRefused as refusal:
            # Worth a line, not a failure: the run falls back to the session
            # cookies and says so if those are gone too.
            logger.info("no access token for %s: %s", system, refusal)
            return None

    def _ui_for(
        self, run: Run, version: SkillVersion | None = None, step: SkillStep | None = None
    ) -> UiDriver | None:
        """The browser this run is performed in, and the page in it.

        A run bound to a device never falls back to the deployment's own
        browser. That one is signed in as somebody else, on a screen nobody
        demonstrated, and quietly using it would be worse than not running.

        The origin goes with it. An operator's Chrome has a dozen tabs and only
        one of them is the system this skill was taught on; without being told
        which, the extension can only take the frontmost page, and a run that
        guesses wrong performs a warehouse task on somebody's email.
        """
        if run.device_id is None:
            return self._ui
        if self._agents is None:
            return None
        return self._agents.ui(
            run.tenant_id, run.device_id, _origin_of(version, step), run.may_take_focus
        )

    def _caller_for(self, run: Run) -> HttpCaller:
        """Whose session the call goes out under. Same rule as the browser."""
        if run.device_id is None:
            return self._http
        if self._agents is None:
            raise TargetUnreachable("this run is bound to a browser this process cannot reach")
        return self._agents.http(run.tenant_id, run.device_id)

    async def _perform_in_ui(
        self, run: Run, step: SkillStep, *, values: dict[str, str], version: SkillVersion
    ) -> StepOutcome:
        """Perform one step of a task that is being run in the browser.

        The write rule is the same as at L1 and matters more here: a click is
        indistinguishable from a call once it has happened, so a stage that may
        not write may not click either.
        """
        plan = step.ui_plan
        if plan is None or not plan.replayable:
            return StepOutcome(
                index=step.index,
                medium=Medium.UI,
                disposition=StepDisposition.SKIPPED,
                intent=step.intent,
                detail="the demonstration left nothing here that can be found again",
            )
        if not run.performs_writes:
            return StepOutcome(
                index=step.index,
                medium=Medium.UI,
                disposition=StepDisposition.WITHHELD,
                intent=step.intent,
                idempotency_key=f"{run.id}:{step.index}",
                detail=(
                    f"{run.stage} does not drive the interface; "
                    f"would {plan.action} {plan.locators[0].describe() if plan.locators else ''}"
                ),
            )
        ui = self._ui_for(run, version)
        if ui is None:
            return self._failed(step, None, "no browser is attached", medium=Medium.UI)

        try:
            locators = tuple(
                ResolvedLocator(
                    strategy=locator.strategy,
                    query=locator.query.render(values),
                    within=locator.within,
                    visible_only=locator.visible_only,
                )
                for locator in plan.locators
            )
            value = plan.value.render(values) if plan.value is not None else None
        except KeyError as missing:
            return self._failed(
                step, None, f"no value for parameter {missing.args[0]!r}", medium=Medium.UI
            )

        try:
            result = await ui.perform(action=plan.action, locators=locators, value=value)
        except UiUnavailable as error:
            return self._failed(step, None, str(error), medium=Medium.UI)

        if not result.performed:
            return self._failed(step, None, result.detail or "control not found", medium=Medium.UI)

        said = [f"{result.candidates} candidates"] if result.candidates > 1 else []
        failures, unchecked = await self._check_on_screen(ui, step, values)
        if unchecked:
            said.append("not checkable from the interface: " + ", ".join(unchecked))
        return StepOutcome(
            index=step.index,
            medium=Medium.UI,
            disposition=StepDisposition.PERFORMED,
            intent=step.intent,
            idempotency_key=f"{run.id}:{step.index}",
            matched_by=result.matched_by.value if result.matched_by else None,
            assertion_failures=failures,
            detail="; ".join(said) or None,
        )

    async def _check_on_screen(
        self, ui: UiDriver, step: SkillStep, values: dict[str, str]
    ) -> tuple[tuple[str, ...], tuple[str, ...]]:
        """What the screen says, after the gesture that was supposed to change it.

        Only where the demonstration proved something visible, so a step whose
        evidence is a response body costs no screenshot. A screen that cannot be
        read is not a failed step -- the gesture landed, and calling the task
        wrong because a capture failed would be worse than saying what happened.
        """
        wanted = tuple(a for a in step.assertions if a.kind is AssertionKind.UI_TEXT_VISIBLE)
        if not wanted:
            return (), ()
        try:
            screen = await ui.capture()
        except (UiUnavailable, VisionUnavailable) as blind:
            return (), (f"the screen could not be read ({blind})",)
        return check_on_screen(step.assertions, screen.text_digest, values=values)

    async def _escalate(
        self,
        run: Run,
        step: SkillStep,
        outcome: StepOutcome,
        failure: FailureKind,
        *,
        values: dict[str, str],
        version: SkillVersion,
    ) -> StepOutcome:
        """Try the next rung, if the policy allows one and the run may act.

        Shadow never drives the interface. A withheld call is a call that did not
        happen; a click on the same screen is a call that did, and a rehearsal
        that quietly changed a warehouse would be worse than no rehearsal.
        """
        rule = next_medium(failure, Medium.NETWORK)
        if rule is None or rule.then is not Medium.UI:
            return outcome
        if not run.performs_writes:
            return replace(
                outcome,
                detail=f"{outcome.detail or failure}; {run.stage} does not drive the interface",
            )
        ui = self._ui_for(run, version)
        if ui is None or step.ui_plan is None or not step.ui_plan.replayable:
            return replace(
                outcome,
                detail=f"{outcome.detail or failure}; nothing to replay in the interface",
            )

        plan = step.ui_plan
        try:
            locators = tuple(
                ResolvedLocator(
                    strategy=locator.strategy,
                    query=locator.query.render(values),
                    within=locator.within,
                    visible_only=locator.visible_only,
                )
                for locator in plan.locators
            )
            value = plan.value.render(values) if plan.value is not None else None
        except KeyError as missing:
            return replace(outcome, detail=f"no value for parameter {missing.args[0]!r}")

        try:
            result = await ui.perform(action=plan.action, locators=locators, value=value)
        except UiUnavailable as error:
            return replace(outcome, detail=f"{outcome.detail or failure}; no browser: {error}")

        if not result.performed:
            # The recorded control is gone. Whether anything above may look at
            # the screen instead is the policy's decision, not this method's.
            return await self._escalate_to_vision(
                run,
                step,
                replace(
                    outcome,
                    escalated_from=Medium.NETWORK,
                    escalation_reason=rule.because,
                    detail=result.detail,
                ),
                version,
            )
        failures, unchecked = await self._check_on_screen(ui, step, values)
        return StepOutcome(
            index=step.index,
            medium=Medium.UI,
            disposition=StepDisposition.PERFORMED,
            intent=step.intent,
            idempotency_key=outcome.idempotency_key,
            escalated_from=Medium.NETWORK,
            escalation_reason=rule.because,
            matched_by=result.matched_by.value if result.matched_by else None,
            assertion_failures=failures,
            detail=(
                f"{outcome.detail or failure} at L1; performed in the interface"
                + (f" ({result.candidates} candidates)" if result.candidates > 1 else "")
                + (
                    "; not checkable from the interface: " + ", ".join(unchecked)
                    if unchecked
                    else ""
                )
            ),
        )

    async def _escalate_to_vision(
        self, run: Run, step: SkillStep, outcome: StepOutcome, version: SkillVersion
    ) -> StepOutcome:
        """The last rung, if the policy allows it and it is configured.

        Every attempt is recorded whether or not the model was reached: a run
        that would have escalated and could not is a different fact from a run
        that never tried, and only one of them means the deployment is missing
        a rung.
        """
        rule = next_medium(FailureKind.CONTROL_NOT_FOUND, Medium.UI)
        if rule is None or rule.then is not Medium.VISION or self._vision is None:
            return outcome

        # The same browser the rungs below it were driving. A run bound to a
        # device is performed in somebody's own Chrome, and a vision rung
        # holding the deployment's driver would photograph a different screen
        # and click on it -- signed in as somebody else, on a page nobody
        # demonstrated. Falling back is the one thing it must not do.
        ui = self._ui_for(run, version)
        if ui is None:
            return replace(
                outcome,
                detail=f"{outcome.detail or 'the control was not found'}; "
                "the browser this run is performed in cannot be reached",
            )

        result = await self._vision.execute(run, step, ui)
        if result.calls:
            async with self._uow as uow:
                for call in result.calls:
                    await uow.model_calls.add(call)
                await uow.commit()

        performed = result.outcome.disposition is StepDisposition.PERFORMED
        # The rung's own docstring says the model may claim a step is done and
        # the demonstration's assertions decide. Nothing decided: a click a
        # model chose by looking at a screenshot was recorded as a step that
        # succeeded, and counted towards the version's promotion. Here is where
        # they decide.
        failures, unchecked = (
            await self._check_on_screen(ui, step, run.values) if performed else ((), ())
        )
        return replace(
            result.outcome,
            escalation_reason=rule.because,
            assertion_failures=failures,
            detail=(
                f"{outcome.detail or 'the control was not found'}; {result.outcome.detail}"
                if not performed
                else (result.outcome.detail or "")
                + (
                    "; not checkable from the interface: " + ", ".join(unchecked)
                    if unchecked
                    else ""
                )
            ),
        )

    async def _perform(
        self,
        run: Run,
        step: SkillStep,
        *,
        values: dict[str, str],
        scope: str,
        objective: ObjectiveKey,
        connections: Sequence[Connection],
        produces: tuple[Parameter, ...] = (),
        parameters: tuple[Parameter, ...] = (),
    ) -> tuple[StepOutcome, dict[str, str], FailureKind | None]:
        plan = step.network_plan
        if plan is None:
            return (
                StepOutcome(
                    index=step.index,
                    medium=Medium.NETWORK,
                    disposition=StepDisposition.SKIPPED,
                    intent=step.intent,
                    detail="the demonstration produced no call here; only the UI moved",
                ),
                {},
                FailureKind.NO_PLAN,
            )
        if not plan.replayable:
            return (
                StepOutcome(
                    index=step.index,
                    medium=Medium.NETWORK,
                    disposition=StepDisposition.SKIPPED,
                    intent=step.intent,
                    detail=plan.unreplayable_reason,
                ),
                {},
                FailureKind.UNREPLAYABLE,
            )

        mutating = plan.is_mutation
        key = f"{run.id}:{step.index}" if mutating else None

        try:
            url = plan.url.render(values)
            body = plan.body.render(values) if plan.body is not None else None
        except KeyError as missing:
            # The step that would have minted this value, not merely some step
            # that was withheld. Any withheld step used to count, so a step that
            # failed for an unrelated reason -- a parameter nobody ever filled
            # in -- was recorded as cleanly withheld, and the run it belonged to
            # earned its way up the ladder on the strength of it.
            producer = next(
                (
                    parameter
                    for parameter in parameters
                    if parameter.name == missing.args[0] and parameter.kind is ParameterKind.DERIVED
                ),
                None,
            )
            withheld = next(
                (
                    s
                    for s in run.steps
                    if s.disposition is StepDisposition.WITHHELD
                    and producer is not None
                    and s.index == producer.source_step_index
                ),
                None,
            )
            if withheld is not None:
                # Not a fault: this rehearsal withheld the write that would have
                # minted the value. A create chain -- post the address, then the
                # client that names it -- can never be rehearsed to the end, and
                # reporting that as a failed step meant every such skill failed
                # its shadow run and could never earn its way off the rung.
                return (
                    StepOutcome(
                        index=step.index,
                        medium=Medium.NETWORK,
                        disposition=StepDisposition.WITHHELD,
                        intent=step.intent,
                        method=plan.method,
                        idempotency_key=key,
                        detail=(
                            f"needs {missing.args[0]!r}, which the withheld write at step "
                            f"{withheld.index} would have produced"
                        ),
                    ),
                    {},
                    None,
                )
            return (
                self._failed(step, key, f"no value for parameter {missing.args[0]!r}"),
                {},
                None,
            )

        # Whose session this call goes out under, decided by the host it is
        # going to rather than by the skill it belongs to.
        #
        # Everything credential-shaped hangs off this: the stored cookie, the
        # minted CSRF token, the live referer, and the bearer. A workflow's
        # second half keyed to its first would fetch the WMS's live token and
        # post it to the ERP -- one system's session handed to another, silently
        # -- and would fail to authenticate against the ERP into the bargain.
        #
        # A host nobody has connected falls back to the skill's own system,
        # which is every run there has ever been: a device run against a system
        # this deployment holds no credentials for is the whole point of naming
        # a device, and dropping its headers would break it.
        # A host nobody has connected falls back to the skill's own system --
        # every run there has ever been -- but only where the whole skill is
        # that one system. A workflow's unconnected half falling back would
        # resolve the *other* system's bearer and referer and send them there,
        # which is the leak this per-call scope exists to close.
        calling = system_of(connections, url) or (
            system_named(connections, url) if len(run.systems) > 1 else objective.target_system
        )
        session_scope = f"{calling}/{objective.facility}"

        resolved = await resolve_headers(
            plan.headers,
            values=values,
            vault=self._vault,
            scope=scope,
            session_scope=session_scope,
            bearer=await self._bearer(scope, session_scope),
            # The operator's own browser is the session. Nothing stored here is
            # sent as one, and nothing stored here is required.
            browser_session=run.device_id is not None,
        )
        if resolved.missing:
            # A device run has already been given the browser's session, so
            # what is missing here is a value minted per run -- and "connect
            # the system" is advice that would not have helped: the token
            # belongs to whichever session it was issued for, and this one is
            # the operator's. Everything before the semicolon is the record the
            # self-healer reads back, so only the advice changes.
            advice = (
                "connect the system"
                if run.device_id is None
                else "a run in your browser cannot mint it"
            )
            return (
                self._failed(
                    step,
                    key,
                    "no live value for " + ", ".join(resolved.missing) + f"; {advice}",
                ),
                {},
                FailureKind.CREDENTIAL_MISSING,
            )

        if mutating and not run.performs_writes:
            return (
                StepOutcome(
                    index=step.index,
                    medium=Medium.NETWORK,
                    disposition=StepDisposition.WITHHELD,
                    intent=step.intent,
                    method=plan.method,
                    url=url,
                    idempotency_key=key,
                    detail=f"{run.stage} does not send writes; the request was produced, not sent",
                ),
                {},
                None,
            )

        headers = {**client_headers(plan.headers, url), **resolved.headers}
        try:
            caller = self._caller_for(run)
            response = await caller.send(plan.method, url, headers=headers, body=body)
        except TargetUnreachable as error:
            detail = str(error)
            if mutating:
                detail += " -- the call may have arrived; do not retry without checking"
            return (
                self._failed(step, key, detail, method=plan.method, url=url),
                {},
                FailureKind.UNREACHABLE,
            )

        # What it found, not only that it answered -- and for a write, what it
        # created. A create returns the record it made, which is the one thing
        # the person who asked wants to see, and discarding it left them
        # looking at a status code for that too.
        answer = read_answer(response.text, url=url)
        if answer is not None and not mutating:
            # And the rest of it. An operator who asks which suppliers exist is
            # not asking for the first page; the paging is the system's own and
            # this walks it in the dialect the demonstration proved.
            answer = await self._rest_of(caller, url, headers, answer)

        failures = check(step.assertions, response, values=values)
        if plan.expected_status is not None and response.status_code != plan.expected_status:
            failures = (
                *failures,
                f"expected status {plan.expected_status}, got {response.status_code}",
            )

        return (
            StepOutcome(
                index=step.index,
                medium=Medium.NETWORK,
                disposition=StepDisposition.PERFORMED,
                intent=step.intent,
                method=plan.method,
                url=url,
                status_code=response.status_code,
                idempotency_key=key,
                assertion_failures=failures,
                found_rows=answer.rows if answer else None,
                found_total=answer.total if answer else None,
                found_partial=bool(answer and answer.partial),
                found=answer.sample if answer else (),
                found_columns=answer.columns if answer else (),
                found_values=(
                    tuple((key, values) for key, values in answer.distinct.items())
                    if answer
                    else ()
                ),
                found_labels=answer.labels if answer else (),
            ),
            _derive(produces, response),
            FailureKind.ASSERTION_FAILED if failures else None,
        )

    async def _rest_of(
        self, caller: HttpCaller, url: str, headers: dict[str, str], first: Answer
    ) -> Answer:
        """Follow this read's own paging until there is nothing after it."""
        paging = how_it_pages(url)
        if not paging.pages or first.rows < paging.limit:
            return first

        pages = [first]
        so_far = first.rows
        for page in range(MOST_PAGES):
            following = next_page(url, paging, so_far=so_far, page=page)
            if following is None:
                break
            try:
                response = await caller.send("GET", following, headers=headers)
            except TargetUnreachable:
                # What was read is still true. Stopping here reports fewer
                # records than exist, which the count beside them already says.
                break
            answer = read_answer(response.text, url=following)
            if answer is None or answer.rows == 0:
                break
            pages.append(answer)
            so_far += answer.rows
            if answer.rows < paging.limit or so_far >= MAX_ROWS:
                break
        return merge(tuple(pages)) or first

    @staticmethod
    def _failed(
        step: SkillStep,
        key: str | None,
        detail: str,
        *,
        method: str | None = None,
        url: str | None = None,
        medium: Medium = Medium.NETWORK,
    ) -> StepOutcome:
        return StepOutcome(
            index=step.index,
            medium=medium,
            disposition=StepDisposition.FAILED,
            intent=step.intent,
            method=method,
            url=url,
            idempotency_key=key,
            detail=detail,
        )


class FinishRun:
    """Close the run and decide what it says.

    Both paths end here -- in-process and durable -- which is why the knowledge
    write-back hangs off this and not off the workflow: a run that survives a
    restart teaches the store the same thing as one that did not.
    """

    def __init__(self, uow: UnitOfWork, clock: Clock, learn: LearnFromRun | None = None) -> None:
        self._uow = uow
        self._clock = clock
        self._learn = learn

    async def execute(self, ctx: RequestContext, *, run_id: RunId) -> Run:
        async with self._uow as uow:
            run = await uow.runs.get(ctx.tenant_id, run_id)
            now = self._clock.now()
            run.finish(now)
            await uow.runs.save(run)

            skill = await uow.skills.get(ctx.tenant_id, run.skill_id)
            version = skill.version(run.skill_version)
            verdict = judge(run)
            version.record_run(verdict, now)
            # The ladder climbs itself. Nobody has time to notice that a skill
            # has earned the next rung, and a stage that waits for someone to
            # notice is a fact about their afternoon rather than about the
            # skill. Demotion below still happens faster, and for less.
            version.earn(verdict, now)
            # Demotion is automatic and needs no human, which is exactly why it
            # is bounded by a small number: confirming a few runs costs an
            # operator minutes, and a broken autonomous skill keeps writing.
            if version.track_record.should_demote and version.stage.rung > (
                PromotionStage.SHADOW.rung
            ):
                version.demote(
                    PromotionStage.SHADOW,
                    now,
                    f"{version.track_record.consecutive_failures} runs failed in a row",
                )
            await uow.skills.save(skill)
            await uow.commit()

        if self._learn is not None:
            # After the commit: what the run did is the record, and a failure to
            # write down what was learned must not undo it.
            await self._learn.execute(ctx, run=run, system=skill.objective_key.target_system)
        return run


class ExecuteSkill:
    """Start, step through, finish. The in-process path.

    The durable path runs the same three use cases as separate activities, so a
    run that survives a restart is the same run, not a second implementation.
    """

    def __init__(
        self,
        uow: UnitOfWork,
        http: HttpCaller,
        vault: CredentialVault,
        clock: Clock,
        ids: IdFactory,
        ui: UiDriver | None = None,
        learn: LearnFromRun | None = None,
        vision: PerformWithVision | None = None,
        agents: AgentDrivers | None = None,
    ) -> None:
        self._uow = uow
        self._start = StartRun(uow, clock, ids)
        self._step = ExecuteStep(uow, http, vault, ui, vision, agents=agents)
        self._finish = FinishRun(uow, clock, learn)

    async def execute(self, ctx: RequestContext, request: ExecutionRequest) -> Run:
        run = await self._start.execute(ctx, request)
        async with self._uow as uow:
            skill = await uow.skills.get(ctx.tenant_id, run.skill_id)
        for index in range(len(skill.version(run.skill_version).steps)):
            await self._step.execute(ctx, run_id=run.id, index=index)
        return await self._finish.execute(ctx, run_id=run.id)


def _origin_of(version: SkillVersion | None, step: SkillStep | None = None) -> str | None:
    """The page a step acts on, as a bare scheme and host.

    The step's own recorded call where it has one, because a skill's steps do
    not all belong to the same system: a workflow checks the WMS and then
    records the receipt in the ERP, and a driver bound to one origin for the
    whole run would attempt the second half in the first half's tab.

    Where the step has no call of its own -- a UI-only step, or one whose host
    is parameterised -- the version answers instead, from the first step that
    names one. A parameterised host is no answer at all: the placeholder is not
    filled in until the step runs, and a tab cannot be chosen by a template.
    """
    if step is not None and (named := _origin_of_call(step)) is not None:
        return named
    if version is None:
        return None
    for each in version.steps:
        if (named := _origin_of_call(each)) is not None:
            return named
    return None


def _origin_of_call(step: SkillStep) -> str | None:
    if step.network_plan is None:
        return None
    parts = urlsplit(step.network_plan.url.raw)
    if parts.scheme in ("http", "https") and parts.netloc and "$" not in parts.netloc:
        return f"{parts.scheme}://{parts.netloc}"
    return None


def _version_of(skill: Skill, requested: int | None) -> SkillVersion:
    if requested is None:
        return skill.versions[-1]
    for version in skill.versions:
        if version.version == requested:
            return version
    raise NotRunnable(f"skill has no version {requested}")


def _check_runnable(version: SkillVersion, request: ExecutionRequest) -> None:
    if version.stage is PromotionStage.RECORDED:
        raise NotRunnable(
            "a recorded skill has not been reviewed by anybody; promote it to shadow "
            "to run it against the system"
        )
    # Authorisation is for changing the system. A skill that only reads asked
    # for a name and told the operator it "performs real writes" while fetching
    # a list -- which is both untrue and the kind of prompt that teaches people
    # to click past prompts.
    if (
        version.changes_the_system
        and version.stage.rung > PromotionStage.SHADOW.rung
        and not request.authorized_by
    ):
        raise NotRunnable(
            f"a {version.stage} run performs real writes and must name the human who authorised it"
        )
    # A version that spans systems is performed in a browser signed in to all of
    # them, and this deployment holds one session per system and never two at
    # once. Refused here rather than discovered at step four, halfway through a
    # job, with the first system already written to.
    if version.crosses_systems and request.device_id is None:
        raise NotRunnable(
            "this skill works across "
            + " and ".join(version.systems)
            + ", so it runs in a browser that is signed in to all of them: name a device"
        )
    supplied = set(request.parameters)
    required = {p.name for p in version.parameters if p.kind is ParameterKind.INPUT}
    if absent := sorted(required - supplied):
        raise NotRunnable("no value supplied for " + ", ".join(absent))


def _derive(produces: tuple[Parameter, ...], response: HttpResponse) -> dict[str, str]:
    """The values this step's response hands to later ones.

    A derived parameter that cannot be extracted is left unbound on purpose: the
    step that needs it then fails with the parameter's name, which points at the
    response that was supposed to carry it rather than at the step that broke.
    """
    bound: dict[str, str] = {}
    for parameter in produces:
        if parameter.source_pointer is None:
            continue
        value = extract(response, parameter.source_pointer)
        if value is not None:
            # Reformatted on the way where the demonstrations were: the WMS
            # answers `42` and the ERP is sent `LPN-00042`, and sending the bare
            # number would be a write the target system rejects or, worse,
            # accepts against the wrong record.
            bound[parameter.name] = (
                parameter.transform.apply(value) if parameter.transform else value
            )
    return bound


def _may_be_retried(step: SkillStep, outcome: StepOutcome) -> bool:
    """Whether sending this step again is safe, on the evidence of the attempt.

    Not on the diagnosis. The healer reads a 302 as proof the request was turned
    away at a login page, which it sometimes is -- and is also exactly what a
    successful form POST answers with. Both look identical from here, so the one
    that decides is whether a mutating request went out at all: a status code
    means the application answered, and an answered POST that is sent again is
    how one create becomes two.
    """
    plan = step.network_plan
    mutating = bool(plan and plan.is_mutation)
    return not (mutating and outcome.status_code is not None)


def _fact(run: Run) -> RunFact:
    return RunFact(
        finished_at=run.ended_at or run.started_at,
        failed=run.status is RunStatus.FAILED,
        writes=run.writes_sent,
    )


def _principal(value: str | None) -> PrincipalId | None:
    return PrincipalId(value) if value else None


__all__ = [
    "ExecuteSkill",
    "ExecuteStep",
    "ExecutionRequest",
    "FinishRun",
    "NotRunnable",
    "Refused",
    "StartRun",
]


def _missing_named(detail: str | None) -> tuple[str, ...]:
    """The headers a step said it had no live value for.

    Read back off the step's own words rather than threaded through a second
    return value: the message is the record, and a healer that diagnosed from
    something the record does not show would be repairing a failure nobody can
    see afterwards.
    """
    if not detail or not detail.startswith("no live value for "):
        return ()
    named = detail[len("no live value for ") :].split(";", 1)[0]
    return tuple(part.strip() for part in named.split(",") if part.strip())
