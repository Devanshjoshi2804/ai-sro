"""Executing a plan: where a lookup goes, and what it does when a system is shut.

Two things are held here. The ADDRESS -- a plan names a knowledge key and a
browser needs a url, and the only honest bridge is a place this deployment has
already been. And the RUN -- a GET with the account's own Steel session, or a
page put up in a Steel tab and photographed, never the operator's browser, with
one system's failure kept as one system's failure.
"""

from __future__ import annotations

import asyncio
import inspect
import json
from collections.abc import Mapping
from dataclasses import replace
from datetime import UTC, datetime
from types import MappingProxyType
from typing import Any
from urllib.parse import parse_qsl, unquote, urlsplit

import pytest

from sro.application.context import RequestContext
from sro.application.lookup.look_it_up import what_was_found
from sro.application.lookup.run_lookups import K_AFTER_HEADERS_S, K_WHILE_TALKING
from sro.application.ports.http import HttpResponse
from sro.domain.execution.account import Account, LeaseState
from sro.domain.execution.lanes import Lane, StepResult
from sro.domain.lookup.address import Address, address_for
from sro.domain.lookup.plan import Lookup, Plan
from sro.domain.observation.gesture import Action, Call, Gesture
from sro.domain.shared.hosts import REDACTED
from sro.domain.skill.signing_in import PageSignals
from sro.domain.skill.workflow import Step
from tests import factories as f
from tests.unit.fakes import FakeHttpCaller
from tests.unit.runtime_support import IDP, LookupWorld, lookup_world

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
    address = address_for(CALL, [_gesture(_call())], T0)

    assert address is not None
    assert address.url.startswith(f"{WMS}{SUPPLIERS}?")


def test_the_question_being_asked_now_beats_the_one_that_was_recorded() -> None:
    address = address_for(
        Lookup(system="blue_yonder", how="call", target=SUPPLIERS, params={"siteId": "MEL"}),
        [_gesture(_call(query="siteId=SG&limit=25"))],
        T0,
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
        T0,
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
    assert address_for(CALL, [_gesture(call)], T0) is None


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
        T0,
    )

    assert address is not None
    assert address.live_headers == ("X-Requested-With",)
    assert address.struck == ("Authorization",)
    assert "Authorization" not in address.headers, "the marker's own text is not a credential"


def test_a_screen_is_the_page_somebody_was_on_and_not_a_url_built_from_a_route() -> None:
    """`libraryContext` is a session token this side cannot invent. Assembling
    origin + hash produces a url that loads the shell and not the screen."""
    address = address_for(SCREEN, [_gesture(url=SCREEN_URL)], T0)

    assert address is not None and address.url == SCREEN_URL


def test_a_route_is_matched_however_the_two_sides_spell_it() -> None:
    # The catalogue writes the menu and the route; the application's url
    # carries the menu in its query and only the route after the hash.
    assert address_for(SCREEN, [_gesture(url=SCREEN_URL)], T0) is not None
    assert (
        address_for(SCREEN, [_gesture(url=f"{WMS}/portal/page#wm.config.partners.clients////")], T0)
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


async def test_a_recorded_account_header_never_rides_on_the_account_s_read() -> None:
    """The recording is the operator's. Only how the body is represented
    comes from it; whatever names an account comes from the account's own
    context."""
    world = await lookup_world(
        _gesture(_call(headers={"X-User-Id": "operator-7", "accept": "application/json"}))
    )

    await world.run_lookups.execute(CTX, plan=Plan(question="q", lookups=(CALL,)))

    (sent,) = world.http.sent
    assert isinstance(sent["headers"], dict)
    assert "x-user-id" not in {name.lower() for name in sent["headers"]}
    assert sent["headers"]["accept"] == "application/json"
    assert world.driver.waited_out == [], "nothing was needed, so nothing is waited for"


async def test_a_header_the_page_never_sends_is_a_gap_inside_the_conversation_s_budget() -> None:
    world = await lookup_world(_gesture(_call(headers={"X-Requested-With": REDACTED})))

    answers = await world.run_lookups.execute(
        CTX, plan=Plan(question="q", lookups=(CALL,)), within=K_WHILE_TALKING
    )

    assert world.http.sent == []
    assert not answers.looked[0].ok and "x-requested-with" in answers.looked[0].detail
    assert world.driver.waited_out
    assert 0 < max(world.driver.waited_out) <= K_WHILE_TALKING - K_AFTER_HEADERS_S
    assert world.driver.tabs == {}


async def test_an_expired_session_signs_in_again_once_and_the_read_is_tried_again() -> None:
    world = await lookup_world(_gesture(_call()))
    world.http.answer(401, "")
    world.http.answer(200, '{"rows": 1}')

    answers = await world.run_lookups.execute(CTX, plan=Plan(question="q", lookups=(CALL,)))

    assert world.reauths == 1 and len(world.http.sent) == 2 and answers.any_answered


async def test_a_read_is_made_by_the_page_and_never_by_the_workers_own_client() -> None:
    """Measured on QA 2026-10-02: the same GET from the worker's own client was
    answered 302 by the site's edge, and the lookup fell through to a photograph.
    The page itself is what the edge lets through."""
    world = await lookup_world(_gesture(_call()))

    answers = await world.run_lookups.execute(CTX, plan=Plan(question="q", lookups=(CALL,)))

    assert answers.any_answered
    ((_, method, url),) = world.driver.sent
    assert method == "GET" and url.startswith(f"{WMS}{SUPPLIERS}")


async def test_a_call_the_edge_sends_to_sign_in_signs_in_again_once() -> None:
    world = await lookup_world(_gesture(_call()))
    world.http.answer(302, "", {"location": "https://idp.example/auth"})
    world.http.answer(200, '{"data": [{"name": "a"}]}')

    answers = await world.run_lookups.execute(CTX, plan=Plan(question="q", lookups=(CALL,)))

    assert world.reauths == 1 and answers.looked[0].ok and answers.looked[0].read is not None


async def test_a_call_that_is_refused_otherwise_is_a_failed_lookup_not_a_photograph() -> None:
    """A photograph holds no records, so the question went on unanswered with
    the lookup reported as having worked. The status is the answer."""
    world = await lookup_world(_gesture(_call(), url=SCREEN_URL))
    world.http.answer(500, "")

    answers = await world.run_lookups.execute(CTX, plan=Plan(question="q", lookups=(CALL,)))

    assert not answers.looked[0].ok and "500" in answers.looked[0].detail
    assert world.reauths == 0 and "image_base64" not in answers.looked[0].answer


async def test_a_screen_is_put_up_in_a_steel_tab_and_nothing_on_it_is_pressed() -> None:
    world = await lookup_world(_gesture(url=SCREEN_URL))

    answers = await world.run_lookups.execute(CTX, plan=Plan(question="q", lookups=(SCREEN,)))

    assert answers.looked[0].ok
    assert set(answers.looked[0].answer) == {"image_base64", "mime_type", "width", "height"}
    assert world.driver.acted == [] and world.driver.pointed == []
    assert world.http.sent == []
    assert world.driver.tabs == {}


async def test_a_screen_is_photographed_after_the_reads_it_made_when_it_was_seen() -> None:
    """QA 2026-10-02: the photograph of the Warehouse Equipment Type page was a spinner
    and the word "Loading" -- the shot was taken the moment the tab settled, before the
    grid's own GET came back. The recording says which GET the page makes."""
    world = await lookup_world(_gesture(_call(), url=SCREEN_URL))
    events: list[str] = []
    driver = world.driver
    goto, wait, shoot = driver.goto, driver.wait_for_call, driver.screenshot

    async def seen_goto(*args: Any, **kwargs: Any) -> Any:
        events.append("goto")
        return await goto(*args, **kwargs)

    async def seen_wait(*args: Any, **kwargs: Any) -> Any:
        events.append(f"wait {kwargs['method']} {kwargs['shape']}")
        return await wait(*args, **kwargs)

    async def seen_shot(*args: Any, **kwargs: Any) -> Any:
        events.append("shot")
        return await shoot(*args, **kwargs)

    driver.goto, driver.wait_for_call, driver.screenshot = seen_goto, seen_wait, seen_shot  # type: ignore[method-assign]

    answers = await world.run_lookups.execute(CTX, plan=Plan(question="q", lookups=(SCREEN,)))

    assert answers.looked[0].ok
    assert events[-2:] == [f"wait GET {SUPPLIERS}", "shot"]
    assert "goto" in events[:-2], "the reads are waited for on a load that was being listened to"


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
    world.driver.http = _Silent()

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


def _leases(world: LookupWorld) -> list[LeaseState]:
    return [one.state for one in world.uow.browser_sessions.leases.values()]


async def test_a_header_the_driver_never_keeps_is_never_waited_for() -> None:
    """A recording that shape-redacts a header with a plain name struck its
    value, but no request log ever holds it: waiting for it would burn the
    whole budget for nothing."""
    world = await lookup_world(_gesture(_call(headers={"X-Acme-Ticket": REDACTED})))

    answers = await world.run_lookups.execute(CTX, plan=Plan(question="q", lookups=(CALL,)))

    assert answers.any_answered
    assert world.driver.needed == () and world.driver.waited_out == []


async def test_the_read_after_a_fresh_sign_in_takes_only_tokens_from_after_it() -> None:
    world = await lookup_world(_gesture(_call()))
    world.http.answer(401, "")
    world.http.answer(200, '{"rows": 1}')

    await world.run_lookups.execute(CTX, plan=Plan(question="q", lookups=(CALL,)))

    first, retry = (int(call[-1]) for call in world.driver.calls if call[0] == "headers_for")
    assert retry > first, "the retry took a token from before the sign-in it followed"


async def test_a_lookup_reads_as_the_tenant_s_recorded_login_not_as_whoever_asked() -> None:
    world = await lookup_world(_gesture(_call()))

    await world.run_lookups.execute(CTX, plan=Plan(question="q", lookups=(CALL,)))

    (lease,) = world.uow.browser_sessions.leases.values()
    assert lease.account == Account.of(f.TENANT.value, IDP, "lena")
    assert CTX.principal_id.value != "lena"


async def test_a_lookup_beside_a_run_never_takes_the_run_s_lease_as_its_own() -> None:
    world = await lookup_world(_gesture(_call()))
    account = await world.broker.account_for(CTX, f"{WMS}/portal")
    run = await world.broker.acquire(CTX, account, f"{WMS}/portal", holder="run_7")

    await world.run_lookups.execute(CTX, plan=Plan(question="q", lookups=(CALL,)))

    assert world.uow.browser_sessions.leases[run.lease.id].holder == "run_7"


async def test_a_one_time_code_during_a_lookup_is_a_gap_and_parks_nobody() -> None:
    world = await lookup_world(_gesture(_call()))
    world.driver.shows_sign_in_until_signed = False
    world.driver.signals_for_every_tab = PageSignals(
        f"{WMS}/portal", autocomplete=frozenset({"one-time-code"})
    )

    answers = await world.run_lookups.execute(CTX, plan=Plan(question="q", lookups=(CALL,)))

    assert not answers.looked[0].ok and "one-time code" in answers.looked[0].detail
    assert LeaseState.WAITING not in _leases(world)
    assert world.driver.tabs == {} and world.http.sent == []


class _SignedOutOnTheFirstRead(FakeHttpCaller):
    def __init__(self, world: LookupWorld) -> None:
        super().__init__()
        self._world = world

    async def send(
        self,
        method: str,
        url: str,
        *,
        headers: Mapping[str, str] = MappingProxyType({}),
        body: str | None = None,
        timeout_s: float = 30.0,
    ) -> HttpResponse:
        self.sent.append({"method": method, "url": url, "headers": dict(headers)})
        self._world.driver.expire_session()
        self._world.driver.refuses = True
        return HttpResponse(status_code=401, headers={}, text="")


async def test_a_password_refused_while_a_lookup_signs_in_again_parks_nobody() -> None:
    world = await lookup_world(_gesture(_call()))
    world.driver.http = _SignedOutOnTheFirstRead(world)

    answers = await world.run_lookups.execute(CTX, plan=Plan(question="q", lookups=(CALL,)))

    assert not answers.looked[0].ok and answers.looked[0].detail
    assert world.reauths == 1
    assert LeaseState.WAITING not in _leases(world)
    assert world.driver.tabs == {}


class _Hangs:
    lane = Lane.UI

    async def execute(self, step: Step, values: Mapping[str, str], ctx: object) -> StepResult:
        await asyncio.Event().wait()
        raise AssertionError("an event nobody sets was set")


async def test_a_conversation_that_runs_out_mid_sign_in_hears_it_is_signing_in_and_it_goes_on() -> (
    None
):
    """QA 2026-10-02: a cold sign-in (24-34 s) outlasts the chat's 10 s. The turn used to
    cancel it and leave the lease READY on the sign-in page, so no ask could ever finish.
    The sign-in now runs on the broker's own task: this turn says so, the next finds it done."""
    world = await lookup_world(_gesture(_call()))
    gate = asyncio.Event()
    execute = world.lane.execute

    async def slow(step: Step, values: Mapping[str, str], ctx: Any) -> StepResult:
        await gate.wait()
        return await execute(step, values, ctx)

    world.lane.execute = slow  # type: ignore[method-assign]
    plan = Plan(question="q", lookups=(CALL,))

    first = await world.run_lookups.execute(CTX, plan=plan, within=K_AFTER_HEADERS_S)

    assert first.looked[0].signing_in and not first.looked[0].ok
    assert first.looked[0].detail.startswith("signing in to ")
    gate.set()
    await world.broker.signings.settled()
    second = await world.run_lookups.execute(CTX, plan=plan, within=K_AFTER_HEADERS_S)

    assert second.looked[0].ok and world.lane.sign_ins == 1
    assert _leases(world) == [LeaseState.READY] and world.driver.tabs == {}


async def test_a_conversation_that_is_over_leaves_no_ready_lease_on_a_sign_in_page() -> None:
    world = await lookup_world(_gesture(_call()))
    world.broker._ui = _Hangs()

    answers = await world.run_lookups.execute(
        CTX, plan=Plan(question="q", lookups=(CALL,)), within=K_AFTER_HEADERS_S
    )
    await world.broker.signings.close()

    assert answers.looked[0].signing_in
    assert LeaseState.READY not in _leases(world) and world.driver.tabs == {}


async def test_a_code_prompt_is_answered_by_a_person_not_by_typing_the_password_again() -> None:
    """Each password typed at a code-guarded account sends its owner another
    code: a question a minute would be a push a minute. Once a code has been
    asked for, a lookup names the gap and leaves the password alone."""
    world = await lookup_world(_gesture(_call()))
    world.driver.signals_for_every_tab = PageSignals(
        f"{WMS}/portal", autocomplete=frozenset({"one-time-code"})
    )
    world.http.answer(401, "")
    world.http.answer(401, "")
    plan = Plan(question="q", lookups=(CALL,))

    first = await world.run_lookups.execute(CTX, plan=plan)
    second = await world.run_lookups.execute(CTX, plan=plan)

    assert world.lane.sign_ins == 1
    assert [one.ok for one in (*first.looked, *second.looked)] == [False, False]
    assert "one-time code" in second.looked[0].detail
    assert LeaseState.READY not in _leases(world), "a lease on a code prompt is not signed in"
    assert world.driver.tabs == {}


async def test_a_screen_that_is_a_sign_in_page_after_signing_back_in_is_a_gap_not_a_photo(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The system's single-page app sends the tab back to sign-in after the
    held page, and again after the sign-in that answered it."""
    world = await lookup_world(_gesture(url=SCREEN_URL))
    acquire, reauth = world.broker.acquire, world.broker.reauth

    async def acquired_then_redirected(*args: Any, **kwargs: Any) -> Any:
        held = await acquire(*args, **kwargs)
        world.driver.expire_session()
        return held

    async def signed_in_then_redirected(*args: Any, **kwargs: Any) -> None:
        await reauth(*args, **kwargs)
        world.driver.expire_session()

    monkeypatch.setattr(world.broker, "acquire", acquired_then_redirected)
    monkeypatch.setattr(world.broker, "reauth", signed_in_then_redirected)

    answers = await world.run_lookups.execute(CTX, plan=Plan(question="q", lookups=(SCREEN,)))

    assert world.reauths == 1
    assert not answers.looked[0].ok and "sign-in page" in answers.looked[0].detail


GRID = "/data/WM/wm/equipmentTypes"
WHOLE = json.dumps({"data": [{"code": "FORKLIFT"}, {"code": "PALLET"}]})
SEARCHED = 'query=[{"property":"code","value":"ZWOYBN"}]'


def _asked_for(code: str) -> Lookup:
    return Lookup(system="blue_yonder", how="call", target=GRID, find=code, cites=(GRID,))


def test_a_search_somebody_ran_is_not_the_read_that_gets_replayed() -> None:
    """Review 1 / R-L1. The newest recorded GET was an operator's filtered search; replayed
    verbatim it reads a filtered list and a lookup would say 'No' off it -- a false 'does not
    exist' that invites a duplicate. The recorded read with nothing narrowing it wins."""
    address = address_for(
        _asked_for("X"),
        [
            _gesture(_call(path=GRID, query="query=[]", at=100.0), at=100.0),
            _gesture(_call(path=GRID, query=SEARCHED, at=900.0), at=900.0),
        ],
        T0,
    )

    assert address is not None and address.narrowed == ()
    assert "ZWOYBN" not in unquote(address.url)


def test_a_read_that_only_ever_carried_a_search_is_marked_narrowed() -> None:
    address = address_for(_asked_for("X"), [_gesture(_call(path=GRID, query=SEARCHED))], T0)

    assert address is not None and address.narrowed == ("query",)


def test_a_filter_the_lookup_names_is_not_a_narrowing_it_did_not_ask_for() -> None:
    lookup = Lookup(
        system="blue_yonder", how="call", target=GRID, find="ZWOYBN", params={"code": "ZWOYBN"}
    )

    address = address_for(lookup, [_gesture(_call(path=GRID, query="code=OLD"))], T0)

    assert address is not None and address.narrowed == ()
    assert "code=ZWOYBN" in address.url


@pytest.mark.parametrize(
    ("recorded", "params", "narrowed"),
    [
        ("status=ALL", {"status": "ACTIVE"}, ("status",)),
        ("query=[]", {"status": "ACTIVE"}, ("status",)),
        ("query=[]", {"status": "ZW1"}, ()),
        ("query=[]", {"code": "zw1"}, ()),
        ("query=[]", {"query": '[{"property":"code","value":"ZW1"}]'}, ("query",)),
        ("query=[]", {"query": '[{"property":"site","value":"SG"}]'}, ("query",)),
        ("query=[]", {"code": "ZW1", "status": "ACTIVE"}, ("status",)),
    ],
)
def test_a_named_param_is_no_narrowing_only_when_it_carries_the_key_asked_for(
    recorded: str, params: dict[str, str], narrowed: tuple[str, ...]
) -> None:
    """Review 2 #3: status=ACTIVE with find=ZW1 reads only active records; 'none is ZW1' off it
    while an inactive ZW1 exists invites the duplicate. Only a value that holds the key is the
    asked-for search itself."""
    lookup = Lookup(system="blue_yonder", how="call", target=GRID, find="ZW1", params=params)

    address = address_for(lookup, [_gesture(_call(path=GRID, query=recorded))], T0)

    assert address is not None and address.narrowed == narrowed


@pytest.mark.parametrize(
    ("find", "params", "narrowed"),
    [
        ("ZW1", {"query": '[{"f":"status","v":"INACTIVE"},{"f":"name","v":"ZW1"}]'}, ("query",)),
        ("ZW1", {"query": '[{"f":"name","v":"ZW1","op":"ne"}]'}, ("query",)),
        ("ZW1", {"query": '[{"f":"name","v":"ZW1"}]'}, ("query",)),
        # exclude=ZW1 is, by value, the same as name=ZW1: only the planner's slot tells them apart.
        ("ZW1", {"exclude": "ZW1"}, ()),
        ("ZW1", {"name": "ZW10"}, ("name",)),
        ("ZW1", {"name": "ZW1*"}, ()),
        ("ZW1", {"name": "%ZW1%"}, ()),
        ("ZW1", {"name": "ZW1"}, ()),
        ("ZW1", {"name": "zw1"}, ()),
        ("ZW1", {"name": ""}, ()),
        ("ZW1", {"code_from": "ZW1", "code_to": "ZW9"}, ("code_to",)),
        ("ZW1", {"code_from": "ZW0", "code_to": "ZW1"}, ("code_from",)),
    ],
)
def test_a_named_param_is_exempt_only_when_it_is_the_key_and_nothing_else(
    find: str, params: dict[str, str], narrowed: tuple[str, ...]
) -> None:
    """Review 3 A: containment is a proxy; a value that holds the key and still narrows (a second
    filter, a negation, a longer code, a range end) must read as could-not-tell."""
    lookup = Lookup(system="blue_yonder", how="call", target=GRID, find=find, params=params)

    address = address_for(lookup, [_gesture(_call(path=GRID, query="query=[]"))], T0)

    assert address is not None and address.narrowed == narrowed


async def test_a_read_filtered_by_a_param_the_planner_named_never_says_no() -> None:
    lookup = Lookup(
        system="blue_yonder",
        how="call",
        target=GRID,
        find="ZW1",
        params={"status": "ACTIVE"},
        cites=(GRID,),
    )
    world = await lookup_world(_gesture(_call(path=GRID, query="query=[]")))
    world.http.answer(200, WHOLE)

    answers = await world.run_lookups.execute(CTX, plan=Plan(question="q", lookups=(lookup,)))

    said = what_was_found(answers)
    assert not said.startswith("No") and "could not tell" in said


async def test_a_list_read_through_a_recorded_search_never_says_no() -> None:
    world = await lookup_world(_gesture(_call(path=GRID, query=SEARCHED)))
    world.http.answer(200, WHOLE)

    answers = await world.run_lookups.execute(
        CTX, plan=Plan(question="q", lookups=(_asked_for("ZWOYBN"),))
    )

    said = what_was_found(answers)
    assert not said.startswith("No") and "could not tell" in said


async def test_a_whole_unfiltered_list_without_the_record_still_says_no() -> None:
    world = await lookup_world(_gesture(_call(path=GRID, query="query=[]")))
    world.http.answer(200, WHOLE)

    answers = await world.run_lookups.execute(
        CTX, plan=Plan(question="q", lookups=(_asked_for("ZWOYBN"),))
    )

    assert what_was_found(answers).startswith("No, none of the 2")


def _typed(value: str, *, at: float = 50.0) -> Gesture:
    return replace(_gesture(at=at), action=Action(kind="type", at=at, value=value))


T0 = 1_700_000_000.0
PARTNERS = "/data/WM/wm/partners"


def _dc(at: float, skew_ms: int = 0) -> str:
    return f"_dc={int(at * 1000) + skew_ms}"


def _shape(
    read_query: str, write_query: str, *extra: Gesture, stamped: bool = True
) -> list[Gesture]:
    """The QA shape (values anonymised): a recorded list read, two recorded saves to two endpoints
    five reads of other endpoints (which carry what the saves carried, so the stamp rides on at
    least five calls when `stamped`). The queries name the stamp as `{dc}`: each call's own
    started_at in milliseconds."""
    calls = [
        (GRID, "GET", read_query, T0),
        (SUPPLIERS, "POST", write_query, T0 + 100),
        (PARTNERS, "POST", write_query, T0 + 200),
    ]
    reads = write_query if stamped else write_query.replace("&{dc}", "")
    calls += [(f"/data/WM/wm/r{n}", "GET", reads, T0 + 300 + n) for n in range(5)]
    return [
        _gesture(_call(method=m, path=path, query=q.replace("{dc}", _dc(at)), at=at), at=at)
        for path, m, q, at in calls
    ] + list(extra)


READ = "query=[]&siteId=SG&subsites=a,b&{dc}"
WROTE = "siteId=SG&subsites=a,b&{dc}"


def test_a_param_the_recorded_writes_carry_with_the_same_value_is_scope_not_a_filter() -> None:
    """R-L6/R-L8: siteId=SG is where records are made, said by saves to two endpoints; the read
    of that place is the whole list. _dc is each call's own time (R-L7): no filter either."""
    address = address_for(_asked_for("X"), _shape(READ, WROTE, _typed("hello")), T0)

    assert address is not None and address.narrowed == ()


def test_a_stamp_two_calls_carry_with_the_same_value_is_still_a_stamp() -> None:
    """R-L7: the QA evidence had 217 _dc values shared by calls in one millisecond; sharing a
    value is no reason to read it as a filter, only a value that is not the call's time is."""
    twin = _gesture(
        _call(path="/data/WM/wm/r0", query=f"siteId=SG&subsites=a,b&{_dc(T0 + 300)}", at=T0 + 300),
        at=T0 + 300,
    )

    address = address_for(_asked_for("X"), [*_shape(READ, WROTE), twin], T0)

    assert address is not None and address.narrowed == ()


@pytest.mark.parametrize("value", ["1700000000", "1700000900000", str(10**14)])
def test_a_big_number_that_is_not_near_its_call_s_time_is_a_filter(value: str) -> None:
    """The old '10+ digit' shape accepted any of these."""
    gestures = _shape(READ.replace("{dc}", f"_dc={value}"), WROTE)

    address = address_for(_asked_for("X"), gestures, T0)

    assert address is not None and address.narrowed == ("_dc",)


def test_a_param_one_call_carries_off_its_time_ruins_the_stamp_for_every_call() -> None:
    off = _gesture(
        _call(path="/data/WM/wm/r9", query=_dc(T0 + 300, 6000), at=T0 + 300), at=T0 + 300
    )

    address = address_for(_asked_for("X"), [*_shape(READ, WROTE), off], T0)

    assert address is not None and address.narrowed == ("_dc",)


def test_a_stamp_within_five_seconds_of_its_call_counts_and_six_does_not() -> None:
    near = _shape(READ.replace("{dc}", _dc(T0, 4999)), WROTE)
    far = _shape(READ.replace("{dc}", _dc(T0, 5001)), WROTE)

    assert (address_for(_asked_for("X"), near, T0) or _never()).narrowed == ()
    assert (address_for(_asked_for("X"), far, T0) or _never()).narrowed == ("_dc",)


def test_a_stamp_seen_on_fewer_than_five_calls_is_not_proven() -> None:
    address = address_for(_asked_for("X"), _shape(READ, WROTE, stamped=False), T0)

    assert address is not None and address.narrowed == ("_dc",)


def test_the_replay_sends_a_fresh_stamp_and_leaves_the_scope_as_recorded() -> None:
    now = T0 + 5000
    address = address_for(_asked_for("X"), _shape(READ, WROTE), now)

    assert address is not None
    sent = dict(parse_qsl(urlsplit(address.url).query))
    assert sent["_dc"] == str(int(now * 1000))
    assert sent["siteId"] == "SG" and sent["subsites"] == "a,b" and sent["query"] == "[]"


def _never() -> Address:
    raise AssertionError("no address")


@pytest.mark.parametrize(
    ("read", "write", "typed", "narrowed"),
    [
        # the write saved to another place: the read is a different list
        ("query=[]&siteId=SG", "siteId=NL", "", ("siteId",)),
        # the writes never carried it: nothing proves it is scope
        ("query=[]&siteId=SG", "x=1", "", ("siteId",)),
        # a value the operator typed is record content, whatever a write also carried
        ("query=[]&siteId=SG", "siteId=SG", "sg", ("siteId",)),
        # a read only for one of the write's values
        ("query=[]&subsites=a", "subsites=a,b", "", ("subsites",)),
    ],
)
def test_a_param_unproven_by_what_was_recorded_stays_a_filter(
    read: str, write: str, typed: str, narrowed: tuple[str, ...]
) -> None:
    extra = (_typed(typed),) if typed else ()

    address = address_for(_asked_for("ZW1"), _shape(read, write, *extra), T0)

    assert address is not None and address.narrowed == narrowed


def _reads(query: str, n: int = 5) -> list[Gesture]:
    return [
        _gesture(_call(path=f"/data/WM/wm/r{i}", query=query, at=T0 + i), at=T0 + i)
        for i in range(n)
    ]


def _write(method: str, path: str, query: str, at: float, status: int = 200) -> Gesture:
    return _gesture(_call(method=method, path=path, query=query, at=at, status=status), at=at)


def test_one_endpoint_edited_twice_is_one_endpoint_not_two() -> None:
    """rr3 #1: PUT /item/1 and /item/2 are one write path shape."""
    gestures = [
        _gesture(_call(path=GRID, query="query=[]&status=ACTIVE", at=T0)),
        _write("PUT", "/data/WM/wm/item/1", "status=ACTIVE", T0 + 1),
        _write("PUT", "/data/WM/wm/item/2", "status=ACTIVE", T0 + 2),
        *_reads("status=ACTIVE"),
    ]

    address = address_for(_asked_for("X"), gestures, T0)

    assert address is not None and address.narrowed == ("status",)


def test_a_stamp_every_call_carries_with_one_value_is_a_filter() -> None:
    """rr3 #2: since=<page load> on a burst of five reads is time-near, but constant."""
    pl = int(T0 * 1000)
    gestures = [
        _gesture(_call(path=GRID, query=f"query=[]&since={pl}", at=T0 + 1)),
        *_reads(f"since={pl}"),
    ]

    address = address_for(_asked_for("X"), gestures, T0)

    assert address is not None and address.narrowed == ("since",)


def test_head_and_options_are_not_writes() -> None:
    gestures = [
        _gesture(_call(path=GRID, query="query=[]&status=ACTIVE", at=T0)),
        _write("OPTIONS", SUPPLIERS, "status=ACTIVE", T0 + 1, 204),
        _write("HEAD", PARTNERS, "status=ACTIVE", T0 + 2),
        *_reads("status=ACTIVE"),
    ]

    address = address_for(_asked_for("X"), gestures, T0)

    assert address is not None and address.narrowed == ("status",)


def test_scope_also_needs_the_pair_on_reads_of_five_other_endpoints() -> None:
    """rr3 #3: POST-as-read search endpoints look like writes; real scope rides on every read."""
    saves = [
        _gesture(_call(path=GRID, query="query=[]&status=ACTIVE", at=T0)),
        _write("POST", "/data/WM/wm/a/search", "status=ACTIVE", T0 + 1),
        _write("POST", "/data/WM/wm/b/search", "status=ACTIVE", T0 + 2),
    ]

    four = address_for(_asked_for("X"), [*saves, *_reads("status=ACTIVE", 4)], T0)
    five = address_for(_asked_for("X"), [*saves, *_reads("status=ACTIVE", 5)], T0)

    assert four is not None and four.narrowed == ("status",)
    assert five is not None and five.narrowed == ()


def test_now_is_a_required_argument() -> None:
    assert inspect.signature(address_for).parameters["now"].default is inspect.Parameter.empty


def test_a_param_the_planner_named_is_never_exempt_as_a_stamp() -> None:
    lookup = replace(_asked_for("X"), params={"_dc": "5"})

    address = address_for(lookup, _shape(READ, WROTE), T0)

    assert address is not None and address.narrowed == ("_dc",)
    assert dict(parse_qsl(urlsplit(address.url).query))["_dc"] == "5"


def test_a_param_one_endpoint_wrote_is_not_scope() -> None:
    one = [
        _gesture(_call(path=GRID, query="query=[]&status=ACTIVE")),
        _gesture(_call(method="POST", path=SUPPLIERS, query="status=ACTIVE"), at=200.0),
        _gesture(_call(method="PUT", path=SUPPLIERS, query="status=ACTIVE"), at=300.0),
    ]

    address = address_for(_asked_for("X"), one, T0)

    assert address is not None and address.narrowed == ("status",)


def test_a_write_that_failed_proves_nothing() -> None:
    gestures = [
        _gesture(_call(path=GRID, query="query=[]&siteId=SG")),
        _gesture(_call(method="POST", path=SUPPLIERS, query="siteId=SG"), at=200.0),
        _gesture(_call(method="POST", path=PARTNERS, query="siteId=SG", status=500), at=300.0),
    ]

    address = address_for(_asked_for("X"), gestures, T0)

    assert address is not None and address.narrowed == ("siteId",)


def test_scope_proven_on_one_system_is_not_proof_on_another() -> None:
    def elsewhere(path: str) -> Call:
        return replace(
            _call(method="POST", path=path, query="siteId=SG"),
            url=f"https://other.example.com{path}?siteId=SG",
        )

    gestures = [
        _gesture(_call(path=GRID, query="query=[]&siteId=SG")),
        _gesture(elsewhere(SUPPLIERS), at=2.0),
        _gesture(elsewhere(PARTNERS), at=3.0),
    ]

    address = address_for(_asked_for("X"), gestures, T0)

    assert address is not None and address.narrowed == ("siteId",)


async def test_a_list_read_with_scope_and_stamp_says_no_and_a_hit_says_yes() -> None:
    """The QA-shaped equipmentTypes read: scope and a stamp, a whole list, so it can say No."""
    world = await lookup_world(*_shape(READ, WROTE, _typed("hello")))
    world.http.answer(200, WHOLE)

    answers = await world.run_lookups.execute(
        CTX, plan=Plan(question="q", lookups=(_asked_for("ZWOYBN"),))
    )
    assert what_was_found(answers).startswith("No, none of the 2")
    (sent,) = world.http.sent
    now_ms = int(datetime(2026, 3, 1, 9, 0, tzinfo=UTC).timestamp() * 1000)
    assert dict(parse_qsl(urlsplit(str(sent["url"])).query))["_dc"] == str(now_ms)

    world.http.answer(200, json.dumps({"data": [{"code": "ZWOYBN"}]}))
    answers = await world.run_lookups.execute(
        CTX, plan=Plan(question="q", lookups=(_asked_for("ZWOYBN"),))
    )
    assert what_was_found(answers).startswith("Yes")


async def test_a_key_found_in_a_narrowed_read_is_still_a_yes() -> None:
    world = await lookup_world(_gesture(_call(path=GRID, query=SEARCHED)))
    world.http.answer(200, json.dumps({"data": [{"code": "ZWOYBN"}]}))

    answers = await world.run_lookups.execute(
        CTX, plan=Plan(question="q", lookups=(_asked_for("ZWOYBN"),))
    )

    assert what_was_found(answers).startswith("Yes")


def test_a_screen_waits_for_the_reads_any_gesture_on_its_route_made() -> None:
    """Review 1 #3: the newest gesture on the route was a click that made no GET."""
    address = address_for(
        SCREEN,
        [
            _gesture(_call(), at=100.0, url=SCREEN_URL),
            _gesture(at=900.0, url=SCREEN_URL),
        ],
        T0,
    )

    assert address is not None and address.reads == (SUPPLIERS,)


async def test_the_paint_wait_is_clamped_to_what_is_left_of_the_turn() -> None:
    """Review 1 #2: K_PAINT_S (8 s) inside the chat's 10 s; a read that never recurs
    cost the whole lookup its photograph. It may cost no more than the budget has left."""
    world = await lookup_world(_gesture(_call(), url=SCREEN_URL))
    asked: list[float] = []
    wait = world.driver.wait_for_call

    async def noted(*args: Any, **kwargs: Any) -> Any:
        asked.append(kwargs["deadline_s"])
        return await wait(*args, **kwargs)

    world.driver.wait_for_call = noted  # type: ignore[method-assign]

    answers = await world.run_lookups.execute(
        CTX, plan=Plan(question="q", lookups=(SCREEN,)), within=3.0
    )

    assert answers.looked[0].ok and asked
    assert max(asked) <= 3.0 - K_AFTER_HEADERS_S


async def test_several_lookups_in_one_plan_share_one_turn_budget() -> None:
    """R-L5. The first read used up the turn; the second may not get a turn of its own."""
    world = await lookup_world(_gesture(_call(), url=SCREEN_URL))
    world.driver.http = _Silent()

    answers = await world.run_lookups.execute(
        CTX, plan=Plan(question="q", lookups=(CALL, SCREEN)), within=0.05
    )

    assert [one.detail.startswith("timed out") for one in answers.looked] == [True, True]
    assert world.driver.tabs == {}


async def test_a_refusal_after_signing_in_again_is_the_system_s_answer_not_a_sign_in_page() -> None:
    """Review 1 #6: a 403 for want of permission is not 'still a sign-in page'."""
    world = await lookup_world(_gesture(_call()))
    world.http.answer(403, "")
    world.http.answer(403, "")

    answers = await world.run_lookups.execute(CTX, plan=Plan(question="q", lookups=(CALL,)))

    assert world.reauths == 1 and not answers.looked[0].ok
    assert answers.looked[0].detail == "the system answered 403"


async def test_a_read_the_browser_could_not_complete_signs_in_again_once() -> None:
    """Review 1 #7: an expired session redirects across origins; the page's fetch is
    refused rather than redirected, and arrives as status 0, not as a 3xx."""
    world = await lookup_world(_gesture(_call()))
    world.http.answer(0, "")
    world.http.answer(200, '{"data": [{"name": "a"}]}')

    answers = await world.run_lookups.execute(CTX, plan=Plan(question="q", lookups=(CALL,)))

    assert world.reauths == 1 and answers.looked[0].ok
