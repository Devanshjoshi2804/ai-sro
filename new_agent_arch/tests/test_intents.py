from rig.correlate import correlate
from rig.intents import INSTRUCTIONS, INTENT_SCHEMA, TAIL, one_line, read_gesture
from rig.models import Answer, FakeAsker
from rig.records import Intent
from rig.trim import is_secret, is_secret_name
from rig.wire import Batch
from tests.fixtures import BATCH

MODEL = "gemini-3.8-flash"


def _gestures():
    gestures, _, _, _ = correlate(Batch.model_validate(BATCH), "new")
    return gestures


def _answer(**data) -> Answer:
    base = {
        "act": "typed a client code",
        "object": "client",
        "system": "http://127.0.0.1:63319",
        "page": "orders",
        "values_seen": [{"field": "clientCode", "value": "ACME-4471"}],
        "continues": None,
        "confidence": "high",
        "why": "the field is labelled Client Code",
    }
    return Answer(data={**base, **data}, in_tokens=400, out_tokens=60, cost_usd=0.0005)


async def test_a_gesture_becomes_an_intent() -> None:
    gesture = _gestures()[0]
    asker = FakeAsker(_answer())

    intent = await read_gesture(gesture, tail=[], asker=asker, model=MODEL)

    assert intent.gesture_id == gesture.id
    assert intent.act == "typed a client code"
    assert intent.values_seen[0].field == "clientCode"
    assert intent.confidence == "high"


async def test_the_cost_of_the_call_lands_on_the_intent() -> None:
    asker = FakeAsker(_answer())

    intent = await read_gesture(_gestures()[0], tail=[], asker=asker, model=MODEL)

    assert intent.in_tokens == 400
    assert intent.out_tokens == 60
    assert intent.cost_usd > 0
    assert intent.model == MODEL


async def test_a_refusal_leaves_an_intent_that_says_so() -> None:
    """A failed reading must not lose the gesture; the window still gets it."""
    asker = FakeAsker(Answer(error="503 from the model"))

    intent = await read_gesture(_gestures()[0], tail=[], asker=asker, model=MODEL)

    assert intent.act is None
    assert intent.error == "503 from the model"


async def test_only_the_last_eight_intents_are_carried_as_context() -> None:
    tail = [Intent(gesture_id=f"ges_{n}", tenant="new", act=f"did {n}") for n in range(20)]
    asker = FakeAsker(_answer())

    await read_gesture(_gestures()[0], tail=tail, asker=asker, model=MODEL)

    sent = asker.asked[0]["evidence"]

    assert "did 19" in sent
    assert "did 12" in sent
    assert "did 11" not in sent
    assert TAIL == 8


async def test_a_thin_target_is_asked_about_with_a_picture() -> None:
    gestures = _gestures()
    thin_one = next(g for g in gestures if g.gesture.secret)  # no name, no label
    asker = FakeAsker(_answer(), _answer())

    await read_gesture(thin_one, tail=[], asker=asker, model=MODEL, image=b"PNG")

    assert asker.asked[0]["image"] == b"PNG"


async def test_a_named_target_is_asked_about_without_one() -> None:
    named = next(g for g in _gestures() if g.gesture.kind == "select")
    asker = FakeAsker(_answer())

    await read_gesture(named, tail=[], asker=asker, model=MODEL, image=b"PNG")

    assert asker.asked[0]["image"] is None


async def test_no_credential_value_reaches_the_prompt() -> None:
    """The fixture's own secret gesture already has value:null in raw JSON, so
    it cannot prove this on its own -- there is nothing in it to leak. Mutate a
    real value into a target's `secret` flag after parsing instead, which is
    the one route wire.Gesture's own validator does not re-check (Task 4's
    finding), and is exactly why trim() holds this rule for itself."""
    ordinary = next(g for g in _gestures() if g.gesture.kind == "type" and not g.gesture.secret)
    real_value = ordinary.gesture.value
    assert real_value  # the fixture must actually carry something to leak

    ordinary.gesture.target.secret = True
    asker = FakeAsker(_answer())

    await read_gesture(ordinary, tail=[], asker=asker, model=MODEL)

    assert real_value not in asker.asked[0]["evidence"]
    assert '"value": null' in asker.asked[0]["evidence"]


async def test_a_stray_type_in_values_seen_does_not_crash_the_reading() -> None:
    """The schema is advisory. A model returning values_seen as anything but a
    list must not take the gesture down with it.

    A string here proved nothing: iterating it yields characters, and the
    per-entry dict guard downstream drops every one of them -- so
    `isinstance(seen_list, list)` could be deleted with this green. One
    container checked and its sibling walked past, which is the same shape as
    Task 4's finding. The values that discriminate are the ones that are not
    iterable at all, and the mapping that iterates as its own keys.
    """
    for stray in (7, None, True, {"clientCode": "ACME-4471"}, "none that I can see"):
        asker = FakeAsker(_answer(values_seen=stray))

        intent = await read_gesture(_gestures()[0], tail=[], asker=asker, model=MODEL)

        assert intent.values_seen == [], stray
        assert intent.error is None, stray


async def test_a_wrong_typed_field_does_not_poison_a_later_gestures_reading() -> None:
    """A list where act should be a string used to reach one_line() unguarded,
    and crash on the NEXT gesture that pulled this intent into its tail."""
    asker = FakeAsker(_answer(act=["typed", "something"]))

    intent = await read_gesture(_gestures()[0], tail=[], asker=asker, model=MODEL)
    assert intent.act is None  # unusable, not fabricated

    downstream = FakeAsker(_answer())
    await read_gesture(_gestures()[1], tail=[intent], asker=downstream, model=MODEL)


async def test_a_wrong_typed_values_seen_entry_is_dropped_not_coerced() -> None:
    """A non-str field is unusable (dropped, not str()'d into a fake one); a
    non-str value is treated as unseen ("") rather than fabricated."""
    asker = FakeAsker(
        _answer(
            values_seen=[
                {"field": 123, "value": "should be dropped, field is not a string"},
                {"field": "qty", "value": 7},
                {"field": "clientCode", "value": "ACME-4471"},
            ]
        )
    )

    intent = await read_gesture(_gestures()[0], tail=[], asker=asker, model=MODEL)

    assert [seen.field for seen in intent.values_seen] == ["qty", "clientCode"]
    assert intent.values_seen[0].value == ""
    assert intent.values_seen[1].value == "ACME-4471"


async def test_an_undeclared_confidence_value_is_unusable() -> None:
    """confidence is declared enum ["high","medium","low"] but nothing checked
    it; a model returning "very high" must not store it verbatim."""
    asker = FakeAsker(_answer(confidence="very high"))

    intent = await read_gesture(_gestures()[0], tail=[], asker=asker, model=MODEL)

    assert intent.confidence is None


def test_the_schema_requires_an_act_and_a_reason() -> None:
    assert set(INTENT_SCHEMA["required"]) >= {"act", "why"}


def test_one_line_is_one_line() -> None:
    line = one_line(Intent(gesture_id="ges_1", tenant="new", act="typed a code", object="client"))

    assert "\n" not in line
    assert "typed a code" in line


async def test_a_reading_it_could_not_price_says_so() -> None:
    """Deleting the unpriced hop in read_gesture left the whole suite green."""
    asker = FakeAsker(Answer(data={"act": "did a thing", "why": "because"}, unpriced=True))

    intent = await read_gesture(_gestures()[0], tail=[], asker=asker, model=MODEL)

    assert intent.unpriced is True


async def test_a_credential_the_model_echoed_back_is_never_stored() -> None:
    """The third place values_seen went unguarded, and the only one that
    reaches storage: save_intent writes this verbatim and GET /v1/gestures
    serves it back. The field name is kept; the value is not.

    The field is deliberately not called "password": with that name this passed
    on `is_secret_name` alone, and deleting the `is_secret(gesture)` half -- the
    branch this test exists for -- left the suite green. "Employee Code" is a
    real WMS label that no name rule flags, so the only thing that blanks it is
    the gesture itself being a credential field.
    """
    gesture = next(g for g in _gestures() if g.gesture.secret)
    assert not is_secret_name("Employee Code")  # nothing else can blank this
    asker = FakeAsker(_answer(values_seen=[{"field": "Employee Code", "value": "hunter2"}]))

    intent = await read_gesture(gesture, tail=[], asker=asker, model=MODEL)

    assert [seen.value for seen in intent.values_seen] == [""]
    assert [seen.field for seen in intent.values_seen] == ["Employee Code"]


async def test_a_credential_named_by_the_model_is_dropped_on_a_public_gesture() -> None:
    """The gesture is not secret -- a login click never is -- so `hide` is
    False and the field name is the only thing that says what this holds."""
    gesture = next(g for g in _gestures() if not g.gesture.secret)
    assert not is_secret(gesture)
    asker = FakeAsker(_answer(values_seen=[{"field": "password", "value": "hunter2"}]))

    intent = await read_gesture(gesture, asker=asker, model=MODEL, tail=[])

    assert [seen.value for seen in intent.values_seen] == [""]
    assert [seen.field for seen in intent.values_seen] == ["password"]


async def test_the_model_is_told_what_to_do_and_given_a_response_schema() -> None:
    """`INSTRUCTIONS = ""` and `INTENT_SCHEMA = {}` both left the suite green.

    Nothing asserted that the prompt or the schema ever reach the API. For a
    system whose measured claim is that citation-forcing cut hallucinated steps
    from 21% to under 7.5%, the two rules that force it -- do not guess at a
    value you cannot see, do not describe the HTML -- arriving at the model is
    the claim itself, not a detail.
    """
    asker = FakeAsker(_answer())

    await read_gesture(_gestures()[0], tail=[], asker=asker, model=MODEL)

    asked = asker.asked[0]

    assert asked["instructions"] == INSTRUCTIONS
    assert "Do not guess at a value you cannot see" in asked["instructions"]
    assert "Do not describe the HTML" in asked["instructions"]

    assert asked["schema"] == INTENT_SCHEMA
    assert set(asked["schema"]["required"]) == {"act", "why"}
    assert set(asked["schema"]["properties"]) >= {
        "act",
        "object",
        "values_seen",
        "continues",
        "confidence",
        "why",
    }


async def test_an_empty_continues_is_not_a_continuation() -> None:
    """The schema itself says "empty unless it continues the last doing", so
    `""` is what a model returns for most gestures. Stored verbatim it is
    neither a link nor an absence, and `continues` is what plan 2 walks to
    join gestures into a workflow."""
    asker = FakeAsker(_answer(continues=""))

    intent = await read_gesture(_gestures()[0], tail=[], asker=asker, model=MODEL)

    assert intent.continues is None
