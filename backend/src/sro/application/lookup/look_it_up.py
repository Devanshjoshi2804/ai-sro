from __future__ import annotations

import logging

from sro.application.context import RequestContext
from sro.application.lookup.answer import existence_across, subject_of
from sro.application.lookup.plan_lookups import PlanLookups
from sro.application.lookup.run_lookups import Answers, Looked, RunLookups
from sro.domain.shared.errors import DomainError

logger = logging.getLogger(__name__)

K_RAN_OUT = ("timeout", "timed out", "deadline")


class LookItUp:
    """A question answered from the system it is about: plan where to read, then read.

    The one door `Converse` and the brain's `lookup` tool both go through."""

    def __init__(self, plan: PlanLookups, run: RunLookups) -> None:
        self._plan = plan
        self._run = run

    async def execute(self, ctx: RequestContext, question: str, *, within: float) -> Answers | None:
        try:
            planned = await self._plan.execute(ctx, question=question)
        except DomainError as refusal:
            logger.info("%s: the lookup could not be planned: %s", ctx.tenant_id.value, refusal)
            return None
        if not planned.plan.ready:
            return None
        return await self._run.execute(ctx, plan=planned.plan, within=within)


def ran_out(detail: str) -> bool:
    said = (detail or "").lower()
    return any(word in said for word in K_RAN_OUT)


def _said(one: Looked) -> str:
    return one.read.sentence(subject_of(one.lookup.target) or "record") if one.read else ""


def _verdicts(found: Answers) -> list[str]:
    """One verdict per asked value, over every lookup that could hold it, failed or not."""
    return [
        existence_across(
            value,
            [
                (subject_of(one.lookup.target) or "record", one.read if one.ok else None)
                for one in found.looked
                if one.lookup.find == value
            ],
        )
        for value in dict.fromkeys(one.lookup.find for one in found.looked if one.lookup.find)
    ]


def what_was_found(found: Answers) -> str:
    answered = [one for one in found.looked if one.ok]
    if not answered:
        why = next((one.detail for one in found.looked if one.detail), "")
        if any(ran_out(one.detail) for one in found.looked):
            return "I could not read that in time. Ask again and I will try once more."
        return f"I could not read that. {why}".strip()
    said = [_said(one) for one in answered if one.read is not None and not one.lookup.find]
    said += _verdicts(found)
    if said:
        return " ".join(said)
    where = ", ".join(sorted({one.lookup.target for one in answered}))
    return f"Read from {where}."
