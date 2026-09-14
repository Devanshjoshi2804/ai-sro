"""Planning where to look, and the four things it will not do.

The read half. A job is mined from what somebody was seen doing; a lookup is
planned from what the systems are known to hold, and `umbrella`'s instructions
mean the miner will never produce one -- "looking something up is a STEP of a
job and not a job" is right, and it is why this is planned rather than mined.

What is worth holding here is not that a plan comes back. It is the refusals:
an endpoint nobody has seen, a lookup that cites nothing, a word this
deployment has already written down as ambiguous, and a question asking for a
write. Each one is a confident wrong answer that would otherwise reach a
warehouse.
"""

from __future__ import annotations

import pytest

from sro.application.context import RequestContext
from sro.application.knowledge.retrieve import Retrieve
from sro.application.lookup.plan_lookups import PlanLookups
from sro.domain.knowledge.entry import EntryKind, EvidenceLevel, KnowledgeEntry, KnowledgeId
from sro.domain.shared.prices import Answer
from tests import factories as f
from tests.unit.fakes import FakeAsker, FakeClock, FakeUnitOfWork

CTX = RequestContext(tenant_id=f.TENANT, principal_id=f.OPERATOR)
WMS = "blue_yonder"

SUPPLIERS = "/data/WM/wm/suppliers"
SUPPLIER_SCREEN = "/portal/page/Suppliers"


def _entry(
    key: str,
    kind: EntryKind,
    *,
    title: str = "",
    body: dict[str, object] | None = None,
    superseded_by: str | None = None,
) -> KnowledgeEntry:
    return KnowledgeEntry(
        id=KnowledgeId(f"kn_{abs(hash(key + kind.value)) % 10**8}"),
        tenant_id=f.TENANT,
        system=WMS,
        kind=kind,
        key=key,
        title=title or key,
        body=body or {},
        source="a test",
        evidence=EvidenceLevel.REPRODUCED,
        observed_at=f.at(0),
        superseded_by=KnowledgeId(superseded_by) if superseded_by else None,
    )


KNOWN = [
    _entry(SUPPLIERS, EntryKind.ENDPOINT, title="suppliers (collection)", body={"params": ["siteId"]}),
    _entry(SUPPLIER_SCREEN, EntryKind.SCREEN, title="Suppliers", body={"seen_on_routes": ["Suppliers"]}),
    _entry("supplierName", EntryKind.FIELD, title="Supplier name"),
]


class _Knows(Retrieve):
    """The knowledge this deployment holds, without a database or an embedder.

    `Retrieve`'s own rule -- structural filter, then similarity -- is proved in
    its own tests. What is under test here is what the planner does with what
    it is handed, so this hands it exactly that.
    """

    def __init__(self, entries: list[KnowledgeEntry]) -> None:
        self._entries = entries
        self.asked: list[str] = []

    async def execute(self, ctx: RequestContext, question: object) -> tuple[KnowledgeEntry, ...]:  # type: ignore[override]
        self.asked.append(getattr(question, "text", ""))
        return tuple(self._entries)


def _planner(
    answer: Answer, entries: list[KnowledgeEntry] | None = None, *, cap_usd: float = 5.0
) -> tuple[PlanLookups, FakeAsker]:
    asker = FakeAsker(answer)
    return (
        PlanLookups(
            FakeUnitOfWork(),
            _Knows(KNOWN if entries is None else entries),
            asker,
            model="m",
            clock=FakeClock(),
            cap_usd=cap_usd,
        ),
        asker,
    )


def _said(**over: object) -> Answer:
    lookup: dict[str, object] = {
        "why": "the suppliers collection answers this",
        "system": WMS,
        "how": "call",
        "target": SUPPLIERS,
        "params": {"siteId": "SG"},
        "cites": [SUPPLIERS],
    }
    lookup.update(over)
    return Answer(data={"why": "one system holds suppliers", "lookups": [lookup]})


async def test_a_question_becomes_a_call_to_an_endpoint_this_deployment_has_seen() -> None:
    planner, asker = _planner(_said())

    planned = await planner.execute(CTX, question="which suppliers are set up at SG")

    assert planned.refused is None
    assert planned.plan.ready
    (lookup,) = planned.plan.lookups
    assert lookup.how == "call" and lookup.target == SUPPLIERS
    assert lookup.params == {"siteId": "SG"}
    assert lookup.cites == (SUPPLIERS,)
    # The key is what a citation has to name, so the key is what it is shown.
    assert SUPPLIERS in str(asker.asked[0]["evidence"])


async def test_an_endpoint_nobody_here_has_seen_is_refused_whole() -> None:
    """The failure this exists to stop: a path that looks like the others.

    Refused whole rather than filtered. A plan that quietly drops one of its
    systems answers a narrower question than the one asked and says nothing
    about having done so.
    """
    planner, _ = _planner(_said(target="/data/WM/wm/vendors", cites=[SUPPLIERS]))

    planned = await planner.execute(CTX, question="which suppliers are set up at SG")

    assert planned.plan.lookups == ()
    assert planned.refused is not None
    assert "/data/WM/wm/vendors" in planned.refused
    assert "nothing here has seen" in planned.refused


async def test_a_lookup_that_cites_nothing_it_was_shown_is_refused() -> None:
    # The same reading `validate` takes of a workflow step: free-generated
    # steps hallucinated at 21%, and selection from real evidence took that
    # below 7.5%. A citation naming something absent is not a citation.
    planner, _ = _planner(_said(cites=["/data/WM/wm/somewhere-else"]))

    planned = await planner.execute(CTX, question="which suppliers are set up at SG")

    assert planned.plan.lookups == ()
    assert planned.refused is not None and "cites nothing" in planned.refused


async def test_a_word_this_deployment_has_already_called_ambiguous_stops_the_plan() -> None:
    """Two endpoints answered "how many transport modes", the system picked the
    first it saw, and an operator found out by counting rows on a screen.

    Asked once. The plan stops, the question comes back with its options and
    the evidence either way, and the operator's answer supersedes it -- so the
    next reading of the same word reads the answer instead of asking again.
    """
    ambiguous = _entry(
        "blue_yonder/supplier/collection",
        EntryKind.QUESTION,
        title='When somebody says "supplier", do they mean the ones at SG, or all of them?',
        body={
            "question": 'When somebody says "supplier", do they mean the ones at SG, or all?',
            "options": ["WMSupplier", "A000144886"],
            "because": ["WMSupplier returned 5 when this was demonstrated"],
        },
    )
    planner, asker = _planner(_said(), [*KNOWN, ambiguous])

    planned = await planner.execute(CTX, question="which suppliers are set up at SG")

    assert planned.plan.asks is not None
    assert planned.plan.asks.options == ("WMSupplier", "A000144886")
    assert planned.plan.lookups == (), "it planned around the thing it says it cannot decide"
    assert asker.asked == [], "a question it will not answer is not a question worth paying for"


async def test_an_ambiguity_somebody_has_already_settled_does_not_stop_anything() -> None:
    # The answer is knowledge like any other. A system that asks the same thing
    # twice has not learned anything.
    settled = _entry(
        "blue_yonder/supplier/collection",
        EntryKind.QUESTION,
        title="blue_yonder/supplier/collection: WMSupplier",
        body={"answer": "WMSupplier", "answered_by": "devansh.j"},
    )
    planner, _ = _planner(_said(), [*KNOWN, settled])

    planned = await planner.execute(CTX, question="which suppliers are set up at SG")

    assert planned.plan.asks is None
    assert planned.plan.ready


async def test_an_ambiguity_about_something_else_does_not_stop_this_question() -> None:
    """Matched on the entity word, not on similarity. A looser rule would stop
    every question on the first unanswered ambiguity in the store."""
    elsewhere = _entry(
        "blue_yonder/transport_mode/collection",
        EntryKind.QUESTION,
        body={"question": "which transport modes?", "options": ["a", "b"]},
    )
    planner, _ = _planner(_said(), [*KNOWN, elsewhere])

    planned = await planner.execute(CTX, question="which suppliers are set up at SG")

    assert planned.plan.asks is None
    assert planned.plan.ready


async def test_a_screen_is_planned_where_no_endpoint_answers() -> None:
    # The other half of what the operator asked for: where there is no call,
    # open the page and read it. The route comes from the knowledge base too.
    planner, _ = _planner(
        _said(how="screen", target=SUPPLIER_SCREEN, params={}, cites=[SUPPLIER_SCREEN])
    )

    planned = await planner.execute(CTX, question="where do I see suppliers")

    (lookup,) = planned.plan.lookups
    assert lookup.how == "screen" and lookup.target == SUPPLIER_SCREEN


async def test_nothing_known_plans_nothing_rather_than_improvising() -> None:
    planner, asker = _planner(_said(), [])

    planned = await planner.execute(CTX, question="which suppliers are set up at SG")

    assert planned.plan.lookups == ()
    assert planned.refused == "nothing retrieved"
    assert asker.asked == [], "it paid a model to plan over an empty knowledge base"


async def test_a_question_with_nothing_in_it_is_refused_before_anything_is_asked() -> None:
    planner, asker = _planner(_said())

    planned = await planner.execute(CTX, question="   ")

    assert planned.refused is not None
    assert asker.asked == []


async def test_a_fan_out_wider_than_a_question_anybody_framed_is_cut() -> None:
    """`K_MAX_LOOKUPS` is a fan-out ceiling rather than a cost one. A question
    that plausibly reaches seven systems is a question nobody framed."""
    many = [
        _entry(f"/data/WM/wm/thing{n}", EntryKind.ENDPOINT, title=f"thing{n}") for n in range(9)
    ]
    answer = Answer(
        data={
            "why": "everywhere",
            "lookups": [
                {
                    "why": "w",
                    "system": WMS,
                    "how": "call",
                    "target": f"/data/WM/wm/thing{n}",
                    "cites": [f"/data/WM/wm/thing{n}"],
                }
                for n in range(9)
            ],
        }
    )
    planner, _ = _planner(answer, many)

    planned = await planner.execute(CTX, question="anything about things")

    assert len(planned.plan.lookups) == 6


async def test_a_model_that_answered_nothing_usable_is_a_refusal_not_a_plan() -> None:
    planner, _ = _planner(Answer(data={}, error="the model returned nothing"))

    planned = await planner.execute(CTX, question="which suppliers are set up at SG")

    assert planned.plan.lookups == ()
    assert planned.refused == "the model returned nothing"


@pytest.mark.parametrize("how", ["post", "delete", "write", ""])
async def test_the_planner_cannot_express_a_write_however_it_is_asked(how: str) -> None:
    """A read may not write, and the schema is where that is enforced rather
    than in a sentence the model may talk itself out of. A mail carrying "and
    then delete the old one" reaches this planner as text, and the only shapes
    it can answer in are a call and a screen.
    """
    planner, _ = _planner(_said(how=how))

    planned = await planner.execute(CTX, question="which suppliers are set up at SG")

    assert planned.plan.lookups == ()
