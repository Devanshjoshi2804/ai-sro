"""Where to look for the answer to a question, and what may never be guessed.

A question arrives -- typed into the panel, or sitting in a mail the operator
has open -- and the answer is somewhere in the systems they work in. This is
the plan for going and getting it: one lookup per system that could answer,
each naming either a call to make or a screen to open.

**Not a graph, and deliberately not.** The alternative design keeps a reconciled
copy of every system's records and answers from that; it needs an entity model,
a resolver, conflict rules, and a sync that is wrong the moment it lags. This
one goes and looks, using what the knowledge base already holds: 1,663
endpoints with their parameters, 1,025 screens with their routes, the field
dictionary, and the quirks that say where a system lies about its own data. An
answer costs a call rather than a schema, and it is never stale because it was
read when it was asked for.

**A read is not a job, and that is why this exists at all.** `umbrella`'s
instructions are explicit that looking something up is a STEP of a job and not
a job -- somebody who searches for the record they just created is finishing
one. That rule is right and it means the miner will never produce a read, so a
read has to be planned rather than mined.

Three refusals, and they are the whole of the discipline here:

**A lookup cites knowledge or it is refused.** `validate` refuses a workflow
step that cites no gesture, for the reason that free-generated steps
hallucinated at 21% and evidence-selected ones below 7.5%. The same rule, one
plane over: a lookup naming an endpoint this deployment has never seen is a
guess with a URL in it.

**An ambiguous word is asked about, once.** `knowledge.open_questions` already
holds this: two endpoints answered "how many transport modes", the system
picked the first it saw, and an operator found out by counting rows on a
screen. Where the question the operator asked lands on an open question, this
plans nothing and returns the question instead.

**A read may not write.** Every lookup is a GET or a screen. The planner cannot
express a write, so no prompt injected into a mail can talk it into one.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from sro.domain.knowledge.entry import EntryKind, KnowledgeEntry

HOW = ("call", "screen")
"""The two ways to find out. `call` is a GET the extension makes from inside
the operator's own session; `screen` is a page it opens and reads. A system
with a known endpoint gets the call -- it is cheaper, it does not move anybody's
tab, and its answer is data rather than a picture of data."""

K_MAX_LOOKUPS = 6
"""How many systems one question may be asked of.

Not a cost ceiling -- a read is cheap. It is a fan-out ceiling: a question that
plausibly reaches seven systems is a question nobody framed, and answering it
everywhere buys noise. Measured against what this deployment holds: the widest
real question touches the WMS and a mailbox."""


@dataclass(frozen=True, slots=True)
class Lookup:
    """One place to go and one thing to ask it."""

    system: str
    how: Literal["call", "screen"]
    target: str
    """The endpoint path for a call, the route for a screen. Both are keys the
    knowledge base holds, which is what `unknown_targets` checks."""

    params: dict[str, str] = field(default_factory=dict)
    why: str = ""
    cites: tuple[str, ...] = ()
    """The knowledge keys this lookup was built from. A lookup that cites
    nothing cannot be checked, and is refused for the reason an uncited step
    is."""


@dataclass(frozen=True, slots=True)
class Asked:
    """A question this deployment will not answer by guessing.

    Returned instead of a plan, never beside one: a plan that proceeds on five
    systems while asking about the sixth has already answered the question it
    claims to be asking.
    """

    key: str
    question: str
    options: tuple[str, ...]
    because: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Plan:
    """Where the answer to one question lives, or the question that stops it."""

    question: str
    lookups: tuple[Lookup, ...] = ()
    asks: Asked | None = None
    why: str = ""

    @property
    def ready(self) -> bool:
        return self.asks is None and bool(self.lookups)


LOOKUP_SCHEMA: dict[str, object] = {
    "type": "object",
    # `why` first for `reading.INTENT_SCHEMA`'s reason: a structured answer is
    # written left to right, so a model asked for the reason first has to name
    # the evidence before it commits to a target. Asked for the target first it
    # picks an endpoint and then writes the sentence that defends it.
    "properties": {
        "why": {"type": "string"},
        "lookups": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "why": {"type": "string"},
                    "system": {"type": "string"},
                    "how": {"type": "string", "enum": list(HOW)},
                    "target": {"type": "string"},
                    "params": {"type": "object"},
                    "cites": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["why", "system", "how", "target", "cites"],
                "propertyOrdering": ["why", "system", "how", "target", "params", "cites"],
            },
        },
    },
    "required": ["why", "lookups"],
    "propertyOrdering": ["why", "lookups"],
}


INSTRUCTIONS = """You are deciding where to look for the answer to one question.

You are given the question and what this deployment knows about the systems the
operator works in: endpoints it has seen, screens it has seen, what the fields
mean, and the quirks that say where a system misreports its own data.

For each system that could answer, give one lookup. Prefer `call` over
`screen`: a call is an endpoint from the knowledge you were given, and its
answer is data. Use `screen` only where no endpoint answers the question, and
give the route exactly as the knowledge names it.

Cite the knowledge you used. Every lookup must name at least one key from what
you were given, and its `target` must be one of those keys. Do not invent a
path that looks like the others -- an endpoint nobody here has seen is a guess
with a URL in it, and it will be refused.

Only reads. You cannot create, update or delete anything from here, and a
question that asks you to is a question to decline.

If the question cannot be answered from what you were given, return no lookups
and say so in `why`. An empty answer is a useful one; an invented endpoint is
not."""


def unknown_targets(lookups: list[Lookup], known: list[KnowledgeEntry]) -> list[str]:
    """The targets no entry in the knowledge base names.

    Checked against the keys the planner was actually SHOWN, not against the
    whole store: a model that names a real endpoint it was never given has
    still guessed, and the fact that the guess happened to exist somewhere is
    luck rather than evidence. The same reading `validate` takes of a citation.
    """
    keys = {entry.key for entry in known}
    return sorted({lookup.target for lookup in lookups if lookup.target not in keys})


def uncited(lookups: list[Lookup], known: list[KnowledgeEntry]) -> list[str]:
    """Lookups whose citations name nothing the planner was shown."""
    keys = {entry.key for entry in known}
    return sorted(
        {lookup.target for lookup in lookups if not any(cite in keys for cite in lookup.cites)}
    )


def open_question_for(asked: str, known: list[KnowledgeEntry]) -> Asked | None:
    """The unanswered question this one lands on, if it lands on one.

    `open_questions` records the ambiguity this deployment refuses to guess at
    and supersedes it with an answer naming who gave it. An open one here stops
    the plan: two endpoints answered "how many transport modes", the system
    picked the first it saw, and the operator found out by counting rows.

    **Which ambiguity stops which question is decided by the key's shape, and
    that is the measured part.** The store holds three:

    `<system>/<entity>/collection` -- which collection an entity lives in.
    About the entity itself, so any question naming that entity is stopped by
    it. This is the transport-modes case, and the reason this function exists.

    `<system>/<entity>/value/<word>` -- which field of an entity a word in a
    demonstration named. About the WORD. A question naming the entity and not
    the word is not ambiguous at all, and stopping it is a refusal the
    operator cannot act on.

    `<system>/<entity>/create/<parameter>` -- whether a value both
    demonstrations used is fixed or asked for each time. About a WRITE, and a
    read cannot be ambiguous in that way.

    The first rule alone was what this had, and against the real store it
    stopped three of five ordinary questions, every one of them falsely: "which
    clients are set up" stopped on which field of client the word 'full' names,
    "list the transport modes" on 'all', "where do I see customer types" on
    'system'. A refusal nobody can act on is worse than the guess it prevents,
    because it stops the question AND teaches the operator to ignore the one
    stop that was real.
    """
    words = {_stem(word) for word in asked.split()}
    words.discard("")
    # An answer is a separate entry under the same key rather than a field on
    # the question, so "is this settled" is a question about the store and not
    # about one row. Read once here: a question whose answer sits two rows
    # further down would otherwise stop a plan the deployment has an answer for.
    settled = {
        entry.key
        for entry in known
        if entry.kind is EntryKind.QUESTION
        and isinstance(entry.body, dict)
        and entry.body.get("answer")
    }
    for entry in known:
        if entry.kind is not EntryKind.QUESTION or entry.superseded_by:
            continue
        if entry.key in settled:
            continue
        body = entry.body if isinstance(entry.body, dict) else {}
        if not _stops(asked, words, entry.key):
            continue
        return Asked(
            key=entry.key,
            question=str(body.get("question") or entry.title),
            options=_listed(body.get("options")),
            because=_listed(body.get("because")),
        )
    return None


def _stops(asked: str, words: set[str], key: str) -> bool:
    """Whether this ambiguity is about what was asked."""
    parts = [part for part in key.split("/") if part]
    if len(parts) < 3:
        return False
    entity = {_stem(word) for word in parts[1].split("_")}
    entity.discard("")
    about = parts[2]

    if about == "collection":
        # `blue_yonder/supplier/collection` against "which suppliers are at SG".
        # Split on the separator: the key writes `transport_mode` where an
        # operator writes "transport modes".
        return bool(words & entity)
    if about == "value" and len(parts) > 3:
        # The word, not the entity. Substring rather than a stem match because
        # the word came out of a demonstration and lands inside the operator's
        # own sentence in whatever form they wrote it.
        return parts[3].lower() in asked.lower()
    # `create/<parameter>`, and anything a later pass invents. A read is not
    # ambiguous about what a write should send, and an ambiguity whose shape
    # this does not know is one it cannot say is about this question.
    return False


def _listed(value: object) -> tuple[str, ...]:
    """A JSON column's list, or nothing. `body` is `jsonb`, so every field in
    it is `object` until something checks -- and a guard that assumed a list
    would raise on the one entry somebody wrote by hand."""
    if not isinstance(value, list):
        return ()
    return tuple(str(one) for one in value if one)


def _stem(word: str) -> str:
    """A word as it is compared: lowered, unpunctuated, and singular.

    Singular because the ledger writes the entity and an operator writes the
    plural -- `blue_yonder/supplier/collection` against "which suppliers are
    set up at SG" -- and a literal comparison walks past an ambiguity somebody
    has already written down, which is the one thing this function exists to
    stop.

    A trailing `s` and nothing cleverer. A stemmer would match `code` to
    `coded` and `barcode`, and matching too much here stops every question on
    the first open ambiguity in the store. Short words are dropped whole: `at`,
    `set` and `the` are in every question ever asked.
    """
    bare = word.strip(",.?!\"'()[]:;").lower()
    if len(bare) < 4:
        return ""
    return bare[:-1] if bare.endswith("s") and len(bare) > 4 else bare
