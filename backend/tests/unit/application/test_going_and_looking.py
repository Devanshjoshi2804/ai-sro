"""Executing a plan: where a lookup goes, and what it does when a system is shut.

Two things are held here. The ADDRESS -- a plan names a knowledge key and a
browser needs a url, and the only honest bridge is a place this deployment has
already been. And the RUN -- a GET with the account's own Steel session, or a
page put up in a Steel tab and photographed, never the operator's browser, with
one system's failure kept as one system's failure.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Mapping
from types import MappingProxyType

import pytest

from sro.application.context import RequestContext
from sro.application.ports.http import HttpResponse
from sro.domain.lookup.address import address_for
from sro.domain.lookup.plan import Lookup, Plan
from sro.domain.observation.gesture import Action, Call, Gesture
from sro.domain.shared.hosts import REDACTED
from tests import factories as f
from tests.unit.fakes import FakeHttpCaller
from tests.unit.runtime_support import lookup_world

CTX = RequestContext(tenant_id=f.TENANT, principal_id=f.OPERATOR)
WMS = "https://bf56-kms-wms-web-np2.jdadelivers.com"
SUPPLIERS = "/data/WM/wm/suppliers"
ROUTE = "#wm.config/wm.config.partners.suppliers////"
SCREEN_URL = (
    f"{WMS}/portal/page?libraryContext=f4d675&siteId=SG"
    "&menu=wm.config#wm.config.partners.suppliers////"
)


def _call(
    *,
    method: str = "GET",
    path: str = SUPPLIERS,
    query: str = "siteId=SG",
    status: int | None = 200,
    at: float = 100.0,
    headers: dict[str, str] | None = None,
    failure: str | None = None,
) -> Call:
    return Call(
        method=method,
        url=f"{WMS}{path}?{query}" if query else f"{WMS}{path}",
        request_id=f"req-{at}",
        started_at=at,
        request_headers=headers if headers is not None else {"accept": "application/json"},
        status=status,
        failure_reason=failure,
    )


def _gesture(*calls: Call, at: float = 100.0, url: str = f"{WMS}/portal") -> Gesture:
    gesture = Gesture(
        id=f"ges-{at}",
        tenant=f.TENANT.value,
        stream_id="str-1",
        batch_id="bat-1",
        at=at,
        url=url,
        system="bf56-kms-wms-web-np2.jdadelivers.com",
        tab_id=7,
        frame_url=None,
        action=Action(kind="click", at=at, url=url),
    )
    gesture.requests.extend(calls)
    return gesture


CALL = Lookup(system="blue_yonder", how="call", target=SUPPLIERS, cites=(SUPPLIERS,))
SCREEN = Lookup(system="blue_yonder", how="screen", target=ROUTE, cites=(ROUTE,))


def test_an_endpoint_is_addressed_from_the_host_this_deployment_signs_into() -> None:
    """The knowledge base catalogues `/data/WM/wm/suppliers` and holds no host.
    The host is whichever one the operator was recorded against."""
    address = address_for(CALL, [_gesture(_call())])

    assert address is not None
    assert address.url.startswith(f"{WMS}{SUPPLIERS}?")


def test_the_question_being_asked_now_beats_the_one_that_was_recorded() -> None:
    address = address_for(
        Lookup(system="blue_yonder", how="call", target=SUPPLIERS, params={"siteId": "MEL"}),
        [_gesture(_call(query="siteId=SG&limit=25"))],
    )

    assert address is not None
    assert "siteId=MEL" in address.url
    # Kept: dropping a parameter the system requires turns a working call into
    # a 400, and nothing here knows which of them it requires.
    assert "limit=25" in address.url


def test_the_newest_call_that_worked_is_the_one_reused() -> None:
    # A session moves. The last call that worked carries the headers the system
    # wanted most recently.
    address = address_for(
        CALL,
        [
            _gesture(_call(at=100.0, headers={"x-old": "1"}), at=100.0),
            _gesture(_call(at=900.0, headers={"x-new": "1"}), at=900.0),
        ],
    )

    assert address is not None and address.seen_at == 900.0
    assert "x-new" in address.headers


@pytest.mark.parametrize(
    "call",
    [
        _call(method="POST"),
        _call(status=403),
        _call(status=None),
        _call(failure="the tab closed"),
        _call(path="/data/WM/wm/suppliers/count"),
    ],
    ids=["a write", "refused", "never answered", "failed", "a different endpoint"],
)
def test_a_call_that_is_not_evidence_of_a_working_read_addresses_nothing(call: Call) -> None:
    """`/suppliers/count` is the one worth naming: a prefix match would answer
    "which suppliers" with a number, which is a different question with a
    plausible-looking answer. And a POST is refused here as well as in the
    schema -- this is the half that reaches somebody's warehouse."""
    assert address_for(CALL, [_gesture(call)]) is None


def test_a_struck_out_header_is_named_as_live_or_named_as_missing() -> None:
    address = address_for(
        CALL,
        [
            _gesture(
                _call(
                    headers={
                        "X-Requested-With": REDACTED,
                        "Authorization": f"Bearer {REDACTED}",
                        "accept": "application/json",
                    }
                )
            )
        ],
    )

    assert address is not None
    assert address.live_headers == ("X-Requested-With",)
    assert address.struck == ("Authorization",)
    assert "Authorization" not in address.headers, "the marker's own text is not a credential"


def test_a_screen_is_the_page_somebody_was_on_and_not_a_url_built_from_a_route() -> None:
    """`libraryContext` is a session token this side cannot invent. Assembling
    origin + hash produces a url that loads the shell and not the screen."""
    address = address_for(SCREEN, [_gesture(url=SCREEN_URL)])

    assert address is not None and address.url == SCREEN_URL


def test_a_route_is_matched_however_the_two_sides_spell_it() -> None:
    # The catalogue writes the menu and the route; the application's url
    # carries the menu in its query and only the route after the hash.
    assert address_for(SCREEN, [_gesture(url=SCREEN_URL)]) is not None
    assert (
        address_for(SCREEN, [_gesture(url=f"{WMS}/portal/page#wm.config.partners.clients////")])
        is None
    )


async def test_a_call_goes_out_as_a_get_with_the_account_s_steel_session() -> None:
    world = await lookup_world(_gesture(_call(headers={"X-Requested-With": REDACTED})))
    world.driver.cookie = "sid=abc"
    world.driver.headers = {"x-requested-with": "XMLHttpRequest"}
    world.http.answer(200, '{"rows": 5}')

    answers = await world.run_lookups.execute(CTX, plan=Plan(question="q", lookups=(CALL,)))

    (sent,) = world.http.sent
    assert sent["method"] == "GET"
    assert isinstance(sent["headers"], dict)
    assert sent["headers"]["cookie"] == "sid=abc"
    assert sent["headers"]["x-requested-with"] == "XMLHttpRequest"
    assert world.driver.needed == ("x-requested-with",)
    assert answers.any_answered
    assert world.driver.tabs == {}


async def test_an_expired_session_signs_in_again_once_and_the_read_is_tried_again() -> None:
    world = await lookup_world(_gesture(_call()))
    world.http.answer(401, "")
    world.http.answer(200, '{"rows": 1}')

    answers = await world.run_lookups.execute(CTX, plan=Plan(question="q", lookups=(CALL,)))

    assert world.reauths == 1 and len(world.http.sent) == 2 and answers.any_answered


async def test_a_call_refused_otherwise_is_read_off_the_page_it_was_seen_on() -> None:
    world = await lookup_world(_gesture(_call(), url=SCREEN_URL))
    world.http.answer(500, "")

    answers = await world.run_lookups.execute(CTX, plan=Plan(question="q", lookups=(CALL,)))

    assert answers.looked[0].ok and answers.looked[0].answer["mime_type"] == "image/png"
    assert ("open_tab", SCREEN_URL) in {(call[0], call[-1]) for call in world.driver.calls}
    assert world.reauths == 0


async def test_a_screen_is_put_up_in_a_steel_tab_and_nothing_on_it_is_pressed() -> None:
    world = await lookup_world(_gesture(url=SCREEN_URL))

    answers = await world.run_lookups.execute(CTX, plan=Plan(question="q", lookups=(SCREEN,)))

    assert answers.looked[0].ok
    assert set(answers.looked[0].answer) == {"image_base64", "mime_type", "width", "height"}
    assert world.driver.acted == [] and world.driver.pointed == []
    assert world.http.sent == []
    assert world.driver.tabs == {}


async def test_an_endpoint_seen_only_as_a_write_is_refused_before_anything_is_sent() -> None:
    world = await lookup_world(_gesture(_call(method="POST")))

    answers = await world.run_lookups.execute(CTX, plan=Plan(question="q", lookups=(CALL,)))

    assert world.http.sent == [] and world.driver.calls == []
    assert answers.looked[0].detail.startswith("nothing here has been to")


async def test_a_system_that_needs_a_person_is_one_named_gap() -> None:
    world = await lookup_world(_gesture(_call()), _gesture(url=SCREEN_URL, at=200.0))
    world.driver.refuses = True

    answers = await world.run_lookups.execute(CTX, plan=Plan(question="q", lookups=(CALL, SCREEN)))

    assert [one.ok for one in answers.looked] == [False, False]
    assert all(one.detail for one in answers.looked)
    assert world.http.sent == []


async def test_what_came_back_is_read_by_the_reader_every_other_read_uses() -> None:
    """The lookup plane was the ONE read in this system that did not.

    It handed the raw body on, so each surface that drew an answer parsed
    JSON, hunted for the rows and picked columns for itself -- three guesses
    at one question. Measured on the deployment 2026-09-21, beside the
    warehouse's own screen: the WMS grid showed `Customer Type | Description`,
    and the panel drew `URNFORMAT | ABSOLUTEGROUP | ALLOCATIONSEARCHPATH` as
    columns of em dashes, which are the first six KEYS of a payload that
    alphabetises.

    `application.execution.answer` had already decided every part of that, for
    the plane that uses it.
    """
    body = json.dumps(
        {
            "totalCount": 137,
            "data": [
                {
                    "URNFormat": None,
                    "absoluteGroup": None,
                    "bulkPickingFlag": False,
                    "supplierNumber": "100012",
                    "supplierName": "ACME LOGISTICS",
                    "self_uri": f"{WMS}{SUPPLIERS}/100012",
                }
            ],
        }
    )
    world = await lookup_world(_gesture(_call()))
    world.http.answer(200, body)

    answers = await world.run_lookups.execute(CTX, plan=Plan(question="q", lookups=(CALL,)))

    read = answers.looked[0].read
    assert read is not None, "the body crossed unread, for every surface to guess at"
    # The count the SYSTEM stated, not the length of the page it sent.
    assert read.counted == 137
    # The columns that carry something, identifying ones first, and no link
    # repeating the address the request was made to.
    assert "supplierNumber" in read.columns and "supplierName" in read.columns
    assert "URNFormat" not in read.columns and "self_uri" not in read.columns
    assert read.columns.index("supplierName") < read.columns.index("bulkPickingFlag")


async def test_an_answer_that_is_not_records_is_left_as_it_came() -> None:
    """A page of HTML, a scalar, a screen's photograph. There is nothing for
    the reader to read, and the surfaces draw those from the body."""
    world = await lookup_world(_gesture(_call()))
    world.http.answer(200, "<html>a page</html>")

    answers = await world.run_lookups.execute(CTX, plan=Plan(question="q", lookups=(CALL,)))

    assert answers.looked[0].read is None
    assert answers.looked[0].answer == {"status": 200, "body": "<html>a page</html>"}


class _Silent(FakeHttpCaller):
    async def send(
        self,
        method: str,
        url: str,
        *,
        headers: Mapping[str, str] = MappingProxyType({}),
        body: str | None = None,
        timeout_s: float = 30.0,
    ) -> HttpResponse:
        await asyncio.Event().wait()
        raise AssertionError("an event nobody sets was set")


async def test_a_lookup_that_runs_out_of_its_budget_is_one_named_gap() -> None:
    """The caller says how long: a conversation turn may not wait as long as
    a door whose answer IS the request. The tab it took is given back."""
    world = await lookup_world(_gesture(_call()))
    world.run_lookups._http = _Silent()

    answers = await world.run_lookups.execute(
        CTX, plan=Plan(question="q", lookups=(CALL,)), within=0.05
    )

    assert answers.looked[0].detail.startswith("timed out after")
    assert world.driver.tabs == {}


async def test_one_unseen_system_is_one_named_gap_and_not_a_failed_question() -> None:
    """The opposite reading from the planner's, deliberately. A target nobody
    has seen means the PLAN is wrong about the world, and three answers with a
    named gap are worth more than nothing."""
    world = await lookup_world(_gesture(_call()))
    elsewhere = Lookup(system="mail", how="call", target="/gmail/v1/threads", cites=("x",))

    answers = await world.run_lookups.execute(
        CTX, plan=Plan(question="q", lookups=(CALL, elsewhere))
    )

    answered, missing = answers.looked
    assert answered.ok
    assert not missing.ok
    assert missing.detail == "nothing here has been to /gmail/v1/threads"
    assert answers.any_answered


async def test_a_plan_that_asks_instead_of_answering_sends_nothing() -> None:
    world = await lookup_world(_gesture(_call()))

    answers = await world.run_lookups.execute(CTX, plan=Plan(question="q"))

    assert world.http.sent == [] and world.driver.calls == [] and answers.looked == ()
