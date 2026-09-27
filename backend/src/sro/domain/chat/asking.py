from __future__ import annotations

import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from difflib import SequenceMatcher

from sro.domain.chat.request import refusal
from sro.domain.chat.thread import Message, Said, Speaker
from sro.domain.execution.field_classes import FieldLimits
from sro.domain.skill.signing_in import Logins

NEEDS = "needs_values"

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

    @property
    def asking_for(self) -> str:
        return self.missing[0] if self.missing else ""

    @property
    def ready(self) -> bool:
        return not self.missing and not self.without


def _holds(pending: Pending, name: str) -> str:
    said = []
    if (holds := pending.limits.get(name)) is not None:
        said.append(f"takes {holds} characters")
    if choices := pending.options.get(name):
        said.append("is one of " + ", ".join(choices))
    return f"{name} {' and '.join(said)}." if said else ""


def _distinct(names: Sequence[str]) -> tuple[str, ...]:
    kept: list[str] = []
    for name in names:
        if not _twins(name, kept):
            kept.append(name)
    return tuple(kept)


def question(pending: Pending) -> str:
    wanted = _distinct(pending.missing)
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
        for name in _distinct(pending.missing)
    ]


def asking_state(pending: Pending) -> dict[str, object]:
    return {
        "asks": asks(pending),
        **({"offered": [list(one) for one in pending.offered]} if pending.offered else {}),
        **({"dropped": list(pending.dropped)} if pending.dropped else {}),
        **(
            {"options": {name: list(one) for name, one in pending.options.items()}}
            if pending.options
            else {}
        ),
    }


def turned_down(pending: Pending) -> str:
    return "".join(f"I did not take {name}: it is {why}. " for name, why in pending.refused.items())


def cannot_without(pending: Pending) -> tuple[str, dict[str, object]]:
    lacking = _listed(pending.without)
    return (
        f"{pending.title} cannot run without {lacking}, and you said you do not have it. "
        "Nothing was started, and I will not ask for it again here.",
        {
            "kind": Said.NOTE,
            "workflow_id": pending.workflow_id,
            "mail_thread": pending.mail_thread,
            "cannot_run": [f"it needs {lacking}"],
            "dropped": list(pending.dropped),
        },
    )


def still_to_ask(pending: Pending, messages: Sequence[Message]) -> Pending:
    dropped: dict[str, None] = dict.fromkeys(pending.dropped)
    offered: set[str] = set()
    for one in messages:
        decision = one.decision
        if one.speaker is not Speaker.ASSISTANT or not decision:
            continue
        if decision.get("workflow_id") != pending.workflow_id:
            continue
        dropped.update(dict.fromkeys(_names(decision.get("dropped"))))
        offered.update(name for name, _ in _pairs(decision.get("offered")))
    return replace(
        pending,
        missing=tuple(name for name in pending.missing if name not in dropped),
        without=tuple(
            dict.fromkeys((*pending.without, *(n for n in pending.missing if n in dropped)))
        ),
        offered=tuple(
            one for one in pending.offered if one[0] not in dropped and one[0] not in offered
        ),
        dropped=tuple(dropped),
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


def _listed(names: Sequence[str]) -> str:
    if len(names) <= 1:
        return "".join(names)
    return ", ".join(names[:-1]) + " and " + names[-1]


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
    if named_in(pending, value):
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


def _offer(decision: Mapping[str, object]) -> tuple[str, str]:
    return str(decision.get("workflow_id") or ""), str(decision.get("mail_thread") or "")


def pending_job(messages: Sequence[Message], answering: str | None = None) -> Pending | None:
    asked = asked_under(messages, answering)
    decision = asked.decision if asked is not None else None
    if not decision or decision.get("kind") != NEEDS:
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


K_WHAT_WE_HAVE = re.compile(r"(?<!\w)what(?:ever)?\s+(?:we|i)\s+(?:have|got)(?!\w)", re.I)

K_NOT_HAD = re.compile(
    r"(?<!\w)(?:(?:do\s*n[o']?t|do\s+not|haven'?t|have\s+not)\s+(?:have|got|know)"
    r"|skip|leave\s+out|without)\s+(?:(?:the|a|an|any)\s+)?"
    r"(?P<what>.+?)\s*(?=[.,;!?]|(?<!\w)(?:just|and|but|so|then)(?!\w)|$)",
    re.I,
)

K_LIKE = 0.8

K_SENTENCE_END = re.compile(r"[;\n]|[.!?](?:\s|$)")


def _marker(name: str) -> str:
    words = re.split(r"[\s_-]+", name.strip())
    return r"(?<!\w)" + r"[\s_-]*".join(re.escape(one) for one in words) + r"\s*(?::-|:|=)"


def _named(said: str, names: Sequence[str]) -> dict[str, str]:
    found = sorted(
        (hit.start(), hit.end(), name)
        for name in names
        for hit in re.finditer(_marker(name), said, re.I)
    )
    kept = [one for n, one in enumerate(found) if all(one[0] >= was[1] for was in found[:n])]
    named: dict[str, str] = {}
    for n, (_, end, name) in enumerate(kept):
        stop = kept[n + 1][0] if n + 1 < len(kept) else len(said)
        value = K_SENTENCE_END.split(said[end:stop], maxsplit=1)[0]
        value = re.sub(r"(?:[\s,;.]|(?<!\w)and(?!\w))+$", "", value).strip()
        if value and name not in named:
            named[name] = value
    return named


def _alike(what: str, name: str) -> bool:
    one, other = _plain(what), _plain(name)
    return bool(one) and (
        one == other or _shares(one, other) or SequenceMatcher(None, one, other).ratio() >= K_LIKE
    )


def _not_had(said: str, names: Sequence[str]) -> tuple[str, ...]:
    if K_WHAT_WE_HAVE.search(said):
        return tuple(names)
    heard = [hit.group("what") for hit in K_NOT_HAD.finditer(said)]
    return tuple(name for name in names if any(_alike(what, name) for what in heard))


def _askable(pending: Pending) -> tuple[str, ...]:
    return (*pending.missing, *(name for name, _ in pending.offered))


def named_in(pending: Pending, said: str) -> bool:
    askable = _askable(pending)
    return bool(_named(said, askable)) or bool(_not_had(said, askable))


def _limits(pending: Pending, name: str) -> FieldLimits:
    return FieldLimits(max_length=pending.limits.get(name), options=pending.options.get(name))


def answered(pending: Pending, said: str, logins: Logins = Logins()) -> Pending:
    value = said.strip()[:K_SAID]
    askable = _askable(pending)
    if not value or not pending.missing:
        return pending
    named = _named(value, askable)
    not_had = _not_had(value, [name for name in askable if name not in named])
    if not named and not not_had:
        named = {pending.missing[0]: value}
    refused = {
        name: why
        for name, one in named.items()
        if (why := refusal(one, value, _limits(pending, name), logins))
    }
    taken = {name: one for name, one in named.items() if name not in refused}
    filled = {
        twin: one
        for name, one in taken.items()
        for twin in (name, *_twins(name, pending.missing))
        if twin not in taken or twin == name
    }
    gone = set(filled) | set(not_had)
    return replace(
        pending,
        values={**pending.values, **filled},
        missing=tuple(name for name in pending.missing if name not in gone),
        offered=tuple(one for one in pending.offered if one[0] not in gone),
        dropped=tuple(dict.fromkeys((*pending.dropped, *not_had))),
        without=tuple(
            dict.fromkeys((*pending.without, *(n for n in pending.missing if n in not_had)))
        ),
        refused=refused,
        confirmed=True,
    )


def _twins(asked: str, rest: Iterable[str]) -> set[str]:
    one = _plain(asked)
    return {other for other in rest if _shares(one, _plain(other))}


def _plain(name: str) -> str:
    return "".join(letter for letter in name.lower() if letter.isalnum())


def _shares(one: str, other: str) -> bool:
    if not one or not other:
        return False
    return one.endswith(other) or other.endswith(one)
