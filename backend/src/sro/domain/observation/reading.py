"""A3 — the words one gesture is read in, and what a model's answer becomes.

Everything here is arithmetic over an answer that has already come back: the
instructions, the response schema, the confidence vocabulary, the one line an
intent contributes to the next gesture's context, and the parsing that turns a
model's JSON into an `Intent`. The call itself is
`sro.application.observation.read_gesture`, which is the only half that needs a
port.

Ported from `new_agent_arch/src/rig/intents.py`. The schema is advisory --
nothing between the model and this file enforces it -- so every field is read
back defensively here rather than trusted, and a field that came back the wrong
type is treated as unusable rather than coerced into a plausible-looking one.
"""

from __future__ import annotations

from dataclasses import replace

from sro.domain.observation.gesture import Gesture, Intent, ValueSeen
from sro.domain.observation.redaction import is_secret_name
from sro.domain.observation.trim import is_secret
from sro.domain.observation.values import K_MIN_VALUE_LEN
from sro.domain.shared.prices import Answer

TAIL = 8
"""How many previous readings a gesture is read against.

`continues` is decided from these lines, so this is the whole memory one
reading has of the doing it belongs to. Eight is what the measured day's
longest job fits inside; every reading pays for them in prompt tokens, once per
gesture, thousands of times a day."""

INSTRUCTIONS = """You are reading one thing a warehouse operator just did in a browser.

You are given the gesture, the control it touched, the network calls it caused,
and a few lines of what the same person did just before.

First say why: point at the one piece of evidence (the control's label, its
component metadata, the request body, the picture) that tells you what
happened. Only then name the act, in the words an operator would use, and the
object they were working on. List the values you can see them entering. Say
whether this looks like a continuation of the previous doing.

If the evidence is thin -- an icon with no label, no field, nothing typed --
say so in why and mark confidence low, rather than guessing at a specific act.

Do not guess at a value you cannot see. Do not describe the HTML."""

_CONFIDENCE = ["high", "medium", "low"]
"""The one declaration of the confidence vocabulary; the schema below and
`CONFIDENCE_VALUES` are both this list. Restated in two places they drift, and
a word the schema offers that the guard has never heard of is nulled on the way
in -- indistinguishable from a model that declined to give one."""

INTENT_SCHEMA: dict[str, object] = {
    "type": "object",
    # `why` first, and `confidence` last, because a structured answer is
    # written left to right: the model fills these fields in this order, so
    # this order is the order it thinks in. Asked for `act` first, it commits
    # to a verb and then writes the sentence that defends it; asked for `why`
    # first, it has to name the evidence -- the label, the component metadata,
    # the request body, the picture -- before it names the act, and states a
    # confidence with both already written down. INSTRUCTIONS asks for exactly
    # this sequence, and a prompt that asks for one order while the schema
    # imposes another is a prompt arguing with itself.
    "properties": {
        "why": {"type": "string", "description": "one sentence, naming the evidence"},
        "act": {"type": "string", "description": "what the person did, in their words"},
        "object": {"type": "string", "description": "the thing they were working on"},
        "system": {"type": "string"},
        "page": {"type": "string"},
        "values_seen": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"field": {"type": "string"}, "value": {"type": "string"}},
                "required": ["field", "value"],
            },
        },
        "continues": {"type": "string", "description": "empty unless it continues the last doing"},
        "confidence": {"type": "string", "enum": _CONFIDENCE},
    },
    # Stated rather than left to the key order above. Gemini honours the dict's
    # own order today -- measured, both with and without this field -- and
    # `propertyOrdering` is the documented way to say so, which makes the
    # ordering a promise of the schema rather than an accident of how Python
    # happens to preserve insertion order through the SDK's conversion.
    "propertyOrdering": [
        "why",
        "act",
        "object",
        "system",
        "page",
        "values_seen",
        "continues",
        "confidence",
    ],
    "required": ["act", "why"],
}

CONFIDENCE_VALUES = frozenset(_CONFIDENCE)


def one_line(intent: Intent) -> str:
    parts = [intent.act or "(unread)"]
    if intent.object:
        parts.append(f"on {intent.object}")
    return " ".join(parts).replace("\n", " ")


def _string_field(data: dict[str, object], key: str) -> str | None:
    """The schema is advisory, not enforced. A model can return `"act": [...]`
    and nothing here validates it before it reaches `Intent`. Treating a
    wrong-typed field as unusable is what stops that field poisoning `one_line`
    the next time this intent is pulled into somebody else's tail context.
    """
    value = data.get(key)
    return value if isinstance(value, str) else None


def intent_from(
    data: dict[str, object] | None, gesture: Gesture, answer: Answer, *, model: str
) -> Intent:
    """One reading, as it will be stored -- whatever came back in it.

    An answer that carried no data still becomes an intent: the model was
    asked, it answered, and it was billed, so the row exists and says why it is
    empty. `model` is passed beside `answer` because `Answer` carries the bill
    but not the name it was run up against -- which is the one thing a reader of
    a $0.00 row needs.
    """
    intent = Intent(
        gesture_id=gesture.id,
        tenant=gesture.tenant,
        model=model,
        in_tokens=answer.in_tokens,
        out_tokens=answer.out_tokens,
        thought_tokens=answer.thought_tokens,
        cost_usd=answer.cost_usd,
        unpriced=answer.unpriced,
        error=answer.error,
    )
    if data is None:
        return intent

    intent.act = _string_field(data, "act")
    intent.object = _string_field(data, "object")
    intent.system = _string_field(data, "system")
    intent.page = _string_field(data, "page")
    # `or None`: the schema says "empty unless it continues the last doing", so
    # "" is what a model returns for most gestures. Stored verbatim it is
    # neither a link nor an absence.
    #
    # This comment used to end "and `continues` is what the mining pass walks
    # to join gestures into one doing", which is not true and was worth
    # checking rather than repeating: `mining_pass` does not contain the word,
    # and `window.as_evidence` -- the function that builds what the miner is
    # shown -- lists `act`, `object`, `page`, `why`, `confidence` and
    # `values_seen`, and not this. Nothing in the backend reads it. It is
    # stored because it is cheap to store and because the day something does
    # join a doing it will want it; it is not load-bearing today, and `TAIL`
    # above should not be defended on its account.
    intent.continues = _string_field(data, "continues") or None
    confidence = _string_field(data, "confidence")
    intent.confidence = confidence if confidence in CONFIDENCE_VALUES else None
    intent.why = _string_field(data, "why")
    intent.values_seen = _values_seen(data, hide=is_secret(gesture))
    return intent


def _values_seen(data: dict[str, object], *, hide: bool) -> list[ValueSeen]:
    """What the model reported the operator entering, with credentials blanked.

    The third place a guard covered the typed value and let values_seen
    through -- after `trim` and `typed_values`, and the only one of the three
    that reaches storage. `save_intent` writes this verbatim and the gestures
    route serves it back, so a password the model echoed into a field it had
    named was persisted and rendered. The field name is kept: that the operator
    typed a password is worth reading, what they typed is not. This is the
    single point every stored values_seen passes through.
    """
    seen_list = data.get("values_seen")
    found: list[ValueSeen] = []
    # Both containers are checked, not just the outer one: a mapping iterates
    # as its own keys and a string as its characters, so an outer guard alone
    # walks a `{"clientCode": "ACME-4471"}` straight into the per-entry code.
    for seen in seen_list if isinstance(seen_list, list) else []:
        if not isinstance(seen, dict):
            continue
        field = seen.get("field")
        # `field` unusable unless it's a non-empty str; a non-str `value` is
        # treated as unseen ("") rather than fabricated by str()-coercing it --
        # same rule as `_string_field` above.
        if not isinstance(field, str) or not field:
            continue
        value = seen.get("value")
        found.append(
            ValueSeen(
                field=field,
                value=""
                if hide or is_secret_name(field)
                else (value if isinstance(value, str) else ""),
            )
        )
    return found


_WRITE_METHODS = frozenset({"POST", "PUT", "PATCH"})


def is_write(gesture: Gesture) -> bool:
    """Whether this gesture's own calls actually wrote something.

    A save click is asked about like every other gesture -- what it touched,
    what it typed -- and it typed nothing: the click itself carries no value,
    only the calls it caused prove a write happened at all.
    """
    return any(
        call.status is not None
        and 200 <= call.status < 300
        and call.method.upper() in _WRITE_METHODS
        for call in gesture.requests
    )


def _carried_any(gesture: Gesture, tail: list[Intent]) -> bool:
    """Whether this gesture's writes actually sent something the tail names.

    The test is the value, not the field name: a form posts `customerType`
    where the label said `Customer Type`, and it is the value that survives
    that translation intact.

    Short values are ignored, on the same reasoning and the same threshold as
    `values.K_MIN_VALUE_LEN`: `0` and `-1` appear in every payload ever sent,
    so matching on one would hand the fold back to the telemetry post this
    guard exists to refuse.
    """
    sent = "\n".join(
        call.request_body.text
        for call in gesture.requests
        if call.status is not None
        and 200 <= call.status < 300
        and call.method.upper() in _WRITE_METHODS
        and call.request_body is not None
        and call.request_body.text
    )
    if not sent:
        return False
    return any(
        seen.value and len(seen.value) >= K_MIN_VALUE_LEN and seen.value in sent
        for prior in tail
        for seen in prior.values_seen
    )


def with_recent_values(intent: Intent, gesture: Gesture, tail: list[Intent]) -> Intent:
    """A write's reading folds in the tail's values, not just its own.

    Measured against a real save: the write's own POST body carried five
    submitted fields, and the model's reading of the click itself named one of
    them -- the rest were typed in the gestures just before it, each already a
    reading sitting in `tail`. Folded in, the save says what it saved.

    What this is NOT for, stated because the first version of this docstring
    claimed it and the claim was wrong: it does not rescue a cross-system
    value crossing. `values.shared_values` needs one value under two distinct
    systems; `_tail_for` hands over the same stream only, so every value
    folded here already belongs to a gesture on the same system, and the
    crossing either existed without this or does not exist. It pushes the
    other way if anything -- `values.frequencies_over` counts the gestures
    carrying a value, so a save that now also carries them raises their
    ubiquity toward the furniture threshold that suppresses a crossing. Small
    at this corpus size, and the direction is worth knowing.

    What it is for: `window.py` serialises `values_seen` into the evidence the
    mining pass reads, and a save whose reading names one field of five is a
    save whose evidence does not say what was submitted.

    Scoped to a write on purpose: folding history into every gesture would
    make an ordinary click on an empty form report values from three screens
    ago. A later tail entry wins a field name over an earlier one -- typed
    twice, the last value is the one that reached the write -- and the
    write's own reading wins over both, being the more direct evidence for
    whatever it actually named.

    And scoped a second time, to a write that carried something the operator
    recently put on screen. `is_write` asks only whether a 2xx POST, PUT or
    PATCH left the gesture, and measured against one real capture that is far
    too generous: of 15 gestures it called writes, **6 were saves**. The other
    nine were the browser talking to itself -- five `sessionKeepAlive` calls
    keeping the session warm, and four posts to `webPerformanceEntries/batch`,
    which is the WMS uploading its own performance telemetry. An operator
    clicking a tab header is not saving anything, and folding a form's worth
    of values into that reading is exactly the failure the paragraph above
    warns about, arriving through a door nobody was watching.

    So the fold has to be earned: at least one value from the tail must
    actually appear in what the write sent. A keepalive sends no body and a
    telemetry post sends timings, so neither earns it, while a real save sends
    the form -- and no endpoint anywhere is named to tell those apart, which
    matters because the next customer's housekeeping endpoints will be called
    something else entirely.

    Returns a new `Intent` rather than editing the one handed over: the caller
    holds the reading it just built, and a `with_` that quietly rewrites its
    argument is the kind of surprise that costs an afternoon.
    """
    if not is_write(gesture) or not _carried_any(gesture, tail):
        return intent
    merged: dict[str, str] = {}
    for prior in tail:
        for seen in prior.values_seen:
            merged[seen.field] = seen.value
    for seen in intent.values_seen:
        merged[seen.field] = seen.value
    return replace(
        intent,
        values_seen=[ValueSeen(field=field, value=value) for field, value in merged.items()],
    )
