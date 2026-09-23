from __future__ import annotations

from datetime import datetime

from sro.domain.execution.run import Medium, Run, RunStatus, StepDisposition
from sro.domain.skill.promotion import PromotionStage
from sro.domain.skill.skill import Skill
from sro.domain.skill.track_record import Verdict

__all__ = ["Verdict", "apply_verdict", "judge"]

_CLEAN_MEDIA = frozenset({Medium.NETWORK, Medium.TOOL})


def judge(run: Run) -> Verdict:
    if run.wrong_because is not None:
        return Verdict.FAILED
    if run.status is not RunStatus.SUCCEEDED:
        return Verdict.UNREACHABLE if _nothing_answered(run) else Verdict.FAILED

    dispositions = {step.disposition for step in run.steps}
    if dispositions <= {StepDisposition.WITHHELD, StepDisposition.SKIPPED}:
        return Verdict.WITHHELD

    for step in run.steps:
        if step.assertion_failures:
            return Verdict.FAILED
        if step.medium not in _CLEAN_MEDIA or step.escalated_from is not None:
            return Verdict.DEGRADED
    return Verdict.CLEAN


def apply_verdict(
    skill: Skill, run: Run, now: datetime, *, revising: Verdict | None = None
) -> Verdict:
    version = skill.version(run.skill_version)
    verdict = judge(run)
    version.record_run(verdict, now, revising=revising)
    version.earn(verdict, now)
    if version.track_record.should_demote and version.stage.rung > PromotionStage.SHADOW.rung:
        version.demote(
            PromotionStage.SHADOW,
            now,
            f"{version.track_record.consecutive_failures} runs failed in a row",
        )
    return verdict


def _nothing_answered(run: Run) -> bool:
    did_not_work = [step for step in run.steps if not step.ok]
    return bool(did_not_work) and all(step.unreachable for step in did_not_work)
