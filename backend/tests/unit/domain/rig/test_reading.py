"""The half of a reading that asks nothing: the words, the schema, the line.

The rest of `new_agent_arch/tests/test_intents.py` lives in
`tests/unit/application/rig/test_read_gesture.py`, because it puts a question
to a model.
"""

from sro.domain.observation.gesture import Action, Body, Call, Gesture, Intent, Target, ValueSeen
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


def _typed(field: str, value: str, *, at: float = 10.0, secret: bool = False) -> Gesture:
    """One gesture the recorder captured somebody typing into a named box."""
    return Gesture(
        id=f"ges_typed_{field}_{at}",
        tenant="acme",
        stream_id="str-1",
        batch_id="bat-1",
        at=at,
        url="https://wms.test/customerTypes",
        system="https://wms.test",
        tab_id=1,
        frame_url=None,
        action=Action(
            kind="type",
            at=at,
            value=value,
            secret=secret,
            target=Target(tag="input", name=field, secret=secret),
        ),
        requests=[],
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


def test_every_field_asked_of_the_reading_is_a_field_something_reads() -> None:
    """This schema is the most expensive prompt in the system by volume -- one
    call per gesture, fifty-five of them for an afternoon's work -- so a field
    here is paid for on every one of them.

    `system` was in it until 2026-09-15, with no description saying what it was
    for, and nothing anywhere read the column it was stored in. It was found
    because it was visibly wrong: one warehouse host came back as `Blue
    Yonder`, `BlueYonder`, `JDA WMS`, `WMS` and `WM` across one day's readings.
    Nothing had told the model what to write, and nothing checked what it did.

    The miner never wanted it. `as_evidence` shows a gesture's own `system` --
    the origin the browser recorded, one name per host by construction -- and
    the tail a reading is given is `one_line`, which is `act` and `object`.

    Each name below carries the reader it is paid for. `continues` was the
    one exception until 2026-09-23: nothing consumed it, and every reading paid
    for the model to write it. Adding a field means naming its reader in the
    same commit.
    """
    properties = _in_schema("properties")
    assert isinstance(properties, dict)

    assert set(properties) == {
        "why",  # the reasoning the order exists to force
        "act",  # one_line, and the whole window
        "object",  # one_line, and the whole window
        "page",  # as_evidence
        "values_seen",  # typed_values, values.crossings, learn_parameters
        "confidence",  # read before a reading is trusted
    }
    assert "continu" not in INSTRUCTIONS, "the words still ask for a field nobody reads"


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

    result = with_recent_values(intent, _gesture(), [_typed("a", "1")])

    assert result.values_seen == []


def test_a_write_folds_in_every_field_just_typed() -> None:
    """The real gap: a save click's own reading names one field the click
    itself correlated with, and the fields typed just before it -- recorded
    keystroke by keystroke -- are folded in rather than left off."""
    intent = Intent(
        gesture_id="ges_save", tenant="acme", values_seen=[ValueSeen("customerType", "DSS0001")]
    )
    recent = [
        _typed("longDescription", "leaning", at=10.0),
        _typed("crossDockFlag", "-1", at=11.0),
    ]
    # The body a real save sends, carrying one of the typed values: that is what
    # earns the fold, and a keepalive or a telemetry post never does.
    sent = _body_call('{"customerType":"DSS0001","longDescription":"leaning"}')

    result = with_recent_values(intent, _gesture(requests=[sent]), recent)

    assert {seen.field: seen.value for seen in result.values_seen} == {
        "customerType": "DSS0001",
        "longDescription": "leaning",
        "crossDockFlag": "-1",
    }


def test_a_field_typed_twice_keeps_the_later_value() -> None:
    recent = [_typed("code", "DSS0001", at=10.0), _typed("code", "DPP0002", at=11.0)]
    intent = Intent(gesture_id="ges_save", tenant="acme", values_seen=[])
    sent = _body_call('{"code":"DPP0002"}')

    result = with_recent_values(intent, _gesture(requests=[sent]), recent)

    assert [seen.value for seen in result.values_seen if seen.field == "code"] == ["DPP0002"]


def test_the_reading_handed_over_is_not_the_one_rewritten() -> None:
    """`with_` names a copy. It mutated its argument in place for a while, and
    the caller holding that reading had no way to know."""
    intent = Intent(
        gesture_id="ges_save", tenant="acme", values_seen=[ValueSeen("code", "DSS0001")]
    )
    sent = _body_call('{"code":"DSS0001","extra":"leaning"}')

    result = with_recent_values(intent, _gesture(requests=[sent]), [_typed("extra", "leaning")])

    assert result is not intent
    assert [seen.field for seen in intent.values_seen] == ["code"], "the argument was rewritten"
    assert {seen.field for seen in result.values_seen} == {"code", "extra"}


def test_the_writes_own_reading_wins_over_what_was_typed() -> None:
    """The write's own reading is the more direct evidence for whatever it
    actually named, so it is applied last and wins a field name it shares
    with an earlier keystroke."""
    intent = Intent(gesture_id="ges_save", tenant="acme", values_seen=[ValueSeen("code", "FRESH")])
    sent = _body_call('{"code":"STALE"}')

    result = with_recent_values(intent, _gesture(requests=[sent]), [_typed("code", "STALE")])

    assert [seen.value for seen in result.values_seen if seen.field == "code"] == ["FRESH"]


def _body_call(text: str, *, status: int = 200, method: str = "POST") -> Call:
    return Call(
        method=method,
        url="https://wms.test/data/customerTypes",
        status=status,
        request_body=Body(text=text, size_bytes=len(text), mime_type="application/json"),
    )


def _typed_before(value: str) -> list[Gesture]:
    return [_typed("code", value)]


def test_a_save_that_sent_what_was_typed_folds_the_tail() -> None:
    """The case the fold exists for: the form went out carrying the value."""
    gesture = _gesture(requests=[_body_call('{"customerType":"DSS0001"}')])

    result = with_recent_values(
        Intent(gesture_id="g", tenant="acme"), gesture, _typed_before("DSS0001")
    )

    assert [seen.value for seen in result.values_seen] == ["DSS0001"]


def test_a_keepalive_is_a_write_by_method_and_folds_nothing() -> None:
    """Measured on one real capture: five of the fifteen gestures `is_write`
    called writes were `sessionKeepAlive`, which sends no body at all."""
    gesture = _gesture(
        requests=[Call(method="POST", url="https://wms.test/sessionKeepAlive", status=200)]
    )

    assert is_write(gesture) is True
    assert (
        with_recent_values(
            Intent(gesture_id="g", tenant="acme"), gesture, _typed_before("DSS0001")
        ).values_seen
        == []
    )


def test_telemetry_carries_a_body_and_still_folds_nothing() -> None:
    """The other four: posts to `webPerformanceEntries/batch`, which is the WMS
    uploading its own timings. A body, a 2xx, and nothing the operator typed."""
    telemetry = '[{"perfDate":"2026-09-10T11:25:32-04:00","name":"WM.common.view","duration":69}]'
    gesture = _gesture(requests=[_body_call(telemetry)])

    result = with_recent_values(
        Intent(gesture_id="g", tenant="acme"), gesture, _typed_before("DSS0001")
    )

    assert result.values_seen == []


def test_a_value_too_short_to_mean_anything_does_not_earn_the_fold() -> None:
    """`0` appears in every payload ever sent, so matching on one would hand
    the fold straight back to the telemetry post."""
    gesture = _gesture(requests=[_body_call('{"duration":69,"perfCount":0}')])

    result = with_recent_values(Intent(gesture_id="g", tenant="acme"), gesture, _typed_before("0"))

    assert result.values_seen == []
