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

from urllib.parse import urlsplit

from sro.application.context import RequestContext
from sro.application.knowledge.record_claim import Claim, RecordClaims, Recorded
from sro.domain.execution.run import Run, RunStatus, StepDisposition, StepOutcome
from sro.domain.knowledge.entry import EntryKind, EvidenceLevel


class LearnFromRun:
    def __init__(self, record: RecordClaims) -> None:
        self._record = record

    async def execute(self, ctx: RequestContext, *, run: Run, system: str) -> Recorded:
        if run.status is not RunStatus.SUCCEEDED:
            return Recorded()

        claims = tuple(_claim(step, run, system) for step in run.steps if _worth_recording(step))
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
