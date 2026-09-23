from __future__ import annotations

import asyncio
import json
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
from sro.application.execution.plan import next_step
from sro.application.execution.self_heal import HealBudget, Healed, SelfHeal
from sro.application.execution.stops import Stops
from sro.application.execution.verify import check, check_on_screen, check_text, extract
from sro.application.execution.vision_step import PerformWithVision
from sro.application.induction import jsonutil
from sro.application.induction.sites import parse_json as _parse_json
from sro.application.induction.sites import render_url
from sro.application.knowledge.learn_from_run import LearnFromRun
from sro.application.ports.agent import AgentDrivers
from sro.application.ports.http import (
    HttpCaller,
    HttpResponse,
    MalformedRequest,
    TargetUnreachable,
)
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.system import Clock, IdFactory
from sro.application.ports.token import TokenRefused, TokenSource
from sro.application.ports.tools import ToolCaller, ToolsUnavailable
from sro.application.ports.ui import ResolvedLocator, UiDriver, UiUnavailable
from sro.application.ports.vault import CredentialVault
from sro.application.ports.vision import VisionUnavailable
from sro.application.skill.repair_drift import RepairDrift
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
from sro.domain.execution.safety import (
    FAILURE_WINDOW,
    MAX_ITEMS_PER_BATCH,
    WRITE_WINDOW,
    RunFact,
    assess,
)
from sro.domain.execution.verdict import apply_verdict
from sro.domain.execution.workflow_run import already_running
from sro.domain.shared.errors import Conflict, DomainError
from sro.domain.shared.identifiers import DeviceId, PrincipalId, SkillId
from sro.domain.shared.objective import ObjectiveKey
from sro.domain.skill.assertion import AssertionKind
from sro.domain.skill.loop import Loop
from sro.domain.skill.parameter import Parameter, ParameterKind
from sro.domain.skill.promotion import PromotionStage
from sro.domain.skill.skill import Skill, SkillStep, SkillVersion

logger = logging.getLogger(__name__)

MAX_RECORDED_BODY_BYTES = 64 * 1024


def _recordable(body: str | None) -> tuple[str | None, str | None]:
    size = len(body.encode()) if body is not None else 0
    if size > MAX_RECORDED_BODY_BYTES:
        return None, f"its {size} byte body was too large to record"
    return body, None


class NotRunnable(DomainError):
    code = "not_runnable"


async def refuse_if_breaker_is_open(
    uow: UnitOfWork, ctx: RequestContext, system: str, now: datetime
) -> None:
    recent = await uow.runs.finished_since(
        ctx.tenant_id, target_system=system, since=now - FAILURE_WINDOW - WRITE_WINDOW
    )
    connection = await uow.connections.find_by_system(ctx.tenant_id, system)
    cleared = connection.failures_acknowledged_at if connection else None
    if cleared is not None:
        recent = tuple(run for run in recent if run.ended_at is None or run.ended_at > cleared)
    verdict = assess(tuple(_fact(run) for run in recent), now)
    if not verdict.permitted:
        raise Refused(verdict.reason or "recent runs against this system have failed")


async def ensure_runnable(
    uow: UnitOfWork,
    ctx: RequestContext,
    skill: Skill,
    version: SkillVersion,
    request: ExecutionRequest,
    now: datetime,
) -> None:
    _check_runnable(version, request)
    for system in version.systems or (skill.objective_key.target_system,):
        await refuse_if_breaker_is_open(uow, ctx, system, now)


@dataclass(frozen=True, slots=True)
class ExecutionRequest:
    skill_id: SkillId
    parameters: dict[str, str]
    version: int | None = None
    authorized_by: str | None = None

    run_id: RunId | None = None

    device_id: DeviceId | None = None

    medium: Medium = Medium.NETWORK

    may_take_focus: bool = False

    intent: str = ""


class Refused(DomainError):
    code = "refused"


class StartRun:
    def __init__(self, uow: UnitOfWork, clock: Clock, ids: IdFactory) -> None:
        self._uow = uow
        self._clock = clock
        self._ids = ids

    async def check(self, ctx: RequestContext, request: ExecutionRequest) -> None:
        async with self._uow as uow:
            await self._may_run(uow, ctx, request, self._clock.now())

    async def _may_run(
        self, uow: UnitOfWork, ctx: RequestContext, request: ExecutionRequest, now: datetime
    ) -> tuple[Skill, SkillVersion]:
        skill = await uow.skills.get(ctx.tenant_id, request.skill_id)
        version = _version_of(skill, request.version)
        await ensure_runnable(uow, ctx, skill, version, request, now)
        if request.device_id is not None:
            busy = await uow.runs.in_flight(ctx.tenant_id, request.device_id)
            if busy is not None and busy != str(request.run_id or ""):
                raise Conflict(already_running(request.device_id.value, busy))
        return skill, version

    async def execute(self, ctx: RequestContext, request: ExecutionRequest) -> Run:
        now = self._clock.now()
        async with self._uow as uow:
            skill, version = await self._may_run(uow, ctx, request, now)
            system = skill.objective_key.target_system

            run = Run(
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
                intent=request.intent,
            )
            await uow.runs.add(run)
            await uow.commit()
        return run


_LOOK_AGAIN = 0.4

NOTHING_ASSERTED = "the step asserts nothing"

SCREEN_SETTLES_WITHIN = 2.0


class ExecuteStep:
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
        tools: ToolCaller | None = None,
        clock: Clock | None = None,
        settles_within: float = SCREEN_SETTLES_WITHIN,
    ) -> None:
        self._uow = uow
        self._tools = tools
        self._clock = clock
        self._http = http
        self._vault = vault
        self._ui = ui
        self._agents = agents
        self._vision = vision
        self._heal_with = heal
        self._tokens = tokens
        self._budgets: dict[str, HealBudget] = {}
        self._settles_within = settles_within

    async def has_more(self, ctx: RequestContext, *, run_id: RunId) -> bool:
        async with self._uow as uow:
            run = await uow.runs.get(ctx.tenant_id, run_id)
            skill = await uow.skills.get(ctx.tenant_id, run.skill_id)
        return next_step(skill.version(run.skill_version), run) is not None

    async def execute(self, ctx: RequestContext, *, run_id: RunId, index: int) -> StepOutcome:
        async with self._uow as uow:
            run = await uow.runs.get(ctx.tenant_id, run_id)
            connections = await uow.connections.list_for_tenant(ctx.tenant_id)
            skill = await uow.skills.get(ctx.tenant_id, run.skill_id)

        version = skill.version(run.skill_version)
        if index < len(run.steps):
            return run.steps[index]

        nxt = next_step(version, run)
        if nxt is None:
            raise NotRunnable(
                f"run {run.id} has no step at position {index}; "
                "a loop's list has not arrived, or the run is already finished"
            )
        step = version.steps[nxt.step_index]
        values = nxt.values

        if step.tool_plan is not None and run.medium is not Medium.UI:
            outcome = await self._perform_with_tool(run, step, values=values)
            outcome = replace(
                outcome, index=index, plan_step=nxt.step_index, iteration=nxt.iteration
            )
            run.record(outcome)
            async with self._uow as uow:
                await uow.runs.save(run)
                await uow.commit()
            return outcome

        if run.medium is Medium.UI:
            outcome = await self._perform_in_ui(
                run, step, values=values, version=version, connections=connections
            )
            outcome = replace(
                outcome, index=index, plan_step=nxt.step_index, iteration=nxt.iteration
            )
            run.record(outcome)
            async with self._uow as uow:
                await uow.runs.save(run)
                await uow.commit()
            return outcome

        produces = tuple(
            parameter
            for parameter in version.parameters
            if parameter.kind is ParameterKind.DERIVED
            and parameter.source_step_index == nxt.step_index
        )

        outcome, derived, failure, iterated = await self._perform(
            run,
            step,
            values=values,
            scope=str(ctx.tenant_id),
            objective=skill.objective_key,
            connections=connections,
            produces=produces,
            parameters=tuple(version.parameters),
            feeds=version.loop_from(nxt.step_index),
        )

        healed = await self._heal(ctx, run, skill, step, outcome, failure)
        if healed is not None and not healed.repaired:
            outcome = replace(
                outcome,
                detail=f"{healed.because}; {healed.detail}"
                + (f" -- {outcome.detail}" if outcome.detail else ""),
            )
        elif healed is not None and _may_be_retried(step, outcome):
            outcome, derived, failure, iterated = await self._perform(
                run,
                step,
                values=values,
                scope=str(ctx.tenant_id),
                objective=skill.objective_key,
                connections=connections,
                produces=produces,
                parameters=tuple(version.parameters),
                feeds=version.loop_from(nxt.step_index),
            )
            outcome = replace(
                outcome,
                detail=f"{healed.because}; {healed.detail}, then retried"
                + (f" -- {outcome.detail}" if outcome.detail else ""),
            )
        elif healed is not None:
            outcome = replace(
                outcome,
                detail=f"{healed.because}; {healed.detail}, and not retried because "
                "this step's write may already have landed"
                + (f" -- {outcome.detail}" if outcome.detail else ""),
            )

        if failure is not None:
            outcome = await self._escalate(
                run,
                step,
                outcome,
                failure,
                values=values,
                version=version,
                connections=connections,
            )
        outcome = replace(outcome, index=index, plan_step=nxt.step_index, iteration=nxt.iteration)
        run.record(outcome)
        for name, value in derived.items():
            run.learn(name, value)
        if iterated is not None:
            run.will_iterate(*iterated)

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
        return self._budgets.setdefault(run.id.value, HealBudget())

    async def _bearer(self, tenant: str, session_scope: str) -> str | None:
        if self._tokens is None:
            return None
        system = session_scope.split("/", 1)[0]
        try:
            return await self._tokens.access_token(tenant=tenant, system=system)
        except TokenRefused as refusal:
            logger.info("no access token for %s: %s", system, refusal)
            return None

    def _ui_for(
        self,
        run: Run,
        version: SkillVersion | None = None,
        step: SkillStep | None = None,
        connections: Sequence[Connection] = (),
    ) -> UiDriver | None:
        if run.device_id is None:
            return self._ui
        if self._agents is None:
            return None
        return self._agents.ui(
            run.tenant_id,
            run.device_id,
            _origin_of(version, step, connections),
            run.may_take_focus,
            starts_on=version.starts_on if version is not None else None,
            doing=step.intent if step is not None else "",
            step=(step.index + 1) if step is not None else None,
            of=len(version.steps) if version is not None else None,
        )

    def _caller_for(self, run: Run) -> HttpCaller:
        if run.device_id is None:
            return self._http
        if self._agents is None:
            raise TargetUnreachable("this run is bound to a browser this process cannot reach")
        return self._agents.http(run.tenant_id, run.device_id)

    async def _perform_in_ui(
        self,
        run: Run,
        step: SkillStep,
        *,
        values: dict[str, str],
        version: SkillVersion,
        connections: Sequence[Connection] = (),
    ) -> StepOutcome:
        if step.when and not values.get(step.when):
            return StepOutcome(
                index=step.index,
                medium=Medium.UI,
                disposition=StepDisposition.SKIPPED,
                intent=step.intent,
                detail=f"nothing was supplied for {step.when}, which this step fills",
            )
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
        ui = self._ui_for(run, version, step, connections)
        if ui is None:
            return self._failed(
                step, None, "no browser is attached", medium=Medium.UI, unreachable=True
            )

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
            return self._failed(step, None, str(error), medium=Medium.UI, unreachable=True)

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
            unchecked=unchecked,
            detail="; ".join(said) or None,
        )

    async def _check_on_screen(
        self, ui: UiDriver, step: SkillStep, values: dict[str, str]
    ) -> tuple[tuple[str, ...], tuple[str, ...]]:
        wanted = tuple(a for a in step.assertions if a.kind is AssertionKind.UI_TEXT_VISIBLE)
        if not wanted:
            return (), tuple(dict.fromkeys(a.kind.value for a in step.assertions)) or (
                NOTHING_ASSERTED,
            )

        failures: tuple[str, ...] = ()
        unchecked: tuple[str, ...] = ()
        waited = 0.0
        while True:
            try:
                screen = await ui.capture()
            except (UiUnavailable, VisionUnavailable) as blind:
                return (), (f"the screen could not be read ({blind})",)
            failures, unchecked = check_on_screen(
                step.assertions, screen.text_digest, values=values
            )
            if not failures or waited >= self._settles_within:
                return failures, unchecked
            await asyncio.sleep(min(_LOOK_AGAIN, self._settles_within - waited))
            waited += _LOOK_AGAIN

    async def _escalate(
        self,
        run: Run,
        step: SkillStep,
        outcome: StepOutcome,
        failure: FailureKind,
        *,
        values: dict[str, str],
        version: SkillVersion,
        connections: Sequence[Connection] = (),
    ) -> StepOutcome:
        rule = next_medium(failure, Medium.NETWORK)
        if rule is None or rule.then is not Medium.UI:
            return outcome
        if not run.performs_writes:
            return replace(
                outcome,
                detail=f"{outcome.detail or failure}; {run.stage} does not drive the interface",
            )
        ui = self._ui_for(run, version, step, connections)
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
                connections,
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
            unchecked=unchecked,
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
        self,
        run: Run,
        step: SkillStep,
        outcome: StepOutcome,
        version: SkillVersion,
        connections: Sequence[Connection] = (),
    ) -> StepOutcome:
        rule = next_medium(FailureKind.CONTROL_NOT_FOUND, Medium.UI)
        if rule is None or rule.then is not Medium.VISION or self._vision is None:
            return outcome

        ui = self._ui_for(run, version, step, connections)
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
        failures, unchecked = (
            await self._check_on_screen(ui, step, run.values) if performed else ((), ())
        )
        return replace(
            result.outcome,
            escalation_reason=rule.because,
            assertion_failures=failures,
            unchecked=unchecked,
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
        feeds: Loop | None = None,
    ) -> tuple[StepOutcome, dict[str, str], FailureKind | None, _Iterations | None]:
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
                None,
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
                None,
            )

        mutating = plan.is_mutation
        key = f"{run.id}:{step.index}" if mutating else None

        rendered = dict(values)
        encoded: dict[str, str] = {}
        for parameter in parameters:
            if (absent := parameter.absent_value) is not None and not rendered.get(parameter.name):
                rendered[parameter.name] = absent
            elif parameter.name in rendered and not parameter.is_the_body:
                written = json.dumps(rendered[parameter.name])
                encoded[parameter.name] = (
                    written if parameter.unquoted_as == "string" else written[1:-1]
                )

        for parameter in parameters:
            supplied = rendered.get(parameter.name)
            if supplied is not None and (refused := parameter.rejects(supplied)) is not None:
                return (self._failed(step, key, refused), {}, None, None)

        try:
            url = render_url(plan.url, rendered)
            body = plan.body.render({**rendered, **encoded}) if plan.body is not None else None
        except KeyError as missing:
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
                    None,
                )
            return (
                self._failed(step, key, f"no value for parameter {missing.args[0]!r}"),
                {},
                None,
                None,
            )

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
            browser_session=run.device_id is not None,
        )
        if resolved.missing:
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
                None,
            )

        if mutating and not run.performs_writes:
            detail = f"{run.stage} does not send writes; the request was produced, not sent"
            recorded, oversize = _recordable(body)
            if oversize is not None:
                detail += f"; {oversize}"
            return (
                StepOutcome(
                    index=step.index,
                    medium=Medium.NETWORK,
                    disposition=StepDisposition.WITHHELD,
                    intent=step.intent,
                    method=plan.method,
                    url=url,
                    idempotency_key=key,
                    request_body=recorded,
                    detail=detail,
                ),
                {},
                None,
                None,
            )

        headers = {**client_headers(plan.headers, url), **resolved.headers}

        sent, oversize = _recordable(body) if mutating else (None, None)

        try:
            caller = self._caller_for(run)
            response = await caller.send(plan.method, url, headers=headers, body=body)
        except TargetUnreachable as error:
            built_wrong = isinstance(error, MalformedRequest)
            detail = str(error)
            if mutating and not built_wrong:
                detail += " -- the call may have arrived; do not retry without checking"
            if oversize is not None:
                detail += f"; {oversize}"
            return (
                self._failed(
                    step,
                    key,
                    detail,
                    method=plan.method,
                    url=url,
                    request_body=sent,
                    unreachable=not built_wrong,
                ),
                {},
                FailureKind.UNREACHABLE,
                None,
            )

        answer = read_answer(response.text, url=url)
        if answer is not None and not mutating:
            answer = await self._rest_of(caller, url, headers, answer)

        failures = check(step.assertions, response, values=values)
        if plan.expected_status is not None and response.status_code != plan.expected_status:
            failures = (
                *failures,
                f"expected status {plan.expected_status}, got {response.status_code}",
            )

        iterated: _Iterations | None = None
        if feeds is not None and not failures:
            found = _iterations_of(feeds, response)
            if isinstance(found, str):
                return (self._failed(step, key, found, method=plan.method, url=url), {}, None, None)
            if len(found) > MAX_ITEMS_PER_BATCH:
                return (
                    self._failed(
                        step,
                        key,
                        f"this would act on {len(found)} things, and more than "
                        f"{MAX_ITEMS_PER_BATCH} in one run is a decision for a person",
                        method=plan.method,
                        url=url,
                    ),
                    {},
                    None,
                    None,
                )
            iterated = (feeds.first_step, found)

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
                request_body=sent,
                detail=oversize,
                assertion_failures=failures,
                unchecked=() if step.assertions else (NOTHING_ASSERTED,),
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
            iterated,
        )

    async def _rest_of(
        self, caller: HttpCaller, url: str, headers: dict[str, str], first: Answer
    ) -> Answer:
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
                break
            answer = read_answer(response.text, url=following)
            if answer is None or answer.rows == 0:
                break
            pages.append(answer)
            so_far += answer.rows
            if answer.rows < paging.limit or so_far >= MAX_ROWS:
                break
        return merge(tuple(pages)) or first

    async def _perform_with_tool(
        self, run: Run, step: SkillStep, *, values: dict[str, str]
    ) -> StepOutcome:
        plan = step.tool_plan
        assert plan is not None  # noqa: S101 -- the caller checked; this is for the reader
        key = f"{run.id}:{step.index}"

        if self._tools is None or not self._tools.available:
            return self._failed(
                step,
                None,
                f"no connector is configured, so {plan.tool} on {plan.server} cannot be called",
                medium=Medium.TOOL,
                unreachable=True,
            )

        try:
            arguments = {name: value.render(values) for name, value in plan.arguments}
        except KeyError as missing:
            return self._failed(
                step,
                None,
                f"no value for {missing.args[0]}",
                medium=Medium.TOOL,
            )

        if plan.writes:
            async with self._uow as uow:
                first = await uow.tool_calls.remember(
                    run.tenant_id,
                    key,
                    tool=f"{plan.server}/{plan.tool}",
                    at=self._clock.now() if self._clock else run.started_at,
                )
                await uow.commit()
            if not first:
                return self._failed(
                    step,
                    key,
                    f"{plan.tool} was already called for this step, and it may have "
                    "landed. Nothing is sent twice on a guess -- start a new run if "
                    "it did not",
                    medium=Medium.TOOL,
                )

        try:
            answered = await self._tools.call(
                run.tenant_id, run.requested_by, plan.server, plan.tool, arguments
            )
        except ToolsUnavailable as gone:
            return self._failed(step, key, str(gone), medium=Medium.TOOL, unreachable=True)

        failures = check_text(step.assertions, answered.text, values=values)
        if answered.failed:
            return self._failed(
                step,
                key,
                answered.detail or f"{plan.tool} refused",
                medium=Medium.TOOL,
            )

        return StepOutcome(
            index=step.index,
            medium=Medium.TOOL,
            disposition=StepDisposition.PERFORMED,
            intent=step.intent,
            url=f"{plan.server}/{plan.tool}",
            idempotency_key=key if plan.writes else None,
            request_body=json.dumps(arguments) if plan.writes else None,
            assertion_failures=failures,
            unchecked=() if step.assertions else (NOTHING_ASSERTED,),
            detail=answered.detail,
        )

    @staticmethod
    def _failed(
        step: SkillStep,
        key: str | None,
        detail: str,
        *,
        method: str | None = None,
        url: str | None = None,
        medium: Medium = Medium.NETWORK,
        request_body: str | None = None,
        unreachable: bool = False,
    ) -> StepOutcome:
        return StepOutcome(
            index=step.index,
            medium=medium,
            disposition=StepDisposition.FAILED,
            intent=step.intent,
            method=method,
            url=url,
            idempotency_key=key,
            request_body=request_body,
            detail=detail,
            unreachable=unreachable,
        )


class FinishRun:
    def __init__(
        self,
        uow: UnitOfWork,
        clock: Clock,
        learn: LearnFromRun | None = None,
        repair: RepairDrift | None = None,
    ) -> None:
        self._uow = uow
        self._clock = clock
        self._learn = learn
        self._repair = repair

    async def execute(
        self, ctx: RequestContext, *, run_id: RunId, stopped: str | None = None
    ) -> Run:
        async with self._uow as uow:
            run = await uow.runs.get(ctx.tenant_id, run_id)
            now = self._clock.now()
            if stopped is None:
                run.finish(now)
            else:
                run.fail(now, stopped)
            await uow.runs.save(run)

            skill = await uow.skills.get(ctx.tenant_id, run.skill_id)
            apply_verdict(skill, run, now)
            version = skill.version(run.skill_version)
            await uow.skills.save(skill)
            await uow.commit()

        if self._learn is not None:
            await self._learn.execute(
                ctx,
                run=run,
                system=skill.objective_key.target_system,
                version=version,
            )
        if self._repair is not None:
            await self._repair.execute(ctx, run=run)
        return run


class ExecuteSkill:
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
        repair: RepairDrift | None = None,
        stops: Stops | None = None,
        tools: ToolCaller | None = None,
    ) -> None:
        self._uow = uow
        self._start = StartRun(uow, clock, ids)
        self._step = ExecuteStep(
            uow, http, vault, ui, vision, agents=agents, tools=tools, clock=clock
        )
        self._finish = FinishRun(uow, clock, learn, repair)
        self._stops = stops or Stops()

    async def execute(self, ctx: RequestContext, request: ExecutionRequest) -> Run:
        return await self.resume(ctx, await self.begin(ctx, request))

    async def begin(self, ctx: RequestContext, request: ExecutionRequest) -> Run:
        return await self._start.execute(ctx, request)

    async def resume(self, ctx: RequestContext, run: Run) -> Run:
        async with self._uow as uow:
            skill = await uow.skills.get(ctx.tenant_id, run.skill_id)
        version = skill.version(run.skill_version)

        position = 0
        stopped: str | None = None
        while True:
            if self._stops.asked(run.id.value):
                stopped = "a person stopped this run"
                break
            async with self._uow as uow:
                current = await uow.runs.get(ctx.tenant_id, run.id)
            if next_step(version, current) is None:
                break
            await self._step.execute(ctx, run_id=run.id, index=position)
            position += 1
        try:
            return await self._finish.execute(ctx, run_id=run.id, stopped=stopped)
        finally:
            self._stops.forget(run.id.value)


def _origin_of(
    version: SkillVersion | None,
    step: SkillStep | None = None,
    connections: Sequence[Connection] = (),
) -> str | None:
    if step is not None and (named := _origin_of_call(step)) is not None:
        return named
    if version is None:
        return None
    for each in version.steps:
        if (named := _origin_of_call(each)) is not None:
            return named
    return _origin_of_system(version, connections)


def _origin_of_system(version: SkillVersion, connections: Sequence[Connection]) -> str | None:
    if len(version.systems) != 1:
        return None
    for connection in connections:
        if connection.target_system != version.systems[0]:
            continue
        parts = urlsplit(connection.base_url)
        if parts.scheme in ("http", "https") and parts.netloc:
            return f"{parts.scheme}://{parts.netloc}"
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
    if (
        version.changes_the_system
        and version.stage.rung > PromotionStage.SHADOW.rung
        and not request.authorized_by
    ):
        raise NotRunnable(
            f"a {version.stage} run performs real writes and must name the human who authorised it"
        )
    if version.loops and request.medium is not Medium.NETWORK:
        raise NotRunnable(
            "this skill does part of its work once for each thing a response lists, "
            f"which only the network rung can read; {request.medium} cannot run it"
        )
    if version.crosses_systems and request.device_id is None:
        raise NotRunnable(
            "this skill works across "
            + " and ".join(version.systems)
            + ", so it runs in a browser that is signed in to all of them: name a device"
        )
    supplied = set(request.parameters)
    required = {p.name for p in version.inputs}
    if absent := sorted(required - supplied):
        raise NotRunnable("no value supplied for " + ", ".join(absent))
    for parameter in version.parameters:
        value = request.parameters.get(parameter.name, "")
        if value and (refused := parameter.rejects(value)) is not None:
            raise NotRunnable(refused)


_Iterations = tuple[int, list[dict[str, str]]]


def _iterations_of(loop: Loop, response: HttpResponse) -> list[dict[str, str]] | str:
    document = _parse_json(response.text)
    if document is None:
        return f"the answer is not JSON, so {loop.over_pointer} could not be read"
    try:
        listed = jsonutil.get(document, loop.over_pointer)
    except (KeyError, IndexError, TypeError):
        return f"the answer has no {loop.over_pointer} to act on"
    if not isinstance(listed, list):
        return f"{loop.over_pointer} is not a list of things"

    bindings: list[dict[str, str]] = []
    for position, element in enumerate(listed):
        bound: dict[str, str] = {}
        for binding in loop.binds:
            try:
                bound[binding.parameter] = jsonutil.as_text(jsonutil.get(element, binding.pointer))
            except (KeyError, IndexError, TypeError):
                return (
                    f"thing {position} at {loop.over_pointer} has no {binding.pointer}, "
                    f"which is where {binding.parameter} comes from"
                )
        bindings.append(bound)
    return bindings


def _derive(produces: tuple[Parameter, ...], response: HttpResponse) -> dict[str, str]:
    bound: dict[str, str] = {}
    for parameter in produces:
        if parameter.source_pointer is None:
            continue
        value = extract(response, parameter.source_pointer)
        if value is not None:
            bound[parameter.name] = (
                parameter.transform.apply(value) if parameter.transform else value
            )
    return bound


def _may_be_retried(step: SkillStep, outcome: StepOutcome) -> bool:
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
    "ensure_runnable",
]


def _missing_named(detail: str | None) -> tuple[str, ...]:
    if not detail or not detail.startswith("no live value for "):
        return ()
    named = detail[len("no live value for ") :].split(";", 1)[0]
    return tuple(part.strip() for part in named.split(",") if part.strip())
