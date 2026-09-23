from __future__ import annotations

import logging
from dataclasses import dataclass, field

from sro.application.context import RequestContext
from sro.application.induction.version import INDUCTION_VERSION
from sro.application.observation.teach import NothingToTeach, TeachCandidate
from sro.application.ports.repositories import UnitOfWork
from sro.domain.observation.candidate import CandidateStatus
from sro.domain.shared.identifiers import CandidateId, SkillId

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class Learned:
    skills: list[SkillId] = field(default_factory=list)
    still_waiting: list[str] = field(default_factory=list)


class LearnWhatRepeats:
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
            if not candidate.worth_offering or not candidate.worth_learning_again(
                INDUCTION_VERSION
            ):
                continue
            await self._tried(ctx, candidate.id)
            try:
                taught = await self._teach.execute(ctx, candidate_id=candidate.id)
            except NothingToTeach as nothing:
                logger.info("%s was not taught: %s", candidate.title, nothing)
                continue
            except Exception:
                logger.exception("%s could not be learned", candidate.title)
                continue

            if taught.skill_id is not None:
                logger.info("learned %s as %s", candidate.title, taught.skill_id)
                learned.skills.append(taught.skill_id)
            else:
                learned.still_waiting.append(f"{candidate.title}: {taught.because}")
        return learned

    async def _tried(self, ctx: RequestContext, candidate_id: CandidateId) -> None:
        async with self._uow as uow:
            candidate = await uow.candidates.get(ctx.tenant_id, candidate_id)
            candidate.learning_tried(INDUCTION_VERSION)
            await uow.candidates.save(candidate)
            await uow.commit()
