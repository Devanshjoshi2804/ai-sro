"""What the system knows, how sure it is, and what happens when that changes."""

from __future__ import annotations

from sro.application.context import RequestContext
from sro.application.knowledge.record_claim import Claim, RecordClaims
from sro.application.knowledge.retrieve import Question, Retrieve
from sro.domain.knowledge.entry import EntryKind, EvidenceLevel
from tests import factories as f
from tests.unit.fakes import FakeClock, FakeEmbedder, FakeIdFactory, FakeUnitOfWork

CTX = RequestContext(tenant_id=f.TENANT, principal_id=f.OPERATOR)

SCRAPED = Claim(
    system="blue_yonder",
    kind=EntryKind.ENDPOINT,
    key="/data/WM/wm/inventory/adjust",
    title="inventory/adjust (collection)",
    body={"status": "unknown"},
    source="index/api-endpoints.json",
    evidence=EvidenceLevel.ASSERTED,
)

PROVED = Claim(
    system="blue_yonder",
    kind=EntryKind.ENDPOINT,
    key="/data/WM/wm/inventory/adjust",
    title="inventory/adjust — answers 200 and queues an approval",
    body={"status": 200, "queues_approval": True},
    source="run_2b5120d8",
    evidence=EvidenceLevel.ROUND_TRIP,
)


# One id factory per store, not per call: two recorders sharing a store must
# not both mint "kb-1", which is a property of the fake rather than of the code.
_IDS: dict[int, FakeIdFactory] = {}


def _recorder(uow: FakeUnitOfWork, embedder: FakeEmbedder | None = None) -> RecordClaims:
    ids = _IDS.setdefault(id(uow), FakeIdFactory())
    return RecordClaims(uow, FakeClock(), ids, embedder or FakeEmbedder())


async def test_ingesting_the_same_catalogue_twice_changes_nothing() -> None:
    uow = FakeUnitOfWork()

    first = await _recorder(uow).execute(CTX, (SCRAPED,))
    second = await _recorder(uow).execute(CTX, (SCRAPED,))

    assert first.believed == 1
    assert second.unchanged == 1 and second.believed == 0
    assert len(uow.knowledge.rows) == 1, "a re-run must not grow the store"


async def test_a_verified_run_supersedes_a_scraped_claim_and_the_old_row_stays() -> None:
    uow = FakeUnitOfWork()
    await _recorder(uow).execute(CTX, (SCRAPED,))

    await _recorder(uow).execute(CTX, (PROVED,))

    entries = list(uow.knowledge.rows.values())
    assert len(entries) == 2, "history is how an incident gets explained afterwards"
    old = next(e for e in entries if e.source == "index/api-endpoints.json")
    new = next(e for e in entries if e.source == "run_2b5120d8")
    assert old.superseded_by == new.id
    assert new.current and new.evidence is EvidenceLevel.ROUND_TRIP


async def test_a_rescrape_does_not_undo_what_a_run_proved() -> None:
    """Evidence decides, not arrival order — or a nightly re-scrape would erase
    everything execution has learned."""
    uow = FakeUnitOfWork()
    await _recorder(uow).execute(CTX, (PROVED,))

    result = await _recorder(uow).execute(CTX, (SCRAPED,))

    assert result.recorded_not_believed == 1
    believed = await uow.knowledge.current(
        f.TENANT, system="blue_yonder", kind=EntryKind.ENDPOINT, key=SCRAPED.key
    )
    assert believed is not None and believed.source == "run_2b5120d8"


async def test_retrieval_never_returns_what_was_superseded() -> None:
    uow = FakeUnitOfWork()
    await _recorder(uow).execute(CTX, (SCRAPED,))
    await _recorder(uow).execute(CTX, (PROVED,))

    found = await Retrieve(uow, FakeEmbedder()).execute(CTX, Question(text="adjust"))

    assert [entry.source for entry in found] == ["run_2b5120d8"]


async def test_a_claim_too_weak_to_act_on_is_kept_and_excluded_from_automation() -> None:
    uow = FakeUnitOfWork()
    await _recorder(uow).execute(CTX, (SCRAPED,))

    shown = await Retrieve(uow, FakeEmbedder()).execute(CTX, Question(text="adjust"))
    actionable = await Retrieve(uow, FakeEmbedder()).execute(
        CTX, Question(text="adjust", automation_only=True)
    )

    assert len(shown) == 1, "worth showing a human"
    assert actionable == (), "not worth building a request from"


async def test_the_store_is_scoped_to_one_system_before_anything_is_measured() -> None:
    uow = FakeUnitOfWork()
    other = Claim(
        system="manhattan",
        kind=EntryKind.ENDPOINT,
        key="/api/inventory/adjust",
        title="inventory/adjust (collection)",
        body={},
        source="index/api-endpoints.json",
        evidence=EvidenceLevel.OBSERVED,
    )
    await _recorder(uow).execute(CTX, (SCRAPED, other))

    found = await Retrieve(uow, FakeEmbedder()).execute(
        CTX, Question(text="adjust", system="blue_yonder")
    )

    assert [entry.system for entry in found] == ["blue_yonder"]


async def test_terms_still_narrow_once_an_embedding_is_available() -> None:
    """A ternary here used to run backwards: the moment embedding succeeded --
    the common case -- term narrowing switched off, leaving nothing between a
    question and a confident nearest neighbour from an unrelated entity."""
    uow = FakeUnitOfWork()
    unrelated = Claim(
        system="blue_yonder",
        kind=EntryKind.ENDPOINT,
        key="/data/WM/wm/transportModes",
        title="transportModes (collection)",
        body={},
        source="index/api-endpoints.json",
        evidence=EvidenceLevel.ASSERTED,
    )
    await _recorder(uow).execute(CTX, (SCRAPED, unrelated))

    found = await Retrieve(uow, FakeEmbedder()).execute(CTX, Question(text="adjust"))

    assert [entry.key for entry in found] == [SCRAPED.key]


async def test_claims_are_embedded_in_one_call_rather_than_one_each() -> None:
    uow, embedder = FakeUnitOfWork(), FakeEmbedder()
    many = tuple(
        Claim(
            system="blue_yonder",
            kind=EntryKind.FIELD,
            key=f"field{index}",
            title=f"Field {index}",
            body={},
            source="index/field-dictionary.json",
            evidence=EvidenceLevel.ASSERTED,
        )
        for index in range(50)
    )

    await _recorder(uow, embedder).execute(CTX, many)

    assert len(embedder.asked) == 1
    assert len(embedder.asked[0]) == 50


async def test_without_an_embedder_everything_still_records_and_retrieves() -> None:
    uow, embedder = FakeUnitOfWork(), FakeEmbedder(available=False)

    await _recorder(uow, embedder).execute(CTX, (SCRAPED,))
    found = await Retrieve(uow, embedder).execute(CTX, Question(text="adjust"))

    assert len(found) == 1
    assert found[0].embedding == ()


class BrokenEmbedder:
    """A backend that is configured and does not work — a bad key, a dead
    endpoint, a quota. Measured live: unguarded, this took down every
    conversation and every ingest."""

    @property
    def available(self) -> bool:
        return True

    @property
    def dimensions(self) -> int:
        return 3

    async def embed(self, texts: tuple[str, ...]) -> tuple[tuple[float, ...], ...]:
        raise RuntimeError("401 UNAUTHENTICATED")


async def test_a_broken_embedder_costs_an_ordering_and_nothing_else() -> None:
    uow = FakeUnitOfWork()
    broken = BrokenEmbedder()

    recorded = await RecordClaims(uow, FakeClock(), FakeIdFactory(), broken).execute(
        CTX, (SCRAPED,)
    )
    found = await Retrieve(uow, broken).execute(CTX, Question(text="adjust"))

    assert recorded.believed == 1, "ingest is not a feature that depends on similarity"
    assert len(found) == 1, "structured filters still answer"
    assert found[0].embedding == ()
