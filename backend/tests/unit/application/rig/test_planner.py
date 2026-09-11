"""One step of a job, planned as one command.

Ported from `new_agent_arch/tests/test_planner.py` -- every test there that puts
a question to a model. The ones that do not are in
`tests/unit/domain/rig/test_planning.py`, which plan 1 brought across with the
schemas and the two rules that need no model.

Several guards here are new, all of them found by mutating what reaches the
call rather than the rule it feeds. Nothing in the rig's suite asserted that
`starts_on` or a withheld `allow_focus` reached the payload, that the cited
evidence or the step's own sentence reached the prompt at all, that `look`
reached it as words as well as a picture, or -- on the plan rung alone, where
the sight rung pins all three -- which words, which schema and which model were
asked. A planner that stopped threading any of them stayed green on all 27.
"""

import copy
import json
from collections.abc import Mapping
from dataclasses import replace
from urllib.parse import urlsplit

from sro.application.execution.plan_step import ACTIONS, plan_by_sight, plan_step
from sro.domain.execution.evidence import locators_for
from sro.domain.execution.planning import (
    PLAN_INSTRUCTIONS,
    PLAN_SCHEMA,
    SIGHT_INSTRUCTIONS,
    SIGHT_SCHEMA,
    Look,
    Planned,
)
from sro.domain.execution.verified_writes import VerifiedWrite
from sro.domain.observation.gesture import Body, Call, Gesture
from sro.domain.observation.trim import trim
from sro.domain.shared.hosts import REDACTED
from sro.domain.shared.prices import Answer, Effort
from sro.domain.skill.workflow import Step
from tests.unit.domain.rig.conftest import gestures as _gestures
from tests.unit.fakes import FakeAsker


def _typed() -> Gesture:
    return next(g for g in _gestures() if g.action.kind == "type" and not g.action.secret)


def _saver() -> Gesture:
    return next(g for g in _gestures() if g.requests)


def test_the_actions_offered_are_the_actions_accepted() -> None:
    """The enum the model is shown and the set its answer is checked against
    are one list. Parting them either offers an action that falls back to the
    gesture's own, or accepts one the schema never allowed."""
    properties = PLAN_SCHEMA["properties"]
    assert isinstance(properties, dict)
    action = properties["action"]
    assert isinstance(action, dict)
    assert frozenset(action["enum"]) == ACTIONS


async def test_a_ui_plan_carries_the_evidence_locators_not_the_models() -> None:
    gesture = _typed()
    asker = FakeAsker(
        Answer(
            data={
                "kind": "ui.perform",
                "action": "type",
                # Not "THIRD": if the model's own word and the run's value are
                # the same string, the test cannot tell which one the payload
                # carried, and deleting the lookup in `value_for` stays green.
                "value": "WRONG",
                "url": None,
                # Nothing validates a model's answer against the schema, which
                # is why the action enum is re-checked and the value is cast --
                # so a model volunteering a ladder of its own is answered here
                # too, and the answer is the demonstration's.
                "locators": [{"strategy": "css_path", "query": "#evil"}],
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
    locators = planned.payload["locators"]
    assert isinstance(locators, list)
    assert locators[0] == {
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
    evidence = asker.asked[0]["evidence"]
    assert isinstance(evidence, str)
    assert "THIRD" in evidence
    assert "allow_focus" not in evidence, "nothing about focus reaches the model"
    assert "http://127.0.0.1:63319/" in evidence, "the step's real page, for a deep job"
    # Not in the rig's suite, and nothing else here reads this key: the whole
    # prompt could stop carrying the cited gestures and every ported test
    # stayed green, because the page above reaches it by another door.
    seen = json.loads(evidence)
    assert seen["evidence"] == [trim(gesture)], (
        "the step is planned from the evidence, so the evidence is what is sent"
    )
    # The sentence the model is asked to perform, and the whole shape of the
    # prompt: blanking either was green on every other test here.
    assert seen["step"] == {"order": 0, "says": "type", "parameters": []}
    assert set(seen) == {
        "step",
        "evidence",
        "values",
        "browser",
        "step_page",
        "previous_attempt_failed",
        "previous_attempt_left",
    }


async def test_an_http_plan_replays_the_recorded_call_with_redacted_headers_dropped() -> None:
    saver = _saver()
    post = next(r for r in saver.requests if r.method == "POST")
    struck = replace(
        post,
        request_headers={"Content-Type": "application/json", "CSRF-ENCRYPT-TOKEN": REDACTED},
    )
    saver.requests[saver.requests.index(post)] = struck
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
    headers = planned.payload["headers"]
    assert isinstance(headers, dict)
    assert "CSRF-ENCRYPT-TOKEN" not in headers, "a marker is never sent as a header"
    assert headers["Content-Type"] == "application/json"
    assert "live_headers" not in planned.payload, "unverified: the rule above is the whole of it"


async def test_a_verified_call_names_its_struck_header_for_a_live_fetch_instead() -> None:
    """The one narrow exception. `verified_writes` carries this call's own
    `(method, path)`, so the header the extension has a live source for is
    named in `live_headers` rather than silently left off -- which is what
    sends a Blue Yonder write into the 404 the KB's own notes describe.
    """
    saver = _saver()
    post = next(r for r in saver.requests if r.method == "POST")
    struck = replace(
        post,
        request_headers={"Content-Type": "application/json", "CSRF-ENCRYPT-TOKEN": REDACTED},
    )
    saver.requests[saver.requests.index(post)] = struck
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
        verified_writes=(VerifiedWrite(method="POST", path_pattern=urlsplit(post.url).path),),
    )

    assert planned.kind == "http.send"
    assert planned.payload["live_headers"] == ["CSRF-ENCRYPT-TOKEN"]
    assert "CSRF-ENCRYPT-TOKEN" not in planned.payload["headers"], (
        "named for a live fetch, never carried on the wire from here"
    )


async def test_a_call_that_matches_no_verified_write_still_drops_the_header() -> None:
    """Verification is per call, not a switch this deployment flips once: a
    ledger naming some other path leaves this one exactly as unverified as an
    empty ledger would."""
    saver = _saver()
    post = next(r for r in saver.requests if r.method == "POST")
    struck = replace(
        post,
        request_headers={"Content-Type": "application/json", "CSRF-ENCRYPT-TOKEN": REDACTED},
    )
    saver.requests[saver.requests.index(post)] = struck
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
        verified_writes=(VerifiedWrite(method="POST", path_pattern="/somewhere/else"),),
    )

    assert "live_headers" not in planned.payload
    assert "CSRF-ENCRYPT-TOKEN" not in planned.payload["headers"]


async def test_an_http_plan_whose_body_the_store_never_kept_is_downgraded_to_the_interface() -> (
    None
):
    saver = _saver()
    post = next(r for r in saver.requests if r.method == "POST")
    assert post.request_body is not None
    offloaded = replace(
        post,
        request_body=replace(post.request_body, text=None, blob_uri="s3://bodies/ges_9de89"),
    )
    saver.requests[saver.requests.index(post)] = offloaded
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
    evidence = asker.asked[0]["evidence"]
    assert isinstance(evidence, str) and "control_not_found" in evidence
    assert asker.asked[0]["image"] == b"\x89PNG"
    # Also not in the rig's suite: `look` reaching the picture was pinned and
    # `look` reaching the words was not, so a planner that told the model
    # nothing about where the browser is could still plan a navigate.
    assert json.loads(evidence)["browser"] == {
        "url": "http://127.0.0.1:63319/",
        "screen_text": "Save",
    }
    assert planned.kind == "navigate" and planned.payload == {
        "url": "http://127.0.0.1:63319/form",
        "origin": "http://127.0.0.1:63319",
        "allow_focus": True,
    }


async def test_an_http_plan_whose_url_carries_a_struck_out_credential_is_downgraded() -> None:
    saver = _saver()
    post = next(r for r in saver.requests if r.method == "POST")
    struck = replace(post, url=f"{post.url}?session={REDACTED}")
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


def _answer(**data: object) -> Answer:
    base: dict[str, object] = {
        "kind": "ui.perform",
        "action": None,
        "value": None,
        "url": None,
        "why": "w",
    }
    return Answer(data={**base, **data})


async def _planned(
    *,
    cited: list[Gesture],
    answer: Answer,
    values: Mapping[str, str] | None = None,
    step: Step | None = None,
    effort: Effort | None = None,
    starts_on: str | None = None,
    allow_focus: bool = False,
) -> tuple[Planned, FakeAsker]:
    asker = FakeAsker(answer)
    planned = await plan_step(
        step=step or Step(order=0, says="do it", system=None, cites=[g.id for g in cited]),
        cited=cited,
        values=values or {},
        look=Look(None, None, ""),
        origin=None,
        starts_on=starts_on,
        allow_focus=allow_focus,
        asker=asker,
        model="m",
        effort=effort,
    )
    return planned, asker


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
    # A real scroll, not the rig's copy of a typed gesture with its kind
    # rewritten: that one kept the typed control's id and its target, so it and
    # the gesture it was meant to be skipped for had the same ladder and the
    # same row in `by_id`. A planner that ignored the preference entirely and
    # took the first cited gesture passed the assertion below on all eight
    # hash seeds.
    scroll.id = "ges_scroll"
    scroll.action = replace(scroll.action, kind="scroll", target=None)
    planned, _ = await _planned(cited=[scroll], answer=_answer(action="click"))
    assert planned.kind == "ui.perform"
    assert planned.payload["locators"] == [], "a scroll has no ladder, and is still a plan"

    typed = _typed()
    ahead, _ = await _planned(cited=[scroll, typed], answer=_answer(action="type", value="x"))
    ladder = [rung.as_payload() for rung in locators_for(typed)]
    assert ladder, "the fixture's typed control has a ladder to tell the two apart by"
    assert ahead.payload["locators"] == ladder, (
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
    assert planned.payload["value"] == gesture.action.value

    numbered, _ = await _planned(cited=[gesture], answer=_answer(action="type", value=123))
    assert numbered.payload["value"] == "123", "nothing validates the model's answer for us"


async def test_a_recorded_call_with_no_body_is_replayed_as_it_was() -> None:
    """Nothing to get wrong is not a reason to refuse to replay. A GETless
    POST -- a delete, a button that posts nothing -- is still the call."""
    saver = _saver()
    post = next(r for r in saver.requests if r.method == "POST")
    saver.requests = [replace(post, request_body=None)]

    planned, _ = await _planned(cited=[saver], answer=_answer(kind="http.send", why="no target"))

    assert planned.kind == "http.send" and planned.payload["body"] is None
    assert planned.why == "no target", "nothing was downgraded"


async def test_an_http_plan_carries_the_body_the_operator_sent() -> None:
    saver = _saver()
    post = next(r for r in saver.requests if r.method == "POST")
    assert post.request_body is not None

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
    evidence = asked["evidence"]
    assert isinstance(evidence, str)
    assert json.loads(evidence)["step_page"] == "http://127.0.0.1:63319/clients/new"
    assert asked["effort"] == "low", "a rescue asks harder than a first attempt"
    # Which words, which shape and which model, not merely that there were
    # some: the sight rung pins all three and this one pinned none, so a
    # planner showing the sight prompt against the plan schema on a model
    # nobody chose was green on every test in this file.
    assert asked["instructions"] == PLAN_INSTRUCTIONS, "a model told nothing plans nothing"
    assert asked["schema"] is PLAN_SCHEMA
    assert asked["model"] == "m", "the model the caller chose"


async def test_a_step_that_waits_for_a_page_carries_it_and_focus_only_when_allowed() -> None:
    """Neither key is in the payload unless the caller asked for it, and both
    reach it when they do. Nothing in the rig's own suite asserted this: a
    planner that stopped threading `starts_on` -- the page a step must be on
    before it is performed -- stayed green on all of it.
    """
    gesture = _typed()
    waited, _ = await _planned(
        cited=[gesture],
        answer=_answer(action="click"),
        starts_on="http://127.0.0.1:63319/form",
        allow_focus=True,
    )
    assert waited.payload["starts_on"] == "http://127.0.0.1:63319/form"
    assert waited.payload["allow_focus"] is True

    plain, _ = await _planned(cited=[gesture], answer=_answer(action="click"))
    assert "starts_on" not in plain.payload, "no page to wait for is no key"
    assert "allow_focus" not in plain.payload, "focus is taken only when it is granted"


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
    assert isinstance(asked["evidence"], str)
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
    assert isinstance(asker.asked[0]["evidence"], str)
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
    assert isinstance(asked["evidence"], str)
    assert json.loads(asked["evidence"])["previous_attempt_left"]["screenshot"] == "the only image"


async def test_a_replayed_call_still_carries_the_answer_that_planned_it() -> None:
    saver = _saver()
    asker = FakeAsker(
        Answer(
            data={"kind": "http.send", "action": None, "value": None, "url": None, "why": "w"},
            cost_usd=0.002,
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
    assert planned.answer is not None and planned.answer.cost_usd == 0.002, "the runner bills it"


def _seen(width: int = 800, height: int = 600, picture: bytes | None = b"png") -> Look:
    return Look(
        url="http://127.0.0.1:63319/form",
        screenshot=picture,
        digest="Client Code Save",
        width=width,
        height=height,
    )


async def _by_sight(
    answer: Answer,
    look: Look | None = None,
    values: Mapping[str, str] | None = None,
    gesture: Gesture | None = None,
) -> tuple[Planned, FakeAsker]:
    gesture = gesture or _typed()
    asker = FakeAsker(answer)
    planned = await plan_by_sight(
        step=Step(
            order=0,
            says="type the code",
            system=None,
            cites=[gesture.id],
            parameters=["clientCode"],
        ),
        cited=[gesture],
        values={"clientCode": "THIRD"} if values is None else values,
        look=look or _seen(),
        origin="http://127.0.0.1:63319",
        asker=asker,
        model="pro",
        failure="control_not_found: gone",
    )
    return planned, asker


def _sight(**data: object) -> Answer:
    base: dict[str, object] = {
        "found": True,
        "x": 40,
        "y": 30,
        "action": "type",
        "value": "WRONG",
        "why": "there",
    }
    return Answer(data={**base, **data})


async def test_the_sight_rung_is_asked_with_the_screen_its_size_and_the_demonstrated_control() -> (
    None
):
    planned, asker = await _by_sight(_sight())

    [asked] = asker.asked
    assert asked["model"] == "pro"
    assert asked["schema"] is SIGHT_SCHEMA
    assert asked["instructions"] == SIGHT_INSTRUCTIONS
    assert asked["image"] == b"png", "the picture it is asked to look at"
    assert isinstance(asked["evidence"], str)
    evidence = json.loads(asked["evidence"])
    assert set(evidence) == {
        "step",
        "demonstrated_on",
        "values",
        "browser",
        "viewport",
        "previous_attempt_failed",
    }
    assert evidence["viewport"] == {"width": 800, "height": 600}
    assert evidence["step"] == {"order": 0, "says": "type the code", "parameters": ["clientCode"]}
    assert evidence["browser"] == {
        "url": "http://127.0.0.1:63319/form",
        "screen_text": "Client Code Save",
    }
    assert evidence["values"] == {"clientCode": "THIRD"}
    assert evidence["previous_attempt_failed"] == "control_not_found: gone"
    assert isinstance(evidence["demonstrated_on"], dict) and evidence["demonstrated_on"]
    # The run's value, not the model's word, and the point as given.
    assert planned.kind == "ui.perform_at" and planned.why == "there"
    assert planned.payload == {
        "origin": "http://127.0.0.1:63319",
        "x": 40,
        "y": 30,
        "action": "type",
        "value": "THIRD",
    }
    assert planned.answer.data is not None


async def test_the_corner_of_the_screen_is_on_it_and_its_far_edge_is_not() -> None:
    on, _ = await _by_sight(_sight(x=0, y=0, action="click"))
    assert on.kind == "ui.perform_at" and on.payload["x"] == 0 and on.payload["y"] == 0
    for x, y in ((800, 0), (0, 600), (-1, 5), (5, -1)):
        off, _ = await _by_sight(_sight(x=x, y=y, action="click"))
        assert off.kind == "none" and f"({x}, {y}) is not on the screen" in off.why, (x, y)
    text, _ = await _by_sight(_sight(x="40", y=30, action="click"))
    assert text.kind == "none", "a point that is not two integers is not a point"


async def test_no_picture_no_size_or_no_answer_is_no_plan() -> None:
    blind, asker = await _by_sight(_sight(), look=_seen(picture=None))
    assert blind.kind == "none" and blind.why == "no screen to look at" and not asker.asked
    sizeless, asker = await _by_sight(_sight(), look=_seen(width=0))
    assert sizeless.kind == "none" and sizeless.why == "no screen to look at" and not asker.asked
    refused, _ = await _by_sight(Answer(error="503 UNAVAILABLE", unpriced=True))
    assert refused.kind == "none" and refused.why == "503 UNAVAILABLE"
    assert refused.answer.unpriced is True, "the refused call is still the bill"
    unseen, _ = await _by_sight(_sight(found=False, why="the form is not open"))
    assert unseen.kind == "none" and unseen.why == "the form is not open"
    silent, _ = await _by_sight(_sight(found=False, why=""))
    assert silent.why == "the control is not on this screen"


async def test_nothing_to_type_is_no_plan_and_a_press_carries_no_value() -> None:
    # A credential is never filled in from anywhere: the one control with no
    # value from the run, the model or the recording.
    secret = next(g for g in _gestures() if g.action.kind == "type" and g.action.secret)
    nothing, _ = await _by_sight(_sight(value="hunter2"), values={}, gesture=secret)
    assert nothing.kind == "none" and nothing.why == "nothing to type: no value for this control"
    press, _ = await _by_sight(_sight(action="press", value="Enter"))
    assert press.kind == "ui.perform_at" and "value" not in press.payload
    # With no run value the model's word is taken, as text, as `plan_step` does.
    said, _ = await _by_sight(_sight(action="type", value=7), values={})
    assert said.kind == "ui.perform_at" and said.payload["value"] == "7"


async def test_an_action_a_point_cannot_take_is_no_plan() -> None:
    """`SIGHT_SCHEMA` offers click, type and press and no select, because
    `performAtInPage` has no way to choose an option at a point -- and nothing
    validates the model's answer against that schema, so the enum is checked
    again here. Not in the rig's suite: with the check deleted, a select
    answered by sight became a `ui.perform_at` the extension cannot perform.
    """
    for action in ("select", "upload", "scroll", "jiggle", None):
        refused, _ = await _by_sight(_sight(action=action))
        assert refused.kind == "none", action
        assert refused.why == f"{action!r} is not an action a point can take"


async def test_the_redaction_marker_reaches_both_prompts_as_itself() -> None:
    """`ensure_ascii=False`, and it is not cosmetic.

    The marker is «redacted». The default escaping writes it into the prompt as
    \\u00abredacted\\u00bb -- a form nothing else in this system uses -- so the
    model would be asked to understand a marker written one way here and
    another way everywhere else. Both prompts this module builds carry trimmed
    evidence, so both can carry one.
    """
    gesture = _typed()
    gesture.requests = [
        Call(
            method="POST",
            url="http://127.0.0.1:63319/api/login",
            request_body=Body(
                text='{"password": "hunter2"}', size_bytes=23, mime_type="application/json"
            ),
        )
    ]

    _, planner = await _planned(cited=[gesture], answer=_answer(action="type", value="x"))
    _, sight = await _by_sight(_sight(), gesture=gesture)

    for asker in (planner, sight):
        sent = asker.asked[0]["evidence"]
        assert isinstance(sent, str)
        assert "hunter2" not in sent
        assert REDACTED in sent, "the marker, not \\u00abredacted\\u00bb"
