"""“Show me supplier TESTSUPPLIERSRO” is not a request for every supplier.

Retrieval found the taught read, replayed it exactly as demonstrated, and
dropped the only word in the sentence that said which supplier — 239 rows for a
question about one. Nothing was wrong with the skill; what was missing was
anything that used what the system already knows.
"""

from __future__ import annotations

import pytest

from sro.application.context import RequestContext
from sro.application.execution.answer import Answer
from sro.application.execution.derived_read import Asked
from sro.application.induction.sites import as_a_filter, filter_terms_of
from sro.application.intent.narrow import NarrowARead, NeedToAsk
from sro.application.ports.intent import Extraction
from sro.domain.knowledge.entry import EntryKind, EvidenceLevel, KnowledgeEntry, KnowledgeId
from sro.domain.shared.identifiers import PrincipalId, SkillId, TenantId
from sro.domain.skill.template import Template
from tests import factories as f
from tests.unit.fakes import FakeUnitOfWork

CTX = RequestContext(tenant_id=TenantId("acme"), principal_id=PrincipalId("clerk"))
LISTING = "https://wms.test/data/WM/wm/suppliers?query=%5B%5D&offset=0&limit=50&siteId=SG"
FILTERED = (
    "https://wms.test/data/WM/wm/addresses?query=%5B%7B%22column%22%3A%22addressName%22%2C"
    "%22operator%22%3A%22EQ%22%2C%22value%22%3A%22ACME%22%7D%5D&siteId=SG"
)


class _Ask:
    """Stands in for what an operator has already settled."""

    def __init__(self, answer: str | None) -> None:
        self.answer = answer

    async def settled(self, ctx: RequestContext, *, key: str) -> str | None:
        return self.answer

    async def raise_question(self, ctx: RequestContext, ambiguity: object) -> None:
        return None


class _Says:
    """Stands in for the system, holding the values its records actually carry."""

    def __init__(self, values: tuple[str, ...]) -> None:
        self.values = values

    async def execute(
        self, ctx: RequestContext, *, skill_id: object, url: str, lead: str = ""
    ) -> Asked:
        return Asked(
            answer=Answer(rows=len(self.values), distinct={"smallPackageFlag": self.values}),
            url=url,
        )


class _Parser:
    """Stands in for the model. It picks between fields that exist."""

    available = True

    def __init__(self, answer: dict[str, str] | None) -> None:
        self.answer = answer
        self.offered: tuple[str, ...] = ()

    async def extract(
        self, utterance: str, *, parameters: tuple[str, ...], context: str = ""
    ) -> Extraction:
        self.offered = parameters
        return Extraction(items=(self.answer,) if self.answer else ())


def _field(name: str, label: str) -> KnowledgeEntry:
    return KnowledgeEntry(
        id=KnowledgeId(f"kn-{name}"),
        tenant_id=TenantId("acme"),
        system="blue_yonder",
        kind=EntryKind.FIELD,
        key=name,
        title=label,
        body={},
        source="catalogue",
        evidence=EvidenceLevel.ASSERTED,
        observed_at=f.T0,
    )


@pytest.fixture
async def uow() -> FakeUnitOfWork:
    unit = FakeUnitOfWork()
    await unit.knowledge.add(_field("supplierNumber", "Supplier (supplierNumber)"))
    await unit.knowledge.add(_field("addressName", "Supplier Address (addressName)"))
    # A taught call on the same system that did carry a filter. This is where
    # the dialect comes from: the supplier screen sends an empty one, so
    # without this there is nothing to say what a term looks like here.
    await unit.skills.add(
        f.skill(
            objective_key=f.objective(target_system="blue_yonder", entity_type="addresse"),
            versions=0,
        )
    )
    taught = (await unit.skills.list_for_tenant(TenantId("acme")))[0]
    taught.add_version(
        f.skill_version(
            steps=(
                f.step(index=0, network_plan=f.network_plan(method="GET", url=Template(FILTERED))),
            )
        )
    )
    await unit.skills.save(taught)
    return unit


def _version() -> object:
    return f.skill_version(
        steps=(
            f.step(
                index=0,
                network_plan=f.network_plan(method="GET", url=Template(LISTING)),
            ),
        )
    )


class TestNarrowing:
    async def test_the_field_dictionary_says_what_the_value_is_called(
        self, uow: FakeUnitOfWork
    ) -> None:
        parser = _Parser({"supplierNumber": "TESTSUPPLIERSRO"})

        narrowed = await NarrowARead(uow, parser).for_utterance(
            CTX,
            utterance="show me supplier TESTSUPPLIERSRO in detail",
            version=_version(),
            system="blue_yonder",
            entity="supplier",
        )

        assert narrowed is not None
        assert narrowed.field == "supplierNumber"
        assert "TESTSUPPLIERSRO" in narrowed.url
        # The model chose between fields that exist rather than naming one.
        assert set(parser.offered) == {"supplierNumber", "addressName"}

    async def test_a_sentence_that_names_no_value_changes_nothing(
        self, uow: FakeUnitOfWork
    ) -> None:
        """Then the taught skill runs exactly as it always did."""
        narrowed = await NarrowARead(uow, _Parser(None)).for_utterance(
            CTX,
            utterance="how many suppliers are there",
            version=_version(),
            system="blue_yonder",
            entity="supplier",
        )

        assert narrowed is None

    async def test_a_field_the_model_invented_is_refused(self, uow: FakeUnitOfWork) -> None:
        """It can name anything; only what the dictionary has survives."""
        narrowed = await NarrowARead(uow, _Parser({"madeUpField": "X"})).for_utterance(
            CTX,
            utterance="show me supplier X",
            version=_version(),
            system="blue_yonder",
            entity="supplier",
        )

        assert narrowed is None


class TestTheDialect:
    def test_an_empty_filter_is_a_slot_the_endpoint_offers(self) -> None:
        """`query=[]` says this call takes a filter and was sent none."""
        composed = as_a_filter(
            LISTING,
            column="supplierNumber",
            placeholder="TESTSUPPLIERSRO",
            shape={"operator": "EQ"},
        )

        assert composed is not None
        assert "supplierNumber" in composed
        assert "TESTSUPPLIERSRO" in composed

    def test_without_a_proven_shape_nothing_is_composed(self) -> None:
        """The term's shape comes from a call this system answered, never from
        an assumption about how filters look."""
        assert as_a_filter(LISTING, column="supplierNumber", placeholder="X") is None

    def test_the_shape_is_read_off_a_call_that_carried_one(self) -> None:
        terms = filter_terms_of(FILTERED)

        assert terms and terms[0]["operator"] == "EQ"


class TestPlacingAWordNobodyTaught:
    """ "Which suppliers are used for parcel" — parcel is a value, and nothing
    names a field after it. Listing every supplier instead answers a wider
    question and calls it an answer."""

    async def test_a_word_the_catalogue_documents_once_is_used(self, uow: FakeUnitOfWork) -> None:
        await uow.knowledge.add(
            _field("smallPackageFlag", "Parcel (smallPackageFlag)"),
        )
        narrow = NarrowARead(uow, _Parser(None), _Ask(None), _Says(("Y", "parcel")))

        placed = await narrow.for_utterance(
            CTX,
            utterance="which suppliers are used for parcel",
            version=_version(),
            system="blue_yonder",
            entity="supplier",
            unexplained=("parcel",),
        )

        assert placed is not None and not isinstance(placed, NeedToAsk)
        assert placed.field == "smallPackageFlag"

    async def test_a_word_nothing_has_heard_of_is_not_asked_about(
        self, uow: FakeUnitOfWork
    ) -> None:
        """ "Used" is not a value anybody can place, and a question about it is
        one nobody can answer either."""
        narrow = NarrowARead(uow, _Parser(None), _Ask(None), _Says(()))

        assert (
            await narrow.for_utterance(
                CTX,
                utterance="which suppliers are used for parcel",
                version=_version(),
                system="blue_yonder",
                entity="supplier",
                unexplained=("used",),
            )
            is None
        )

    async def test_several_fields_mentioning_it_becomes_a_question(
        self, uow: FakeUnitOfWork
    ) -> None:
        """Choosing between two plausible fields is the guess this avoids."""
        await uow.knowledge.add(_field("smallPackageFlag", "Parcel (smallPackageFlag)"))
        await uow.knowledge.add(_field("serviceName", "Parcel Manifest Service (serviceName)"))
        narrow = NarrowARead(uow, _Parser(None), _Ask(None), _Says(()))

        asking = await narrow.for_utterance(
            CTX,
            utterance="which suppliers are used for parcel",
            version=_version(),
            system="blue_yonder",
            entity="supplier",
            unexplained=("parcel",),
        )

        assert isinstance(asking, NeedToAsk)
        assert set(asking.options) == {"smallPackageFlag", "serviceName"}

    async def test_an_answered_word_is_asked_of_the_data_next_time(
        self, uow: FakeUnitOfWork
    ) -> None:
        """Somebody said parcel means smallPackageFlag. The records spell it
        `Y`, and asking for `smallPackageFlag = parcel` would find none and
        report that as an answer."""
        narrow = NarrowARead(uow, _Parser(None), _Ask("smallPackageFlag"), _Says(("Y", "N")))

        asking = await narrow.for_utterance(
            CTX,
            utterance="which suppliers are used for parcel",
            version=_version(),
            system="blue_yonder",
            entity="supplier",
            skill_id=SkillId("skl-1"),
            unexplained=("parcel",),
        )

        assert isinstance(asking, NeedToAsk), asking
        assert asking.options == ("smallPackageFlag=N", "smallPackageFlag=Y"), asking.question
