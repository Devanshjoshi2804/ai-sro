from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from difflib import SequenceMatcher
from itertools import pairwise

from sro.domain.chat.request import Candidate, field_of, refusal
from sro.domain.chat.thread import Message, Said, Speaker
from sro.domain.execution.field_classes import FieldLimits
from sro.domain.execution.mail_job import DRAFTED, SENT
from sro.domain.lookup.asking import is_a_question
from sro.domain.recording.sensitivity import is_secret_field
from sro.domain.skill.signing_in import Logins

NEEDS = "needs_values"

# The decisions that wait on the operator's answer: a missing value, a run's question, the brain's.
ASKS = frozenset({NEEDS, "run_asks", "brain_asks"})

JOB = "job"

SAID_YES = frozenset(
    {
        "yes",
        "yes please",
        "yep",
        "yeah",
        "ok",
        "okay",
        "sure",
        "go",
        "go on",
        "go ahead",
        "do it",
        "do it now",
        "please do",
        "pls do",
        "plz do",
        "run it",
        "run it now",
        "yes do it",
        "yes run it",
        "that one",
    }
)

K_SAID = 200

LET_GO = frozenset(
    {
        "no",
        "no thanks",
        "nope",
        "stop",
        "cancel",
        "forget it",
        "never mind",
        "nevermind",
        "drop it",
        "leave it",
    }
)


@dataclass(frozen=True)
class Pending:
    workflow_id: str
    title: str
    values: Mapping[str, str]
    missing: tuple[str, ...]
    items: tuple[Mapping[str, str], ...] = ()
    watched: bool = True
    can_find: bool = False

    mail_thread: str = ""

    offered: tuple[tuple[str, str], ...] = ()

    from_step: int = 0

    limits: Mapping[str, int] = field(default_factory=dict)

    confirmed: bool = True

    options: Mapping[str, tuple[str, ...]] = field(default_factory=dict)

    dropped: tuple[str, ...] = ()

    without: tuple[str, ...] = ()

    refused: Mapping[str, str] = field(default_factory=dict)

    changing: bool = False

    which: Mapping[str, tuple[str, ...]] = field(default_factory=dict)

    doubted: tuple[str, ...] = ()

    doubting: tuple[str, ...] = ()

    known: Candidate | None = None

    offer: str = ""

    @property
    def asking_for(self) -> str:
        return self.missing[0] if self.missing else ""

    @property
    def ready(self) -> bool:
        return not self.missing and not self.without


def _holds(pending: Pending, name: str) -> str:
    said = []
    holds = pending.limits.get(name)
    if holds is not None and (not pending.changing or len(pending.values.get(name, "")) > holds):
        said.append(f"takes {holds} characters")
    if choices := pending.options.get(name):
        said.append("is one of " + ", ".join(choices))
    return f"{name} {' and '.join(said)}." if said else ""


def _the_values(pending: Pending) -> str:
    return "; ".join(
        f"{name}: {_short(value)}"
        for name, value in pending.values.items()
        if not is_secret_field(name)
    )


def refusal_question(pending: Pending, reason: str, also: str = "") -> str:
    """What is asked when the system refused a write: its words as quoted data,
    then the question. A limit is said only for a value that exceeds it."""
    said = f'{pending.title} was not done: "{_short(reason.strip().rstrip("."))}". '
    over = {
        name: holds
        for name, holds in pending.limits.items()
        if len(pending.values.get(name, "")) > holds
    }
    return said + (f"{also} " if also else "") + question(replace(pending, limits=over))


def question(pending: Pending) -> str:
    wanted = pending.missing
    if pending.changing:
        held = [one for one in (_holds(pending, name) for name in wanted) if one]
        return " ".join(
            [
                *held,
                f"It has {_the_values(pending)}.",
                "Which value should change?",
            ]
        )
    if len(wanted) <= 1:
        asked = pending.asking_for
        holds = _holds(pending, asked)
        return f"{holds} What should it be?" if holds else f"What should {asked} be?"
    held = [one for one in (_holds(pending, name) for name in wanted) if one]
    return " ".join(
        [
            *held,
            f"What should {_listed(wanted)} be?",
            "Say them as " + "; ".join(f"{name}: …" for name in wanted) + ".",
        ]
    )


def asks(pending: Pending) -> list[dict[str, object]]:
    return [
        {
            "name": name,
            "max_length": pending.limits.get(name),
            "options": list(pending.options.get(name, ())),
        }
        for name in pending.missing
    ]


def asking_state(pending: Pending) -> dict[str, object]:
    return {
        "asks": asks(pending),
        **({"offered": [list(one) for one in pending.offered]} if pending.offered else {}),
        **({"dropped": list(pending.dropped)} if pending.dropped else {}),
        **({"doubted": list(pending.doubted)} if pending.doubted else {}),
        **({"refused": dict(pending.refused)} if pending.refused else {}),
        **({"changing": True} if pending.changing else {}),
        **(
            {"options": {name: list(one) for name, one in pending.options.items()}}
            if pending.options
            else {}
        ),
    }


def turned_down(pending: Pending) -> str:
    return "".join(
        [
            *(f"I did not take {name}: it is {why}. " for name, why in pending.refused.items()),
            *(
                f"Did you mean to skip {name}, or is it part of the value? "
                for name in pending.doubting
            ),
            *(
                f'I could not tell which field "{said}" is: {_listed(names, "or")}. '
                for said, names in pending.which.items()
            ),
        ]
    )


def cannot_without(pending: Pending, *, ran: bool = False) -> tuple[str, dict[str, object]]:
    lacking = _listed(pending.without)
    said = (
        f"{pending.title} stopped — it needs {lacking} to run, and you said you do not have it."
        if ran
        else f"{pending.title} cannot run without {lacking}, and you said you do not have it, "
        "so nothing was started."
    )
    return (
        f"{said} When you have it, ask for {pending.title} again.",
        {
            "kind": Said.NOTE,
            "workflow_id": pending.workflow_id,
            "mail_thread": pending.mail_thread,
            "cannot_run": [f"it needs {lacking}"],
            "values": dict(pending.values),
            "dropped": list(pending.dropped),
        },
    )


def still_to_ask(pending: Pending, messages: Sequence[Message]) -> Pending:
    last = next(
        (
            one.decision
            for one in reversed(messages)
            if one.speaker is Speaker.ASSISTANT
            and one.decision
            and one.decision.get("workflow_id") == pending.workflow_id
        ),
        None,
    )
    if not last or not last.get("resume") or _strings(last.get("values")) != dict(pending.values):
        return pending
    dropped = tuple(dict.fromkeys((*pending.dropped, *_names(last.get("dropped")))))
    return replace(
        pending,
        missing=tuple(name for name in pending.missing if name not in dropped),
        without=tuple(
            dict.fromkeys((*pending.without, *(n for n in pending.missing if n in dropped)))
        ),
        offered=(),
        dropped=dropped,
    )


def unusable(values: Mapping[str, str], limits: Mapping[str, int]) -> tuple[str, ...]:
    return tuple(
        name
        for name, value in values.items()
        if name in limits and isinstance(value, str) and len(value) > limits[name]
    )


K_SHOWN = 90


def opening(pending: Pending, about: str = "") -> str:
    said = [f"{pending.title}{f' — {about}' if about.strip() else ''}.", *_held(pending)]
    for name in pending.missing:
        holds, was = pending.limits.get(name), pending.values.get(name, "")
        if holds is not None and was.strip():
            said.append(f"The request said {name} {_short(was)}, which is {len(was)} characters.")
    if also := also_set(pending):
        said.append(also)
    said.append(question(pending))
    return " ".join(said)


def should_we(pending: Pending, about: str = "", sent_to: Sequence[str] = ()) -> str:
    said = [f"{pending.title}{f' — {about}' if about.strip() else ''}."]
    if sent_to:
        said.append(f"You sent this to {_listed(list(sent_to))}.")
    said.extend(_held(pending))
    said.append("Should our system do it? Say yes to run it, or no to leave it.")
    return " ".join(said)


def of_the_offer(pending: Pending) -> str:
    return " ".join(
        [
            f"{pending.title} is waiting on your word.",
            *_held(pending),
            "Say yes to run it, or no to leave it.",
            NOTHING_NEW,
        ]
    )


NOTHING_NEW = "Nothing new was started."

FROM_THE_MAIL = "the mail"
FROM_THE_REPLY = "the reply"
FROM_THE_CHAT = "your answer in the chat"
FROM_THE_REQUEST = "your request"


def sourced(values: Mapping[str, str], came: Mapping[str, str], rest: str) -> str:
    said = [
        f"{name} = {quoted(value, came.get(name, rest))} ({came.get(name, rest)})"
        for name, value in values.items()
        if value.strip() and not is_secret_field(name)
    ]
    return f" Values: {'; '.join(said)}." if said else ""


def quoted(value: str, source: str) -> str:
    """A value that came out of somebody else's mail is shown as quoted data,
    bounded; one the operator gave is shown plain."""
    return f"'{_short(value)}'" if source in (FROM_THE_REPLY, FROM_THE_MAIL) else _short(value)


def _held(pending: Pending) -> list[str]:
    held = [
        f"{name}: {_short(value)}"
        for name, value in pending.values.items()
        if name not in pending.missing and value.strip()
    ]
    return ["I have " + "; ".join(held) + "."] if held else []


def also_set(pending: Pending) -> str:
    if not pending.offered:
        return ""
    return (
        "I can also set "
        + _listed([name for name, _ in pending.offered])
        + _last_time(pending.offered)
        + " — say so if you want any, or I will run without."
    )


def _listed(names: Sequence[str], joined: str = "and") -> str:
    if len(names) <= 1:
        return "".join(names)
    return ", ".join(names[:-1]) + f" {joined} " + names[-1]


def _last_time(offered: Sequence[tuple[str, str]]) -> str:
    seen = [f"{name}: {_short(value)}" for name, value in offered if value.strip()]
    return f" — last time {'; '.join(seen)}" if seen else ""


def shortened(value: str) -> str:
    return _short(value)


def _short(value: str) -> str:
    said = " ".join(value.split())
    return said if len(said) <= K_SHOWN else said[:K_SHOWN] + "…"


def too_long_for(pending: Pending, said: str) -> int | None:
    asked = pending.asking_for
    holds = pending.limits.get(asked)
    value = said.strip()[:K_SAID]
    if pending.changing or named_in(pending, value):
        return None
    return holds if holds is not None and len(value) > holds else None


def asked_under(messages: Sequence[Message], answering: str | None = None) -> Message | None:
    if answering is None:
        return next(
            (
                one
                for one in reversed(messages)
                if one.speaker is Speaker.ASSISTANT and one.decision
            ),
            None,
        )
    at = next((n for n, one in enumerate(messages) if one.id.value == answering), None)
    if at is None or messages[at].speaker is not Speaker.ASSISTANT or not messages[at].decision:
        return None
    offer = _offer(messages[at].decision)
    closed = any(
        one.speaker is Speaker.ASSISTANT and one.decision and _offer(one.decision) == offer
        for one in messages[at + 1 :]
    )
    return None if closed else messages[at]


def standing(messages: Sequence[Message]) -> Message | None:
    """The question this chat is waiting on: its last decision, if that asks."""
    asked = asked_under(messages)
    return asked if asked is not None and (asked.decision or {}).get("kind") == NEEDS else None


def waiting_on_mail(messages: Sequence[Message], mail_thread: str) -> Pending | None:
    last = next(
        (
            one
            for one in reversed(messages)
            if one.speaker is Speaker.ASSISTANT
            and one.decision
            and one.decision.get("mail_thread") == mail_thread
        ),
        None,
    )
    return pending_job(messages, last.id.value) if last is not None else None


def envelope_of(messages: Sequence[Message], mail_thread: str) -> dict[str, str]:
    if not mail_thread:
        return {}
    for one in reversed(messages):
        decision = one.decision or {}
        mail = decision.get("mail")
        if decision.get("mail_thread") == mail_thread and isinstance(mail, dict):
            return {str(name): str(value) for name, value in mail.items()}
    return {}


def asked_by_mail(messages: Sequence[Message], mail_thread: str) -> str:
    if not mail_thread:
        return ""
    drafts = {
        one.id.value
        for one in messages
        if (one.decision or {}).get("kind") == DRAFTED
        and (one.decision or {}).get("thread") == mail_thread
    }
    return next(
        (
            str(decision.get("to") or "")
            for one in reversed(messages)
            if (decision := one.decision or {}).get("kind") == SENT
            and decision.get("sent")
            and decision.get("draft_id") in drafts
        ),
        "",
    )


def _offer(decision: Mapping[str, object]) -> tuple[str, str]:
    return str(decision.get("workflow_id") or ""), str(decision.get("mail_thread") or "")


def the_request(messages: Sequence[Message], offer: str, workflow_id: str) -> tuple[str, ...]:
    chain = {offer} if offer else set()
    for one in reversed(messages):
        if one.id.value in chain and _chats_about(one, workflow_id) and _link(one):
            chain.add(_link(one))
    return tuple(
        before.text
        for before, one in pairwise(messages)
        if _chats_about(one, workflow_id)
        and (one.id.value in chain or _link(one) in chain)
        and before.speaker is Speaker.OPERATOR
        and before.text.strip()
    )


def _link(message: Message) -> str:
    return str((message.decision or {}).get("offer") or "")


def _chats_about(message: Message, workflow_id: str) -> bool:
    decision = message.decision or {}
    return (
        message.speaker is Speaker.ASSISTANT
        and decision.get("kind") in (JOB, NEEDS)
        and _offer(decision) == (workflow_id, "")
    )


def pending_job(messages: Sequence[Message], answering: str | None = None) -> Pending | None:
    asked = asked_under(messages, answering)
    decision = asked.decision if asked is not None else None
    if asked is None or not decision or decision.get("kind") != NEEDS:
        return None
    listed = decision.get("missing")
    missing = tuple(str(one) for one in listed) if isinstance(listed, list | tuple) else ()
    if not missing or not decision.get("workflow_id"):
        return None
    items = decision.get("items")
    return Pending(
        workflow_id=str(decision["workflow_id"]),
        title=str(decision.get("title") or ""),
        values=_strings(decision.get("values")),
        missing=missing,
        offered=_pairs(decision.get("offered")),
        items=tuple(_strings(one) for one in items) if isinstance(items, list | tuple) else (),
        watched=bool(decision.get("watched", True)),
        limits=_numbers(decision.get("limits")),
        from_step=_step(decision.get("from_step")),
        mail_thread=str(decision.get("mail_thread") or ""),
        confirmed=not decision.get("unconfirmed"),
        options=_choices(decision.get("options")),
        dropped=_names(decision.get("dropped")),
        doubted=_names(decision.get("doubted")),
        refused=_strings(decision.get("refused")),
        changing=bool(decision.get("changing")),
        # The question's own message id unless it re-asks one: the mail door and
        # the panel both key a run on this, so one question starts one run.
        offer=str(decision.get("offer") or asked.id.value),
    )


def _names(said: object) -> tuple[str, ...]:
    return tuple(str(one) for one in said) if isinstance(said, list | tuple) else ()


def _choices(said: object) -> dict[str, tuple[str, ...]]:
    if not isinstance(said, dict):
        return {}
    return {str(key): _names(one) for key, one in said.items() if isinstance(one, list | tuple)}


def _pairs(said: object) -> tuple[tuple[str, str], ...]:
    if not isinstance(said, list | tuple):
        return ()
    return tuple(
        (str(one[0]), str(one[1]))
        for one in said
        if isinstance(one, list | tuple) and len(one) == 2
    )


def _step(said: object) -> int:
    if isinstance(said, bool) or not isinstance(said, int) or said < 0:
        return 0
    return said


def _numbers(said: object) -> dict[str, int]:
    if not isinstance(said, dict):
        return {}
    return {
        str(key): value
        for key, value in said.items()
        if isinstance(value, int) and not isinstance(value, bool) and value > 0
    }


def _strings(said: object) -> dict[str, str]:
    return {str(key): str(value) for key, value in said.items()} if isinstance(said, dict) else {}


def let_go(said: str) -> bool:
    return _plainly(said) in LET_GO


def said_yes(said: str) -> bool:
    return _plainly(said) in SAID_YES


def _plainly(said: str) -> str:
    return " ".join(said.strip().strip(".!?,").lower().split())


def _items(said: object) -> tuple[Mapping[str, str], ...]:
    return tuple(_strings(one) for one in said) if isinstance(said, list | tuple) else ()


def offered_job(messages: Sequence[Message], answering: str | None = None) -> Pending | None:
    asked = asked_under(messages, answering)
    decision = asked.decision if asked is not None else None
    if not decision or decision.get("kind") != JOB or not decision.get("workflow_id"):
        return None
    if decision.get("resume"):
        return None
    listed = decision.get("missing")
    return Pending(
        workflow_id=str(decision["workflow_id"]),
        title=str(decision.get("title") or ""),
        values=_strings(decision.get("values")),
        missing=tuple(str(one) for one in listed) if isinstance(listed, list | tuple) else (),
        items=_items(decision.get("items")),
        watched=bool(decision.get("watched", True)),
        can_find=bool(decision.get("can_find", False)),
        mail_thread=str(decision.get("mail_thread") or ""),
    )


K_WITH_WHAT_WE_HAVE = re.compile(
    r"(?<!\w)(?:run|go|do)(?:\s+it)?\s+(?:with\s+)?what(?:ever)?\s+we(?:'ve)?\s+(?:have|got)(?!\w)",
    re.I,
)

K_DROP = re.compile(
    r"(?<!\w)(?:(?:i|we)\s+)?(?:(?:do\s*n[o']?t|do\s+not)\s+have|skip|without)\s+"
    r"(?:(?:the|a|an|any)\s+)?(?P<what>\S.*)$",
    re.I | re.S,
)

K_HOLDING = re.compile(
    r"(?<!\w)(?:do\s*n[o']?t\s+know|do\s+not\s+know|let\s+me\s+check|not\s+yet|no\s+idea"
    r"|will\s+check|check\s+later"
    r"|(?:do\s*n[o']?t|do\s+not)\s+have\s+[^,;.]*?(?<!\w)(?:yet|for\s+now|right\s+now|at\s+the\s+moment))"
    r"(?!\w)",
    re.I,
)

K_CLAUSE = re.compile(r"[,;\n]+|[.!?]+(?=\s|$)|\s+and\s+", re.I)

K_LABELLED = re.compile(
    r"^\s*(?P<label>[^\W\d][\w '-]{0,60}?)\s*(?::-|:|=)(?!//)\s*(?P<value>.*)$", re.S
)

K_NOT_READY = re.compile(r"(?<!\w)(?:yet|for\s+now|right\s+now|at\s+the\s+moment)(?!\w)", re.I)

K_FIRST_PERSON = re.compile(r"(?:(?:i|we)\s+)?(?:do\s*n[o']?t|do\s+not)\s+have", re.I)

K_WHAT_ENDS = re.compile(r"[.!?]+(?=\s|$)|\s+(?:just|but|so|then|please|yet)(?!\w)", re.I)

K_PRONOUNS = frozenset({"it", "that", "this", "them", "those", "one"})

K_LIKE = 0.8

K_MARGIN = 0.1


def _words(said: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", said.lower())


def _labels(pending: Pending, name: str) -> tuple[str, ...]:
    known = pending.known
    one = next((each for each in known.fields if each.name == name), None) if known else None
    return (name, *(one.labels if one else ()))


def _score(said: str, label: str) -> float:
    if _plain(said) == _plain(label):
        return 1.0
    one, other = _words(said), _words(label)
    if not one or len(one) != len(other):
        return 0.0
    return min(SequenceMatcher(None, a, b).ratio() for a, b in zip(one, other, strict=True))


def _field(said: str, pending: Pending) -> tuple[str | None, tuple[str, ...]]:
    askable = _askable(pending)
    hit = field_of(said, pending.known) if pending.known is not None else None
    if hit is not None and hit[0] in askable:
        return hit[0], ()
    exact = [
        name
        for name in askable
        if any(_plain(one) == _plain(said) for one in _labels(pending, name))
    ]
    if len(exact) == 1:
        return exact[0], ()
    scored = sorted(
        ((max(_score(said, one) for one in _labels(pending, name)), name) for name in askable),
        reverse=True,
    )
    best = scored[0] if scored else (0.0, "")
    runner = scored[1][0] if len(scored) > 1 else 0.0
    if not exact and best[0] >= K_LIKE and best[0] - runner >= K_MARGIN:
        return best[1], ()
    words = set(_words(said))
    near = tuple(exact) or tuple(
        name
        for score, name in scored
        if score >= K_LIKE or (words and 2 * _shared(words, _labels(pending, name)) >= len(words))
    )
    return None, near


def _shared(words: set[str], labels: Sequence[str]) -> int:
    theirs = {one for label in labels for one in _words(label)}
    return sum(
        1
        for word in words
        if word in theirs or (len(word) >= 3 and any(one.startswith(word) for one in theirs))
    )


@dataclass(frozen=True, slots=True)
class _Reply:
    named: dict[str, str] = field(default_factory=dict)
    dropped: tuple[str, ...] = ()
    which: dict[str, tuple[str, ...]] = field(default_factory=dict)
    all_the_rest: bool = False
    holding: bool = False
    doubt: dict[str, str] = field(default_factory=dict)

    @property
    def says_what_it_is(self) -> bool:
        return bool(self.named or self.dropped or self.which or self.all_the_rest or self.doubt)


@dataclass(slots=True)
class _Value:
    name: str
    start: int
    end: int
    open: bool


def _clauses(said: str) -> list[tuple[int, int]]:
    spans, at = [], 0
    for cut in K_CLAUSE.finditer(said):
        spans.append((at, cut.start()))
        at = cut.end()
    return [*spans, (at, len(said))]


def _dropping(
    clause: str, pending: Pending
) -> tuple[re.Match[str], str, str | None, tuple[str, ...]] | None:
    drop = K_DROP.search(clause)
    if drop is None or K_NOT_READY.search(drop.group("what")):
        return None
    what = K_WHAT_ENDS.split(drop.group("what"), maxsplit=1)[0].strip()
    name, near = _field(what, pending)
    return drop, what, name, near


def _label_of(label: str, pending: Pending) -> tuple[str | None, tuple[str, ...]]:
    name, near = _field(label, pending)
    if name is not None or near:
        return name, near
    other = field_of(label, pending.known) if pending.known is not None else None
    return None, (other[0],) if other is not None else ()


def _starts(clause: str, pending: Pending) -> bool:
    labelled = K_LABELLED.match(clause)
    if labelled is not None and any(_label_of(labelled.group("label"), pending)):
        return True
    drop = _dropping(clause, pending)
    return (
        (drop is not None and (drop[2] is not None or bool(drop[3])))
        or K_HOLDING.search(clause) is not None
        or K_WITH_WHAT_WE_HAVE.search(clause) is not None
    )


def _exactly(what: str, name: str, pending: Pending) -> bool:
    hit = field_of(what, pending.known) if pending.known is not None else None
    return (hit is not None and hit[0] == name) or any(
        _plain(one) == _plain(what) for one in _labels(pending, name)
    )


def _read(pending: Pending, said: str) -> _Reply:
    if is_a_question(said):
        return _Reply(holding=True)
    reply = _Reply(all_the_rest=K_WITH_WHAT_WE_HAVE.search(said) is not None)
    dropped: list[str] = []
    holding = K_HOLDING.search(said) is not None
    values: list[_Value] = []
    for start, end in _clauses(said):
        clause = said[start:end]
        if not clause.strip():
            continue
        if values and values[-1].open and not _starts(clause, pending):
            values[-1].end = end
            continue
        if values:
            values[-1].open = False
        labelled = K_LABELLED.match(clause)
        cut = end
        doubt = ""
        if (drop := _dropping(clause, pending)) is not None:
            match, what, name, near = drop
            inside = labelled is not None and match.start() >= labelled.start("value")
            if (
                inside
                and not K_FIRST_PERSON.match(match.group(0))
                and name is not None
                and _exactly(what, name, pending)
                and name not in pending.doubted
            ):
                doubt = name
            elif not inside or K_FIRST_PERSON.match(match.group(0)):
                if name is not None:
                    dropped.append(name)
                elif near:
                    reply.which[what] = near
                elif _words(what) and set(_words(what)) <= K_PRONOUNS:
                    holding = True
                if name is not None or near:
                    cut = start + match.start()
        if labelled is None or start + labelled.start("value") > cut:
            continue
        name, near = _label_of(labelled.group("label"), pending)
        if name is not None:
            values.append(_Value(name, start + labelled.start("value"), cut, cut == end))
            if doubt:
                reply.doubt[name] = doubt
        elif near:
            reply.which[labelled.group("label").strip()] = near
    for one in values:
        value = said[one.start : one.end].strip()
        if value and one.name not in reply.named:
            reply.named[one.name] = value
    return replace(reply, dropped=tuple(dict.fromkeys(dropped)), holding=holding)


def changes(pending: Pending, given: Mapping[str, str]) -> dict[str, str]:
    """What a reply to a refusal that named no value changes: only a value that
    is not the one the system already refused (case and spacing aside)."""
    return {
        name: value
        for name, value in given.items()
        if _plain_words(value) != _plain_words(pending.values.get(name, ""))
    }


def _plain_words(value: str) -> str:
    return " ".join(value.split()).casefold()


def _askable(pending: Pending) -> tuple[str, ...]:
    return (*pending.missing, *(name for name, _ in pending.offered))


def named_in(pending: Pending, said: str) -> bool:
    return _read(pending, said).says_what_it_is


def _limits(pending: Pending, name: str) -> FieldLimits:
    return FieldLimits(max_length=pending.limits.get(name), options=pending.options.get(name))


def _the_option(pending: Pending, said: str) -> str | None:
    fits = [
        name
        for name in pending.missing
        if any(_plain(one) == _plain(said) for one in pending.options.get(name, ()))
    ]
    return fits[0] if len(fits) == 1 else None


def answered(pending: Pending, said: str, logins: Logins = Logins()) -> Pending:
    value = said.strip()[:K_SAID]
    if not value or not pending.missing:
        return pending
    reply = _read(pending, value)
    named = {name: one for name, one in reply.named.items() if name not in reply.doubt}
    which = dict(reply.which)
    if not reply.says_what_it_is and not reply.holding:
        if len(pending.missing) == 1:
            named = {pending.missing[0]: value}
        elif (only := _the_option(pending, value)) is not None:
            named = {only: value}
        else:
            which = {value: pending.missing}
    refused = {
        name: why
        for name, one in named.items()
        if (why := refusal(one, value, _limits(pending, name), logins))
    }
    taken = {name: one for name, one in named.items() if name not in refused}
    taken = changes(pending, taken)
    not_had = (
        *reply.dropped,
        *(
            name
            for name in _askable(pending)
            if reply.all_the_rest and name not in taken and name not in refused
        ),
    )
    gone = (
        set(taken) | set(not_had) | (set(pending.missing) if taken and pending.changing else set())
    )
    return replace(
        pending,
        values={**pending.values, **taken},
        missing=tuple(name for name in pending.missing if name not in gone),
        offered=tuple(one for one in pending.offered if one[0] not in gone),
        dropped=tuple(dict.fromkeys((*pending.dropped, *not_had))),
        without=tuple(
            dict.fromkeys((*pending.without, *(n for n in pending.missing if n in not_had)))
        ),
        refused=refused,
        which=which,
        doubting=tuple(dict.fromkeys(reply.doubt.values())),
        doubted=tuple(dict.fromkeys((*pending.doubted, *reply.doubt.values()))),
        confirmed=True,
    )


def _plain(name: str) -> str:
    return "".join(letter for letter in name.lower() if letter.isalnum())
