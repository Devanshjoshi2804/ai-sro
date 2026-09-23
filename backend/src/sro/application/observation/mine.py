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
        by_principal: dict[PrincipalId, list[Observed]] = {}
        for batch in batches:
            try:
                payload = once_each(await self._blobs.read(batch.uri))
            except (KeyError, OSError):
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
    steps = [step for step in signature.split(" → ") if step]
    if not steps:
        return f"Something on {host}"

    changing = [step for step in steps if step.split(" ", 1)[0] in _VERBS]
    method, path = (changing[-1] if changing else steps[-1]).split(" ", 1)
    entity = next((part for part in reversed(path.split("/")) if part and part != "*"), "something")
    return f"{_VERBS.get(method, 'Read')} {entity.replace('-', ' ')} on {host}"


class MineEverything:
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
                try:
                    await self._propose.execute(ctx)
                except Exception:
                    logger.exception(
                        "%s: nothing could be proposed about the candidates", tenant_id
                    )
        return mined
