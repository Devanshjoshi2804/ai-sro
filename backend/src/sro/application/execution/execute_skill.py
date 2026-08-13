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

from dataclasses import dataclass

from sro.application.context import RequestContext
from sro.application.execution.headers import resolve_headers
from sro.application.execution.verify import check, extract
from sro.application.ports.http import HttpCaller, HttpResponse, TargetUnreachable
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.system import Clock, IdFactory
from sro.application.ports.vault import CredentialVault
from sro.domain.execution.run import Medium, Run, RunId, StepDisposition, StepOutcome
from sro.domain.shared.errors import DomainError
from sro.domain.shared.identifiers import PrincipalId, SkillId
from sro.domain.skill.parameter import Parameter, ParameterKind
from sro.domain.skill.promotion import PromotionStage
from sro.domain.skill.skill import Skill, SkillStep, SkillVersion


class NotRunnable(DomainError):
    """The skill cannot be run as asked. Never a partial run: this is raised
    before anything is sent."""

    code = "not_runnable"


@dataclass(frozen=True, slots=True)
class ExecutionRequest:
    skill_id: SkillId
    parameters: dict[str, str]
    version: int | None = None
    authorized_by: str | None = None


class StartRun:
    """Create the run. Nothing has been sent when this returns."""

    def __init__(self, uow: UnitOfWork, clock: Clock, ids: IdFactory) -> None:
        self._uow = uow
        self._clock = clock
        self._ids = ids

    async def execute(self, ctx: RequestContext, request: ExecutionRequest) -> Run:
        async with self._uow as uow:
            skill = await uow.skills.get(ctx.tenant_id, request.skill_id)
            version = _version_of(skill, request.version)
            _check_runnable(version, request)

            run = Run(
                id=self._ids.new_run_id(),
                tenant_id=ctx.tenant_id,
                skill_id=skill.id,
                skill_version=version.version,
                stage=version.stage,
                parameters=dict(request.parameters),
                requested_by=ctx.principal_id,
                started_at=self._clock.now(),
                authorized_by=_principal(request.authorized_by),
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

    def __init__(self, uow: UnitOfWork, http: HttpCaller, vault: CredentialVault) -> None:
        self._uow = uow
        self._http = http
        self._vault = vault

    async def execute(self, ctx: RequestContext, *, run_id: RunId, index: int) -> StepOutcome:
        async with self._uow as uow:
            run = await uow.runs.get(ctx.tenant_id, run_id)
            skill = await uow.skills.get(ctx.tenant_id, run.skill_id)

        version = skill.version(run.skill_version)
        if index < len(run.steps):
            return run.steps[index]  # already done; never send it twice

        step = version.steps[index]
        produces = next(
            (
                parameter
                for parameter in version.parameters
                if parameter.kind is ParameterKind.DERIVED and parameter.source_step_index == index
            ),
            None,
        )

        outcome, derived = await self._perform(
            run,
            step,
            values=run.values,
            scope=str(ctx.tenant_id),
            session_scope=(f"{skill.objective_key.target_system}/{skill.objective_key.facility}"),
            produces=produces,
        )
        run.record(outcome)
        for name, value in derived.items():
            run.learn(name, value)

        async with self._uow as uow:
            await uow.runs.save(run)
            await uow.commit()
        return outcome

    async def _perform(
        self,
        run: Run,
        step: SkillStep,
        *,
        values: dict[str, str],
        scope: str,
        session_scope: str,
        produces: Parameter | None = None,
    ) -> tuple[StepOutcome, dict[str, str]]:
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
            )

        mutating = plan.method.upper() not in {"GET", "HEAD", "OPTIONS"}
        key = f"{run.id}:{step.index}" if mutating else None

        try:
            url = plan.url.render(values)
            body = plan.body.render(values) if plan.body is not None else None
        except KeyError as missing:
            return (
                self._failed(step, key, f"no value for parameter {missing.args[0]!r}"),
                {},
            )

        resolved = await resolve_headers(
            plan.headers,
            values=values,
            vault=self._vault,
            scope=scope,
            session_scope=session_scope,
        )
        if resolved.missing:
            return (
                self._failed(
                    step,
                    key,
                    "no live value for " + ", ".join(resolved.missing) + "; connect the system",
                ),
                {},
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
            )

        try:
            response = await self._http.send(plan.method, url, headers=resolved.headers, body=body)
        except TargetUnreachable as error:
            detail = str(error)
            if mutating:
                detail += " -- the call may have arrived; do not retry without checking"
            return self._failed(step, key, detail, method=plan.method, url=url), {}

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
            ),
            _derive(produces, response),
        )

    @staticmethod
    def _failed(
        step: SkillStep,
        key: str | None,
        detail: str,
        *,
        method: str | None = None,
        url: str | None = None,
    ) -> StepOutcome:
        return StepOutcome(
            index=step.index,
            medium=Medium.NETWORK,
            disposition=StepDisposition.FAILED,
            intent=step.intent,
            method=method,
            url=url,
            idempotency_key=key,
            detail=detail,
        )


class FinishRun:
    """Close the run and decide what it says."""

    def __init__(self, uow: UnitOfWork, clock: Clock) -> None:
        self._uow = uow
        self._clock = clock

    async def execute(self, ctx: RequestContext, *, run_id: RunId) -> Run:
        async with self._uow as uow:
            run = await uow.runs.get(ctx.tenant_id, run_id)
            run.finish(self._clock.now())
            await uow.runs.save(run)
            await uow.commit()
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
    ) -> None:
        self._uow = uow
        self._start = StartRun(uow, clock, ids)
        self._step = ExecuteStep(uow, http, vault)
        self._finish = FinishRun(uow, clock)

    async def execute(self, ctx: RequestContext, request: ExecutionRequest) -> Run:
        run = await self._start.execute(ctx, request)
        async with self._uow as uow:
            skill = await uow.skills.get(ctx.tenant_id, run.skill_id)
        for index in range(len(skill.version(run.skill_version).steps)):
            await self._step.execute(ctx, run_id=run.id, index=index)
        return await self._finish.execute(ctx, run_id=run.id)


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
    if version.stage.rung > PromotionStage.SHADOW.rung and not request.authorized_by:
        raise NotRunnable(
            f"a {version.stage} run performs real writes and must name the human who authorised it"
        )
    supplied = set(request.parameters)
    required = {p.name for p in version.parameters if p.kind is ParameterKind.INPUT}
    if absent := sorted(required - supplied):
        raise NotRunnable("no value supplied for " + ", ".join(absent))


def _derive(produces: Parameter | None, response: HttpResponse) -> dict[str, str]:
    """A value this step's response hands to a later one.

    A derived parameter that cannot be extracted is left unbound on purpose: the
    step that needs it then fails with the parameter's name, which points at the
    response that was supposed to carry it rather than at the step that broke.
    """
    if produces is None or produces.source_pointer is None:
        return {}
    value = extract(response, produces.source_pointer)
    return {} if value is None else {produces.name: value}


def _principal(value: str | None) -> PrincipalId | None:
    return PrincipalId(value) if value else None


__all__ = [
    "ExecuteSkill",
    "ExecuteStep",
    "ExecutionRequest",
    "FinishRun",
    "NotRunnable",
    "StartRun",
]
