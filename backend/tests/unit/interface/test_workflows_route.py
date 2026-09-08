"""The menu of jobs, and the day underneath one of them.

Ported from `new_agent_arch/src/rig/api.py:812` and `:904`. Two routes and two
different doors, which is what this file exists to hold:

`GET /v1/workflows` is authorised. A browser holding its own secret may ask,
because the listing is the menu of jobs that browser could be offered, and
prose about a job is not a fact about anybody's day.

`GET /v1/workflows/{id}/evidence` is tenant-only. What a workflow cites is
every browser's gestures -- what somebody typed, where they clicked, the calls
their page made -- and two browsers sharing a workflow is the normal case,
because that is what a mined job IS. Serving the evidence to a browser's
secret would hand one operator another's afternoon through a job they happen
to have in common.

Swapping those two dependencies is the mutation this file is written to kill,
and it has to die in both directions: the listing refusing a browser is as
wrong as the evidence serving one. So the browser that is served the listing
below and the browser that is refused the evidence are the same registered
browser, holding the same real secret, in the same test.

Naming a browser with its own real secret is the only way to reach
`tenant_only` at all: a secret with no `?device_id=`, or an id with no secret,
is a half-pair `asking_device` refuses as a 404 long before the tenant rule is
consulted.

Nothing here is dated today. Every run is planted at `f.at(...)` -- March
2026, six months from the wall clock -- so a fixture cannot come to agree with
a route by the calendar.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import httpx
import pytest
from httpx import ASGITransport

from sro.domain.execution.workflow_run import RunStep, WorkflowRun
from sro.domain.observation.gesture import Action, Body, Call, Component, Gesture, Target
from sro.domain.shared.identifiers import DeviceId
from sro.domain.skill.workflow import Step, Workflow
from sro.interface.http.app import create_app
from sro.interface.http.deps import get_container
from tests import factories as f
from tests.unit.fakes import FakeUnitOfWork
from tests.unit.interface.test_http import _FakeContainer, token_for

LAPTOP = DeviceId("dev-1")
HERS = "the-secret-the-laptop-was-minted"

JOB = "wfl_zebra"
"""The workflow every asymmetry test below reads, and the first one planted.

Its id sorts LAST of the three, and it is saved FIRST. `known` is oldest
first, so the wanted order is `[zebra, alpha, mid]` -- which is neither sorted
by id, nor that reversed, nor the plant reversed. Every ordering a route could
substitute by accident is a different list from the right one.
"""

SIBLING = "wfl_alpha"
THIRD = "wfl_mid"


@pytest.fixture
def uow() -> FakeUnitOfWork:
    return FakeUnitOfWork()


@pytest.fixture
def container(uow: FakeUnitOfWork) -> _FakeContainer:
    return _FakeContainer(uow)


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
async def rival(container: _FakeContainer) -> AsyncIterator[httpx.AsyncClient]:
    """A second tenant's credential against the same container.

    A route that hardcoded `acme` -- or read the tenant off anything but `ctx`
    -- passes every other assertion in this file.
    """
    app = create_app()
    app.dependency_overrides[get_container] = lambda: container
    async with httpx.AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {token_for(tenant='rival')}"},
    ) as http:
        yield http


# --- what gets planted ------------------------------------------------------


def _gesture(
    gesture_id: str,
    *,
    stream: str,
    at: float,
    tenant: str = "acme",
    calls: list[Call] | None = None,
) -> Gesture:
    """One gesture with every field carrying something, so a blanked model shows.

    Nothing here is a default: `redacted_fields`, `component`, the response
    body, the tab id. A response model that dropped a field would otherwise
    match a fixture that never set it.
    """
    return Gesture(
        id=gesture_id,
        tenant=tenant,
        stream_id=stream,
        batch_id=f"bat_{gesture_id}",
        at=at,
        url=f"http://wms.test/orders/{gesture_id}",
        system="wms.test",
        tab_id=7,
        frame_url="http://wms.test/frame",
        action=Action(
            kind="type",
            at=at,
            value="ACME-4471",
            secret=False,
            url=f"http://wms.test/orders/{gesture_id}",
            target=Target(
                tag="input",
                role="textbox",
                name="Client code",
                secret=False,
                text="ACME-4471",
                test_id="client-code",
                css_path="form > input.code",
                xpath="//input[@id='code']",
                component=Component(
                    item_id="clientCode",
                    query="textfield[itemId=clientCode]",
                    field_label="Client code",
                    name="clientCode",
                    xtype="textfield",
                ),
            ),
        ),
        page_url="http://wms.test/orders",
        requests=list(calls or []),
    )


def _call(request_id: str) -> Call:
    return Call(
        method="POST",
        url="http://wms.test/api/orders",
        request_id=request_id,
        started_at=1772359200.0,
        request_headers={"content-type": "application/json"},
        request_body=Body(text='{"code":"ACME-4471"}', size_bytes=20, mime_type="application/json"),
        status=201,
        response_body=Body(text='{"id":88}', size_bytes=9, mime_type="application/json"),
        failure_reason=None,
        blocked_reason=None,
        tab_id=7,
    )


def _workflow(
    workflow_id: str, *, tenant: str = "acme", cites: list[str] | None = None
) -> Workflow:
    """One mined job with every field set, and its steps planted out of order.

    The steps go in as 2, 0, 1. The wanted answer is 0, 1, 2 -- which is
    neither the plant nor the plant reversed -- because `Workflow.steps` is a
    list nothing promises is ordered and a job served in the wrong order reads
    as a plausible one.
    """
    cited = cites or []
    return Workflow(
        id=workflow_id,
        tenant=tenant,
        title=f"create a client ({workflow_id})",
        narrative="open the client screen, type the code, save",
        systems=["wms.test", "billing.test"],
        steps=[
            Step(order=2, says="save", system="wms.test", cites=cited[2:3], parameters=[]),
            Step(
                order=0,
                says="open the client screen",
                system="wms.test",
                cites=cited[0:1],
                parameters=[],
            ),
            Step(
                order=1,
                says="type the code",
                system="billing.test",
                cites=cited[1:2],
                parameters=["clientCode"],
            ),
        ],
        parameters=[{"name": "clientCode", "evidence": "proven"}],
        shape_key=[["wms.test", "clientCode", "type"]],
        same_as=None,
        unproven=["the approval nobody could place"],
        pass_id="pas_7",  # noqa: S106 -- the mining pass that found it, not a password
    )


def _run(run_id: str, *, workflow_id: str, held: bool, wrote: bool = False) -> WorkflowRun:
    return WorkflowRun(
        id=run_id,
        tenant="acme",
        workflow_id=workflow_id,
        device_id=LAPTOP.value,
        values={},
        started_by="offer",
        live=True,
        allow_focus=True,
        started_at=f.at(-3600).isoformat(),
        finished_at=f.at(-1800).isoformat(),
        outcome="held" if held else "broke",
        steps=[
            RunStep(
                order=0,
                says="save",
                verdict="held" if held else "broke",
                verdict_by="status",
                result={"wrote": True} if wrote else None,
            )
        ],
    )


@pytest.fixture
async def mined(uow: FakeUnitOfWork) -> list[Gesture]:
    """Three jobs and the evidence one of them cites.

    Saved zebra, alpha, mid -- see `JOB`. The four gestures arrive on three
    streams and out of clock order, so the streams `recordings` answers with
    (`str_m`, `str_a`, `str_z`) are neither sorted, nor that reversed, nor the
    order they were planted in.
    """
    cited = [
        _gesture("ges_2", stream="str_a", at=20.0, calls=[_call("req_2")]),
        _gesture("ges_1", stream="str_m", at=10.0, calls=[_call("req_1a"), _call("req_1b")]),
        _gesture("ges_3", stream="str_z", at=30.0, calls=[]),
    ]
    uncited = _gesture("ges_4", stream="str_never", at=40.0, calls=[_call("req_4")])
    await uow.gestures.add_gestures((*cited, uncited))

    await uow.workflows.save(_workflow(JOB, cites=["ges_1", "ges_2", "ges_3"]))
    await uow.workflows.save(_workflow(SIBLING))
    await uow.workflows.save(_workflow(THIRD))
    return cited


async def _listed(client: httpx.AsyncClient) -> httpx.Response:
    return await client.get("/v1/workflows")


async def _evidence(client: httpx.AsyncClient, workflow_id: str = JOB) -> httpx.Response:
    return await client.get(f"/v1/workflows/{workflow_id}/evidence")


# --- the asymmetry, in both directions --------------------------------------


async def test_a_browser_may_list_the_jobs_it_could_be_offered(
    client: httpx.AsyncClient, uow: FakeUnitOfWork, mined: list[Gesture]
) -> None:
    """The listing is authorised, as it is in the rig.

    The browser names itself with its own real secret, which is the only way
    past `asking_device` -- and the jobs come back, all three of them. A 200
    over an empty body would pass a route that had lost its store, so the
    count is asserted with the status.
    """
    await uow.devices.add(f.device(id=LAPTOP, secret=HERS))

    answered = await client.get(
        "/v1/workflows",
        params={"device_id": LAPTOP.value},
        headers={"X-Device-Secret": HERS},
    )

    assert answered.status_code == 200
    assert [row["id"] for row in answered.json()["workflows"]] == [JOB, SIBLING, THIRD]


async def test_a_browser_may_not_read_the_evidence_under_a_job(
    client: httpx.AsyncClient, uow: FakeUnitOfWork, mined: list[Gesture]
) -> None:
    """The same browser, the same secret, one URL further down: refused.

    A workflow's citations are every browser's gestures, and two browsers
    sharing a workflow is the normal case. This browser could be offered the
    job; it may not read whose afternoon proved it.

    The tenant's own 200 on the same URL is asserted here rather than left to
    the test below, so this 403 cannot be an absent route, an unroutable path
    or a 404 for a workflow nobody planted.
    """
    await uow.devices.add(f.device(id=LAPTOP, secret=HERS))

    answered = await client.get(
        f"/v1/workflows/{JOB}/evidence",
        params={"device_id": LAPTOP.value},
        headers={"X-Device-Secret": HERS},
    )

    assert answered.status_code == 403
    assert answered.json()["detail"] == "that is the tenant's to do, not a browser's"
    assert (await _evidence(client)).status_code == 200


async def test_the_tenant_may_read_a_jobs_evidence(
    client: httpx.AsyncClient, mined: list[Gesture]
) -> None:
    """And gets the gestures, not an empty envelope: a route that answered 200
    over nothing would pass on the status alone."""
    answered = await _evidence(client)

    assert answered.status_code == 200
    assert sorted(answered.json()["gestures"]) == ["ges_1", "ges_2", "ges_3"]


# --- what a job's card says -------------------------------------------------


async def test_a_mined_job_reaches_the_wire_whole(
    client: httpx.AsyncClient, mined: list[Gesture]
) -> None:
    """Every field of a planted workflow, round-tripped.

    Blanking the content of a response model has survived a full suite more
    than once, so this compares the row entire rather than checking that a row
    exists. `unproven` and `parameters` are in it deliberately: they are the
    pass's own model output, they exist nowhere else a reader can reach, and
    they are what a route emitting their siblings drops.
    """
    row = next(row for row in (await _listed(client)).json()["workflows"] if row["id"] == JOB)

    assert row == {
        "id": JOB,
        "title": f"create a client ({JOB})",
        "narrative": "open the client screen, type the code, save",
        "systems": ["wms.test", "billing.test"],
        "pass_id": "pas_7",
        "parameters": [{"name": "clientCode", "evidence": "proven"}],
        "unproven": ["the approval nobody could place"],
        "steps": [
            {
                "order": 0,
                "says": "open the client screen",
                "system": "wms.test",
                "cites": ["ges_1"],
                "parameters": [],
            },
            {
                "order": 1,
                "says": "type the code",
                "system": "billing.test",
                "cites": ["ges_2"],
                "parameters": ["clientCode"],
            },
            {
                "order": 2,
                "says": "save",
                "system": "wms.test",
                "cites": ["ges_3"],
                "parameters": [],
            },
        ],
        "runs": {"total": 0, "held": 0, "stale": 0, "earned": False},
    }


async def test_the_steps_come_back_in_the_order_the_job_runs_in(
    client: httpx.AsyncClient, mined: list[Gesture]
) -> None:
    """The plant is 2, 0, 1 and the answer is 0, 1, 2.

    Neither the stored order nor its reverse, so a route that served
    `workflow.steps` as it found them -- or reversed them -- answers a
    different list. A job whose steps are out of order still reads as a job.
    """
    row = next(row for row in (await _listed(client)).json()["workflows"] if row["id"] == JOB)

    assert [step["order"] for step in row["steps"]] == [0, 1, 2]
    assert row["steps"][0]["says"] == "open the client screen"


async def test_the_jobs_come_back_oldest_first(
    client: httpx.AsyncClient, mined: list[Gesture]
) -> None:
    """`known` is oldest first, and this plant disagrees with every ordering a
    route could reach for by accident: the ids sort `alpha, mid, zebra`, and
    the answer is `zebra, alpha, mid`.

    Sorted, reverse-sorted and the plant reversed are three different lists
    from that one, so a `sorted(...)` or a `reversed(...)` anywhere between
    the store and the wire fails here rather than agreeing by coincidence.
    """
    listed = [row["id"] for row in (await _listed(client)).json()["workflows"]]

    assert listed == [JOB, SIBLING, THIRD]
    assert listed != sorted(listed)
    assert listed != sorted(listed, reverse=True)
    assert listed != listed[::-1]


async def test_a_job_the_pass_could_not_place_is_still_on_the_menu(
    client: httpx.AsyncClient, uow: FakeUnitOfWork, mined: list[Gesture]
) -> None:
    """This is the console's list, not the extension's.

    `/v1/shapes` skips an unproven workflow, because it is offering a job to
    run. This route is answering "what did the pass find", and the jobs it
    could not place are the ones somebody most needs to see. A route that
    copied `serve_shapes`' gate would drop every one of them, and every
    workflow this file plants carries `unproven`.
    """
    listed = (await _listed(client)).json()["workflows"]

    assert len(listed) == 3
    assert all(row["unproven"] for row in listed)


# --- what has become of the job ---------------------------------------------


async def test_the_tally_is_this_jobs_and_not_its_neighbours(
    client: httpx.AsyncClient, uow: FakeUnitOfWork, mined: list[Gesture]
) -> None:
    """Two jobs with different histories, so a workflow id passed to the wrong
    read -- or a tally looked up under a sibling's id -- is a wrong number
    rather than the same one twice.

    Three runs on this job and one held; one run on the sibling and it held.
    No pair of those figures is equal, and neither job's pair is the other's.
    """
    for run in ("run_1", "run_2"):
        await uow.workflow_runs.save(_run(run, workflow_id=JOB, held=False))
    await uow.workflow_runs.save(_run("run_3", workflow_id=JOB, held=True))
    await uow.workflow_runs.save(_run("run_4", workflow_id=SIBLING, held=True))

    by_id = {row["id"]: row["runs"] for row in (await _listed(client)).json()["workflows"]}

    assert (by_id[JOB]["total"], by_id[JOB]["held"]) == (3, 1)
    assert (by_id[SIBLING]["total"], by_id[SIBLING]["held"]) == (1, 1)
    assert (by_id[THIRD]["total"], by_id[THIRD]["held"]) == (0, 0)


async def test_a_job_whose_page_is_moving_says_so(
    client: httpx.AsyncClient, uow: FakeUnitOfWork, mined: list[Gesture]
) -> None:
    """`stale` is per workflow, and this route is `mark_stale`'s only reader.

    Two weak steps on this job and one on the sibling, so a count asked with
    the wrong id answers 1 where 2 is right -- and a count asked tenant-wide
    answers 3 to both.
    """
    await uow.workflows.mark_stale(JOB, 0, matched_by="text", noticed_at=f.at(-60).isoformat())
    await uow.workflows.mark_stale(JOB, 1, matched_by="css", noticed_at=f.at(-60).isoformat())
    await uow.workflows.mark_stale(SIBLING, 0, matched_by="text", noticed_at=f.at(-60).isoformat())

    by_id = {row["id"]: row["runs"] for row in (await _listed(client)).json()["workflows"]}

    assert (by_id[JOB]["stale"], by_id[SIBLING]["stale"], by_id[THIRD]["stale"]) == (2, 1, 0)


async def test_a_job_that_has_earned_its_writes_says_so_and_its_neighbour_does_not(
    client: httpx.AsyncClient, uow: FakeUnitOfWork, mined: list[Gesture]
) -> None:
    """Three live held runs, every write verified by a state belt.

    The sibling gets three held runs too, and no register at all -- so `earned`
    cannot be `held > 0` wearing a different name, which is the shape
    `application.execution.effects.earned` exists to refuse: a job with a
    hundred held runs and nothing in its register has earned nothing.
    """
    for index in range(3):
        run_id = f"run_{index}"
        await uow.workflow_runs.save(_run(run_id, workflow_id=JOB, held=True, wrote=True))
        await uow.workflows.record_effect(
            JOB, run_id=run_id, ord_=0, verified_by="status", at=f.at(-1800).isoformat()
        )
        await uow.workflow_runs.save(
            _run(f"other_{index}", workflow_id=SIBLING, held=True, wrote=True)
        )

    by_id = {row["id"]: row["runs"] for row in (await _listed(client)).json()["workflows"]}

    assert by_id[JOB]["earned"] is True
    assert by_id[SIBLING]["earned"] is False
    assert by_id[SIBLING]["held"] == 3


# --- the evidence itself ----------------------------------------------------


async def test_a_cited_gesture_reaches_the_bridge_whole(
    client: httpx.AsyncClient, mined: list[Gesture]
) -> None:
    """The shape `application.skill.from_rig` reads a replayable plan out of.

    Every field of the planted gesture, down to the component query that is
    the strongest locator rung there is: a bridge handed a gesture with its
    target blanked builds a plan with no locators and no error. `tenant` and
    `requests` are the two fields that must NOT be in here -- the first
    because the caller proved it, the second because it is served beside.
    """
    served = (await _evidence(client)).json()["gestures"]["ges_1"]

    assert "tenant" not in served
    assert "requests" not in served
    assert served == {
        "id": "ges_1",
        "stream_id": "str_m",
        "batch_id": "bat_ges_1",
        "at": 10.0,
        "url": "http://wms.test/orders/ges_1",
        "system": "wms.test",
        "tab_id": 7,
        "frame_url": "http://wms.test/frame",
        "page_url": "http://wms.test/orders",
        "page_events": [],
        "action": {
            "kind": "type",
            "at": 10.0,
            "value": "ACME-4471",
            "secret": False,
            "url": "http://wms.test/orders/ges_1",
            "target": {
                "tag": "input",
                "role": "textbox",
                "name": "Client code",
                "secret": False,
                "text": "ACME-4471",
                "test_id": "client-code",
                "css_path": "form > input.code",
                "xpath": "//input[@id='code']",
                "component": {
                    "item_id": "clientCode",
                    "query": "textfield[itemId=clientCode]",
                    "field_label": "Client code",
                    "name": "clientCode",
                    "xtype": "textfield",
                },
            },
        },
    }


async def test_the_calls_a_gesture_made_come_back_keyed_by_it(
    client: httpx.AsyncClient, mined: list[Gesture]
) -> None:
    """Complete rather than trimmed, bodies and all.

    The bridge takes a status and a request body today; assertions are the
    next consumer, and post-conditions are built from responses. A route
    called `evidence` that quietly ships part of the evidence is the shape of
    defect this project keeps finding -- so the response body is asserted, not
    just the request.

    Keyed by gesture id and one list each, as the rig served it: `ges_1` made
    two calls and `ges_3` made none, so a map that had lost its keying answers
    the wrong list for at least one of them.
    """
    body = (await _evidence(client)).json()

    assert sorted(body["requests"]) == ["ges_1", "ges_2", "ges_3"]
    assert [call["request_id"] for call in body["requests"]["ges_1"]] == ["req_1a", "req_1b"]
    assert body["requests"]["ges_3"] == []
    first = body["requests"]["ges_1"][0]
    assert first["method"] == "POST"
    assert first["status"] == 201
    assert first["request_body"]["text"] == '{"code":"ACME-4471"}'
    assert first["response_body"]["text"] == '{"id":88}'
    assert first["request_headers"] == {"content-type": "application/json"}


async def test_only_what_the_job_cites_is_served(
    client: httpx.AsyncClient, mined: list[Gesture]
) -> None:
    """A workflow is a claim about specific evidence, not about the store.

    `ges_4` is this tenant's, on a stream of its own, and no step cites it. A
    route that answered `gestures_for` with no ids serves it -- and the
    largest real workflow cites 35 of 387 gestures, so that route would ship
    ten times what was asked for and still look right.
    """
    body = (await _evidence(client)).json()

    assert "ges_4" not in body["gestures"]
    assert "str_never" not in body["recordings"]


async def test_the_streams_are_distinct_and_oldest_first(
    client: httpx.AsyncClient, mined: list[Gesture]
) -> None:
    """`Provenance` reads these as the streams a job's evidence arrived on.

    Three gestures on three streams, planted out of clock order, and the
    answer is their own clock's order: `str_m` (t=10), `str_a` (t=20),
    `str_z` (t=30). That is neither sorted, nor sorted backwards, nor the
    order they were added in -- so getting it from any of those three fails
    here rather than agreeing.
    """
    recordings = (await _evidence(client)).json()["recordings"]

    assert recordings == ["str_m", "str_a", "str_z"]
    assert recordings != sorted(recordings)
    assert recordings != sorted(recordings, reverse=True)
    assert recordings != ["str_a", "str_m", "str_z"]


async def test_a_job_that_cites_nothing_is_an_answer_and_not_a_failure(
    client: httpx.AsyncClient, mined: list[Gesture]
) -> None:
    """`SIBLING` cites no gesture at all. Empty maps, a 200, and no `IN ()`
    reaching Postgres: a workflow with no citations is a real row, and the
    caller has to be able to tell it from a job that does not exist."""
    answered = await _evidence(client, SIBLING)

    assert answered.status_code == 200
    assert answered.json() == {"gestures": {}, "requests": {}, "recordings": []}


# --- whose, and which -------------------------------------------------------


async def test_a_job_nobody_mined_is_a_404_and_never_an_empty_list(
    client: httpx.AsyncClient, mined: list[Gesture]
) -> None:
    """Softening this into `{"gestures": {}}` is the mutation this asserts
    against: it would tell a caller their bridge is fine and their job is
    empty, which is the one wrong answer that looks like a right one."""
    answered = await _evidence(client, "wfl_nobody_mined")

    assert answered.status_code == 404
    assert answered.json()["title"] == "Not found"


async def test_another_tenants_job_is_not_found_rather_than_read(
    rival: httpx.AsyncClient, mined: list[Gesture]
) -> None:
    """The evidence read is tenant-scoped, and this is the whole of its 404.

    A `rival` credential naming `acme`'s workflow by its real id must not get
    a gesture. The tenant comes off the credential and never off a literal.
    """
    answered = await _evidence(rival)

    assert answered.status_code == 404


async def test_another_tenants_credential_lists_its_own_nothing(
    rival: httpx.AsyncClient, mined: list[Gesture]
) -> None:
    """Three jobs are planted and `rival` sees none of them. A route that
    hardcoded a tenant, or read one off the path, passes every other listing
    assertion in this file."""
    answered = await _listed(rival)

    assert answered.status_code == 200
    assert answered.json() == {"workflows": []}


async def test_no_credential_reaches_neither_door(
    client: httpx.AsyncClient, mined: list[Gesture]
) -> None:
    """Authorised is not open. The listing is the laxer of the two doors, so
    it is the one worth naming here."""
    assert (await client.get("/v1/workflows", headers={"Authorization": ""})).status_code == 401
    assert (
        await client.get(f"/v1/workflows/{JOB}/evidence", headers={"Authorization": ""})
    ).status_code == 401
