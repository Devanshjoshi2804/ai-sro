from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass, replace
from datetime import datetime

from sro.application.context import RequestContext
from sro.application.knowledge.open_questions import Ambiguity, AskAbout
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.system import Clock
from sro.domain.execution.run import Run, RunStatus
from sro.domain.knowledge.entry import SUPPORTS_AUTOMATION, EntryKind, KnowledgeEntry
from sro.domain.shared.errors import Conflict
from sro.domain.shared.identifiers import PrincipalId, TenantId
from sro.domain.skill.locator import ControlLocator
from sro.domain.skill.plan import UiPlan
from sro.domain.skill.promotion import PromotionStage
from sro.domain.skill.skill import Skill, SkillStep, SkillVersion
from sro.domain.skill.track_record import REQUIRED_CLEAN_RUNS, TrackRecord

REPAIR = PrincipalId("drift-repair")

SETTLED = 3

WINDOW = REQUIRED_CLEAN_RUNS


@dataclass(frozen=True, slots=True)
class Drift:
    step: SkillStep
    plan: UiPlan
    taught: ControlLocator
    matched: str
    agreed: int = SETTLED

    against: int = 0

    answer: str | None = None

    @property
    def worked(self) -> ControlLocator | None:
        found = [
            locator for locator in self.plan.locators if locator.strategy.value == self.matched
        ]
        return found[0] if len(found) == 1 else None

    @property
    def adopted(self) -> ControlLocator | None:
        worked = self.worked
        if worked is None:
            return None
        if not self.against:
            return worked
        return worked if self.answer == worked.describe() else None

    @property
    def contest(self) -> str:
        return f"control {self.taught.describe()} is reached two ways"


class RepairDrift:
    def __init__(self, uow: UnitOfWork, clock: Clock, ask: AskAbout) -> None:
        self._uow = uow
        self._clock = clock
        self._ask = ask

    async def execute(self, ctx: RequestContext, *, run: Run) -> int | None:
        if run.status is not RunStatus.SUCCEEDED:
            return None

        number: int | None = None
        async with self._uow as uow:
            skill = await uow.skills.get(ctx.tenant_id, run.skill_id)
            version = skill.version(run.skill_version)
            if version is not skill.latest:
                return None

            drifts = tuple(
                [
                    drift
                    async for drift in self._drifted(
                        ctx, uow, version, system=skill.objective_key.target_system
                    )
                ]
            )
            repaired = {
                drift.step.index: _trying_first(drift, adopted)
                for drift in drifts
                if (adopted := drift.adopted) is not None
            }
            if repaired:
                number = _adopt(skill, version, run, repaired, drifts, at=self._clock.now())
                await uow.skills.save(skill)
                try:
                    await uow.commit()
                except Conflict:
                    return None

        for drift in drifts:
            if drift.adopted is None and drift.answer is None:
                await self._ask.raise_question(
                    ctx,
                    _question(
                        drift,
                        run=run,
                        system=skill.objective_key.target_system,
                        skill_name=skill.name,
                        version=version,
                    ),
                )
        return number

    async def _drifted(
        self, ctx: RequestContext, uow: UnitOfWork, version: SkillVersion, *, system: str
    ) -> AsyncIterator[Drift]:
        for step in version.steps:
            plan = step.ui_plan
            if plan is None or not plan.locators:
                continue
            taught = plan.locators[0]
            reading = _reading(
                await uow.knowledge.history(
                    ctx.tenant_id,
                    system=system,
                    kind=EntryKind.SCREEN,
                    key=f"control {taught.describe()}",
                    limit=WINDOW,
                )
            )
            if reading is None:
                continue
            matched, agreed, against = reading
            drift = Drift(
                step=step,
                plan=plan,
                taught=taught,
                matched=matched,
                agreed=agreed,
                against=against,
            )
            yield (
                drift
                if not against
                else replace(
                    drift,
                    answer=await _answer(uow, ctx.tenant_id, system=system, key=drift.contest),
                )
            )


async def _answer(uow: UnitOfWork, tenant_id: TenantId, *, system: str, key: str) -> str | None:
    for entry in await uow.knowledge.history(
        tenant_id, system=system, kind=EntryKind.QUESTION, key=key, limit=SETTLED
    ):
        answer = entry.body.get("answer")
        if isinstance(answer, str):
            return answer
    return None


def _reading(entries: tuple[KnowledgeEntry, ...]) -> tuple[str, int, int] | None:
    matched = _settled(entries[:SETTLED])
    if matched is not None:
        return matched, SETTLED, 0
    return _contested(entries)


def _contested(entries: tuple[KnowledgeEntry, ...]) -> tuple[str, int, int] | None:
    verified = [entry for entry in entries if entry.evidence.rank >= SUPPORTS_AUTOMATION.rank]
    drifted: dict[str, set[str]] = {}
    for entry in verified:
        if entry.body.get("drifted") is True:
            drifted.setdefault(str(entry.body.get("found_by")), set()).add(entry.source)
    if not drifted:
        return None
    matched, agreed = max(drifted.items(), key=lambda claim: (len(claim[1]), claim[0]))
    against = {entry.source for entry in verified} - agreed
    if len(agreed) < SETTLED or len(against) < SETTLED:
        return None
    return matched, len(agreed), len(against)


def _settled(entries: tuple[KnowledgeEntry, ...]) -> str | None:
    if len(entries) < SETTLED:
        return None
    if len({entry.source for entry in entries}) < SETTLED:
        return None
    if any(entry.evidence.rank < SUPPORTS_AUTOMATION.rank for entry in entries):
        return None
    if not all(entry.body.get("drifted") is True for entry in entries):
        return None
    found = {str(entry.body.get("found_by")) for entry in entries}
    return found.pop() if len(found) == 1 else None


def _adopt(
    skill: Skill,
    version: SkillVersion,
    run: Run,
    repaired: dict[int, SkillStep],
    drifts: tuple[Drift, ...],
    *,
    at: datetime,
) -> int:
    fresh = replace(
        version,
        version=skill.next_version_number(),
        steps=tuple(repaired.get(step.index, step) for step in version.steps),
        stage=PromotionStage.RECORDED,
        track_record=TrackRecord(),
        promoted_at=None,
        promoted_by=None,
        promoted_from="",
        demotion_reason=None,
        provenance=replace(
            version.provenance,
            repaired_from=run.id.value,
            induced_at=at,
            induced_by=REPAIR,
            note=_note(run, version, drifts),
        ),
    )
    skill.add_version(fresh)
    inherited = (
        version.stage
        if version.stage.rung < PromotionStage.AUTONOMOUS.rung
        else PromotionStage.ASSISTED
    )
    while fresh.stage.rung < inherited.rung:
        fresh.promote(
            fresh.stage.next_stage(),
            at,
            REPAIR,
            acknowledging_fixed_values=True,
            from_where="repair",
        )
    return fresh.version


def _trying_first(drift: Drift, worked: ControlLocator) -> SkillStep:
    others = tuple(loc for loc in drift.plan.locators if loc is not worked)
    return replace(drift.step, ui_plan=replace(drift.plan, locators=(worked, *others)))


def _question(
    drift: Drift, *, run: Run, system: str, skill_name: str, version: SkillVersion
) -> Ambiguity:
    if drift.against:
        return _contest(drift, run=run, system=system, skill_name=skill_name, version=version)
    return Ambiguity(
        system=system,
        key=f"control {drift.taught.describe()} was not found where it was taught",
        question=(
            f"{drift.taught.describe()} is being reached by {drift.matched} rather than by the "
            f"{drift.taught.strategy.value} this skill was taught with, and this version does "
            "not say which control that is. Where is it now?"
        ),
        options=("demonstrate the step again", "leave the skill as it is and keep escalating"),
        because=(
            f"{SETTLED} verified runs of {skill_name} v{version.version} step "
            f"{drift.step.index} agree, most recently run {run.id.value}",
        ),
    )


def _contest(
    drift: Drift, *, run: Run, system: str, skill_name: str, version: SkillVersion
) -> Ambiguity:
    worked = drift.worked
    total = drift.agreed + drift.against
    return Ambiguity(
        system=system,
        key=drift.contest,
        question=(
            f"{drift.taught.describe()} is reached by {drift.matched} on some runs and by the "
            f"{drift.taught.strategy.value} it was taught with on others. Neither is rare enough "
            "to be a slow page, so nothing here will ever settle on its own. Which should this "
            "skill lead with?"
        ),
        options=(
            worked.describe() if worked is not None else "demonstrate the step again",
            "leave it as it is and keep escalating",
        ),
        because=(
            f"{drift.agreed} of the last {total} verified runs reached it by {drift.matched}; "
            f"{drift.against} found it by the {drift.taught.strategy.value} it was taught with",
            f"{skill_name} v{version.version} step {drift.step.index} falls through its plan on "
            f"{drift.agreed} runs in {total} and a run that does is never clean, so the "
            f"{REQUIRED_CLEAN_RUNS} clean runs unattended running needs never start -- and no "
            "amount of running fixes that, because the evidence contradicts itself every time",
            f"most recently run {run.id.value}",
        ),
    )


def _note(run: Run, version: SkillVersion, drifts: tuple[Drift, ...]) -> str:
    adopted = [d for d in drifts if d.adopted is not None]
    changes = ", ".join(
        f"step {d.step.index} is found by {d.matched} rather than the "
        f"{d.taught.strategy.value} it was taught with"
        + (f" ({d.agreed} runs to {d.against}, answered by hand)" if d.against else "")
        for d in adopted
    )
    proof = (
        f"after {SETTLED} verified runs agreed, the last of them {run.id.value}"
        if all(not d.against for d in adopted)
        else f"after somebody settled what the runs could not, most recently {run.id.value}"
    )
    return (
        f"repaired from v{version.version} {proof}: {changes}. "
        "Nobody demonstrated this again; every other step is the one those runs performed."
    )
