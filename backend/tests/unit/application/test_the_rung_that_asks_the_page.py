"""Rung 1 of the ladder, asked directly.

A click's own reply says "I found the control and clicked it" and nothing
about what the server answered, so before this existed a UI step could never
reach the verifier's first rung: every step of every run this deployment had
performed was judged `screen` -- a screenshot, an upload and a vision call,
per step -- 67 times out of 67, the slowest and weakest rung there is.

So the browser is asked what its own driven tab called, and the step's
demonstrated endpoint answering 200 settles it with no picture taken.

The runner's suite reaches this through a whole run, where what it asserts is
the run's outcome. That leaves the discriminating branches unheld: a mutation
sweep found twenty-three survivors here and no test that called it. Those
branches are the difference between a status that settles a step and a
telemetry beacon that happens to be a 200 on the same host -- which is exactly
the mistake `expected_statuses` was taught by the same beacons.
"""

from __future__ import annotations

import pytest

from sro.application.execution.verify import by_what_the_page_called
from sro.application.ports.channel import Reply
from sro.domain.observation.gesture import Action, Call, Gesture
from sro.domain.shared.identifiers import DeviceId, TenantId
from sro.domain.skill.workflow import Step
from tests.unit.fakes import FakeChannel

TENANT, DEVICE, RUN = TenantId("acme"), DeviceId("dev-1"), "run_1"
ENDPOINT = "https://wms.acme.test/api/equipmentTypes"


def _gesture(*, method: str = "POST", url: str = ENDPOINT, status: int = 201) -> Gesture:
    """A demonstrated write: the call the operator's own click produced."""
    return Gesture(
        id="ges-1",
        tenant="acme",
        stream_id="str-1",
        batch_id="bat-1",
        at=1.0,
        url="https://wms.acme.test/equipment",
        system="https://wms.acme.test",
        tab_id=1,
        frame_url=None,
        action=Action(kind="click", at=1.0),
        requests=[Call(method=method, url=url, status=status)],
    )


def _answered(calls: object) -> FakeChannel:
    return FakeChannel({"calls.since": [Reply(ok=True, result={"calls": calls})]})


async def _asked(channel: FakeChannel, gesture: Gesture | None = None) -> object:
    return await by_what_the_page_called(
        step=Step(order=1, says="create an equipment type", system=None, cites=["ges-1"]),
        cited=[gesture or _gesture()],
        since=1.0,
        channel=channel,
        tenant_id=TENANT,
        device_id=DEVICE,
        run_id=RUN,
    )


# -- when it settles the step --------------------------------------------------


async def test_the_demonstrated_endpoint_answering_as_it_did_holds_the_step() -> None:
    verdict = await _asked(_answered([{"method": "POST", "url": ENDPOINT, "status": 201}]))

    assert verdict is not None
    assert (verdict.state, verdict.by) == ("held", "status")


async def test_an_id_in_the_path_is_not_a_mismatch() -> None:
    """Matched by path SHAPE. This run's call carries a different id from the
    one the demonstration made, and a matcher comparing urls would send every
    such step to the screen. An id is a segment of digits -- `_looks_like_an_id`
    deliberately does not star `order-status`, which is a route word."""
    verdict = await _asked(
        _answered([{"method": "POST", "url": f"{ENDPOINT}/9001", "status": 201}]),
        gesture=_gesture(url=f"{ENDPOINT}/1183"),
    )

    assert verdict is not None
    assert verdict.state == "held"


async def test_the_server_refusing_fails_the_step_on_its_status_not_on_a_picture() -> None:
    verdict = await _asked(_answered([{"method": "POST", "url": ENDPOINT, "status": 409}]))

    assert verdict is not None
    assert verdict.state == "failed"
    assert "409" in verdict.reason


async def test_the_last_call_is_the_one_that_answers() -> None:
    """Read newest first. A retried write leaves both attempts in the tab's
    log, and the step was settled by the one that finished it."""
    verdict = await _asked(
        _answered(
            [
                {"method": "POST", "url": ENDPOINT, "status": 500},
                {"method": "POST", "url": ENDPOINT, "status": 201},
            ]
        )
    )

    assert verdict is not None
    assert verdict.state == "held", "the earlier failure decided a step the retry completed"


# -- when it declines to decide ------------------------------------------------


@pytest.mark.parametrize(
    ("calls", "why"),
    [
        ([], "the tab called nothing at all"),
        ([{"method": "GET", "url": ENDPOINT, "status": 200}], "a different method"),
        (
            [{"method": "POST", "url": "https://wms.acme.test/api/telemetry", "status": 200}],
            "a beacon on the same host, which is what taught this rule",
        ),
        ([{"method": "POST", "url": ENDPOINT}], "a call with no status"),
        ([{"method": "POST", "url": ENDPOINT, "status": "201"}], "a status that is not a number"),
        (["not a call at all"], "an entry that is not an object"),
        ("not a list", "a result whose calls are not a list"),
        (None, "a result with no calls in it"),
    ],
)
async def test_what_it_cannot_recognise_is_looked_at_instead_of_decided(
    calls: object, why: str
) -> None:
    """None is not "the step failed". It is the absence of evidence, and the
    ladder goes on to the read and the screen -- which is the whole reason
    this rung may be strict without being dangerous."""
    assert await _asked(_answered(calls)) is None, why


async def test_a_status_the_demonstration_never_saw_is_left_to_the_ladder() -> None:
    """Not a failure and not a hold. The endpoint answered something this
    workflow has no opinion about, and guessing either way is worse than
    looking."""
    verdict = await _asked(
        _answered([{"method": "POST", "url": ENDPOINT, "status": 302}]),
        gesture=_gesture(status=201),
    )

    assert verdict is None


async def test_a_browser_that_cannot_answer_is_not_evidence_of_anything() -> None:
    channel = FakeChannel({"calls.since": [Reply(ok=False, error_kind="not_actionable")]})

    assert await _asked(channel) is None


async def test_a_step_that_writes_nothing_has_no_status_to_be_held_by() -> None:
    """A read has no write to be settled by, and 2xx on a page's keep-alive is
    not a step being done."""
    verdict = await _asked(
        _answered([{"method": "GET", "url": ENDPOINT, "status": 200}]),
        gesture=_gesture(method="GET", status=200),
    )

    assert verdict is None


# -- the shapes that tell skipping apart from stopping -------------------------
#
# A list of one cannot: with a single entry, "skip this and keep looking" and
# "give up here" reach the same answer, and a sweep found every `continue` in
# the loop surviving because nothing put a call it had to walk PAST in front of
# one it had to find. A real tab's log is never one call.


async def test_it_walks_past_what_it_does_not_recognise_to_reach_what_it_does() -> None:
    """Newest first, so the beacon is the one it meets before the write.

    If the loop stopped at the first entry that did not match instead of
    skipping it, this step would be sent to the screen -- which is what
    happened to every step of every run before this rung existed.
    """
    verdict = await _asked(
        _answered(
            [
                {"method": "POST", "url": ENDPOINT, "status": 201},
                {"method": "GET", "url": ENDPOINT, "status": 200},
                "not a call at all",
                {"method": "POST", "url": "https://wms.acme.test/api/telemetry", "status": 200},
                {"method": "POST", "url": ENDPOINT, "status": None},
            ]
        )
    )

    assert verdict is not None, "it stopped at the first thing it could not use"
    assert verdict.state == "held"


async def test_a_call_that_names_no_method_is_skipped_rather_than_matched() -> None:
    """`call.get("method", "")` defaults to empty on purpose. Defaulting to
    `None` would compare the string "NONE", which matches nothing -- until the
    day a step's method is literally that, and until then it hides the fact
    that nothing ever sent a call without one."""
    verdict = await _asked(
        _answered(
            [
                {"method": "POST", "url": ENDPOINT, "status": 201},
                {"url": ENDPOINT, "status": 500},
            ]
        )
    )

    assert verdict is not None
    assert verdict.state == "held", "a call with no method decided the step"


async def test_a_call_that_names_no_url_is_skipped_rather_than_matched() -> None:
    verdict = await _asked(
        _answered(
            [
                {"method": "POST", "url": ENDPOINT, "status": 201},
                {"method": "POST", "status": 500},
            ]
        )
    )

    assert verdict is not None
    assert verdict.state == "held"


# -- what goes out on the wire -------------------------------------------------


async def test_the_browser_is_asked_for_calls_since_the_command_went_out() -> None:
    """The envelope, not just the answer. `since` is the extension's own
    counter and the key it reads; renamed, the browser answers with everything
    it has ever seen and this rung starts settling steps on somebody else's
    call. Nothing checked the key until a sweep pointed out that renaming it
    changed no test at all.
    """
    channel = _answered([{"method": "POST", "url": ENDPOINT, "status": 201}])

    await _asked(channel)

    asked = [one for one in channel.sent if one["kind"] == "calls.since"]
    assert len(asked) == 1
    assert asked[0]["payload"] == {"since": 1.0}
    assert asked[0]["run_id"] == RUN
