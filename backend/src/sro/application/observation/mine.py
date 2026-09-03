"""Noticing that somebody keeps doing the same thing.

No model decides what a candidate is. Clustering is a function of the evidence,
so the same week of observation produces the same candidates every time it is
mined, and a candidate can be argued with by reading its episodes. What a model
may do later is write the sentence on the front of it.

Re-runnable by construction: an episode already recorded is not counted twice,
so mining the same window again changes nothing and a better segmenter can be
run over evidence that is already stored.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from sro.application.context import RequestContext
from sro.application.observation.evidence import once_each
from sro.application.observation.propose import ProposeAboutCandidates
from sro.application.observation.segment import Observed, Segment, read, segment
from sro.application.ports.blob import BlobStore
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.system import IdFactory
from sro.domain.observation.batch import ObservationBatch
from sro.domain.observation.candidate import TaskCandidate
from sro.domain.shared.identifiers import PrincipalId, TenantId

_VERBS = {"POST": "Create", "PUT": "Update", "PATCH": "Update", "DELETE": "Remove"}

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class Mined:
    episodes: int
    candidates_seen: int
    candidates_new: int
    occurrences_new: int


class MineObservations:
    """One tenant's observation, over a window, turned into candidates."""

    def __init__(self, uow: UnitOfWork, blobs: BlobStore, ids: IdFactory) -> None:
        self._uow = uow
        self._blobs = blobs
        self._ids = ids

    async def execute(
        self, ctx: RequestContext, *, since: datetime, until: datetime | None = None
    ) -> Mined:
        async with self._uow as uow:
            batches = await uow.observations.between(ctx.tenant_id, since=since, until=until)
            known = {
                (candidate.principal_id.value, candidate.signature): candidate
                for candidate in await uow.candidates.list_for_tenant(ctx.tenant_id)
            }

            segments = 0
            fresh = 0
            occurrences = 0
            for principal, observed in (await self._observed(batches)).items():
                for found in segment(observed):
                    segments += 1
                    key = (principal.value, found.signature)
                    candidate = known.get(key)
                    if candidate is None:
                        candidate = self._candidate(ctx.tenant_id, principal, found)
                        known[key] = candidate
                        await uow.candidates.add(candidate)
                        fresh += 1
                    if candidate.observed(found.episode):
                        occurrences += 1
                        await uow.candidates.save(candidate)

            await uow.commit()

        return Mined(
            episodes=segments,
            candidates_seen=len(known),
            candidates_new=fresh,
            occurrences_new=occurrences,
        )

    async def _observed(
        self, batches: Sequence[ObservationBatch]
    ) -> dict[PrincipalId, list[Observed]]:
        """Every batch's events, read back and grouped by whose browser they
        came from. A task is one person's; two operators doing the same work is
        two candidates, and the sentence an extension shows says "you"."""
        by_principal: dict[PrincipalId, list[Observed]] = {}
        for batch in batches:
            try:
                payload = once_each(await self._blobs.read(batch.uri))
            except (KeyError, OSError):
                # Evidence that has aged out of its retention window. The
                # candidates it fed are already counted; a missing blob is not a
                # reason to fail a mining run.
                continue
            by_principal.setdefault(batch.principal_id, []).extend(read(payload, batch.id))
        return by_principal

    def _candidate(
        self, tenant_id: TenantId, principal: PrincipalId, found: Segment
    ) -> TaskCandidate:
        return TaskCandidate(
            id=self._ids.new_candidate_id(),
            tenant_id=tenant_id,
            principal_id=principal,
            signature=found.signature,
            host=found.episode.host,
            starts_on=found.episode.starts_on,
            title=title_for(found.signature, found.episode.host),
        )


def title_for(signature: str, host: str) -> str:
    """A sentence somebody can recognise, derived rather than written.

    Deliberately not a model's: naming is the one thing here a model would be
    good at, and it is also the one thing that would make a candidate's identity
    depend on what was answered that afternoon. A person renames it when they
    teach it.
    """
    steps = [step for step in signature.split(" → ") if step]
    if not steps:
        return f"Something on {host}"

    changing = [step for step in steps if step.split(" ", 1)[0] in _VERBS]
    method, path = (changing[-1] if changing else steps[-1]).split(" ", 1)
    entity = next((part for part in reversed(path.split("/")) if part and part != "*"), "something")
    return f"{_VERBS.get(method, 'Read')} {entity.replace('-', ' ')} on {host}"


class MineEverything:
    """Every tenant that has been observed lately.

    Deliberately tenant-blind, and the only caller is the scheduled sweep: there
    is no request behind this and nobody to take a tenant from. It asks which
    tenants have evidence and then mines each one inside its own context.
    """

    def __init__(
        self,
        uow: UnitOfWork,
        mine: MineObservations,
        propose: ProposeAboutCandidates | None = None,
    ) -> None:
        self._uow = uow
        self._mine = mine
        self._propose = propose

    async def execute(self, *, since: datetime, until: datetime | None = None) -> dict[str, Mined]:
        async with self._uow as uow:
            tenants = await uow.observations.tenants_since(since)

        mined: dict[str, Mined] = {}
        for tenant_id in tenants:
            ctx = RequestContext(tenant_id=tenant_id, principal_id=PrincipalId("miner"))
            mined[tenant_id.value] = await self._mine.execute(ctx, since=since, until=until)
            if self._propose is not None:
                # After the counting, never instead of it. What the miner
                # decided stands whatever a model says next, and a model that
                # is unreachable costs this sweep its sentences and nothing
                # else -- so its failure is logged here rather than raised
                # into a sweep that has already done its real work.
                try:
                    await self._propose.execute(ctx)
                except Exception:
                    logger.exception(
                        "%s: nothing could be proposed about the candidates", tenant_id
                    )
        return mined
