import copy
import json

from rig.correlate import correlate
from rig.locators import locators_for
from rig.models import Answer, FakeAsker
from rig.planner import PLAN_SCHEMA, Look, plan_step
from rig.wire import REDACTED, Batch
from rig.workflows import Step
from tests.fixtures import BATCH


def _gestures():
    gestures, _, _, _ = correlate(Batch.model_validate(BATCH), "acme")
    return gestures


def _typed():
    return next(g for g in _gestures() if g.gesture.kind == "type" and not g.gesture.secret)


async def test_a_ui_plan_carries_the_evidence_locators_not_the_models() -> None:
    gesture = _typed()
    asker = FakeAsker(
        Answer(
            data={
                "kind": "ui.perform",
                "action": "type",
                # Not "THIRD": if the model's own word and the run's value are
                # the same string, the test cannot tell which one the payload
                # carried, and deleting the lookup in `_value_for` stays green.
                "value": "WRONG",
                "url": None,
                "why": "the step types the code",
            },
            cost_usd=0.0003,
        )
    )

    planned = await plan_step(
        step=Step(order=0, says="type the code", system=None, cites=[gesture.id]),
        cited=[gesture],
        values={"clientCode": "THIRD"},
        look=Look(url="http://127.0.0.1:63319/", screenshot=None, digest=""),
        origin="http://127.0.0.1:63319",
        starts_on=None,
        allow_focus=True,
        asker=asker,
        model="gemini-3.8-flash",
    )

    assert planned.kind == "ui.perform"
    assert planned.payload["action"] == "type" and planned.payload["value"] == "THIRD"
    assert planned.payload["locators"][0] == {
        "strategy": "component",
        "query": "panel#clients textfield#clientCode",
        "within": None,
        "visible_only": True,
    }
    assert planned.payload["origin"] == "http://127.0.0.1:63319"
    assert planned.payload["allow_focus"] is True
    assert planned.answer.cost_usd == 0.0003


async def test_the_values_the_run_was_given_are_what_the_model_sees_not_the_recorded_ones() -> None:
    gesture = _typed()
    asker = FakeAsker(
        Answer(data={"kind": "ui.perform", "action": "type", "value": "x", "url": None, "why": ""})
    )
    await plan_step(
        step=Step(order=0, says="type", system=None, cites=[gesture.id]),
        cited=[gesture],
        values={"clientCode": "THIRD"},
        look=Look(None, None, ""),
        origin=None,
        starts_on=None,
        allow_focus=False,
        asker=asker,
        model="m",
    )
    assert "THIRD" in asker.asked[0]["evidence"]
    assert "allow_focus" not in asker.asked[0]["evidence"], "nothing about focus reaches the model"
    assert "http://127.0.0.1:63319/" in asker.asked[0]["evidence"], (
        "the step's real page, for a deep job"
    )


async def test_an_http_plan_replays_the_recorded_call_with_redacted_headers_dropped() -> None:
    saver = next(g for g in _gestures() if g.requests)
    post = next(r for r in saver.requests if r.method == "POST")
    post.request_headers = {"Content-Type": "application/json", "CSRF-ENCRYPT-TOKEN": "«redacted»"}
    asker = FakeAsker(
        Answer(
            data={
                "kind": "http.send",
                "action": None,
                "value": None,
                "url": None,
                "why": "no ui target",
            }
        )
    )

    planned = await plan_step(
        step=Step(order=0, says="save", system=None, cites=[saver.id]),
        cited=[saver],
        values={},
        look=Look(None, None, ""),
        origin=None,
        starts_on=None,
        allow_focus=False,
        asker=asker,
        model="m",
    )

    assert planned.kind == "http.send"
    assert planned.payload["method"] == "POST" and planned.payload["url"] == post.url
    assert "CSRF-ENCRYPT-TOKEN" not in planned.payload["headers"], (
        "a marker is never sent as a header"
    )
    assert planned.payload["headers"]["Content-Type"] == "application/json"


async def test_an_http_plan_whose_body_the_store_never_kept_is_downgraded_to_the_interface() -> (
    None
):
    saver = next(g for g in _gestures() if g.requests)
    post = next(r for r in saver.requests if r.method == "POST")
    post.request_body = post.request_body.model_copy(
        update={"text": None, "blob_uri": "s3://bodies/ges_9de89"}
    )
    asker = FakeAsker(
        Answer(
            data={
                "kind": "http.send",
                "action": None,
                "value": None,
                "url": None,
                "why": "replaying the save",
            }
        )
    )

    planned = await plan_step(
        step=Step(order=0, says="save", system=None, cites=[saver.id]),
        cited=[saver],
        values={},
        look=Look(None, None, ""),
        origin=None,
        starts_on=None,
        allow_focus=False,
        asker=asker,
        model="m",
    )

    assert planned.kind == "ui.perform"
    assert planned.payload["locators"], "the downgrade is a real plan, not an empty one"
    assert "not replayable" in planned.why


async def test_a_model_that_could_not_answer_plans_nothing_and_says_why() -> None:
    gesture = _typed()
    planned = await plan_step(
        step=Step(order=0, says="type", system=None, cites=[gesture.id]),
        cited=[gesture],
        values={},
        look=Look(None, None, ""),
        origin=None,
        starts_on=None,
        allow_focus=False,
        asker=FakeAsker(Answer(error="boom", unpriced=True)),
        model="m",
    )
    assert planned.kind == "none" and "boom" in planned.why


async def test_a_kind_the_protocol_does_not_have_is_planned_as_nothing() -> None:
    gesture = _typed()
    planned = await plan_step(
        step=Step(order=0, says="type", system=None, cites=[gesture.id]),
        cited=[gesture],
        values={},
        look=Look(None, None, ""),
        origin=None,
        starts_on=None,
        allow_focus=False,
        asker=FakeAsker(
            Answer(data={"kind": "rm -rf", "action": None, "value": None, "url": None, "why": ""})
        ),
        model="m",
    )
    assert planned.kind == "none"


async def test_a_retry_carries_the_failure_and_the_second_screenshot() -> None:
    gesture = _typed()
    asker = FakeAsker(
        Answer(
            data={
                "kind": "navigate",
                "action": None,
                "value": None,
                "url": "http://127.0.0.1:63319/form",
                "why": "wrong page",
            }
        )
    )
    planned = await plan_step(
        step=Step(order=0, says="type", system=None, cites=[gesture.id]),
        cited=[gesture],
        values={},
        look=Look("http://127.0.0.1:63319/", b"\x89PNG", "Save"),
        origin="http://127.0.0.1:63319",
        starts_on=None,
        allow_focus=True,
        asker=asker,
        model="m",
        failure="control_not_found: no visible match",
    )
    assert "control_not_found" in asker.asked[0]["evidence"]
    assert asker.asked[0]["image"] == b"\x89PNG"
    assert planned.kind == "navigate" and planned.payload == {
        "url": "http://127.0.0.1:63319/form",
        "origin": "http://127.0.0.1:63319",
        "allow_focus": True,
    }


def test_the_schema_puts_why_last_and_kind_first() -> None:
    """Decide before explaining: identifying the command before composing the
    reason measurably beats composing first."""
    assert list(PLAN_SCHEMA["properties"]) == ["kind", "action", "value", "url", "why"]


async def test_an_http_plan_whose_url_carries_a_struck_out_credential_is_downgraded() -> None:
    saver = next(g for g in _gestures() if g.requests)
    post = next(r for r in saver.requests if r.method == "POST")
    struck = post.model_copy(update={"url": f"{post.url}?session={REDACTED}"})
    saver.requests[saver.requests.index(post)] = struck
    asker = FakeAsker(
        Answer(
            data={
                "kind": "http.send",
                "action": None,
                "value": None,
                "url": None,
                "why": "replaying the save",
            }
        )
    )

    planned = await plan_step(
        step=Step(order=0, says="save", system=None, cites=[saver.id]),
        cited=[saver],
        values={},
        look=Look(None, None, ""),
        origin=None,
        starts_on=None,
        allow_focus=False,
        asker=asker,
        model="m",
    )

    assert planned.kind == "ui.perform", "the marker would have gone out as the session id"
    assert "not replayable" in planned.why


def _answer(**data) -> Answer:
    base = {"kind": "ui.perform", "action": None, "value": None, "url": None, "why": "w"}
    return Answer(data={**base, **data})


async def _planned(*, cited, answer, values=None, step=None, **over):
    asker = over.pop("asker", None) or FakeAsker(answer)
    call = {
        "step": step or Step(order=0, says="do it", system=None, cites=[g.id for g in cited]),
        "cited": cited,
        "values": values or {},
        "look": Look(None, None, ""),
        "origin": None,
        "starts_on": None,
        "allow_focus": False,
        "asker": asker,
        "model": "m",
    }
    return await plan_step(**{**call, **over}), asker


async def test_every_way_out_hands_back_the_reading_that_paid_for_it() -> None:
    """A plan the runner cannot use still cost a call, and the runner bills
    what it is handed. An answer dropped on any of these paths is a step that
    reads as free."""
    gesture = _typed()
    unusable = Answer(error="boom", unpriced=True, cost_usd=0.0)
    for answer, kind in (
        (unusable, "none"),
        (_answer(kind="rm -rf"), "none"),
        (_answer(kind="navigate", url=""), "none"),
        (_answer(kind="navigate", url="http://127.0.0.1:63319/form"), "navigate"),
        (_answer(action="type", value="x"), "ui.perform"),
    ):
        planned, _ = await _planned(cited=[gesture], answer=answer)
        assert planned.kind == kind, answer
        assert planned.answer is answer
        assert isinstance(planned.payload, dict)
        assert isinstance(planned.why, str) and planned.why


async def test_a_navigate_with_nowhere_to_go_is_not_a_navigate() -> None:
    """An empty url is not a url. Sent on, the extension would be told to open
    the empty string."""
    gesture = _typed()
    for url in (None, "", 7):
        planned, _ = await _planned(cited=[gesture], answer=_answer(kind="navigate", url=url))
        assert (planned.kind, planned.payload) == ("none", {}), url


async def test_the_why_on_the_plan_is_the_models_own_and_empty_when_it_gave_none() -> None:
    gesture = _typed()
    planned, _ = await _planned(
        cited=[gesture], answer=_answer(action="type", value="x", why="the field wants the code")
    )
    assert planned.why == "the field wants the code"

    silent, _ = await _planned(cited=[gesture], answer=_answer(action="type", value="x", why=None))
    assert silent.why == "", "no explanation is an empty one, not the word None"


async def test_a_step_that_only_cites_a_scroll_is_still_planned_from_it() -> None:
    """`primary` prefers a gesture the extension can act on, and a scroll is
    not one -- but a step citing nothing else is not a step to give up on."""
    scroll = copy.deepcopy(_typed())
    scroll.gesture.kind = "scroll"
    planned, _ = await _planned(cited=[scroll], answer=_answer(action="click"))
    assert planned.kind == "ui.perform"

    typed = _typed()
    ahead, _ = await _planned(cited=[scroll, typed], answer=_answer(action="type", value="x"))
    assert ahead.payload["locators"] == locators_for(typed), (
        "the scroll is skipped for the gesture that can be acted on"
    )


async def test_the_action_is_the_models_when_the_protocol_has_it_and_the_gestures_when_not() -> (
    None
):
    gesture = _typed()  # a type gesture, so a fallback is visible
    chosen, _ = await _planned(cited=[gesture], answer=_answer(action="click"))
    assert chosen.payload["action"] == "click"

    invented, _ = await _planned(cited=[gesture], answer=_answer(action="jiggle"))
    assert invented.payload["action"] == "type", "back to what the operator did"


async def test_a_value_is_carried_for_every_action_that_takes_one_and_for_no_other() -> None:
    gesture = _typed()
    for action in ("type", "select", "upload", "press"):
        planned, _ = await _planned(cited=[gesture], answer=_answer(action=action, value="SAID"))
        assert planned.payload["value"] == "SAID", action

    clicked, _ = await _planned(cited=[gesture], answer=_answer(action="click", value="SAID"))
    assert clicked.payload["value"] is None, "a click types nothing"


async def test_with_no_value_from_the_run_or_the_model_the_recorded_one_stands() -> None:
    gesture = _typed()
    planned, _ = await _planned(cited=[gesture], answer=_answer(action="type", value=None))
    assert planned.payload["value"] == gesture.gesture.value

    numbered, _ = await _planned(cited=[gesture], answer=_answer(action="type", value=123))
    assert numbered.payload["value"] == "123", "nothing validates the model's answer for us"


async def test_a_recorded_call_with_no_body_is_replayed_as_it_was() -> None:
    """Nothing to get wrong is not a reason to refuse to replay. A GETless
    POST -- a delete, a button that posts nothing -- is still the call."""
    saver = next(g for g in _gestures() if g.requests)
    post = next(r for r in saver.requests if r.method == "POST")
    saver.requests = [post.model_copy(update={"request_body": None})]

    planned, _ = await _planned(cited=[saver], answer=_answer(kind="http.send", why="no target"))

    assert planned.kind == "http.send" and planned.payload["body"] is None
    assert planned.why == "no target", "nothing was downgraded"


async def test_an_http_plan_carries_the_body_the_operator_sent() -> None:
    saver = next(g for g in _gestures() if g.requests)
    post = next(r for r in saver.requests if r.method == "POST")

    planned, _ = await _planned(cited=[saver], answer=_answer(kind="http.send"))

    assert planned.payload["body"] == post.request_body.text
    assert planned.payload["body"], "the fixture's save posts a body"


async def test_an_http_plan_for_a_step_whose_evidence_made_no_call_plans_nothing() -> None:
    gesture = _typed()  # a typed field; the recorder heard no traffic from it
    planned, _ = await _planned(cited=[gesture], answer=_answer(kind="http.send"))
    assert (planned.kind, planned.payload) == ("none", {})


async def test_the_model_is_told_where_the_step_was_demonstrated_and_under_what_effort() -> None:
    gesture = copy.deepcopy(_typed())
    gesture.page_url = "http://127.0.0.1:63319/clients/new"
    _, asker = await _planned(
        cited=[gesture], answer=_answer(action="type", value="x"), effort="low"
    )

    [asked] = asker.asked
    assert json.loads(asked["evidence"])["step_page"] == "http://127.0.0.1:63319/clients/new"
    assert asked["effort"] == "low", "a rescue asks harder than a first attempt"
    assert asked["instructions"], "a model told nothing plans nothing"


async def test_a_rescue_is_shown_the_page_the_failed_attempt_left_behind() -> None:
    gesture = _typed()
    asker = FakeAsker(
        Answer(
            data={"kind": "ui.perform", "action": "type", "value": "THIRD", "url": None, "why": "w"}
        )
    )
    now = Look("http://127.0.0.1:63319/form", b"now-png", "Client code")
    left = Look("http://127.0.0.1:63319/form?after", b"left-png", "still empty")

    await plan_step(
        step=Step(order=0, says="type the code", system=None, cites=[gesture.id]),
        cited=[gesture],
        values={"clientCode": "THIRD"},
        look=now,
        origin=None,
        starts_on=None,
        allow_focus=False,
        asker=asker,
        model="pro",
        failure="the code was not typed",
        failed_look=left,
    )

    asked = asker.asked[0]
    assert asked["image"] == b"now-png", "the page as it is now is the first picture"
    assert asked["images"] == (b"left-png",), "the page the failed attempt left is the second"
    evidence = json.loads(asked["evidence"])
    assert evidence["previous_attempt_failed"] == "the code was not typed"
    assert evidence["previous_attempt_left"]["screenshot"] == "the second image"
    assert evidence["previous_attempt_left"]["url"].endswith("?after")


async def test_a_first_attempt_carries_no_second_picture() -> None:
    gesture = _typed()
    asker = FakeAsker(
        Answer(
            data={"kind": "ui.perform", "action": "type", "value": "THIRD", "url": None, "why": "w"}
        )
    )
    await plan_step(
        step=Step(order=0, says="type the code", system=None, cites=[gesture.id]),
        cited=[gesture],
        values={},
        look=Look(None, None, ""),
        origin=None,
        starts_on=None,
        allow_focus=False,
        asker=asker,
        model="flash",
    )
    assert asker.asked[0]["images"] == ()
    assert json.loads(asker.asked[0]["evidence"])["previous_attempt_left"] is None


async def test_the_failed_attempts_picture_is_named_by_its_position() -> None:
    gesture = _typed()
    asker = FakeAsker(
        Answer(data={"kind": "ui.perform", "action": "type", "value": "T", "url": None, "why": "w"})
    )
    await plan_step(
        step=Step(order=0, says="type", system=None, cites=[gesture.id]),
        cited=[gesture],
        values={},
        look=Look("http://127.0.0.1:63319/form", None, "no picture this time"),
        origin=None,
        starts_on=None,
        allow_focus=False,
        asker=asker,
        model="pro",
        failure="f",
        failed_look=Look("http://127.0.0.1:63319/form", b"left-png", "left"),
    )
    asked = asker.asked[0]
    assert asked["image"] is None and asked["images"] == (b"left-png",)
    assert json.loads(asked["evidence"])["previous_attempt_left"]["screenshot"] == "the only image"
