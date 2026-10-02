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

import json

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
    _entry(
        SUPPLIERS, EntryKind.ENDPOINT, title="suppliers (collection)", body={"params": ["siteId"]}
    ),
    _entry(
        SUPPLIER_SCREEN, EntryKind.SCREEN, title="Suppliers", body={"seen_on_routes": ["Suppliers"]}
    ),
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

    async def execute(self, ctx: RequestContext, question: object) -> tuple[KnowledgeEntry, ...]:
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
        "params": json.dumps({"siteId": "SG"}),
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


async def test_an_ambiguity_about_a_word_stops_only_a_question_that_uses_that_word() -> None:
    """Measured against the real store, where the first version of this rule
    stopped three of five ordinary questions and every stop was false.

    `blue_yonder/client/value/full` asks which field of client the word 'full'
    named in a demonstration. "which clients are set up" is not ambiguous in
    that way, and a refusal nobody can act on is worse than the guess it
    prevents: it stops the question AND teaches the operator to ignore the one
    stop that was real.
    """
    about_a_word = _entry(
        "blue_yonder/client/value/full",
        EntryKind.QUESTION,
        body={
            "question": "Which field of client does 'full' name?",
            "options": ["inboundTransFullValidationFlag", "useFullPalletUomQuantity"],
        },
    )
    planner, _ = _planner(_said(), [*KNOWN, about_a_word])

    walked_past = await planner.execute(CTX, question="which clients are set up")
    assert walked_past.plan.asks is None

    planner, _ = _planner(_said(), [*KNOWN, about_a_word])
    stopped = await planner.execute(CTX, question="which clients have full validation")
    assert stopped.plan.asks is not None


async def test_an_ambiguity_about_a_write_never_stops_a_read() -> None:
    """`create/<parameter>` asks whether a value both demonstrations used is
    fixed or asked for each time. A read cannot be ambiguous in that way."""
    about_a_write = _entry(
        "blue_yonder/supplier/create/resource_id",
        EntryKind.QUESTION,
        body={"question": "Both demonstrations used 'A000144886'. Is that fixed?"},
    )
    planner, _ = _planner(_said(), [*KNOWN, about_a_write])

    planned = await planner.execute(CTX, question="which suppliers are set up at SG")

    assert planned.plan.asks is None and planned.plan.ready


async def test_an_answer_stored_as_its_own_entry_settles_the_question_beside_it() -> None:
    """The store keeps the answer as a second entry under the same key rather
    than as a field on the question. A plan that read only the row in front of
    it stopped on a question this deployment has an answer for."""
    key = "blue_yonder/supplier/collection"
    planner, _ = _planner(
        _said(),
        [
            *KNOWN,
            _entry(
                key, EntryKind.QUESTION, body={"question": "which collection?", "options": ["a"]}
            ),
            _entry(
                key, EntryKind.QUESTION, body={"answer": "WMSupplier", "answered_by": "devansh.j"}
            ),
        ],
    )

    planned = await planner.execute(CTX, question="which suppliers are set up at SG")

    assert planned.plan.asks is None and planned.plan.ready


async def test_a_screen_is_planned_where_no_endpoint_answers() -> None:
    # The other half of what the operator asked for: where there is no call,
    # open the page and read it. The route comes from the knowledge base too.
    planner, _ = _planner(
        _said(how="screen", target=SUPPLIER_SCREEN, params="{}", cites=[SUPPLIER_SCREEN])
    )

    planned = await planner.execute(CTX, question="where do I see suppliers")

    (lookup,) = planned.plan.lookups
    assert lookup.how == "screen" and lookup.target == SUPPLIER_SCREEN


async def test_a_screen_is_shown_with_the_endpoints_it_loads_so_a_call_can_be_chosen() -> None:
    """QA 2026-10-02: "is there a warehouse equipment type called X" was planned as a
    SCREEN on the Warehouse Equipment Type route -- a photograph that holds no records
    -- though that grid is a GET on `equipmentTypes`. The screen was shown by name only
    and the endpoint under another name, so nothing joined them for the model."""
    grid = "/data/WM/wm/equipmentTypes"
    route = "#wm.config/wm.config.equipment.equipment.warehouseequipmenttype////"
    planner, asker = _planner(
        _said(target=grid, params="{}", cites=[grid, route]),
        [
            _entry(
                grid,
                EntryKind.ENDPOINT,
                title="equipmentTypes (collection)",
                body={"resource": "equipmentTypes", "params": ["query"]},
            ),
            _entry(
                "/data/WM/wm/codes",
                EntryKind.ENDPOINT,
                title="codes (collection)",
                body={"resource": "codes"},
            ),
            _entry(
                route,
                EntryKind.SCREEN,
                title="Warehouse Equipment Type",
                body={"resources": ["equipmentTypes", "unseenThing"]},
            ),
        ],
    )

    await planner.execute(CTX, question="is there a warehouse equipment type called ZWOYBN")

    shown = str(asker.asked[0]["evidence"])
    on_the_screen = shown.split(route)[1].split("ENDPOINT")[0]
    assert f"loads: {grid}" in on_the_screen and "/data/WM/wm/codes" not in on_the_screen


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
    planner, _ = _planner(Answer(data={}))

    planned = await planner.execute(CTX, question="which suppliers are set up at SG")

    assert planned.plan.lookups == ()
    assert planned.refused == "plan_lookup v4: the answer does not match its schema"


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


async def test_the_value_an_existence_question_asks_about_rides_on_the_lookup() -> None:
    planner, _ = _planner(_said(find=" ZWOYBN "))

    planned = await planner.execute(CTX, question="is there a supplier called ZWOYBN")

    assert planned.plan.lookups[0].find == "ZWOYBN"


async def test_a_parameter_the_endpoint_does_not_declare_never_reaches_the_address() -> None:
    """The model picks values for the slots the endpoint declares. A key it
    invents -- or one that would overwrite what the recording asked with --
    is not the model's to set on a request that leaves the building."""
    planner, _ = _planner(
        _said(params=json.dumps({"siteId": "MEL", "libraryContext": "x", "limit": "1"}))
    )

    planned = await planner.execute(CTX, question="which suppliers are there in MEL")

    assert planned.plan.lookups[0].params == {"siteId": "MEL"}


async def test_params_that_are_not_a_json_object_refuse_the_plan_not_drop_the_filter() -> None:
    for bad in ("{bad", "[1]", '"x"', "null", ""):
        planner, _ = _planner(_said(params=bad))

        planned = await planner.execute(CTX, question="which suppliers are set up at SG")

        assert planned.refused and "params" in planned.refused and not planned.plan.lookups


async def test_a_lookup_that_takes_no_params_says_so_in_a_string_or_not_at_all() -> None:
    absent = _said()
    del absent.data["lookups"][0]["params"]
    for said in (_said(params="{}"), absent):
        planner, _ = _planner(said)

        planned = await planner.execute(CTX, question="which suppliers are set up at SG")

        assert planned.refused is None and planned.plan.lookups[0].params == {}
