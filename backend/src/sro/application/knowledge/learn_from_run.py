from __future__ import annotations

from collections.abc import Iterator
from urllib.parse import urlsplit

from sro.application.context import RequestContext
from sro.application.knowledge.record_claim import Claim, RecordClaims, Recorded
from sro.domain.execution.run import Medium, Run, RunStatus, StepDisposition, StepOutcome
from sro.domain.knowledge.entry import EntryKind, EvidenceLevel
from sro.domain.skill.plan import UiPlan
from sro.domain.skill.skill import SkillVersion


class LearnFromRun:
    def __init__(self, record: RecordClaims) -> None:
        self._record = record

    async def execute(
        self,
        ctx: RequestContext,
        *,
        run: Run,
        system: str,
        version: SkillVersion | None = None,
    ) -> Recorded:
        if run.status is not RunStatus.SUCCEEDED:
            return Recorded()

        claims = tuple(_claim(step, run, system) for step in run.steps if _worth_recording(step))
        if version is not None:
            claims += tuple(_control_claims(run, version, system))
        return await self._record.execute(ctx, claims)


def _worth_recording(step: StepOutcome) -> bool:
    return (
        step.disposition is StepDisposition.PERFORMED
        and step.status_code is not None
        and step.method is not None
        and step.url is not None
        and not step.assertion_failures
    )


def _claim(step: StepOutcome, run: Run, system: str) -> Claim:
    path = urlsplit(step.url or "").path
    return Claim(
        system=system,
        kind=EntryKind.STATUS,
        key=f"{step.method} {path}",
        title=f"{step.method} {path} answers {step.status_code}",
        body={
            "method": step.method,
            "path": path,
            "status": step.status_code,
            "medium": step.medium.value,
            "escalated_from": step.escalated_from.value if step.escalated_from else None,
            "skill_id": run.skill_id.value,
            "skill_version": run.skill_version,
        },
        source=run.id.value,
        evidence=EvidenceLevel.REPRODUCED,
    )


def _control_claims(run: Run, version: SkillVersion, system: str) -> Iterator[Claim]:
    for index, (plan, matched) in _agreed(run, version).items():
        taught = plan.locators[0]
        drifted = matched != taught.strategy.value
        yield Claim(
            system=system,
            kind=EntryKind.SCREEN,
            key=f"control {taught.describe()}",
            title=(
                f"{taught.describe()} is found by {matched}"
                + (f", not by the {taught.strategy.value} it was taught with" if drifted else "")
            ),
            body={
                "control": taught.query.raw,
                "taught_as": taught.strategy.value,
                "found_by": matched,
                "drifted": drifted,
                "skill_id": run.skill_id.value,
                "skill_version": run.skill_version,
                "step": index,
            },
            source=run.id.value,
            evidence=EvidenceLevel.REPRODUCED,
        )


def _agreed(run: Run, version: SkillVersion) -> dict[int, tuple[UiPlan, str]]:
    seen: dict[int, tuple[UiPlan, set[str]]] = {}
    for outcome in run.steps:
        if outcome.medium not in (Medium.UI, Medium.VISION):
            continue
        if outcome.disposition is not StepDisposition.PERFORMED:
            continue
        if outcome.assertion_failures or outcome.unchecked:
            continue
        index = outcome.step_index
        plan = version.steps[index].ui_plan if index < len(version.steps) else None
        if plan is None or not plan.locators:
            continue
        seen.setdefault(index, (plan, set()))[1].add(outcome.matched_by or "nothing")
    return {
        index: (plan, matched.pop()) for index, (plan, matched) in seen.items() if len(matched) == 1
    }
