"""Listing recordings, against fakes.

Written by following docs/03-backend-walkthrough.md literally. If a step there
does not work as written, the document is wrong and fixing it is part of the
change.
"""

from __future__ import annotations

from sro.application.context import RequestContext
from sro.application.recording.list_recordings import ListRecordings
from sro.domain.shared.identifiers import PrincipalId, RecordingId, TenantId
from tests import factories as f
from tests.unit.fakes import FakeUnitOfWork

OTHER = TenantId("other-corp")
CTX = RequestContext(tenant_id=f.TENANT, principal_id=f.OPERATOR)
OTHER_CTX = RequestContext(tenant_id=OTHER, principal_id=PrincipalId("clerk@other.test"))


async def _seeded() -> FakeUnitOfWork:
    uow = FakeUnitOfWork()
    await uow.recordings.add(f.recording(id=RecordingId("ours-1")))
    await uow.recordings.add(f.recording(id=RecordingId("ours-2")))
    await uow.recordings.add(f.recording(id=RecordingId("theirs"), tenant_id=OTHER))
    return uow


async def test_only_the_caller_s_tenant_comes_back() -> None:
    uow = await _seeded()

    ours = await ListRecordings(uow).execute(CTX)
    theirs = await ListRecordings(uow).execute(OTHER_CTX)

    assert {r.id.value for r in ours} == {"ours-1", "ours-2"}
    assert {r.id.value for r in theirs} == {"theirs"}


async def test_filtering_by_objective_narrows_to_pairable_runs() -> None:
    uow = await _seeded()
    await uow.recordings.add(
        f.recording(
            id=RecordingId("other-objective"),
            objective_key=f.objective(objective_type="count_cycle"),
        )
    )

    found = await ListRecordings(uow).execute(CTX, objective_key=f.objective())

    assert "other-objective" not in {r.id.value for r in found}


async def test_paging_does_not_lose_the_tenant_filter() -> None:
    uow = await _seeded()

    page = await ListRecordings(uow).execute(CTX, limit=1, offset=0)

    assert len(page) == 1
    assert page[0].tenant_id == f.TENANT
