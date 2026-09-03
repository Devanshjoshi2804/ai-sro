from rig.correlate import correlate
from rig.intents import INTENT_SCHEMA, TAIL, one_line, read_gesture
from rig.models import Answer, FakeAsker
from rig.records import Intent
from rig.wire import Batch
from tests.fixtures import BATCH

MODEL = "gemini-3.8-flash"


def _gestures():
    gestures, _, _ = correlate(Batch.model_validate(BATCH), "new")
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
    secret = next(g for g in _gestures() if g.gesture.secret)
    asker = FakeAsker(_answer())

    await read_gesture(secret, tail=[], asker=asker, model=MODEL)

    assert "hunter2" not in asker.asked[0]["evidence"]
    assert '"value": null' in asker.asked[0]["evidence"]


def test_the_schema_requires_an_act_and_a_reason() -> None:
    assert set(INTENT_SCHEMA["required"]) >= {"act", "why"}


def test_one_line_is_one_line() -> None:
    line = one_line(Intent(gesture_id="ges_1", tenant="new", act="typed a code", object="client"))

    assert "\n" not in line
    assert "typed a code" in line
