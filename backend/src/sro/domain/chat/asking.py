from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field

from sro.domain.chat.thread import Message, Speaker

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

    @property
    def asking_for(self) -> str:
        return self.missing[0] if self.missing else ""

    @property
    def ready(self) -> bool:
        return not self.missing


def question(pending: Pending) -> str:
    asked = pending.asking_for
    holds = pending.limits.get(asked)
    if holds is None:
        return f"What should {asked} be?"
    return f"{asked} takes {holds} characters. What should it be?"


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
    )


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


def answered(pending: Pending, said: str) -> Pending:
    value = said.strip()[:K_SAID]
    if not value or not pending.missing:
        return pending
    if too_long_for(pending, said) is not None:
        return pending
    asked = pending.missing[0]
    filled = {asked, *_twins(asked, pending.missing[1:])}
    return Pending(
        workflow_id=pending.workflow_id,
        title=pending.title,
        values={**pending.values, **dict.fromkeys(filled, value)},
        missing=tuple(name for name in pending.missing if name not in filled),
        items=pending.items,
        watched=pending.watched,
        limits=pending.limits,
        from_step=pending.from_step,
        mail_thread=pending.mail_thread,
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
