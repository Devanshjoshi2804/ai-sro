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
from sro.domain.execution.learned_step import LearnedStep
from sro.domain.execution.planning import (
    PLAN_INSTRUCTIONS,
    PLAN_SCHEMA,
    SIGHT_INSTRUCTIONS,
    SIGHT_SCHEMA,
    Look,
    Planned,
)
from sro.domain.execution.secrets import secret_key_for
from sro.domain.execution.verified_writes import VerifiedWrite
from sro.domain.observation.gesture import Body, Call, Component, Gesture
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


def _twice_over(*, sent: str, then: str) -> tuple[Gesture, Gesture]:
    """The same save, demonstrated twice with different values.

    What a job demonstrated twice actually looks like in the store: one step
    citing both doings, each carrying its own create. The fixture's save posts
    `{"clientCode": …, "dock": "D3"}` to `/api/orders`, so `clientCode` is the
    key that varies and `dock` is the structure.
    """

    def _doing(gesture_id: str, code: str) -> Gesture:
        one = copy.deepcopy(_saver())
        one.id = gesture_id
        keep = next(r for r in one.requests if r.method == "POST" and "orders" in r.url)
        assert keep.request_body is not None, "the fixture's save posts a body"
        text = json.dumps({"clientCode": code, "dock": "D3"})
        one.requests = [replace(keep, request_body=replace(keep.request_body, text=text))]
        return one

    return _doing("doing-1", sent), _doing("doing-2", then)


def test_the_actions_offered_are_the_actions_accepted() -> None:
    """The enum the model is shown and the set its answer is checked against
    are one list. Parting them either offers an action that falls back to the
    gesture's own, or accepts one the schema never allowed."""
    properties = PLAN_SCHEMA["properties"]
    assert isinstance(properties, dict)
    action = properties["action"]
    assert isinstance(action, dict)
    assert frozenset(action["enum"]) == ACTIONS


async def test_a_credential_step_types_whatever_the_model_answers() -> None:
    """The model's action wins over the evidence everywhere but here.

    `click` is a legal answer, and on a step whose evidence is a redacted
    `type` it left `VALUED` and took the credential branch with it: no vault
    lookup, no refusal naming the key, no value. Measured on the deployment
    2026-09-22, `run_2a9d4c7d`: `{"action": "click", "value": null}` at
    `input#password`, the box left empty, nobody signed in -- and the same
    step had typed the vault's password on the eight runs before it.
    """
    secret = next(g for g in _gestures() if g.action.target and g.action.target.secret)
    asker = FakeAsker(
        Answer(
            data={
                "kind": "ui.perform",
                "action": "click",
                "value": None,
                "url": None,
                "locators": [{"strategy": "css_path", "query": "input#password"}],
                "why": "clicking the password field",
            },
            cost_usd=0.0002,
        )
    )
    asked: list[str] = []

    async def _vault(key: str) -> str | None:
        asked.append(key)
        return "from-the-vault"

    planned = await plan_step(
        step=Step(order=1, says="Type the password.", system=None, cites=[secret.id]),
        cited=[secret],
        values={},
        look=Look(url=secret.url, screenshot=None, digest=""),
        origin=None,
        starts_on=None,
        allow_focus=True,
        asker=asker,
        model="gemini-3.8-flash",
        secret_for=_vault,
        tenant_id="acme",
    )

    assert planned.kind == "ui.perform"
    assert planned.payload["action"] == "type", "a credential step was planned as a click"
    assert planned.payload["value"] == "from-the-vault"
    assert asked, "the vault was never asked for the password"


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


async def test_a_learned_locator_leads_the_ladder_and_is_still_visible_only() -> None:
    """A control this skill has already found once by a strategy that worked
    is tried before the evidence's own ladder -- and still constrained to
    what is visible, the same as every other rung."""
    gesture = _typed()
    planned = await plan_step(
        step=Step(
            order=0,
            says="type the code",
            system=None,
            cites=[gesture.id],
            parameters=["clientCode"],
        ),
        learned=LearnedStep(ord=0, strategy="css_path", query="input#clientCode", found_by="sight"),
        cited=[gesture],
        values={"clientCode": "THIRD"},
        look=Look(None, None, ""),
        origin=None,
        starts_on=None,
        allow_focus=False,
        asker=FakeAsker(_answer(action="type", value="THIRD")),
        model="m",
    )

    locators = planned.payload["locators"]
    assert isinstance(locators, list)
    assert locators[0] == {
        "strategy": "css_path",
        "query": "input#clientCode",
        "within": None,
        "visible_only": True,
    }


async def test_an_unusable_learned_locator_is_not_tried_at_all() -> None:
    """`usable` is the gate: a learned step with no strategy or no query is
    nothing to lead the ladder with, and the evidence's own ladder is used as
    if nothing had been learned."""
    gesture = _typed()
    without_learning = await plan_step(
        step=Step(
            order=0,
            says="type the code",
            system=None,
            cites=[gesture.id],
            parameters=["clientCode"],
        ),
        cited=[gesture],
        values={"clientCode": "THIRD"},
        look=Look(None, None, ""),
        origin=None,
        starts_on=None,
        allow_focus=False,
        asker=FakeAsker(_answer(action="type", value="THIRD")),
        model="m",
    )
    with_unusable_learning = await plan_step(
        step=Step(
            order=0,
            says="type the code",
            system=None,
            cites=[gesture.id],
            parameters=["clientCode"],
        ),
        learned=LearnedStep(ord=0, strategy="", query="", found_by="sight"),
        cited=[gesture],
        values={"clientCode": "THIRD"},
        look=Look(None, None, ""),
        origin=None,
        starts_on=None,
        allow_focus=False,
        asker=FakeAsker(_answer(action="type", value="THIRD")),
        model="m",
    )

    assert with_unusable_learning.payload["locators"] == without_learning.payload["locators"]


async def test_a_step_declaring_nothing_is_aimed_at_the_box_the_run_has_a_value_for() -> None:
    """The planner hands `primary_gesture` the names the run holds values under.

    Without that the rule has nothing to go on and aims where mining listed
    first -- on the deployment's `Delete a Customer Type`, a click on no
    component at all, cited before eight typings into the filter box.
    """
    typed = _typed()
    stray = copy.deepcopy(typed)
    stray.id = "ges_stray_click"
    target = stray.action.target
    assert target is not None
    stray.action = replace(
        stray.action,
        kind="click",
        value=None,
        target=replace(
            target, component=Component(item_id="searchField", query="panel#grid button#search")
        ),
    )
    asker = FakeAsker(
        Answer(data={"kind": "ui.perform", "action": "type", "value": "WRONG", "url": None})
    )

    planned = await plan_step(
        # No parameters, the way mining leaves them.
        step=Step(order=0, says="enter search criteria", system=None, cites=[stray.id, typed.id]),
        cited=[stray, typed],
        values={"clientCode": "THIRD"},
        look=Look(url="http://127.0.0.1:63319/", screenshot=None, digest=""),
        origin="http://127.0.0.1:63319",
        starts_on=None,
        allow_focus=True,
        asker=asker,
        model="gemini-3.8-flash",
    )

    locators = planned.payload["locators"]
    assert isinstance(locators, list)
    assert locators[0]["query"] == "panel#clients textfield#clientCode", (
        "aimed at the stray click rather than the box this run has a value for"
    )
    assert planned.payload["value"] == "THIRD"


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


async def test_a_call_planned_for_the_step_a_run_begins_at_can_open_its_own_page() -> None:
    """`starts_on` is what the extension opens a tab at when the operator's own
    is somewhere else, and an `http.send` used not to carry it.

    It never needed to: the steps that walked the browser to the form ran
    first and left a tab on the origin. A job whose write goes out as a call
    performs none of them, and a resumed run can begin at the call itself --
    and `httpSend` answers `no_tab_for_origin` to an operator who simply has no
    tab there. `run_workflow` passes this for the run's FIRST command alone, so
    a later step still cannot drag the browser back to where the job began.
    """
    saver = _saver()
    post = next(r for r in saver.requests if r.method == "POST")
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
        starts_on="http://127.0.0.1:63319/form",
        allow_focus=False,
        asker=asker,
        model="m",
    )

    assert planned.kind == "http.send"
    assert planned.payload["starts_on"] == "http://127.0.0.1:63319/form"
    assert planned.payload["url"] == post.url, "and the call is still the recorded one"


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


async def test_a_struck_header_nothing_can_fetch_live_is_not_named_for_a_live_fetch() -> None:
    """`LIVE_FETCHABLE_HEADERS` is a fixed menu the extension owns, and this is
    the half of the rule the happy path cannot show.

    A recording carries a marker wherever a header was struck out, and only two
    of those names have a live source -- both read off `Ext.Ajax.defaultHeaders`
    on a Blue Yonder page. Naming any other one asks the extension to run JS it
    does not have for a value nobody can supply, so the write goes out short of
    the header either way and the plan has lied about which.
    """
    saver = _saver()
    post = next(r for r in saver.requests if r.method == "POST")
    struck = replace(
        post,
        request_headers={
            "Content-Type": "application/json",
            "CSRF-ENCRYPT-TOKEN": REDACTED,
            # Struck out at the boundary like the one above, and with nothing
            # on the page that could read it back.
            "Authorization": REDACTED,
        },
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

    assert planned.payload["live_headers"] == ["CSRF-ENCRYPT-TOKEN"]
    assert "Authorization" not in planned.payload["headers"], "and it is still not on the wire"


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
    verified_writes: tuple[VerifiedWrite, ...] = (),
    seen: Mapping[str, frozenset[str]] | None = None,
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
        verified_writes=verified_writes,
        seen=seen or {},
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
        assert planned.why == "navigate with no url", url


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


async def test_an_http_plan_carries_the_body_the_operator_sent_where_nothing_varies() -> None:
    """A job with no parameters replays exactly as it was demonstrated, which is
    what most calls still are."""
    saver = _saver()
    post = next(r for r in saver.requests if r.method == "POST")
    assert post.request_body is not None

    planned, _ = await _planned(cited=[saver], answer=_answer(kind="http.send"))

    assert planned.payload["body"] == post.request_body.text
    assert planned.payload["body"], "the fixture's save posts a body"


async def test_an_http_plan_aims_the_operators_body_at_this_runs_values() -> None:
    """The defect this whole path existed with: the payload carried
    `call.request_body.text` and nothing put the run's values into it, so a
    replay created the record the DEMONSTRATION created. The operator asks for
    one code and the warehouse is told another, and answers 201 for it.
    """
    first, second = _twice_over(sent="ACME", then="WIDGET")
    step = Step(order=0, says="save", system=None, cites=[first.id, second.id])

    planned, _ = await _planned(
        cited=[first, second],
        answer=_answer(kind="http.send"),
        step=step,
        values={"clientCode": "THIRD"},
        verified_writes=(VerifiedWrite(method="POST", path_pattern="/api/orders"),),
        seen={"clientCode": frozenset({"ACME", "WIDGET"})},
    )

    assert planned.kind == "http.send"
    assert json.loads(str(planned.payload["body"]))["clientCode"] == "THIRD"
    assert planned.rewrote is True
    assert planned.filled == {"clientCode": "clientCode"}
    assert planned.confirm == {}


async def test_a_body_that_cannot_be_aimed_downgrades_to_clicking_save() -> None:
    """The form transformed what was typed -- the ledger's own gotcha, `csttyp
    truncates at 4 chars` -- so the typed value is nowhere in the body and
    nothing can say where this run's value goes. Sending the recorded bytes
    would send the demonstration's value, so it falls through to the interface
    the same way an unreplayable body does, and the click still works.
    """
    first, second = _twice_over(sent="ACME", then="WIDGET")
    step = Step(order=0, says="save", system=None, cites=[first.id, second.id])

    planned, _ = await _planned(
        cited=[first, second],
        answer=_answer(kind="http.send"),
        step=step,
        values={"clientCode": "THIRD"},
        verified_writes=(VerifiedWrite(method="POST", path_pattern="/api/orders"),),
        # The operator was seen typing something the body never carried.
        seen={"clientCode": frozenset({"TRUNCATED"})},
    )

    assert planned.kind == "ui.perform"
    assert "cannot be re-aimed" in planned.why


async def test_a_value_that_would_pick_a_row_is_refused_when_the_step_also_writes() -> None:
    """Opening the list first would perform this step's own write to find out
    what is on it, and performing the recorded choice instead of the one
    asked for would write the wrong thing -- so this step is refused by name."""
    gesture = _saver()
    planned, _ = await _planned(
        cited=[gesture],
        answer=_answer(action="click"),
        step=Step(
            order=3, says="pick the depot", system=None, cites=[gesture.id], parameters=["depot"]
        ),
        values={"depot": "D3"},
    )

    assert planned.kind == "none"
    assert planned.why == (
        "step 3 was given depot and a click cannot carry a value: this step also writes, so the "
        "list cannot be opened first, and performing it would use the "
        "recorded choice instead of the one asked for"
    )
    assert planned.answer is not None


async def test_a_run_given_no_values_at_all_does_not_claim_a_body_could_not_be_aimed() -> None:
    """Nothing to aim is not the same failure as a value that cannot be found
    in the body -- the second message is reserved for the second case."""
    first, second = _twice_over(sent="ACME", then="WIDGET")
    step = Step(order=0, says="save", system=None, cites=[first.id, second.id])

    planned, _ = await _planned(
        cited=[first, second],
        answer=_answer(kind="http.send"),
        step=step,
        values={},
        verified_writes=(VerifiedWrite(method="POST", path_pattern="/api/orders"),),
        seen={"clientCode": frozenset({"ACME", "WIDGET"})},
    )

    assert "cannot be re-aimed" not in planned.why


async def test_an_http_plan_for_a_step_whose_evidence_made_no_call_plans_nothing() -> None:
    gesture = _typed()  # a typed field; the recorder heard no traffic from it
    planned, _ = await _planned(cited=[gesture], answer=_answer(kind="http.send"))
    assert (planned.kind, planned.payload) == ("none", {})
    assert planned.why == "http.send planned for a step whose evidence carries no call"
    assert planned.answer is not None


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
    assert asked["evidence"].splitlines()[1] == '  "step": {', "pretty-printed at two spaces"
    evidence = json.loads(asked["evidence"])
    assert evidence["previous_attempt_failed"] == "the code was not typed"
    assert evidence["previous_attempt_left"]["screenshot"] == "the second image"
    assert evidence["previous_attempt_left"]["url"].endswith("?after")
    assert evidence["previous_attempt_left"]["screen_text"] == "still empty"


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


def _seen(
    width: int = 800,
    height: int = 600,
    picture: bytes | None = b"png",
    refused: str = "",
) -> Look:
    return Look(
        url="http://127.0.0.1:63319/form",
        screenshot=picture,
        digest="Client Code Save",
        width=width,
        height=height,
        refused=refused,
    )


async def _by_sight(
    answer: Answer,
    look: Look | None = None,
    values: Mapping[str, str] | None = None,
    gesture: Gesture | None = None,
    opened: bool = False,
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
        opened=opened,
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
    # And with the browser's own reason where it gave one. Measured on the
    # deployment, 2026-09-17 at 15:20: two runs gave up on the same step saying
    # "no screen to look at", and nothing anywhere said whether the tab had
    # refused the screen, was not the visible one, or had answered with a
    # picture of no size. Three faults, three fixes, told apart by nothing.
    said, _ = await _by_sight(
        _sight(),
        look=_seen(picture=None, refused="focus_not_permitted: not the visible one"),
    )
    assert said.why == "no screen to look at: focus_not_permitted: not the visible one"
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


async def _picking(
    *,
    opened: bool = False,
    values: Mapping[str, str] | None = None,
    allow_focus: bool = True,
    starts_on: str | None = "http://127.0.0.1:63319/form",
) -> Planned:
    """A step whose parameter can only be chosen from a list.

    The model answers `click`, which carries no value, and the step was given
    one -- so the planner splits it into two clicks: open the control, then
    click the row named by the value asked for. `_typed()` cites a gesture with
    no request on it, so the step does not write and the list may be opened
    first.
    """
    gesture = _typed()
    asker = FakeAsker(_answer(action="click"))
    return await plan_step(
        step=Step(
            order=0,
            says="choose the client",
            system=None,
            cites=[gesture.id],
            parameters=["clientCode"],
        ),
        cited=[gesture],
        values={"clientCode": "THIRD"} if values is None else values,
        look=Look(None, None, ""),
        origin="http://127.0.0.1:63319",
        starts_on=starts_on,
        allow_focus=allow_focus,
        asker=asker,
        model="m",
        opened=opened,
    )


async def test_a_value_a_click_cannot_carry_opens_the_list_first() -> None:
    """The first of the two clicks, and `opens` is what tells the runner that
    nothing has been done yet: it sends this command and plans the step again
    rather than moving on, the same shape `navigate` has."""
    planned = await _picking()

    assert planned.kind == "ui.perform"
    assert planned.opens is True
    assert "opening the list" in planned.why
    # The whole payload, because every key in it is one the extension matches
    # on: an action spelled `CLICK` reaches a browser that has no such command.
    assert planned.payload["action"] == "click"
    assert planned.payload["value"] is None
    assert planned.payload["origin"] == "http://127.0.0.1:63319"
    # The permission to move somebody's tab, and the page the click starts on.
    # Neither had a test, and a planner that stopped threading either would
    # have stayed green: a run that may not take focus cannot reach a control
    # the page only renders when focused.
    assert planned.payload["allow_focus"] is True
    assert planned.payload["starts_on"] == "http://127.0.0.1:63319/form"
    locators = planned.payload["locators"]
    assert isinstance(locators, list) and locators, "the evidence's own ladder opens it"
    assert planned.answer is not None


async def test_the_second_click_is_the_row_named_by_the_value_asked_for() -> None:
    """Not the row the recording happened to contain. The operator's own choice
    is what the evidence carries, and using it would do the job with somebody
    else's client code."""
    planned = await _picking(opened=True)

    assert planned.opens is False
    assert "choosing THIRD" in planned.why
    assert planned.payload["locators"] == [
        {"strategy": "text", "query": "THIRD", "within": None, "visible_only": True}
    ]
    assert planned.payload["action"] == "click" and planned.payload["value"] is None
    assert planned.payload["origin"] == "http://127.0.0.1:63319"
    assert planned.payload["allow_focus"] is True
    assert planned.payload["starts_on"] == "http://127.0.0.1:63319/form"
    assert planned.answer is not None


async def test_a_pick_that_may_not_take_the_screen_says_nothing_about_focus() -> None:
    # Absent, not False: the extension refuses a command that would move a tab
    # unless the key is there, and a `False` it had to read would be a second
    # way to say the same thing.
    planned = await _picking(allow_focus=False, starts_on=None)

    assert "allow_focus" not in planned.payload
    assert "starts_on" not in planned.payload


async def test_a_click_nobody_asked_a_value_of_is_planned_as_itself() -> None:
    # The split only happens where a value was supplied for the step. A plain
    # Save is a click, and turning it into two would click Save twice.
    planned = await _picking(values={})

    assert planned.opens is False
    assert planned.payload["action"] == "click"
    assert "opening the list" not in planned.why


async def test_the_sight_rung_opens_what_the_control_is_under() -> None:
    """Measured on the deployment, 2026-09-17.

    The step clicks the "Customer Types" tab, and this rung answered "not
    currently visible on the screen. It is likely under the 'Partners' menu
    which needs to be opened first" -- the right answer, as prose, with no way
    to act on it. The run then did the job by its call, which is the fallback
    and not the point: a job whose write has no call would have stopped there
    holding the fix.

    The same two-click shape a dropdown already uses: this one opens, the
    runner plans again with a fresh picture, and the second answers the step.
    """
    planned, _ = await _by_sight(
        _sight(
            found=False,
            points_at="what_reveals_it",
            x=120,
            y=44,
            why="not visible; it is under the Partners menu",
        )
    )

    assert planned.kind == "ui.perform_at"
    assert planned.opens is True, "the runner would have taken this for the step itself"
    assert planned.payload["x"] == 120
    assert planned.payload["action"] == "click"
    assert "Partners" in planned.why


async def test_an_older_answer_with_no_enum_still_means_what_it_meant() -> None:
    """`points_at` is required, so every current answer carries it -- but a
    deployment pinned to an earlier model answers with `found` alone, and those
    answers still mean what they always did."""
    planned, _ = await _by_sight(_sight(found=True, x=40, y=50, action="click"))
    assert planned.kind == "ui.perform_at"

    refused, _ = await _by_sight(_sight(found=False, why="not on this screen"))
    assert refused.kind == "none"


async def test_a_dialog_in_the_way_is_dismissed_like_a_menu_is_opened() -> None:
    """Measured on the deployment, 2026-09-17. The screen rung walked the menu
    and reached the Customer Types screen -- and a modal sat over the form:

        Exception Occurred
        Processing completed without exception. (Status: 0)   [ OK ]

    A warehouse system puts one of those in front of a page for things that
    are not errors at all. Until this, the rung could only clear it by calling
    an OK button "what reveals it", which the instructions steer against -- so
    a run reached the right screen and stopped in front of a notice.

    One answer for both shapes: click it, take a new picture, and the step is
    what you answer then.
    """
    planned, _ = await _by_sight(
        _sight(
            found=False,
            points_at="what_is_in_the_way",
            x=300,
            y=420,
            why="a dialog headed Exception Occurred is over the form",
        )
    )

    assert planned.kind == "ui.perform_at"
    assert planned.opens is True, "the runner would have taken this for the step itself"
    assert planned.payload["x"] == 300
    assert "clearing what is in the way" in planned.why


async def test_a_menu_may_be_opened_again_because_a_screen_has_more_than_one() -> None:
    """A screen is answered with as many clicks as it takes: open the menu, see
    the item, click it. A rung allowed exactly one thing could not reach a
    control under a menu nobody demonstrated -- measured on the deployment
    across 2026-09-16 and 17, where that job never once reached its form.

    How many is the RUNNER's to bound (`K_OPENINGS`), and it refuses the rest.
    What this rung must not do is point at the same thing twice, which the
    fresh picture it is shown each time is what settles.
    """
    planned, _ = await _by_sight(
        _sight(found=False, points_at="what_reveals_it", x=120, y=44, why="under the next one"),
        opened=True,
    )

    assert planned.kind == "ui.perform_at"
    assert planned.opens is True
    assert planned.payload["x"] == 120


async def test_a_point_to_open_that_is_not_on_the_screen_is_not_taken() -> None:
    """The rung's whole rule is that it does not guess, and the picture IS the
    viewport: a point outside it was not seen."""
    planned, _ = await _by_sight(
        _sight(found=False, points_at="what_reveals_it", x=4000, y=44, why="under a menu")
    )

    assert planned.kind == "none"


async def test_the_sight_rung_with_no_picture_costs_nothing_and_says_so() -> None:
    """`kind` is what the runner switches on, and `none` is what stops it.

    Both early returns hand back a blank `Answer()` rather than the model's,
    because no model was asked -- a step that reads as having cost money is a
    step the day's spend is wrong about.
    """
    asker = FakeAsker(_answer())
    planned = await plan_by_sight(
        step=Step(order=0, says="type the code", system=None, cites=[_typed().id]),
        cited=[_typed()],
        values={},
        look=Look(url="http://127.0.0.1:63319/form", screenshot=None, digest=""),
        origin=None,
        asker=asker,
        model="m",
        failure=None,
    )

    assert planned.kind == "none"
    assert planned.payload == {}
    assert planned.why == "no screen to look at"
    assert planned.answer is not None and planned.answer.cost_usd == 0.0
    assert asker.asked == [], "nothing was asked, so nothing may be billed"


async def test_the_sight_rung_with_a_picture_and_no_evidence_asks_nobody() -> None:
    # A step whose every citation is gone or untargeted. The screen is there
    # and there is still nothing to say about what to find on it.
    asker = FakeAsker(_answer())
    planned = await plan_by_sight(
        step=Step(order=0, says="type the code", system=None, cites=["ges-gone"]),
        cited=[],
        values={},
        look=_seen(),
        origin=None,
        asker=asker,
        model="m",
        failure=None,
    )

    assert planned.kind == "none"
    assert planned.payload == {}
    assert planned.why == "no evidence to act on"
    assert asker.asked == []


# A password the recording was never allowed to keep


def _secret_field() -> Gesture:
    """The gesture a login leaves behind: a type into a field marked secret,
    with no value, because the boundary struck it out."""
    return next(g for g in _gestures() if g.action.kind == "type" and g.action.secret)


def _says_type() -> FakeAsker:
    return FakeAsker(
        Answer(
            data={
                "kind": "ui.perform",
                "action": "type",
                "value": None,
                "url": None,
                "locators": [],
                "why": "the step signs in",
            },
            cost_usd=0.0001,
        )
    )


async def test_a_password_comes_from_the_vault_and_never_from_the_recording() -> None:
    """The operator's question answered. The evidence still holds no value --
    it never will -- and the step types one anyway, fetched at the moment it is
    sent, by a key built from the system and the field.
    """
    field = _secret_field()
    asked: list[str] = []

    async def vault(key: str) -> str | None:
        asked.append(key)
        return "kept-once-deliberately"

    planned = await plan_step(
        step=Step(order=0, says="sign in", system=None, cites=[field.id]),
        cited=[field],
        values={},
        look=Look(None, None, ""),
        origin=None,
        starts_on=None,
        allow_focus=False,
        asker=_says_type(),
        model="m",
        tenant_id="new",
        secret_for=vault,
    )

    assert planned.payload["value"] == "kept-once-deliberately"
    assert field.action.value is None, "the recording still holds nothing"
    assert asked == [secret_key_for("new", field)]


async def test_a_step_that_needs_a_password_nobody_stored_refuses_by_name() -> None:
    """Not a blank typed into a login form. A blank submits, fails, and looks
    to everybody like the job being broken -- where this says the exact key an
    operator can go and store."""
    field = _secret_field()

    async def nothing_stored(key: str) -> str | None:
        return None

    planned = await plan_step(
        step=Step(order=0, says="sign in", system=None, cites=[field.id]),
        cited=[field],
        values={},
        look=Look(None, None, ""),
        origin=None,
        starts_on=None,
        allow_focus=False,
        asker=_says_type(),
        model="m",
        tenant_id="new",
        secret_for=nothing_stored,
    )

    assert planned.kind == "none"
    assert secret_key_for("new", field) in planned.why
    assert planned.answer is not None


async def test_a_run_with_no_vault_says_so_rather_than_typing_nothing() -> None:
    field = _secret_field()

    planned = await plan_step(
        step=Step(order=0, says="sign in", system=None, cites=[field.id]),
        cited=[field],
        values={},
        look=Look(None, None, ""),
        origin=None,
        starts_on=None,
        allow_focus=False,
        asker=_says_type(),
        model="m",
    )

    assert planned.kind == "none"
    assert planned.payload == {}
    assert "vault" in planned.why
    assert planned.answer is not None


async def test_a_password_key_defaults_to_no_tenant_when_none_is_given() -> None:
    """A run with no tenant of its own still keys the vault lookup by
    something -- an empty tenant segment, not a placeholder."""
    field = _secret_field()
    asked: list[str] = []

    async def vault(key: str) -> str | None:
        asked.append(key)
        return "kept"

    await plan_step(
        step=Step(order=0, says="sign in", system=None, cites=[field.id]),
        cited=[field],
        values={},
        look=Look(None, None, ""),
        origin=None,
        starts_on=None,
        allow_focus=False,
        asker=_says_type(),
        model="m",
        secret_for=vault,
    )

    assert asked == [secret_key_for("", field)]


async def test_the_secret_key_falls_back_to_the_gestures_system_with_no_url() -> None:
    """A step with no url of its own -- nothing the browser navigated to --
    still has to be keyed by wherever it was demonstrated."""
    field = copy.deepcopy(_secret_field())
    field.url = None
    field.page_url = None
    asked: list[str] = []

    async def vault(key: str) -> str | None:
        asked.append(key)
        return "kept"

    await plan_step(
        step=Step(order=0, says="sign in", system=None, cites=[field.id]),
        cited=[field],
        values={},
        look=Look(None, None, ""),
        origin=None,
        starts_on=None,
        allow_focus=False,
        asker=_says_type(),
        model="m",
        tenant_id="new",
        secret_for=vault,
    )

    assert asked == [secret_key_for("new", field)]


async def test_a_step_that_needs_a_password_says_which_one_as_structure() -> None:
    """The operator who has to fix this is a person in a warehouse with a panel
    open. They have no console, no shell and no reason to know what a vault key
    is -- so the panel has to draw "this job needs your password for <system>"
    and a box, which it cannot do by parsing a sentence.
    """
    field = _secret_field()

    async def nothing_stored(key: str) -> str | None:
        return None

    planned = await plan_step(
        step=Step(order=0, says="sign in", system=None, cites=[field.id]),
        cited=[field],
        values={},
        look=Look(None, None, ""),
        origin=None,
        starts_on=None,
        allow_focus=False,
        asker=_says_type(),
        model="m",
        tenant_id="new",
        secret_for=nothing_stored,
    )

    needs = planned.payload["needs_secret"]
    assert isinstance(needs, dict)
    assert needs["key"] == secret_key_for("new", field)
    assert needs["field"] and needs["system"], "a card cannot ask for a password it cannot name"
    # And still no value anywhere near it.
    assert "value" not in planned.payload


def _chose_from_a_list() -> Gesture:
    """The click that answers a filter box: a row in the list it opened.

    Ext's own xtype for that list is `boundlist`; an application that
    subclasses it keeps the word, and this deployment's is `rpBoundList`.
    """
    one = copy.deepcopy(_typed())
    one.id = "ges_boundlist"
    target = one.action.target
    assert target is not None
    # The whole sentence the page puts on the row, as the recorder captured
    # it: `<what was typed> in <Column>`. `_typed()` types ACME-4471.
    one.action = replace(
        one.action,
        kind="click",
        value=None,
        target=replace(
            target,
            name="ACME-4471 in Customer Type",
            text="ACME-4471 in Customer Type",
            component=Component(query="rpBoundList", xtype="rpBoundList"),
        ),
    )
    return one


async def _filtering(
    *, opened: bool = False, says: str = "type", parameters: tuple[str, ...] = ("clientCode",)
) -> Planned:
    """A step whose demonstration TYPED into a box and then chose from the list
    it opened -- which is what a filter box is."""
    typed, chosen = _typed(), _chose_from_a_list()
    return await plan_step(
        step=Step(
            order=0,
            says="Enter filter criteria to search for the customer type",
            system=None,
            cites=[typed.id, chosen.id],
            parameters=list(parameters),
        ),
        cited=[typed, chosen],
        values={"clientCode": "MRN5"},
        look=Look(None, None, ""),
        origin="http://127.0.0.1:63319",
        starts_on="",
        allow_focus=False,
        asker=FakeAsker(_answer(action=says, value="MRN5" if says == "type" else None)),
        model="m",
        opened=opened,
    )


async def test_a_box_that_answers_with_a_list_is_typed_into_and_then_chosen_from() -> None:
    """Measured on the deployment 2026-09-22 at 09:51. `Delete a Customer
    Type` typed MRN5 into the filter box, the suggestion list offered "MRN5 in
    Customer Type", nothing clicked it, and the next step failed with "the
    customer type row is not selected".

    The two-click compound beside this one handles a step whose demonstration
    CLICKED a combobox. A step whose demonstration TYPED into one got here
    instead, because a type carries a value and that compound only ever ran
    for actions that do not.
    """
    planned = await _filtering()

    assert planned.kind == "ui.perform"
    assert planned.payload["action"] == "type"
    assert planned.payload["value"] == "MRN5"
    assert planned.opens is True, "the runner would have moved on with the list still open"


async def test_the_second_half_clicks_the_row_the_value_names() -> None:
    planned = await _filtering(opened=True)

    assert planned.opens is False
    assert planned.payload["action"] == "click"
    assert planned.payload["value"] is None
    # The page's own wording with this run's value in it -- never the value
    # alone, which finds the GRID's cell and opens the record.
    assert planned.payload["locators"] == [
        {
            "strategy": "role_and_name",
            "query": "option|MRN5 in Customer Type",
            "within": None,
            "visible_only": True,
        }
    ]


async def test_the_row_is_chosen_even_when_the_model_says_click_with_the_list_open() -> None:
    """Measured on the deployment 2026-09-22 at 13:12.

    The first half typed MRN1 and the list opened. Re-asked with the list in
    front of it the model answered "click" -- the right act -- and the second
    half only ran for a `type`, so the plan fell through to a click on the box
    itself. Ext picked a row on its own, and the run filtered "Create Shipment
    By = MRN1". The step declared no parameters, as mining leaves it.
    """
    planned = await _filtering(opened=True, says="click", parameters=())

    assert planned.payload["locators"] == [
        {
            "strategy": "role_and_name",
            "query": "option|MRN5 in Customer Type",
            "within": None,
            "visible_only": True,
        }
    ], "the list was open and the plan clicked something other than the demonstrated row"


async def test_a_box_that_takes_a_value_and_closes_is_typed_into_once() -> None:
    """Read off the step's own evidence and never assumed. A form field whose
    demonstration shows no list is untouched -- and there are far more of those
    than there are filter boxes."""
    typed = _typed()
    planned = await plan_step(
        step=Step(
            order=0,
            says="type the code",
            system=None,
            cites=[typed.id],
            parameters=["clientCode"],
        ),
        cited=[typed],
        values={"clientCode": "MRN5"},
        look=Look(None, None, ""),
        origin="http://127.0.0.1:63319",
        starts_on="",
        allow_focus=False,
        asker=FakeAsker(_answer(action="type", value="MRN5")),
        model="m",
    )

    assert planned.payload["action"] == "type"
    assert planned.opens is False, "a plain field was treated as a list"


async def test_a_list_whose_wording_the_demonstration_does_not_carry_is_left_alone() -> None:
    """A guessed name clicks something nobody demonstrated.

    Where the recorded option does not contain what was recorded as typed,
    there is no template to substitute into -- so the step is typed once and
    the compound stays out of it.
    """
    typed, chosen = _typed(), _chose_from_a_list()
    target = chosen.action.target
    assert target is not None
    chosen.action = replace(
        chosen.action, target=replace(target, name="something else entirely", text="")
    )

    planned = await plan_step(
        step=Step(
            order=0,
            says="filter",
            system=None,
            cites=[typed.id, chosen.id],
            parameters=["clientCode"],
        ),
        cited=[typed, chosen],
        values={"clientCode": "MRN5"},
        look=Look(None, None, ""),
        origin="http://127.0.0.1:63319",
        starts_on="",
        allow_focus=False,
        asker=FakeAsker(_answer(action="type", value="MRN5")),
        model="m",
    )

    assert planned.payload["action"] == "type"
    assert planned.opens is False


async def test_a_click_on_something_other_than_a_list_is_not_a_list() -> None:
    """Typed, then clicked Save is the commonest shape there is. Reading any
    click as a list would turn every one of those into two commands, the
    second hunting an option that does not exist."""
    typed = _typed()
    after = copy.deepcopy(typed)
    after.id = "ges_a_button"
    target = after.action.target
    assert target is not None
    after.action = replace(
        after.action,
        kind="click",
        value=None,
        target=replace(
            target,
            name="ACME-4471 in Customer Type",
            component=Component(query="toolbar button#saveButton", xtype="button"),
        ),
    )

    planned = await plan_step(
        step=Step(
            order=0,
            says="type it and save",
            system=None,
            cites=[typed.id, after.id],
            parameters=["clientCode"],
        ),
        cited=[typed, after],
        values={"clientCode": "MRN5"},
        look=Look(None, None, ""),
        origin="http://127.0.0.1:63319",
        starts_on="",
        allow_focus=False,
        asker=FakeAsker(_answer(action="type", value="MRN5")),
        model="m",
    )

    assert planned.payload["action"] == "type"
    assert planned.opens is False, "a Save button was taken for a dropdown list"


async def test_a_replayed_delete_goes_to_the_record_this_run_named() -> None:
    """The plan knew the url and the payload sent the recording's: a delete's
    value is in its path, so the recording's url names the demonstration's
    record -- MRN5, already gone -- and not the one this run was asked for."""
    from sro.application.execution.plan_step import replay_without_asking

    doings = []
    for n, code in enumerate(("MRN5", "DDLS")):
        one = copy.deepcopy(_saver())
        one.id = f"ges_delete_{n}"
        one.requests = [
            replace(
                one.requests[0],
                method="DELETE",
                url=f"http://127.0.0.1:63319/api/customerTypes/{code}?siteId=SG",
                request_body=None,
                status=200,
                failure_reason=None,
                started_at=one.at,
            )
        ]
        doings.append(one)

    planned = replay_without_asking(
        step=Step(order=4, says="confirm", system=None, cites=[one.id for one in doings]),
        cited=doings,
        values={"Customer Type": "MRN1"},
        verified_writes=(VerifiedWrite("DELETE", "/api/customerTypes/{id}"),),
        seen={"Customer Type": frozenset({"MRN5", "DDLS"})},
    )

    assert planned is not None
    assert planned.payload["url"] == "http://127.0.0.1:63319/api/customerTypes/MRN1?siteId=SG"
