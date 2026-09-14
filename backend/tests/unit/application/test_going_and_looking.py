"""Executing a plan: where a lookup goes, and what it does when a system is shut.

Two things are held here. The ADDRESS -- a plan names a knowledge key and a
browser needs a url, and the only honest bridge is a place this deployment has
already been. And the RUN -- a GET in the operator's session, or a page put up
and photographed, with one system's failure kept as one system's failure.
"""

from __future__ import annotations

import pytest

from sro.application.context import RequestContext
from sro.application.lookup.run_lookups import RunLookups
from sro.application.ports.channel import Reply
from sro.domain.lookup.address import address_for
from sro.domain.lookup.plan import Lookup, Plan
from sro.domain.observation.gesture import Action, Call, Gesture
from sro.domain.shared.hosts import REDACTED
from tests import factories as f
from tests.unit.fakes import FakeChannel, FakeUnitOfWork

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


async def test_a_call_goes_out_as_a_get_in_the_operators_own_session() -> None:
    channel = FakeChannel({"http.send": [Reply(ok=True, result={"status": 200, "rows": 5})]})
    uow = FakeUnitOfWork()
    await uow.gestures.add_gestures((_gesture(_call(headers={"X-Requested-With": REDACTED})),))

    answers = await RunLookups(uow, channel).execute(CTX, plan=Plan(question="q", lookups=(CALL,)))

    (sent,) = channel.sent
    assert sent["kind"] == "http.send"
    assert sent["payload"]["method"] == "GET"
    assert sent["payload"]["live_headers"] == ["X-Requested-With"]
    assert answers.any_answered and answers.looked[0].answer["rows"] == 5


async def test_a_screen_is_put_up_and_then_photographed() -> None:
    channel = FakeChannel(
        {
            "navigate": [Reply(ok=True, result={"navigated": True})],
            "screenshot": [Reply(ok=True, result={"image_base64": "iVBOR", "width": 1280})],
        }
    )
    uow = FakeUnitOfWork()
    await uow.gestures.add_gestures((_gesture(url=SCREEN_URL),))

    answers = await RunLookups(uow, channel).execute(
        CTX, plan=Plan(question="q", lookups=(SCREEN,)), allow_focus=True
    )

    assert [one["kind"] for one in channel.sent] == ["navigate", "screenshot"]
    assert channel.sent[0]["payload"]["url"] == SCREEN_URL
    assert channel.sent[0]["payload"]["origin"] == "https://bf56-kms-wms-web-np2.jdadelivers.com"
    assert answers.looked[0].ok


async def test_a_system_nobody_has_open_is_opened_and_asked_again() -> None:
    """The whole point of the fallback: without it a question is answerable
    only by the systems the operator happens to have in front of them."""
    channel = FakeChannel(
        {
            "http.send": [
                Reply(ok=False, error_kind="no_tab_for_origin", error_detail="no tab"),
                Reply(ok=True, result={"rows": 5}),
            ],
            "tab.open": [Reply(ok=True, result={"opened": True, "tab_id": 42})],
        }
    )
    uow = FakeUnitOfWork()
    await uow.gestures.add_gestures((_gesture(_call()),))

    answers = await RunLookups(uow, channel).execute(CTX, plan=Plan(question="q", lookups=(CALL,)))

    assert [one["kind"] for one in channel.sent] == ["http.send", "tab.open", "http.send"]
    assert str(channel.sent[1]["payload"]["url"]).startswith(f"{WMS}{SUPPLIERS}")
    assert answers.looked[0].ok


async def test_a_system_that_is_open_and_still_will_not_answer_is_not_retried() -> None:
    # A second attempt costs the same time twice and changes nothing: another
    # tab does not fix a page that would not answer.
    channel = FakeChannel(
        {
            "http.send": [
                Reply(ok=False, error_kind="unreachable", error_detail="the page did not answer")
            ]
        }
    )
    uow = FakeUnitOfWork()
    await uow.gestures.add_gestures((_gesture(_call()),))

    answers = await RunLookups(uow, channel).execute(CTX, plan=Plan(question="q", lookups=(CALL,)))

    assert [one["kind"] for one in channel.sent] == ["http.send"]
    assert answers.looked[0].detail == "unreachable: the page did not answer"


async def test_a_screen_on_a_shut_system_is_opened_before_it_is_given_up_on() -> None:
    channel = FakeChannel(
        {
            "navigate": [
                Reply(ok=False, error_kind="no_tab_for_system", error_detail="no page"),
                Reply(ok=True, result={"navigated": True}),
            ],
            "tab.open": [Reply(ok=True, result={"opened": True, "tab_id": 42})],
            "screenshot": [Reply(ok=True, result={"image_base64": "iVBOR"})],
        }
    )
    uow = FakeUnitOfWork()
    await uow.gestures.add_gestures((_gesture(url=SCREEN_URL),))

    answers = await RunLookups(uow, channel).execute(
        CTX, plan=Plan(question="q", lookups=(SCREEN,))
    )

    assert [one["kind"] for one in channel.sent] == [
        "navigate",
        "tab.open",
        "navigate",
        "screenshot",
    ]
    assert answers.looked[0].ok


async def test_a_page_that_would_not_come_up_is_not_photographed() -> None:
    # The picture would be of whatever was there before, and reading it would
    # be answering the question with a different screen.
    channel = FakeChannel(
        {
            "navigate": [Reply(ok=False, error_kind="no_tab_for_system", error_detail="no page")],
            "tab.open": [
                Reply(ok=False, error_kind="not_actionable", error_detail="not an http url")
            ],
        }
    )
    uow = FakeUnitOfWork()
    await uow.gestures.add_gestures((_gesture(url=SCREEN_URL),))

    answers = await RunLookups(uow, channel).execute(
        CTX, plan=Plan(question="q", lookups=(SCREEN,))
    )

    assert [one["kind"] for one in channel.sent] == ["navigate", "tab.open"]
    assert answers.looked[0].detail == "not_actionable: not an http url"


async def test_one_shut_system_is_one_named_gap_and_not_a_failed_question() -> None:
    """The opposite reading from the planner's, deliberately. A target nobody
    has seen means the PLAN is wrong about the world; a system with no tab open
    means that system was shut, and three answers with a named gap are worth
    more than nothing."""
    channel = FakeChannel({"http.send": [Reply(ok=True, result={"rows": 5})]})
    uow = FakeUnitOfWork()
    await uow.gestures.add_gestures((_gesture(_call()),))
    elsewhere = Lookup(system="mail", how="call", target="/gmail/v1/threads", cites=("x",))

    answers = await RunLookups(uow, channel).execute(
        CTX, plan=Plan(question="q", lookups=(CALL, elsewhere))
    )

    answered, missing = answers.looked
    assert answered.ok
    assert not missing.ok
    assert missing.detail == "nothing here has been to /gmail/v1/threads"
    assert answers.any_answered


async def test_no_browser_connected_refuses_every_lookup_by_name() -> None:
    class _Nobody(FakeChannel):
        def online(self, tenant_id: object) -> tuple[()]:
            return ()

    answers = await RunLookups(FakeUnitOfWork(), _Nobody()).execute(
        CTX, plan=Plan(question="q", lookups=(CALL,))
    )

    assert not answers.any_answered
    assert answers.looked[0].detail == "no browser is connected"


async def test_a_plan_that_asks_instead_of_answering_sends_nothing() -> None:
    channel = FakeChannel()

    answers = await RunLookups(FakeUnitOfWork(), channel).execute(CTX, plan=Plan(question="q"))

    assert channel.sent == [] and answers.looked == ()
