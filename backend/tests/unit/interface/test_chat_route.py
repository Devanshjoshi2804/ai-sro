"""`POST /v1/ask`, the job half: who may ask, what it costs them, and what
comes back. `container.read_chat()` is the reading; `/v1/ask` is the only
door that reaches it, once `is_a_question` has said this sentence is not one.

The reading itself is proved in `tests/unit/application/rig/test_read_chat.py`
and `test_understand.py`. What is here is the wire: that a deployment with no
model answers 503 rather than a quiet "no job matched", that a tenant over its
cap answers 429, that every figure the reading measured survives the trip, that
the operator's own sentence does NOT, and that a browser's secret does not open
the tenant's purse.

Nothing is dated today. The container's clock stands in February 2025, six
months from any wall clock this runs against, so a route that reached for
`datetime.now(UTC)` bills a different day than the one asserted here.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from httpx import ASGITransport

from sro.config import Settings
from sro.domain.chat.reading import ChatReading
from sro.domain.shared.identifiers import DeviceId, TenantId
from sro.domain.shared.prices import Answer
from sro.domain.skill.workflow import Step, Workflow
from sro.infrastructure.db.codec import when
from sro.interface.http.app import create_app
from sro.interface.http.deps import get_container
from tests import factories as f
from tests.unit.fakes import FakeAsker, FakeChatRepository, FakeClock, FakeUnitOfWork
from tests.unit.interface.test_http import _FakeContainer, token_for

TENANT = TenantId("acme")
LAPTOP = DeviceId("dev-1")
HERS = "the-secret-the-laptop-was-minted"

NOW = datetime(2025, 2, 11, 23, 0, tzinfo=UTC)
CAP = 5.0

MODEL = "gemini-3.8-flash-preview"
"""Deliberately not the shipped `gemini_plan_model`, and deliberately not
`gemini_mine_model` either -- a chat door and a mining door look like they
should share a model and must not, so a route wired to the wrong one of the
model settings fails here rather than agreeing with a default."""

SAID = "create a work area for zone 4"


@pytest.fixture
def uow() -> FakeUnitOfWork:
    return FakeUnitOfWork()


@pytest.fixture
def container(uow: FakeUnitOfWork) -> _FakeContainer:
    built = _FakeContainer(uow)
    built.settings = Settings(daily_usd_cap=CAP, gemini_plan_model=MODEL, _env_file=None)
    built.clock = FakeClock(NOW)
    return built


@pytest.fixture
async def client(container: _FakeContainer) -> AsyncIterator[httpx.AsyncClient]:
    app = create_app()
    app.dependency_overrides[get_container] = lambda: container
    async with httpx.AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {token_for()}"},
    ) as http:
        yield http


@pytest.fixture
async def held(uow: FakeUnitOfWork) -> Workflow:
    """One job this tenant was seen doing, with two parameters and one of them
    given below -- so `values` and `missing` are two different answers rather
    than one answer twice."""
    workflow = Workflow(
        id="wfl_1",
        tenant=TENANT.value,
        title="create a work area",
        narrative="the operator created a work area",
        steps=[Step(order=0, says="s", system=None, cites=["ges_1"])],
        parameters=[
            {"name": "areaName", "seen_values": ["NEWTESTS"], "required": True},
            {"name": "zone", "seen_values": ["3"], "required": True},
        ],
    )
    await uow.workflows.save(workflow)
    return workflow


def _billed_rows(uow: FakeUnitOfWork) -> list[ChatReading]:
    """The bills this store holds, typed.

    `FakeUnitOfWork.chats` is annotated as the `ChatRepository` port and the
    port has no `rows`: the narrowing is `test_mine_route.py`'s own `_rows`
    idiom, and it is an assertion rather than an ignore so that a fake swapped
    for one without a row list fails here instead of at the read.
    """
    assert isinstance(uow.chats, FakeChatRepository)
    return uow.chats.rows


def _answer(workflow_id: str | None, values: list[dict[str, str]], **over: object) -> Answer:
    return Answer(
        data={"workflow_id": workflow_id, "values": values, "missing": []},
        **over,
    )


def test_this_containers_clock_is_nowhere_near_the_wall_clock() -> None:
    assert abs(datetime.now(UTC) - NOW) > timedelta(days=2)


# --- the two refusals -------------------------------------------------------


async def test_a_deployment_with_no_model_says_so_rather_than_offering_nothing(
    client: httpx.AsyncClient, held: Workflow
) -> None:
    """503, not a 200 saying no job matched. `_FakeContainer.asker` is `None`,
    which is what a deployment with no key has, and "the model named nothing"
    is exactly what an operator's own badly-worded sentence looks like -- they
    would go and rephrase a sentence that was never read."""
    answered = await client.post("/v1/ask", json={"said": SAID})

    assert answered.status_code == 503
    assert "gemini_api_key" in answered.text
    assert "interpretation_enabled" in answered.text


async def test_a_tenant_over_its_cap_is_told_to_come_back_later(
    container: _FakeContainer, client: httpx.AsyncClient, uow: FakeUnitOfWork, held: Workflow
) -> None:
    """429 and not 402 or 403: nothing about the sentence is wrong and it will
    be read tomorrow. The body names both numbers, so whoever reads it knows
    whether to raise the cap or to go and find the unpriced call.

    `type` and not `code`: `errors._problem` renders `exc.code` into the
    problem document's `type`, and there is no `code` key on the wire.
    """
    container.asker = FakeAsker(_answer("wfl_1", []))
    await uow.chats.record(
        ChatReading(
            id="cht_1", tenant=TENANT.value, at=NOW.replace(hour=10).isoformat(), cost_usd=5.01
        )
    )

    answered = await client.post("/v1/ask", json={"said": SAID})

    assert answered.status_code == 429
    body = answered.json()
    assert body["type"] == "https://ai-sro.dev/problems/over_cap"
    assert "$5.0100 of $5.00" in body["detail"]
    assert [row.id for row in _billed_rows(uow)] == ["cht_1"], "the refusal billed a row of its own"


async def test_the_cap_the_door_judges_against_is_the_configured_one(
    container: _FakeContainer, client: httpx.AsyncClient, uow: FakeUnitOfWork, held: Workflow
) -> None:
    """Asked twice, against two caps. One cap proves only that the route does
    not answer the other number; the answer having to move is what no literal
    can do."""
    container.asker = FakeAsker(_answer("wfl_1", []), _answer("wfl_1", []))
    await uow.chats.record(
        ChatReading(
            id="cht_1", tenant=TENANT.value, at=NOW.replace(hour=10).isoformat(), cost_usd=5.01
        )
    )
    assert (await client.post("/v1/ask", json={"said": SAID})).status_code == 429

    container.settings = Settings(daily_usd_cap=50.0, gemini_plan_model=MODEL, _env_file=None)

    assert (await client.post("/v1/ask", json={"said": SAID})).status_code == 200


async def test_a_sentence_nobody_typed_is_refused_before_the_model_is_asked(
    container: _FakeContainer, client: httpx.AsyncClient, held: Workflow
) -> None:
    """422 for the empty string and for a body with no `utterance` at all.

    The rig read `str(body.get("utterance") or "")` and asked the model that:
    a missing field spent money on a prompt containing nothing and offered
    nothing back. This is the one refusal that costs nothing to make.
    """
    asked = FakeAsker(_answer("wfl_1", []))
    container.asker = asked

    assert (await client.post("/v1/ask", json={"said": ""})).status_code == 422
    assert (await client.post("/v1/ask", json={})).status_code == 422
    # Stripped before it is measured, or `min_length` judges something other
    # than what would have been sent. Three spaces is a paid call about nothing.
    assert (await client.post("/v1/ask", json={"said": "   \t\n "})).status_code == 422

    assert asked.asked == [], "an empty sentence reached the model anyway"


async def test_a_sentence_longer_than_anybody_types_is_refused_before_it_is_paid_for(
    container: _FakeContainer, client: httpx.AsyncClient, held: Workflow
) -> None:
    """The utterance is the one part of this prompt a caller controls, and
    without a ceiling one request's spend is unbounded -- on the door whose
    whole premise is refusing before it spends.

    501 characters and 500, either side of the bound, so a route that dropped
    `max_length` fails and one that took a different number fails too.
    """
    asked = FakeAsker(_answer("wfl_1", []))
    container.asker = asked

    assert (await client.post("/v1/ask", json={"said": "x" * 501})).status_code == 422
    assert asked.asked == [], "a body nobody could have typed reached the model"

    assert (await client.post("/v1/ask", json={"said": "x" * 500})).status_code == 200


# --- what comes back --------------------------------------------------------


async def test_the_offer_and_the_bill_both_reach_the_wire(
    container: _FakeContainer, client: httpx.AsyncClient, held: Workflow
) -> None:
    """Every field carrying something other than its default.

    `values` and `missing` are two parameters of one job, so a body that
    answered one for the other fails. `thought_tokens` is inside `out_tokens`
    and is reported beside it anyway: 140 and 40, not 180.
    """
    container.asker = FakeAsker(
        _answer(
            "wfl_1",
            [{"name": "areaName", "value": "ZONE4"}],
            in_tokens=900,
            out_tokens=140,
            thought_tokens=40,
            cost_usd=0.0007,
        )
    )

    answered = await client.post("/v1/ask", json={"said": SAID})

    assert answered.status_code == 200, answered.text
    body = answered.json()
    assert body["job"]["workflow_id"] == "wfl_1"
    assert body["job"]["values"] == {"areaName": "ZONE4"}
    assert body["job"]["missing"] == ["zone"]
    assert body["job"]["error"] is None
    assert (body["job"]["in_tokens"], body["job"]["out_tokens"], body["job"]["thought_tokens"]) == (
        900,
        140,
        40,
    )
    assert (body["job"]["cost_usd"], body["job"]["unpriced"]) == (0.0007, False)


async def test_a_sentence_naming_no_job_is_an_offer_of_nothing_and_still_a_bill(
    container: _FakeContainer, client: httpx.AsyncClient, uow: FakeUnitOfWork, held: Workflow
) -> None:
    """The model named a job nobody holds, which is a hallucination and not an
    offer -- and the call still happened and was still paid for.

    `read_utterance`'s docstring: a row is written on every reading, a refusal
    included, because it is then the only record left of a call that cost money
    and returned nothing.
    """
    container.asker = FakeAsker(_answer("wfl_invented", [], cost_usd=0.0009))

    body = (await client.post("/v1/ask", json={"said": SAID})).json()

    assert body["job"]["workflow_id"] is None
    assert (body["job"]["values"], body["job"]["missing"]) == ({}, [])
    assert body["job"]["cost_usd"] == 0.0009
    (row,) = _billed_rows(uow)
    assert (row.workflow_id, row.cost_usd) == (None, 0.0009)


async def test_a_reading_whose_model_call_failed_is_not_answered_as_no_job_matched(
    container: _FakeContainer, client: httpx.AsyncClient, held: Workflow
) -> None:
    """`error` and `unpriced` both carrying something other than their default.

    Not hypothetical: `mining_passes` on the real store already holds a call
    that billed $1.9984 and returned nothing, `error='truncated: the answer hit
    the 65536 output-token ceiling after 2610 tokens'`. Replayed through a
    route that answered `error: null`, a failure like that is indistinguishable
    from a sentence about work this tenant has never been seen doing -- and the
    operator goes and rewords a sentence that was never read.

    `unpriced` is the same fact on the billing side: a model name the price
    table never knew about records $0.0000 with the flag set, and a wire that
    hardcoded `false` reports an honestly cheap reading while the tenant spends.
    """
    container.asker = FakeAsker(
        Answer(error="truncated: the answer hit the 65536 output-token ceiling", unpriced=True)
    )

    body = (await client.post("/v1/ask", json={"said": SAID})).json()

    assert body["job"]["error"] == "truncated: the answer hit the 65536 output-token ceiling"
    assert body["job"]["unpriced"] is True
    assert body["job"]["workflow_id"] is None


async def test_the_bill_is_not_rounded_on_the_way_out(
    container: _FakeContainer, client: httpx.AsyncClient, held: Workflow
) -> None:
    """Unrounded. Rounding for display is the reader's job; a
    bill rounded on the way out cannot be summed against the `chats` row it
    came from -- and `/v1/spend`, which does round, sums the raw figure."""
    container.asker = FakeAsker(_answer("wfl_1", [], cost_usd=0.0123456789))

    body = (await client.post("/v1/ask", json={"said": SAID})).json()

    assert body["job"]["cost_usd"] == 0.0123456789


async def test_what_is_missing_comes_back_in_the_order_the_reader_sorted_it(
    container: _FakeContainer, client: httpx.AsyncClient, uow: FakeUnitOfWork
) -> None:
    """The wire hands the form its fields in one order and never re-sorts them
    into another.

    `declared` is a set in `understand`, so `missing` is sorted there -- a form
    whose fields reorder between two identical sentences is a form nothing can
    screenshot. That the sort survives an unlucky interpreter is settled under
    real `PYTHONHASHSEED` values in
    `tests/unit/application/rig/test_read_chat.py`, which is where the set is;
    what is held here is that nothing between it and the browser reorders the
    list it produced. Eight names, declared in an order that is neither the
    answer nor its reverse.
    """
    await uow.workflows.save(
        Workflow(
            id="wfl_8",
            tenant=TENANT.value,
            title="t",
            narrative="n",
            parameters=[
                {"name": "zone", "required": True},
                {"name": "clientCode", "required": True},
                {"name": "statusCombo", "required": True},
                {"name": "areaName", "required": True},
                {"name": "ownerCode", "required": True},
                {"name": "dockId", "required": True},
                {"name": "siteCode", "required": True},
                {"name": "lane", "required": True},
            ],
        )
    )
    container.asker = FakeAsker(_answer("wfl_8", []))

    body = (await client.post("/v1/ask", json={"said": SAID})).json()

    assert body["job"]["missing"] == [
        "areaName",
        "clientCode",
        "dockId",
        "lane",
        "ownerCode",
        "siteCode",
        "statusCombo",
        "zone",
    ]


async def test_the_sentence_itself_is_not_stored_and_is_not_echoed_back(
    container: _FakeContainer, client: httpx.AsyncClient, uow: FakeUnitOfWork, held: Workflow
) -> None:
    """`ChatReading` has no field for it and that is deliberate: there is no
    column for an operator's words about their own warehouse.

    And the response model has none either, which is the same decision one
    layer out. A body that echoed the sentence back would put it into every
    proxy log, browser history and error report the answer passes through --
    undoing the column that was deliberately never added.

    The 200 and the billed row are asserted first on purpose: every assertion
    below is an absence, and an absence is satisfied by any answer that never
    reached the route at all. Without them a deleted endpoint passes this test
    -- the 404 quotes none of these words either -- so the door would be proved
    private and absent at the same time, which is no proof of privacy.
    """
    said = "create a work area for zone 4 for ACME-99, ask Priya"
    container.asker = FakeAsker(_answer("wfl_1", [{"name": "areaName", "value": "ZONE4"}]))

    answered = await client.post("/v1/ask", json={"said": said})

    assert answered.status_code == 200, answered.text
    assert len(_billed_rows(uow)) == 1, "the reading was never stored, so it stores nothing"
    for word in ("ACME-99", "Priya", said):
        assert word not in answered.text, f"{word!r} came back on the wire"
        assert word not in str(_billed_rows(uow)), f"{word!r} reached the row"


# --- whose sentence, whose jobs, whose clock --------------------------------


async def test_the_model_asked_is_the_one_this_deployment_configured(
    container: _FakeContainer, client: httpx.AsyncClient, held: Workflow
) -> None:
    """`gemini_plan_model` and not `gemini_mine_model`. An operator is standing
    at a screen waiting for this answer, so it is the fast model -- the same
    trade `gemini_intent_model` records measuring at ~2.3s against ~4.8s."""
    asked = FakeAsker(_answer("wfl_1", []))
    container.asker = asked

    await client.post("/v1/ask", json={"said": SAID})

    assert [one["model"] for one in asked.asked] == [MODEL]


async def test_the_sentence_the_model_reads_is_the_one_on_the_request(
    container: _FakeContainer, client: httpx.AsyncClient, held: Workflow
) -> None:
    """The one thing the caller supplies, carried from the body to the prompt.

    A route that dropped it -- or that asked with the empty string the rig's
    `body.get("utterance") or ""` fell back to -- still answers 200, still
    bills the tenant and still offers whatever the model makes of nothing.
    Every other assertion in this file passes while it does.
    """
    asked = FakeAsker(_answer("wfl_1", []))
    container.asker = asked
    said = "make me a work area called NEWTEST9 in zone 4"

    await client.post("/v1/ask", json={"said": said})

    assert said in str(asked.asked[0]["evidence"])


async def test_the_jobs_read_against_are_the_ones_on_the_credential(
    container: _FakeContainer, uow: FakeUnitOfWork, held: Workflow
) -> None:
    """Two tenants, because a route that hardcoded `acme` -- or read the tenant
    off anything but `ctx` -- passes every other assertion in this file. The
    rival holds nothing, so the job the model names is one nobody holds."""
    asked = FakeAsker(_answer("wfl_1", [{"name": "areaName", "value": "ZONE4"}]))
    container.asker = asked
    app = create_app()
    app.dependency_overrides[get_container] = lambda: container
    async with httpx.AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {token_for(tenant='rival')}"},
    ) as rival:
        body = (await rival.post("/v1/ask", json={"said": SAID})).json()

    assert body["job"]["workflow_id"] is None
    assert "wfl_1" not in str(asked.asked[0]["evidence"])
    assert [row.tenant for row in _billed_rows(uow)] == ["rival"], "billed to the wrong tenant"


async def test_the_reading_is_stamped_with_the_containers_clock(
    container: _FakeContainer, client: httpx.AsyncClient, uow: FakeUnitOfWork, held: Workflow
) -> None:
    """The route reads no clock. Which day a reading is billed to comes off the
    container's, and every plant here is six months from the wall clock, so a
    route that read one of its own stamps today."""
    container.asker = FakeAsker(_answer("wfl_1", []))

    await client.post("/v1/ask", json={"said": SAID})

    (row,) = _billed_rows(uow)
    assert when(row.at) == NOW


# --- who may ask ------------------------------------------------------------


async def test_a_browser_may_not_spend_the_tenants_model_budget(
    container: _FakeContainer, client: httpx.AsyncClient, uow: FakeUnitOfWork, held: Workflow
) -> None:
    """Tenant-only, as in the rig (`api.py:1495`,
    `dependencies=[Depends(tenant_only)]`). Naming itself with its own real
    secret is the only way a browser reaches `tenant_only` at all -- a wrong
    secret is refused earlier as a 404."""
    container.asker = FakeAsker(_answer("wfl_1", []))
    await uow.devices.add(f.device(id=LAPTOP, secret=HERS))

    answered = await client.post(
        "/v1/ask",
        json={"said": SAID},
        params={"device_id": LAPTOP.value},
        headers={"X-Device-Secret": HERS},
    )

    assert answered.status_code == 403
    assert answered.json()["detail"] == "that is the tenant's to do, not a browser's"
    # And the same request without the browser is answered, so the 403 is the
    # refusal and not this route being absent or unroutable.
    assert (await client.post("/v1/ask", json={"said": SAID})).status_code == 200


async def test_no_credential_is_refused_before_anything_is_read(
    client: httpx.AsyncClient, held: Workflow
) -> None:
    answered = await client.post("/v1/ask", json={"said": SAID}, headers={"Authorization": ""})

    assert answered.status_code == 401


async def test_the_request_name_survives_the_trip_to_the_question(
    client: httpx.AsyncClient, uow: FakeUnitOfWork
) -> None:
    """`POST /v1/chat/about-an-offer`: the whole point of `about` is that the
    conversation can say WHICH request it is asking about, and there may be
    four alike in the thread.

    It was dropped at this one line for an afternoon. Every layer either side
    carried it -- the mail read it, the offer shipped it, the browser sent it,
    the domain rendered it -- and the route called the door without it, so the
    question said "Create a Customer Type." and named nothing. Nothing failed,
    because nothing between the two ends was ever asked to agree.
    """
    answered = await client.post(
        "/v1/chat/about-an-offer",
        json={
            "workflow_id": "wfl_1",
            "title": "Create a Customer Type",
            "values": {"Customer Type": "NEWSROTEST"},
            "missing": [],
            "limits": {"Customer Type": 4},
            "about": "Customer type for the SRO pilot, round twenty-nine",
        },
    )

    assert answered.status_code == 200, answered.text
    asked = answered.json()["asked"]
    assert asked.startswith(
        "Create a Customer Type — Customer type for the SRO pilot, round twenty-nine."
    ), asked
    # And it reached the thread, not just the response.
    threads = await uow.threads.list_for_tenant(TENANT, limit=1)
    assert threads and threads[0].messages[-1].text == asked
