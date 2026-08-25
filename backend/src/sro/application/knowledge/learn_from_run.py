"""What a run proved, written back as knowledge.

This is the half of the loop that makes the store more than a scrape. The
catalogue says an endpoint exists; a verified run says what it answers, for this
tenant, at this facility, today. Evidence outranks arrival order, so a later
re-scrape cannot undo it -- see ``domain/knowledge/supersede.py``.

Only from a run that verified. A step that failed its assertions proves nothing
about the system except that the skill and the system disagree, and recording
that as knowledge would teach the store the skill's bugs.
"""

from __future__ import annotations

from collections.abc import Iterator
from urllib.parse import urlsplit

from sro.application.context import RequestContext
from sro.application.knowledge.record_claim import Claim, RecordClaims, Recorded
from sro.domain.execution.run import Medium, Run, RunStatus, StepDisposition, StepOutcome
from sro.domain.knowledge.entry import EntryKind, EvidenceLevel
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
    """Sent, answered, and checked. Anything less is not evidence about the WMS.

    A withheld shadow write in particular says nothing: the request was built
    and never left, so its status is unknown rather than good.
    """
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
        # Keyed by what was done, not by which skill did it: two skills calling
        # the same endpoint are two observations of one fact.
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
        # Reproduced rather than round-trip: the run made the call and checked
        # the answer, which is not the same as creating, reading back, changing
        # and deleting. Claiming the higher level here would be the exact
        # inflation the knowledge base's own audit was written about.
        evidence=EvidenceLevel.REPRODUCED,
    )


def _control_claims(run: Run, version: SkillVersion, system: str) -> Iterator[Claim]:
    """Which locator actually found each control, run after run.

    A skill carries several ways to find a control, strongest first, and the
    driver takes the first that resolves. Which one won was recorded on the run
    and read by nobody -- so a step that has quietly fallen through to its
    last-resort CSS path, or that no locator finds at all any more and only a
    model looking at the screen can reach, looks exactly like a step that works.
    It does work. It is also one screen change from not working, and the system
    knew and said nothing.

    Kept as knowledge rather than written back onto the skill: a locator is
    evidence from a demonstration, and the healer's rule is that evidence is
    changed by demonstrating again. This is the same instinct as Healenium's
    store of healed locators (docs/16), minus the part where the tool rewrites
    what the test said.
    """
    for outcome in run.steps:
        if outcome.medium not in (Medium.UI, Medium.VISION):
            continue
        if outcome.disposition is not StepDisposition.PERFORMED or outcome.assertion_failures:
            continue
        plan = version.steps[outcome.index].ui_plan if outcome.index < len(version.steps) else None
        if plan is None or not plan.locators:
            continue

        taught = plan.locators[0]
        found = outcome.matched_by or "nothing"
        drifted = found != taught.strategy.value
        yield Claim(
            system=system,
            kind=EntryKind.SCREEN,
            # The control, not the skill: two skills clicking one button are two
            # observations of where that button is, the same way two skills
            # calling one endpoint are two observations of what it answers.
            key=f"control {taught.describe()}",
            title=(
                f"{taught.describe()} is found by {found}"
                + (f", not by the {taught.strategy.value} it was taught with" if drifted else "")
            ),
            body={
                "control": taught.query.raw,
                "taught_as": taught.strategy.value,
                "found_by": found,
                "drifted": drifted,
                "skill_id": run.skill_id.value,
                "skill_version": run.skill_version,
                "step": outcome.index,
            },
            source=run.id.value,
            evidence=EvidenceLevel.REPRODUCED,
        )
