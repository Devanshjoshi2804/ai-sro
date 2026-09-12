"""The half of a reading that asks nothing: the words, the schema, the line.

The rest of `new_agent_arch/tests/test_intents.py` lives in
`tests/unit/application/rig/test_read_gesture.py`, because it puts a question
to a model.
"""

from sro.domain.observation.gesture import Action, Call, Gesture, Intent, ValueSeen
from sro.domain.observation.reading import (
    CONFIDENCE_VALUES,
    INSTRUCTIONS,
    INTENT_SCHEMA,
    is_write,
    one_line,
    with_recent_values,
)


def _gesture(*, kind: str = "click", requests: list[Call] | None = None) -> Gesture:
    return Gesture(
        id="ges_save",
        tenant="acme",
        stream_id="str-1",
        batch_id="bat-1",
        at=100.0,
        url="https://wms.test/customerTypes",
        system="https://wms.test",
        tab_id=1,
        frame_url=None,
        action=Action(kind=kind, at=100.0),
        requests=requests or [],
    )


def _write_call(*, status: int = 201, method: str = "POST") -> Call:
    return Call(method=method, url="https://wms.test/data/customerTypes", status=status)


def _in_schema(*path: str) -> object:
    """One key at a time, because a JSON schema is `dict[str, object]` and the
    layer's own rule is that nothing here reaches for `Any`."""
    found: object = INTENT_SCHEMA
    for key in path:
        assert isinstance(found, dict)
        found = found[key]
    return found


def test_the_schema_requires_an_act_and_a_reason() -> None:
    required = _in_schema("required")
    assert isinstance(required, list)

    assert set(required) >= {"act", "why"}


def test_the_reason_is_asked_for_before_the_act_and_the_confidence_last() -> None:
    """The order is the reasoning order -- a structured answer is written left
    to right -- and nothing asserted it, so a change that claimed to reorder
    this schema and did not was invisible for a whole session. This is what
    makes that claim checkable.

    Both places it is stated have to agree: the key order, which is what the
    SDK converts, and `propertyOrdering`, which is what the API documents.
    """
    properties = _in_schema("properties")
    assert isinstance(properties, dict)
    ordering = _in_schema("propertyOrdering")

    assert list(properties) == ordering, "the two statements of the order disagree"
    assert next(iter(properties)) == "why", "the act was asked for before its reason"
    assert list(properties)[-1] == "confidence", "confidence was set before the answer existed"


def test_the_words_ask_for_the_order_the_schema_imposes() -> None:
    """A prompt that asks for one order while the schema imposes another is a
    prompt arguing with itself, which is what shipped once already."""
    assert "First say why" in INSTRUCTIONS
    assert INSTRUCTIONS.index("First say why") < INSTRUCTIONS.index("name the act")


def test_one_line_is_one_line() -> None:
    line = one_line(Intent(gesture_id="ges_1", tenant="new", act="typed a code", object="client"))

    assert "\n" not in line
    assert "typed a code" in line


def test_the_confidence_vocabulary_is_the_schemas_own() -> None:
    """`CONFIDENCE_VALUES` is the same list the schema offers the model, not a
    second copy of it. Restated, the two drift: the schema grows a fourth word,
    the model starts returning it, and the guard that reads this frozenset nulls
    every one of them -- silently, because a nulled confidence looks exactly
    like a model that declined to give one.
    """
    declared = _in_schema("properties", "confidence", "enum")
    assert isinstance(declared, list)

    assert frozenset(declared) == CONFIDENCE_VALUES
    assert set(declared) == {"high", "medium", "low"}


def test_a_click_with_no_calls_is_not_a_write() -> None:
    assert is_write(_gesture()) is False


def test_a_2xx_post_makes_a_gesture_a_write() -> None:
    assert is_write(_gesture(requests=[_write_call()])) is True


def test_a_failed_write_does_not_count() -> None:
    assert is_write(_gesture(requests=[_write_call(status=500)])) is False


def test_a_get_does_not_count_as_a_write() -> None:
    assert is_write(_gesture(requests=[_write_call(method="GET")])) is False


def test_a_non_write_gesture_keeps_its_own_values_untouched() -> None:
    """No calls at all: `with_recent_values` is a no-op rather than folding
    unrelated history into an ordinary click."""
    intent = Intent(gesture_id="ges_x", tenant="acme", values_seen=[])
    tail = [Intent(gesture_id="ges_0", tenant="acme", values_seen=[ValueSeen("a", "1")])]

    result = with_recent_values(intent, _gesture(), tail)

    assert result.values_seen == []


def test_a_write_folds_in_every_field_the_tail_typed() -> None:
    """The real gap: a save click's own reading names one field the click
    itself correlated with, and the fields typed just before it -- already
    readings sitting in `tail` -- are folded in rather than left off."""
    intent = Intent(
        gesture_id="ges_save", tenant="acme", values_seen=[ValueSeen("customerType", "DSS")]
    )
    tail = [
        Intent(gesture_id="ges_0", tenant="acme", values_seen=[ValueSeen("longDescription", "x")]),
        Intent(gesture_id="ges_1", tenant="acme", values_seen=[ValueSeen("crossDockFlag", "-1")]),
    ]

    result = with_recent_values(intent, _gesture(requests=[_write_call()]), tail)

    assert {seen.field: seen.value for seen in result.values_seen} == {
        "customerType": "DSS",
        "longDescription": "x",
        "crossDockFlag": "-1",
    }


def test_a_field_typed_twice_keeps_the_later_tail_value() -> None:
    tail = [
        Intent(gesture_id="ges_0", tenant="acme", values_seen=[ValueSeen("code", "DSS")]),
        Intent(gesture_id="ges_1", tenant="acme", values_seen=[ValueSeen("code", "DPP")]),
    ]
    intent = Intent(gesture_id="ges_save", tenant="acme", values_seen=[])

    result = with_recent_values(intent, _gesture(requests=[_write_call()]), tail)

    assert [seen.value for seen in result.values_seen if seen.field == "code"] == ["DPP"]


def test_the_reading_handed_over_is_not_the_one_rewritten() -> None:
    """`with_` names a copy. It mutated its argument in place for a while, and
    the caller holding that reading had no way to know."""
    intent = Intent(gesture_id="ges_save", tenant="acme", values_seen=[ValueSeen("code", "DSS")])
    tail = [Intent(gesture_id="ges_0", tenant="acme", values_seen=[ValueSeen("extra", "1")])]

    result = with_recent_values(intent, _gesture(requests=[_write_call()]), tail)

    assert result is not intent
    assert [seen.field for seen in intent.values_seen] == ["code"], "the argument was rewritten"
    assert {seen.field for seen in result.values_seen} == {"code", "extra"}


def test_the_writes_own_reading_wins_over_the_tail() -> None:
    """The write's own reading is the more direct evidence for whatever it
    actually named, so it is applied last and wins a field name it shares
    with the tail."""
    tail = [Intent(gesture_id="ges_0", tenant="acme", values_seen=[ValueSeen("code", "STALE")])]
    intent = Intent(gesture_id="ges_save", tenant="acme", values_seen=[ValueSeen("code", "FRESH")])

    result = with_recent_values(intent, _gesture(requests=[_write_call()]), tail)

    assert [seen.value for seen in result.values_seen if seen.field == "code"] == ["FRESH"]
