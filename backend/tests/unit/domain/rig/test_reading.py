"""The half of a reading that asks nothing: the words, the schema, the line.

The rest of `new_agent_arch/tests/test_intents.py` lives in
`tests/unit/application/rig/test_read_gesture.py`, because it puts a question
to a model.
"""

from sro.domain.observation.gesture import Intent
from sro.domain.observation.reading import CONFIDENCE_VALUES, INTENT_SCHEMA, one_line


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
