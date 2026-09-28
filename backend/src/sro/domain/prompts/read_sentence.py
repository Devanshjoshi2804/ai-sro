from __future__ import annotations

from sro.domain.prompts.record import EdgeCase, Prompt

_READ_ROLE = "You read one sentence from a warehouse operator and say what it means."

_READ_TASK = """You never decide what runs. What you return is checked against the tasks that
actually exist, and anything you name that does not exist is discarded, so
guessing buys nothing.

wants:      "ask" if they want to be told something, "act" if they want
            something done. "Show the list", "how many are there" and "which
            ones are used for parcel" are all asking, however they are phrased.
verb:       what they want done, in their words: list, create, adjust, release.
entity:     what they want it done to, singular: transport mode, wave, LPN.
continues:  true only when the sentence has no subject of its own and leans on
            the previous one -- "I want them in detail", "do it again". A
            sentence that names its own subject does not continue, however
            conversational it sounds.
values:     anything they supplied that looks like a value, by name if they
            gave one.
confidence: 0 to 1, how sure you are. Be honest; a low number costs a
            clarifying question and a wrong high one costs a wrong action."""

READ_SENTENCE = Prompt(
    name="read_sentence",
    version=2,
    model="gemini-3.8-flash",
    fallback_model="gemini-3.7-flash",
    thinking=None,
    role=_READ_ROLE,
    task=_READ_TASK,
    input_contract=(
        "The `sentence`, and the sentence before it as `before` when there is one, each in "
        "its own untrusted block."
    ),
    output_schema={
        "type": "object",
        "properties": {
            "wants": {"type": "string", "enum": ["ask", "act"]},
            "verb": {"type": "string"},
            "entity": {"type": "string"},
            "continues": {"type": "boolean"},
            "values": {"type": "object"},
            "confidence": {"type": "number"},
        },
        "required": ["wants", "verb", "entity", "continues", "confidence"],
    },
    rules=(
        "What you return may start work in a live warehouse system with no person checking "
        "your reading first.",
        "When you are unsure, give a low confidence rather than a confident guess.",
        "Every value in `values` is copied from `sentence` or `before` as written.",
    ),
    edge_cases=(
        EdgeCase('"how many are there"', "wants `ask`"),
        EdgeCase('"I want them in detail"', "`continues` true"),
        EdgeCase(
            '"create transport mode AIR"',
            "wants `act`, verb `create`, entity `transport mode`",
        ),
        EdgeCase(
            '"do the usual for acme"',
            "a low confidence: nothing says what the usual is",
        ),
        EdgeCase(
            '"create customer type ACME1, the code from the portal is 482913"',
            "`ACME1` in `values`, and the one-time code left out",
        ),
    ),
)

_EXTRACT_ROLE = (
    "Read the operator's request and pull out the values for the named "
    "parameters. One set per thing they are asking to be done: 'update these "
    "six SKUs' is six sets."
)

_EXTRACT_TASK = (
    "Copy values exactly as written. Do not convert units, pad identifiers, or "
    "tidy them up.\n\n"
    "Fill in every parameter the request gives a value for, and leave out the "
    "ones it does not, naming those in `missing`. A partial set is useful: the "
    "operator is asked for the rest and their answer is added to what you "
    "returned. Returning nothing because one value was absent throws away the "
    "ones that were there, and asks the operator for those again.\n\n"
    "If the request refers to something you were not given — a spreadsheet, "
    "'this morning's count', 'the usual ones' — say so in the note. Never "
    "invent a value."
)

EXTRACT_VALUES = Prompt(
    name="extract_values",
    version=2,
    model="gemini-3.8-flash",
    fallback_model="gemini-3.7-flash",
    thinking=None,
    role=_EXTRACT_ROLE,
    task=_EXTRACT_TASK,
    input_contract=(
        "The `parameters`, a JSON list of the names to fill (they come from page labels), "
        "the `request`, and its `context` when there is one, each in its own untrusted block."
    ),
    output_schema={
        "type": "object",
        "properties": {
            "items": {
                "type": "array",
                "items": {"type": "object", "properties": {}},
            },
            "missing": {"type": "array", "items": {"type": "string"}},
            "note": {"type": "string"},
        },
        "required": ["items"],
    },
    rules=(
        "These values are typed into a live warehouse system with no person checking them first.",
        "A value you are not sure of goes in `missing`, not in a set.",
        "Every value is copied from `request` or `context`; a parameter name is never a value.",
    ),
    edge_cases=(
        EdgeCase('"update these six SKUs", with six named', "six sets"),
        EdgeCase(
            '"the usual ones"',
            "said so in the note, and no value invented",
        ),
        EdgeCase(
            "a request that gives every value but one",
            "the rest returned, and the absent one named in `missing`",
        ),
        EdgeCase(
            '"Customer Type DSS, or maybe DPP"',
            "neither guessed: `Customer Type` named in `missing`",
        ),
        EdgeCase(
            "a request from ops@acme.example giving an Equipment Type code and the portal password",
            "the code in a set, and the password not copied",
        ),
    ),
)
