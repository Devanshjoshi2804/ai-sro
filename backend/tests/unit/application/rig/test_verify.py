"""Did one step of a mined job actually happen -- status, then a read, then a picture.

Ported from `new_agent_arch/tests/test_verify.py` -- every test there that puts
a question to a wire or to a model. The six that ask only the pure belts are in
`tests/unit/domain/rig/test_belts.py`, which plan 1 brought across with
`expected_statuses`, `confirming_read` and `mentions`.

Eight guards here are new, and every one was found by mutating an argument at
the call site rather than the rule it feeds. Nothing in the rig's suite asserted
that `sent_kind` gates the status belt at all (its own answers never carried a
status unless the step was an `http.send`, so a verifier that ignored the
argument stayed green); that the named model, the verdict schema, the
instructions' own words and the status the browser came back with reach the
asker; that a step with no values never spends a round trip on a probe; that the
screen's own words reach the prompt unescaped; or that the probe never names an
origin -- which is a decision the rig recorded in a comment and nothing held it
to. The tenant the probe goes out on is guarded too, and is not the rig's at
all: its channel had no tenant.

Two of the eight are the belt order itself, and both hide the same way: EVERY
test in which an earlier belt decides handed the verifier
`Look(None, None, "")`, so an `asker.asked == []` beside such a test is vacuous
-- the model was never going to be asked, order or no order. Read-over-screen
and status-over-screen each get a test that puts a real picture on the table
first. Status-over-screen is the expensive one: `status` is a `state_verified`
belt and `screen` is not, so promoting a screen verdict over a status verdict
would let a model reading a picture decide what a job earns the right to write
unasked.
"""

import copy
import json
from collections.abc import Mapping
from dataclasses import replace

from sro.application.execution.verify import verify
from sro.application.ports.channel import Reply
from sro.domain.execution.belts import SCREEN_INSTRUCTIONS, SCREEN_SCHEMA, StepVerdict
from sro.domain.execution.planning import Look
from sro.domain.observation.gesture import Gesture
from sro.domain.shared.hosts import REDACTED
from sro.domain.shared.identifiers import DeviceId, TenantId
from sro.domain.shared.prices import Answer
from sro.domain.skill.workflow import Step
from tests.unit.domain.rig.conftest import gestures as _gestures
from tests.unit.fakes import FakeAsker, FakeChannel

_TENANT = TenantId("caller")
_DEVICE = DeviceId("dev_test")
_STREAM = "http://127.0.0.1:63319/api/stream"


def _saver() -> Gesture:
    return next(g for g in _gestures() if g.requests)


def _step(gesture: Gesture) -> Step:
    return Step(order=0, says="save", system=None, cites=[gesture.id])


def _read(body: str, status: int = 200) -> FakeChannel:
    return FakeChannel({"http.send": [Reply(ok=True, result={"status": status, "body": body})]})


def _payload(channel: FakeChannel) -> Mapping[str, object]:
    payload = channel.sent[0]["payload"]
    assert isinstance(payload, dict)
    return payload


async def _verify(
    saver: Gesture,
    *,
    channel: FakeChannel,
    values: Mapping[str, str],
    sent_kind: str = "ui.perform",
    answer: Reply | None = None,
    asker: FakeAsker | None = None,
    look_before: Look | None = None,
    look_after: Look | None = None,
    origin: str | None = "http://127.0.0.1:63319",
    model: str = "m",
    rewrote: bool = False,
    confirm: Mapping[str, str] | None = None,
) -> StepVerdict:
    """One step verified. The helper is the rig's own `_verified`, widened so
    the tests that varied a look, an asker or a model do not have to spell the
    other thirteen arguments."""
    return await verify(
        step=_step(saver),
        sent_kind=sent_kind,
        answer=answer or Reply(ok=True, result={"performed": True}),
        cited=[saver],
        values=values,
        look_before=look_before or Look(None, None, ""),
        look_after=look_after or Look(None, None, ""),
        channel=channel,
        tenant_id=_TENANT,
        device_id=_DEVICE,
        rewrote=rewrote,
        # What a re-aimed write is checked against: the slot the plan put each
        # value in. `WritePlan.confirm` is where a run gets it; the tests that
        # re-aim by hand say it by hand, because `rewrote` with nothing to
        # confirm now means "there is no read that could settle this".
        confirm=confirm or {},
        run_id="run_1",
        origin=origin,
        asker=asker or FakeAsker(),
        model=model,
    )


async def test_a_call_that_returned_the_status_the_evidence_expects_is_held_by_status() -> None:
    saver = _saver()
    post = next(r for r in saver.requests if r.method == "POST")
    saver.requests[saver.requests.index(post)] = replace(post, status=201)
    asker = FakeAsker()

    verdict = await _verify(
        saver,
        channel=FakeChannel(),
        values={},
        sent_kind="http.send",
        answer=Reply(ok=True, result={"status": 201, "body": "{}"}),
        asker=asker,
        origin=None,
    )

    assert (verdict.state, verdict.by) == ("held", "status")
    assert asker.asked == [], "no model was asked when the state already said"


async def test_a_call_the_warehouse_rejected_is_failed_by_status() -> None:
    verdict = await _verify(
        _saver(),
        channel=FakeChannel(),
        values={},
        sent_kind="http.send",
        answer=Reply(ok=True, result={"status": 422, "body": "no"}),
        origin=None,
    )
    assert (verdict.state, verdict.by) == ("failed", "status") and "422" in verdict.reason


async def test_a_ui_step_is_confirmed_by_the_read_the_evidence_shows_the_page_makes() -> None:
    """Hidden state before visible state: the read comes back with the value
    the run supplied, and no screenshot is looked at.

    The probe is the first read after the write that CAME BACK. The capture
    has a GET to a dead host one millisecond after the POST; asking it again
    would prove nothing, so it is not the one chosen.
    """
    channel = _read('{"workArea":"THIRD"}')

    verdict = await _verify(_saver(), channel=channel, values={"workArea": "THIRD"})

    assert (verdict.state, verdict.by) == ("held", "read")
    asked = _payload(channel)["url"]
    assert asked == _STREAM
    assert asked != "http://127.0.0.1:1/never", "a read that never completed is not a confirmation"


async def test_a_read_that_did_not_come_back_2xx_decides_nothing() -> None:
    """A 503 answers ok=True with a body that matches nothing, and marking a
    correct write failed on that is worse than not deciding."""
    verdict = await _verify(
        _saver(), channel=_read("service unavailable", status=503), values={"workArea": "THIRD"}
    )
    assert verdict.by != "read"

    # The other half of the same rule, which the rig never scripted: a reply
    # the extension refused still carries whatever `result` it chose to put
    # there -- `infrastructure/agent/channel.py` passes that dict through
    # regardless of `ok` -- so a timed-out probe can arrive with a 200 and a
    # matching body. Not a read that came back.
    refused = FakeChannel(
        {
            "http.send": [
                Reply(
                    ok=False,
                    error_kind="timeout",
                    result={"status": 200, "body": '{"workArea":"THIRD"}'},
                )
            ]
        }
    )
    assert (await _verify(_saver(), channel=refused, values={"workArea": "THIRD"})).by != "read"


async def test_the_read_matches_a_whole_value_not_a_substring_of_one() -> None:
    inside = await _verify(
        _saver(), channel=_read('{"orders":[{"id":"ORD-1"}]}'), values={"n": "1"}
    )
    assert (inside.state, inside.by) == ("failed", "read"), "ORD-1 is not the value 1"

    whole = await _verify(
        _saver(), channel=_read('{"code":"THIRD"}'), values={"clientCode": "THIRD"}
    )
    assert (whole.state, whole.by) == ("held", "read")


async def test_the_probe_never_carries_a_header_the_boundary_struck_out() -> None:
    saver = _saver()
    stream = next(r for r in saver.requests if r.url == _STREAM)
    saver.requests[saver.requests.index(stream)] = replace(
        stream, request_headers={"X-CSRF": REDACTED, "Accept": "application/json"}
    )
    channel = _read('{"workArea":"THIRD"}')

    await _verify(saver, channel=channel, values={"workArea": "THIRD"})

    assert _payload(channel)["headers"] == {"Accept": "application/json"}


async def test_a_status_that_already_decided_is_not_second_guessed_by_a_read() -> None:
    """Belt order, not belt availability: the read would have confirmed too,
    and it is never sent.

    True of bytes replayed VERBATIM, which is what this asserts. The endpoint
    answered the demonstration the same way, so its answer means the
    demonstrated effect. A body this run RE-AIMED does not get this -- see
    `test_a_body_this_run_re_aimed_is_not_held_on_its_status_alone`.
    """
    channel = _read('{"workArea":"THIRD"}')

    verdict = await _verify(
        _saver(),
        channel=channel,
        values={"workArea": "THIRD"},
        sent_kind="http.send",
        answer=Reply(ok=True, result={"status": 200, "body": "{}"}),
    )

    assert (verdict.state, verdict.by) == ("held", "status")
    assert channel.sent == [], "the state already said; nothing else was asked"


async def test_a_status_the_operator_also_got_is_still_a_refusal() -> None:
    """A demonstration that recorded a 409 does not make 409 mean success."""
    saver = _saver()
    post = next(r for r in saver.requests if r.method == "POST")
    saver.requests[saver.requests.index(post)] = replace(post, status=409)

    verdict = await _verify(
        saver,
        channel=FakeChannel(),
        values={},
        sent_kind="http.send",
        answer=Reply(ok=True, result={"status": 409, "body": "conflict"}),
    )
    assert (verdict.state, verdict.by) == ("failed", "status")


async def test_the_screenshot_is_last_and_least() -> None:
    saver = _saver()
    saver.requests = []  # nothing to read, nothing to confirm by
    asker = FakeAsker(
        Answer(data={"held": True, "why": "the form shows the saved record"}, cost_usd=0.0002)
    )

    verdict = await _verify(
        saver,
        channel=FakeChannel(),
        values={},
        asker=asker,
        look_before=Look("u", b"before", "Save"),
        look_after=Look("u", b"after", "Saved"),
        origin=None,
    )

    assert (verdict.state, verdict.by) == ("held", "screen")
    assert asker.asked[0]["image"] == b"after"
    # Nothing else off the browser's answer: for an http.send that dict is the
    # response body and headers, and no trim rule stands between it and here.
    evidence = asker.asked[0]["evidence"]
    assert isinstance(evidence, str)
    shown = json.loads(evidence)
    assert shown["browser_answered"] == {"ok": True, "status": None}
    assert verdict.answer is not None and verdict.answer.cost_usd == 0.0002


async def test_no_screenshot_and_no_state_is_unclear_not_held() -> None:
    saver = _saver()
    saver.requests = []
    verdict = await _verify(saver, channel=FakeChannel(), values={}, origin=None)
    assert verdict.state == "unclear" and verdict.by == "none"


async def test_a_command_the_browser_refused_is_failed_before_anything_is_verified() -> None:
    verdict = await _verify(
        _saver(),
        channel=FakeChannel(),
        values={},
        answer=Reply(ok=False, error_kind="control_not_found", error_detail="no visible match"),
        origin=None,
    )
    assert verdict.state == "failed" and verdict.reason == "control_not_found: no visible match"
    assert verdict.by == "none", "nothing looked at anything; the browser refused"


async def test_a_confirming_read_whose_url_carries_a_marker_is_never_sent() -> None:
    saver = _saver()
    stream = next(r for r in saver.requests if r.url == _STREAM)
    saver.requests[saver.requests.index(stream)] = replace(
        stream, url=f"{stream.url}?token={REDACTED}"
    )
    channel = _read('{"code": "THIRD"}')

    verdict = await _verify(saver, channel=channel, values={"clientCode": "THIRD"})

    assert channel.sent == [], "a probe carrying the marker asks nothing about the state"
    assert verdict.by != "read"


async def test_the_call_that_returned_exactly_400_is_a_refusal_not_a_success() -> None:
    """The boundary itself: 400 is the first status that is a refusal, and a
    run that read it as anything else would go on to the next step."""
    verdict = await _verify(
        _saver(),
        channel=FakeChannel(),
        values={},
        sent_kind="http.send",
        answer=Reply(ok=True, result={"status": 400, "body": "bad request"}),
    )
    assert (verdict.state, verdict.by) == ("failed", "status")


async def test_a_2xx_the_evidence_never_saw_does_not_hold_by_status() -> None:
    """The evidence recorded a 201. A 200 is not that, so the status belt has
    nothing to say and the run falls through to the belts that look."""
    saver = _saver()
    post = next(r for r in saver.requests if r.method == "POST")
    saver.requests = [replace(post, status=201)]

    verdict = await _verify(
        saver,
        channel=FakeChannel(),
        values={},
        sent_kind="http.send",
        answer=Reply(ok=True, result={"status": 200, "body": "{}"}),
    )
    assert verdict.by != "status"


async def test_with_no_status_in_the_evidence_only_a_2xx_holds() -> None:
    """Nothing recorded, so 2xx and only 2xx is success. 300 is a redirect
    nobody followed, not a record that was written."""
    for status, held in ((200, True), (299, True), (300, False)):
        saver = _saver()
        saver.requests = []
        verdict = await _verify(
            saver,
            channel=FakeChannel(),
            values={},
            sent_kind="http.send",
            answer=Reply(ok=True, result={"status": status, "body": "{}"}),
        )
        assert ((verdict.state, verdict.by) == ("held", "status")) is held, status


async def test_the_probe_is_a_bodiless_get_sent_to_this_run_and_this_browser() -> None:
    channel = _read('{"workArea":"THIRD"}')

    verdict = await _verify(_saver(), channel=channel, values={"workArea": "THIRD"})

    [sent] = channel.sent
    assert sent["device_id"] == "dev_test" and sent["run_id"] == "run_1"
    # The tenant too, which the rig's channel did not have: this one dials a
    # socket per tenant, and a probe on the wrong one asks a browser that is
    # not the caller's. `_TENANT` is deliberately not "acme" -- the correlated
    # evidence carries that one, so dialling `cited[0].tenant` instead of the
    # caller's tenant is a plausible slip that this assertion could not have
    # told apart while the two strings were the same.
    assert sent["tenant_id"] == "caller"
    assert _payload(channel)["method"] == "GET" and _payload(channel)["body"] is None
    assert _STREAM in verdict.reason, "the record says what was read"


async def test_a_read_that_did_not_show_the_value_says_which_read_it_was() -> None:
    verdict = await _verify(
        _saver(), channel=_read('{"workArea":"FIRST"}'), values={"workArea": "THIRD"}
    )
    assert (verdict.state, verdict.by) == ("failed", "read")
    assert _STREAM in verdict.reason


async def test_a_read_that_came_back_300_is_not_a_read_that_came_back() -> None:
    verdict = await _verify(
        _saver(), channel=_read('{"workArea":"THIRD"}', status=300), values={"workArea": "THIRD"}
    )
    assert verdict.by != "read"


async def test_a_value_nested_inside_the_read_is_still_a_value_the_read_shows() -> None:
    """Leaves, at any depth: the confirming read of a created record answers
    the record, not a flat dictionary of it."""
    verdict = await _verify(
        _saver(),
        channel=_read('{"data":{"order":{"workArea":"THIRD"}}}'),
        values={"workArea": "THIRD"},
    )
    assert (verdict.state, verdict.by) == ("held", "read")


async def test_a_read_that_is_not_json_is_matched_on_its_text() -> None:
    held = await _verify(
        _saver(), channel=_read("<p>work area THIRD saved</p>"), values={"workArea": "THIRD"}
    )
    assert (held.state, held.by) == ("held", "read")

    missing = await _verify(
        _saver(), channel=_read("<p>nothing here</p>"), values={"workArea": "THIRD"}
    )
    assert (missing.state, missing.by) == ("failed", "read")


async def test_nothing_to_decide_on_is_unclear_and_says_so() -> None:
    saver = _saver()
    saver.requests = []
    verdict = await _verify(saver, channel=FakeChannel(), values={})
    assert (verdict.state, verdict.by) == ("unclear", "none")
    assert verdict.reason, "a verdict nobody can read is not a record"

    # And where the browser said WHY there was no screen, that is the record.
    # A step that types a value has no status and nothing to read back, so the
    # screen is its only belt: measured on the deployment, 2026-09-17 at 17:05,
    # a value that WAS typed (`ok: true, matched_by: component`) was collapsed
    # on four words that named none of the three faults that produce them.
    saver = _saver()
    saver.requests = []
    said = await _verify(
        saver,
        channel=FakeChannel(),
        values={},
        look_after=Look(None, None, "", refused="focus_not_permitted: not the visible one"),
    )
    assert said.reason.endswith("focus_not_permitted: not the visible one"), said.reason


async def test_a_model_that_answered_nothing_leaves_the_step_unclear_with_its_error() -> None:
    saver = _saver()
    saver.requests = []
    judged = Answer(data=None, error="the model returned no candidates", cost_usd=0.0001)
    asker = FakeAsker(judged)

    verdict = await _verify(
        saver,
        channel=FakeChannel(),
        values={},
        asker=asker,
        look_before=Look(None, None, ""),
        look_after=Look("u", b"after", "Saved"),
        origin=None,
    )

    assert (verdict.state, verdict.by) == ("unclear", "screen")
    assert verdict.reason == "the model returned no candidates"
    assert verdict.answer is judged, "the verdict carries what the reading cost"
    assert asker.asked[0]["instructions"], "a model told nothing judges nothing"


async def test_the_screen_verdict_is_the_models_own_word_and_its_own_reason() -> None:
    saver = _saver()
    saver.requests = []

    async def _screened(data: dict[str, object]) -> StepVerdict:
        return await _verify(
            saver,
            channel=FakeChannel(),
            values={},
            asker=FakeAsker(Answer(data=data)),
            look_before=Look("u", b"before", "Save"),
            look_after=Look("u", b"after", "Saved"),
            origin=None,
        )

    refused = await _screened({"held": False, "why": "the form still shows the old code"})
    assert (refused.state, refused.by) == ("failed", "screen")
    # The model's account of the screen, and the screen's own words beside it.
    # Measured on the deployment, 2026-09-17 at 23:05: a Save refused with "An
    # exception dialog appeared" -- true, and a paraphrase. Whether that dialog
    # said a field was too long, a session had expired or a code was taken is
    # the whole question, and the run kept one sentence of prose about it.
    assert refused.reason.startswith("the form still shows the old code")
    assert "the screen said: Saved" in refused.reason, refused.reason

    held = await _screened({"held": True, "why": "the saved record is on screen"})
    assert (held.state, held.by) == ("held", "screen")
    assert held.reason == "the saved record is on screen"

    silent = await _screened({"held": True})
    assert silent.reason == "", "no explanation is an empty one, not the word None"


async def test_the_screen_belt_is_told_the_step_the_command_and_both_pictures_words() -> None:
    asker = FakeAsker(Answer(data={"held": True, "why": "the row is there"}))
    verdict = await _verify(
        _saver(),
        channel=FakeChannel(),
        values={"clientCode": "THIRD"},
        asker=asker,
        look_before=Look("http://127.0.0.1:63319/form", b"before", "an empty form"),
        look_after=Look("http://127.0.0.1:63319/list", b"after", "THIRD in the list"),
    )
    assert verdict.state == "held" and verdict.by == "screen"
    evidence = asker.asked[0]["evidence"]
    assert isinstance(evidence, str)
    shown = json.loads(evidence)
    # The names the instructions use, and the things they name: not one of
    # them may drift, because the model reads the words.
    assert shown["step"] == {"says": "save"}
    assert shown["sent"] == "ui.perform"
    assert shown["screen_before"] == "an empty form"
    assert shown["screen_after"] == "THIRD in the list"
    assert shown["values"] == {"clientCode": "THIRD"}
    assert set(shown) >= {
        "step",
        "sent",
        "browser_answered",
        "screen_before",
        "screen_after",
        "values",
    }


# The guards the rig's own suite did not have. Each one is an argument, or a
# belt boundary, that a mutation crossed with all 24 ported tests green.


async def test_a_ui_perform_whose_reply_carries_a_status_is_not_decided_by_the_status_belt() -> (
    None
):
    """`sent_kind` is what makes the status belt apply, and it was unguarded:
    every rig test that passed a status also said `http.send`, so a verifier
    that ignored `sent_kind` entirely stayed green on all 24.

    The distinction is real, not hypothetical. `http.send` answers the
    warehouse's status; `ui.perform` answers whether the extension found a
    control, and any status beside it is whatever the page happened to be
    doing -- not the step's outcome. Here the read says the value never
    landed, and a status-first verifier would have called the step held.
    """
    verdict = await _verify(
        _saver(),
        channel=_read('{"workArea":"FIRST"}'),
        values={"workArea": "THIRD"},
        answer=Reply(ok=True, result={"performed": True, "status": 200}),
    )

    assert (verdict.state, verdict.by) == ("failed", "read")


async def test_the_read_decides_before_a_picture_is_ever_looked_at() -> None:
    """Belt order between the two belts the rig never made compete: every one
    of its read tests passed `Look(None, None, "")`, so the screen belt could
    not have decided even if it had been asked first. With a screenshot on the
    table the order shows, and the model is not asked -- because a model
    reading a screenshot is not evidence anything was written.
    """
    asker = FakeAsker(Answer(data={"held": True, "why": "it looks saved to me"}))

    verdict = await _verify(
        _saver(),
        channel=_read('{"workArea":"FIRST"}'),
        values={"workArea": "THIRD"},
        asker=asker,
        look_before=Look("u", b"before", "Save"),
        look_after=Look("u", b"after", "Saved"),
    )

    assert (verdict.state, verdict.by) == ("failed", "read")
    assert asker.asked == [], "the state answered; no picture was read"


async def test_the_probe_names_no_origin_because_the_url_already_does() -> None:
    """`origin` is threaded and deliberately unused: the extension picks the
    probe's tab from the url itself (tabOnOrigin), so an origin in the payload
    would be ignored. The rig recorded that in a comment and nothing held it --
    this fails the day a probe starts carrying one.
    """
    channel = _read('{"workArea":"THIRD"}')

    await _verify(_saver(), channel=channel, values={"workArea": "THIRD"}, origin="http://other")

    assert set(_payload(channel)) == {"method", "url", "headers", "body"}


async def test_the_screen_belt_asks_the_named_model_against_the_verdict_schema() -> None:
    """The run picks which model reads the picture and the schema is what makes
    the answer parseable. Neither was asserted anywhere in the rig's suite, so
    a verifier that hardcoded a model name -- or asked for free text -- passed
    all 24."""
    saver = _saver()
    saver.requests = []
    asker = FakeAsker(Answer(data={"held": True, "why": "the row is there"}))

    await _verify(
        saver,
        channel=FakeChannel(),
        values={},
        asker=asker,
        look_after=Look("u", b"after", "Saved"),
        model="gemini-3.8-flash",
    )

    assert asker.asked[0]["model"] == "gemini-3.8-flash"
    assert asker.asked[0]["schema"] == SCREEN_SCHEMA
    assert asker.asked[0]["image"] == b"after"
    # The words themselves, not just that there were some. This is the only
    # place `SCREEN_INSTRUCTIONS` is ever spoken to a model, and the sentence
    # named here is what makes the weakest belt conservative: without it the
    # cheapest reading of a screenshot -- no error visible, so it worked -- is
    # the one that promotes a step to held.
    assert asker.asked[0]["instructions"] == SCREEN_INSTRUCTIONS
    assert "Do not assume success from the absence of an error." in SCREEN_INSTRUCTIONS


async def test_a_read_with_no_value_to_look_for_is_never_sent() -> None:
    """ "Nothing was found" is not evidence the step failed. With no values
    there is no proposition the read could confirm, so the probe is not worth a
    round trip -- and a verifier that sent it anyway would call every
    parameterless step failed on a body that matched nothing.

    The rig never guarded this: its own no-value steps all had their status
    belt decide first, or no confirming read at all.
    """
    channel = _read('{"workArea":"THIRD"}')

    verdict = await _verify(_saver(), channel=channel, values={})

    assert channel.sent == [], "no value to look for is nothing to ask about"
    assert (verdict.state, verdict.by) == ("unclear", "none")


async def test_the_screen_the_model_is_shown_reaches_it_in_its_own_characters() -> None:
    """`ensure_ascii=False`, and it is not cosmetic.

    A warehouse screen is arbitrary text -- accented, non-Latin, and where the
    boundary struck a credential out, the marker «redacted». The default
    escaping writes those into the prompt as \\u00abredacted\\u00bb and
    \\u00c1rea: a form nothing else in this system uses, and one the model is
    then asked to read as words.
    """
    saver = _saver()
    saver.requests = []
    asker = FakeAsker(Answer(data={"held": True, "why": "the row is there"}))

    await _verify(
        saver,
        channel=FakeChannel(),
        values={"area": "Área"},
        asker=asker,
        look_after=Look("u", b"after", f"Área guardada — token {REDACTED}"),
    )

    evidence = asker.asked[0]["evidence"]
    assert isinstance(evidence, str)
    assert "Área guardada" in evidence and REDACTED in evidence
    assert "\\u00e1" not in evidence and "\\u00ab" not in evidence


async def test_the_screen_belt_is_told_the_status_the_browser_came_back_with() -> None:
    """A step reaches the picture with a status behind it whenever the status
    belt saw one it could not decide on -- here a 200 where the evidence only
    ever recorded a 201. The model is told that number, and a verifier that
    blanked it stayed green on all 24 ported tests: the only one asserting
    `browser_answered` sent a `ui.perform`, whose reply carries no status at
    all, so `{"status": None}` was the right answer there either way.
    """
    saver = _saver()
    post = next(r for r in saver.requests if r.method == "POST")
    saver.requests = [replace(post, status=201)]
    asker = FakeAsker(Answer(data={"held": True, "why": "the row is there"}))

    verdict = await _verify(
        saver,
        channel=FakeChannel(),
        values={},
        sent_kind="http.send",
        answer=Reply(ok=True, result={"status": 200, "body": "{}"}),
        asker=asker,
        look_after=Look("u", b"after", "Saved"),
    )

    assert (verdict.state, verdict.by) == ("held", "screen")
    evidence = asker.asked[0]["evidence"]
    assert isinstance(evidence, str)
    assert json.loads(evidence)["browser_answered"] == {"ok": True, "status": 200}


async def test_a_picture_never_overrides_the_status_the_warehouse_itself_returned() -> None:
    """The status belt outranks the screen belt whether or not there is a
    picture -- and no test in the rig's suite or in the first pass of this one
    could tell. Every step the status belt decided was handed
    `Look(None, None, "")`, so `asker.asked == []` was true because there was
    nothing to look at, not because the belt order held.

    It is the inversion this module exists to prevent, and the most expensive
    one available: `status` is a `state_verified` belt and `screen` is not, so
    a screen verdict promoted over a status verdict would let a model reading a
    picture decide what a job earns the right to write unasked.
    """
    seen = Look("u", b"after", "Saved")
    for status, state in ((200, "held"), (422, "failed")):
        asker = FakeAsker(Answer(data={"held": True, "why": "it looks fine to me"}))

        verdict = await _verify(
            _saver(),
            channel=FakeChannel(),
            values={},
            sent_kind="http.send",
            answer=Reply(ok=True, result={"status": status, "body": "{}"}),
            asker=asker,
            look_before=Look("u", b"before", "Save"),
            look_after=seen,
        )

        assert (verdict.state, verdict.by) == (state, "status"), status
        assert asker.asked == [], f"a picture was on the table and {status} still decided"


async def test_a_step_that_changes_nothing_is_held_on_having_been_performed() -> None:
    """The rung that unblocked every cross-system job this rig mines.

    `new`'s `Create a Warehouse Equipment Type` opens the request in Gmail
    before it touches the WMS, and that click's only recorded traffic is a
    `POST` to `play.google.com/log` -- Google's telemetry beacon, on another
    origin. So `writes` says no (after the origin fix in `recorded_call`),
    there is no status to read, no confirming read to send, and a stub browser
    has no screenshot. The verdict was `unclear`, `run_workflow` stops on
    anything but `held`, and the job died on its first rung every time.

    There is no state such a step could confirm. The browser reporting that it
    performed the command and found the control is the whole of the evidence
    it can ever have, so that is what it is held on.
    """
    reader = copy.deepcopy(_saver())
    reader.requests = [
        replace(reader.requests[0], method="POST", url="https://play.google.com/log", status=200)
    ]

    verdict = await _verify(reader, channel=FakeChannel(), values={}, origin=None)

    assert (verdict.state, verdict.by) == ("held", "performed")
    assert "changes nothing" in verdict.reason


async def test_a_step_that_typed_something_is_never_held_on_having_been_performed() -> None:
    """The right control and the wrong text is a failure nothing on this page
    shows. A step that put a value somewhere is judged on the value."""
    typing = copy.deepcopy(_saver())
    typing.requests = [
        replace(typing.requests[0], method="POST", url="https://play.google.com/log", status=200)
    ]
    typing.action = replace(typing.action, kind="type", value="DDD")

    verdict = await _verify(typing, channel=FakeChannel(), values={}, origin=None)

    assert verdict.state == "unclear", "typing is not held on the browser's say-so"


async def test_evidence_that_was_never_watched_is_not_evidence_of_no_write() -> None:
    """ "Changes nothing" and "we have no evidence either way" are different
    claims, and only the first earns a `held`. A cited gesture whose call never
    returned was not watched, so what it did is unknown."""
    unwatched = copy.deepcopy(_saver())
    unwatched.requests = [replace(unwatched.requests[0], method="GET", status=None)]

    verdict = await _verify(unwatched, channel=FakeChannel(), values={}, origin=None)

    assert verdict.state == "unclear"


# -- a body this run re-aimed is not the body that was demonstrated ------------


async def test_a_body_this_run_re_aimed_is_not_held_on_its_status_alone() -> None:
    """The case that makes running without asking defensible.

    A 201 says something was created. It does not say the thing carries the
    values this run was given, and the ledger's own note is the instance:
    `csttyp truncates at 4 chars`, so a create asking for five characters is
    answered with the status the demonstration got and the record is four, with
    nobody told. (The fixture's own save answered 200, so that is what a replay
    of it comes back with -- `expected_statuses` is narrowed to what this
    endpoint was actually seen to answer.)

    So a re-aimed write falls past the status to the read-back, and the
    read-back is what notices.
    """
    channel = _read('{"workArea":"WAS-TRUNCATED"}')

    verdict = await _verify(
        _saver(),
        channel=channel,
        values={"workArea": "THIRD"},
        sent_kind="http.send",
        answer=Reply(ok=True, result={"status": 200, "body": "{}"}),
        rewrote=True,
        confirm={"workArea": "THIRD"},
    )

    assert (verdict.state, verdict.by) == ("failed", "read")
    assert channel.sent, "the status was allowed to settle a body this run changed"


async def test_a_re_aimed_write_the_read_back_confirms_is_held_by_the_read() -> None:
    channel = _read('{"workArea":"THIRD"}')

    verdict = await _verify(
        _saver(),
        channel=channel,
        values={"workArea": "THIRD"},
        sent_kind="http.send",
        answer=Reply(ok=True, result={"status": 200, "body": "{}"}),
        rewrote=True,
        confirm={"workArea": "THIRD"},
    )

    assert (verdict.state, verdict.by) == ("held", "read")


async def test_the_read_back_after_a_re_aimed_write_wants_every_value_not_any() -> None:
    """`mentions` is `any`, and a truncated record is exactly the shape that
    defeats it: the description still matches and the code does not. Measured
    live on 2026-09-15, four runs of a job typing a new code and the same
    reference each time all skipped their write and reported held on `any`.
    """
    unchanged = '{"workArea":"WAS-TRUNCATED","reference":"SAME"}'

    onany = await _verify(
        _saver(),
        channel=_read(unchanged),
        values={"workArea": "THIRD", "reference": "SAME"},
        sent_kind="http.send",
        answer=Reply(ok=True, result={"status": 200, "body": "{}"}),
        rewrote=False,
    )
    onevery = await _verify(
        _saver(),
        channel=_read(unchanged),
        values={"workArea": "THIRD", "reference": "SAME"},
        sent_kind="http.send",
        answer=Reply(ok=True, result={"status": 200, "body": "{}"}),
        rewrote=True,
        confirm={"workArea": "THIRD", "reference": "SAME"},
    )

    assert onany.by == "status", "a verbatim replay is settled before the read"
    assert (onevery.state, onevery.by) == ("failed", "read"), (
        "the half that did not change matched, and the half that did was not looked at"
    )


async def test_a_record_the_server_worded_its_own_way_is_not_a_failed_write() -> None:
    """The defect this replaced, and it un-earned jobs for being right.

    Measured over the 94 recorded creates whose request and response are both
    JSON objects: 16 send a value that appears nowhere in the answer, every one
    a `…Description` key where the form posts the code and the server stores
    the label it resolves to. Searching the whole record for `ZV9054` finds
    nothing, so a correct create was marked `failed` -- which stops the run and
    empties the job's register of verified effects.

    `confirm` is `WritePlan.confirm`, already narrowed to the slots the
    demonstration's own answer handed back unchanged, so the rewritten one is
    never asked about and the record is judged on the slot that can be judged.
    """
    channel = _read('{"workArea":"THIRD","summary":"Any handling unit for pallet movement"}')

    verdict = await _verify(
        _saver(),
        channel=channel,
        values={"workArea": "THIRD", "summary": "ZV9054"},
        sent_kind="http.send",
        answer=Reply(ok=True, result={"status": 200, "body": "{}"}),
        rewrote=True,
        confirm={"workArea": "THIRD"},
    )

    assert (verdict.state, verdict.by) == ("held", "read")


async def test_a_held_read_names_the_record_the_run_made() -> None:
    """The card has to say WHICH record, and on this endpoint `made_by` cannot.

    Its suffix rule wants a key ending in `id`/`code`/`name`/`number`/`key`,
    and the identifier for a customer type is `customerType`. Measured on the
    live create, 2026-09-16: 201, the record created, `made` empty -- so a run
    could say it had made something and not which.

    The plan already knows which keys this job varies, so the row those keys
    found is the row to name, read back from the warehouse rather than echoed
    from what was sent.
    """
    channel = _read('{"data":[{"workArea":"THIRD","summary":"as the warehouse kept it"}]}')

    verdict = await _verify(
        _saver(),
        channel=channel,
        values={"workArea": "THIRD"},
        sent_kind="http.send",
        answer=Reply(ok=True, result={"status": 200, "body": "{}"}),
        rewrote=True,
        confirm={"workArea": "THIRD"},
    )

    assert (verdict.state, verdict.by) == ("held", "read")
    assert dict(verdict.made) == {"workArea": "THIRD"}


async def test_the_card_names_a_row_and_never_quotes_a_paragraph_back() -> None:
    """Same discipline `made_by` already keeps, and for the same reason.

    What is stored on the run is what NAMES the record, not the record. A
    description field can be a paragraph of somebody's data, and this row is
    kept for as long as the tenant keeps the run -- so the boundary is the
    whole of the rule and both sides of it are checked.
    """
    just_short = "x" * 64
    too_long = "y" * 65
    channel = _read(
        json.dumps({"data": [{"workArea": "THIRD", "note": just_short, "essay": too_long}]})
    )

    verdict = await _verify(
        _saver(),
        channel=channel,
        values={"workArea": "THIRD"},
        sent_kind="http.send",
        answer=Reply(ok=True, result={"status": 200, "body": "{}"}),
        rewrote=True,
        confirm={"workArea": "THIRD", "note": just_short, "essay": too_long},
    )

    assert verdict.state == "held"
    assert dict(verdict.made) == {"workArea": "THIRD", "note": just_short}, (
        "sixty-four characters is a name; sixty-five is a paragraph"
    )


async def test_a_re_aimed_write_with_no_slot_a_read_could_settle_never_makes_the_read() -> None:
    """Every field this run wrote is one the demonstration shows the server
    rewriting, so there is no proposition a read could confirm. Asking anyway
    spends a round trip to be told the record does not hold what was posted
    into it -- which is true of the demonstration's own record too."""
    channel = _read('{"summary":"Any handling unit for pallet movement"}')

    verdict = await _verify(
        _saver(),
        channel=channel,
        values={"summary": "ZV9054"},
        sent_kind="http.send",
        answer=Reply(ok=True, result={"status": 200, "body": "{}"}),
        rewrote=True,
        confirm={},
    )

    assert (verdict.state, verdict.by) == ("held", "status")
    assert not channel.sent, "a read was made for a record it could not settle"


async def test_with_no_read_to_make_a_re_aimed_write_still_holds_on_its_status() -> None:
    """Belt availability, decided rather than assumed. A job whose evidence
    carries no confirming read has nothing but its status, and the status is
    real -- falling to the screen for it would photograph a page to ask a model
    about a record the warehouse already answered for."""
    verdict = await _verify(
        _saver(),
        channel=FakeChannel(),
        values={},
        sent_kind="http.send",
        answer=Reply(ok=True, result={"status": 200, "body": "{}"}),
        rewrote=True,
    )

    assert (verdict.state, verdict.by) == ("held", "status")
    assert "no read to confirm it by" in verdict.reason


async def test_a_replayed_create_says_what_the_warehouse_called_the_record() -> None:
    """`made` is what an undo would address, and it was empty on every run this
    system has ever recorded -- the `http.send` rung never called `made_by`."""
    created = '{"@type":"ResponseBodyWrapper","data":{"resourceId":"GGD"}}'

    verdict = await _verify(
        _saver(),
        channel=FakeChannel(),
        values={},
        sent_kind="http.send",
        answer=Reply(ok=True, result={"status": 200, "body": created}),
    )

    assert (verdict.state, verdict.by) == ("held", "status")
    assert verdict.made == {"resourceId": "GGD"}
