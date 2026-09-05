from rig.correlate import correlate
from rig.models import Answer, FakeAsker
from rig.planner import PLAN_SCHEMA, Look, plan_step
from rig.wire import Batch
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
