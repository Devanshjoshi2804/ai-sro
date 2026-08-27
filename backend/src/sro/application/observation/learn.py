"""Learning a task nobody demonstrated.

The evidence for a task somebody keeps doing is already stored, verbatim, and
teaching a candidate reads it back rather than asking for the task again. So
the only thing standing between "you have done this three times" and a skill is
somebody pressing a button -- and the operator this system is for is doing
their job, not watching a panel.

So it presses it. What that produces is a skill at the bottom of the ladder:
`recorded`, never run, never promoted by this. Every gate that decides whether
something may act is downstream of here and untouched -- a rehearsal, ten clean
runs, a named person for anything that writes. What is automatic is the
noticing, which was always evidence rather than judgement.

Nothing here decides identity: which doings are the same task is the miner's
exact clustering, and what varies between two of them is the two-run diff.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from sro.application.context import RequestContext
from sro.application.observation.teach import NothingToTeach, TeachCandidate
from sro.application.ports.repositories import UnitOfWork
from sro.domain.observation.candidate import CandidateStatus
from sro.domain.shared.identifiers import CandidateId, SkillId

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class Learned:
    skills: list[SkillId] = field(default_factory=list)
    still_waiting: list[str] = field(default_factory=list)
    """Candidates that have been done often enough but whose evidence will not
    induce yet, and the reason for each. They stay `new`, which is what puts
    them in front of an operator as "teach me this once"."""


class LearnWhatRepeats:
    """Every candidate done often enough to be worth offering, taught."""

    def __init__(self, uow: UnitOfWork, teach: TeachCandidate) -> None:
        self._uow = uow
        self._teach = teach

    async def execute(self, ctx: RequestContext) -> Learned:
        async with self._uow as uow:
            candidates = await uow.candidates.list_for_tenant(
                ctx.tenant_id, status=CandidateStatus.NEW
            )

        learned = Learned()
        for candidate in candidates:
            if not candidate.worth_offering or not candidate.worth_learning_again:
                # Nothing new to try it on. The sweep comes round every quarter
                # of an hour; an attempt on evidence that already refused would
                # refuse again and leave two more sealed recordings behind it.
                continue
            await self._tried(ctx, candidate.id)
            try:
                taught = await self._teach.execute(ctx, candidate_id=candidate.id)
            except NothingToTeach as nothing:
                # Somebody dismissed or taught it between the listing and here.
                logger.info("%s was not taught: %s", candidate.title, nothing)
                continue
            except Exception:
                # One candidate whose evidence breaks induction must not stop
                # the others: this runs unattended, on a sweep, and a sweep
                # that dies on the first bad candidate silently stops learning
                # anything at all.
                logger.exception("%s could not be learned", candidate.title)
                continue

            if taught.skill_id is not None:
                logger.info("learned %s as %s", candidate.title, taught.skill_id)
                learned.skills.append(taught.skill_id)
            else:
                learned.still_waiting.append(f"{candidate.title}: {taught.because}")
        return learned

    async def _tried(self, ctx: RequestContext, candidate_id: CandidateId) -> None:
        """Written down before the attempt, not after it.

        An attempt that dies halfway -- a model timing out, a process killed --
        must still count, or a candidate that breaks induction becomes a sweep
        that does the same expensive thing forever.
        """
        async with self._uow as uow:
            candidate = await uow.candidates.get(ctx.tenant_id, candidate_id)
            candidate.learning_tried()
            await uow.candidates.save(candidate)
            await uow.commit()
