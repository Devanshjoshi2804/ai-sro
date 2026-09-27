"""`POST /v1/lookups`: who may ask, what leaves the building, and what comes back.

The planner is proved in `test_where_to_look_for_an_answer`, the going-and-
looking in `test_going_and_looking`. What is here is the wire: that a plan
nobody asked to execute is not executed, that a question this deployment has
already called ambiguous never reaches a browser, that a device's own secret
does not open the tenant's purse, and that a screen's picture does not come
back through a door nothing on this side can read it with.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import httpx
import pytest
from httpx import ASGITransport

from sro.application.context import RequestContext
from sro.application.lookup.run_lookups import Answers, Looked, RunLookups
from sro.config import Settings
from sro.domain.knowledge.entry import EntryKind, EvidenceLevel, KnowledgeEntry, KnowledgeId
from sro.domain.lookup.plan import Lookup, Plan
from sro.domain.shared.identifiers import DeviceId
from sro.domain.shared.prices import Answer
from sro.interface.http.app import create_app
from sro.interface.http.deps import get_container
from tests import factories as f
from tests.unit.fakes import FakeAsker, FakeClock, FakeUnitOfWork
from tests.unit.interface.test_http import _FakeContainer, token_for

SUPPLIERS = "/data/WM/wm/suppliers"
WMS = "blue_yonder"
QUESTION = "which supplier records are set up at SG"
"""Singular, because the FAKE knowledge store matches a term as a substring of
the key and the real one stems: `suppliers` would find
`blue_yonder/supplier/collection` in Postgres and not in the fake. The
planner's own plural handling is held in `test_where_to_look_for_an_answer`,
where it is the thing under test rather than a fixture detail."""
HERS = "the-secret-the-laptop-was-minted"

"""Deliberately not the shipped default, so a route wired to a literal fails
rather than agreeing with it."""


def _entry(key: str, kind: EntryKind, body: dict[str, object] | None = None) -> KnowledgeEntry:
    return KnowledgeEntry(
        id=KnowledgeId(f"kn_{abs(hash(key + kind.value)) % 10**8}"),
        tenant_id=f.TENANT,
        system=WMS,
        kind=kind,
        key=key,
        title=key,
        body=body or {},
        source="a test",
        evidence=EvidenceLevel.REPRODUCED,
        observed_at=f.at(0),
    )


def _plan_answer(**over: object) -> Answer:
    lookup: dict[str, object] = {
        "why": "the suppliers collection answers this",
        "system": WMS,
        "how": "call",
        "target": SUPPLIERS,
        "params": {"siteId": "SG"},
        "cites": [SUPPLIERS],
    }
    lookup.update(over)
    return Answer(
        data={"why": "one system holds suppliers", "lookups": [lookup]},
        cost_usd=0.004,
        in_tokens=900,
        out_tokens=60,
    )


class _Container(_FakeContainer):
    """The real route, the real planner, and a browser that answers on script."""

    def __init__(self, uow: FakeUnitOfWork, answers: Answers | None = None) -> None:
        super().__init__(uow)
        self.settings = Settings(_env_file=None)
        self.clock = FakeClock()
        self.asker = FakeAsker(_plan_answer())
        self.looked: list[Plan] = []
        self._answers = answers

    def run_lookups(self) -> RunLookups:
        outer = self

        class _Runs(RunLookups):
            async def execute(
                self,
                ctx: RequestContext,
                *,
                plan: Plan,
                # The deadline the conversation door passes. Named here only so
                # this stands in for the real one: a fake whose signature has
                # drifted from what it replaces is a test of nothing.
                within: float = 0.0,
            ) -> Answers:
                outer.looked.append(plan)
                return outer._answers or Answers(plan=plan)

        return _Runs(self.unit_of_work(), self.session_broker(), self.http)


@pytest.fixture
def uow() -> FakeUnitOfWork:
    return FakeUnitOfWork()


@pytest.fixture
async def known(uow: FakeUnitOfWork) -> None:
    for entry in (
        _entry(SUPPLIERS, EntryKind.ENDPOINT, {"params": ["siteId"]}),
        _entry("/portal/page/Suppliers", EntryKind.SCREEN),
    ):
        await uow.knowledge.add(entry)


def _client(container: _FakeContainer, *, token: str | None = None) -> httpx.AsyncClient:
    app = create_app()
    app.dependency_overrides[get_container] = lambda: container
    return httpx.AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {token or token_for()}"},
    )


@pytest.fixture
async def client(uow: FakeUnitOfWork) -> AsyncIterator[httpx.AsyncClient]:
    async with _client(_Container(uow)) as http:
        yield http


async def test_a_question_comes_back_as_a_plan_with_the_bill_beside_it(
    uow: FakeUnitOfWork, known: None
) -> None:
    async with _client(_Container(uow)) as http:
        got = await http.post("/v1/lookups", json={"question": QUESTION, "execute": False})

    assert got.status_code == 200
    body = got.json()
    assert body["lookups"] == [
        {
            "system": WMS,
            "how": "call",
            "target": SUPPLIERS,
            "params": {"siteId": "SG"},
            "why": "the suppliers collection answers this",
            "cites": [SUPPLIERS],
        }
    ]
    assert body["answers"] == []
    assert body["cost_usd"] == 0.004 and body["in_tokens"] == 900


async def test_a_plan_nobody_asked_to_execute_reaches_no_browser(
    uow: FakeUnitOfWork, known: None
) -> None:
    container = _Container(uow)
    async with _client(container) as http:
        await http.post("/v1/lookups", json={"question": QUESTION, "execute": False})

    assert container.looked == [], "a plan is readable before anything leaves the building"


async def test_what_each_system_answered_comes_back_beside_the_plan(
    uow: FakeUnitOfWork, known: None
) -> None:
    lookup = Lookup(system=WMS, how="call", target=SUPPLIERS, cites=(SUPPLIERS,))
    answers = Answers(
        plan=Plan(question=QUESTION, lookups=(lookup,)),
        looked=(
            Looked(
                lookup=lookup,
                ok=True,
                url=f"https://wms.test{SUPPLIERS}?siteId=SG",
                answer={"status": 200, "body": '{"rows": 5}', "duration_ms": 91},
            ),
        ),
    )
    async with _client(_Container(uow, answers)) as http:
        got = await http.post("/v1/lookups", json={"question": QUESTION})

    (answered,) = got.json()["answers"]
    assert answered["ok"] and answered["status"] == 200
    assert answered["body"] == '{"rows": 5}'
    assert answered["truncated"] is False
    assert answered["seen"]["duration_ms"] == 91


async def test_a_screens_picture_does_not_come_back_through_this_door(
    uow: FakeUnitOfWork, known: None
) -> None:
    """Hundreds of kilobytes of base64 per screen, and nothing on this side can
    read it: what a picture MEANS is a model's question, and asking one is not
    this door."""
    lookup = Lookup(system=WMS, how="screen", target="/portal/page/Suppliers")
    answers = Answers(
        plan=Plan(question=QUESTION, lookups=(lookup,)),
        looked=(
            Looked(
                lookup=lookup,
                ok=True,
                url="https://wms.test/portal/page#suppliers",
                answer={
                    "image_base64": "iVBORw0KGgo" * 5000,
                    "width": 1280,
                    "height": 800,
                    "text_digest": "suppliers ▸ 5 rows",
                },
            ),
        ),
    )
    async with _client(_Container(uow, answers)) as http:
        got = await http.post("/v1/lookups", json={"question": QUESTION})

    (answered,) = got.json()["answers"]
    assert "image_base64" not in got.text
    assert answered["seen"] == {"width": 1280, "height": 800, "text_digest": "suppliers ▸ 5 rows"}


async def test_an_answer_longer_than_this_door_carries_says_it_was_cut(
    uow: FakeUnitOfWork, known: None
) -> None:
    # An answer silently cut in half is a wrong answer with no sign on it.
    lookup = Lookup(system=WMS, how="call", target=SUPPLIERS, cites=(SUPPLIERS,))
    answers = Answers(
        plan=Plan(question=QUESTION, lookups=(lookup,)),
        looked=(Looked(lookup=lookup, ok=True, answer={"status": 200, "body": "x" * 70000}),),
    )
    async with _client(_Container(uow, answers)) as http:
        got = await http.post("/v1/lookups", json={"question": QUESTION})

    (answered,) = got.json()["answers"]
    assert answered["truncated"] is True and len(answered["body"]) == 64 * 1024


async def test_a_word_this_deployment_calls_ambiguous_never_reaches_a_browser(
    uow: FakeUnitOfWork, known: None
) -> None:
    await uow.knowledge.add(
        _entry(
            "blue_yonder/supplier/collection",
            EntryKind.QUESTION,
            {"question": "which suppliers?", "options": ["WMSupplier", "A000144886"]},
        )
    )
    container = _Container(uow)
    async with _client(container) as http:
        got = await http.post("/v1/lookups", json={"question": QUESTION})

    assert got.json()["asks"]["options"] == ["WMSupplier", "A000144886"]
    assert container.looked == []
    assert container.asker.asked == [], "a question it will not answer is not one worth paying for"


async def test_a_deployment_with_no_model_says_so_rather_than_looking(
    uow: FakeUnitOfWork, known: None
) -> None:
    container = _Container(uow)
    container.asker = None
    async with _client(container) as http:
        got = await http.post("/v1/lookups", json={"question": QUESTION})

    assert got.status_code == 503
    assert container.looked == []


async def test_a_browsers_own_secret_does_not_open_the_tenants_purse(
    uow: FakeUnitOfWork, known: None
) -> None:
    """Tenant-only, as the chat door is. This spends the tenant's budget and
    then drives the tenant's browser; a device naming itself with its own real
    secret must not be able to do either by typing into a box."""
    await uow.devices.add(f.device(id=DeviceId("dev-1"), secret=HERS))
    container = _Container(uow)
    async with _client(container) as http:
        got = await http.post(
            "/v1/lookups",
            params={"device_id": "dev-1"},
            headers={"X-Device-Secret": HERS},
            json={"question": QUESTION},
        )

        assert got.status_code == 403
        assert container.looked == []
        # And the same question without the browser is answered, so the 403 is
        # the refusal rather than this route being absent.
        assert (await http.post("/v1/lookups", json={"question": QUESTION})).status_code == 200


@pytest.mark.parametrize("question", ["", "   ", "x" * 501])
async def test_a_question_with_nothing_in_it_is_refused_before_a_model_is_asked(
    uow: FakeUnitOfWork, question: str
) -> None:
    container = _Container(uow)
    async with _client(container) as http:
        got = await http.post("/v1/lookups", json={"question": question})

    assert got.status_code == 422
    assert container.asker.asked == []


async def test_an_instruction_goes_to_the_job_door_and_a_question_to_the_lookup_one(
    uow: FakeUnitOfWork, known: None
) -> None:
    """`POST /v1/ask` is one box in front of both worlds, so the extension does
    not carry a copy of the rule that decides."""
    container = _Container(uow)
    async with _client(container) as http:
        asked = await http.post("/v1/ask", json={"said": QUESTION})
        told = await http.post("/v1/ask", json={"said": "create a supplier called WMSupplier"})

    assert asked.json()["kind"] == "lookup"
    assert asked.json()["lookup"]["lookups"][0]["target"] == SUPPLIERS
    assert told.json()["kind"] == "job"
    assert told.json()["lookup"] is None


async def test_an_instruction_wearing_a_question_mark_is_still_an_instruction(
    uow: FakeUnitOfWork, known: None
) -> None:
    # The failure that matters: read as a question, the operator waits for
    # something that is never going to happen.
    container = _Container(uow)
    async with _client(container) as http:
        got = await http.post("/v1/ask", json={"said": "can you add demo values?"})

    assert got.json()["kind"] == "job"
    assert container.looked == [], "an instruction reached no browser as a read"
