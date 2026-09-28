from __future__ import annotations

import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from email.utils import getaddresses
from typing import Final
from urllib.parse import urlsplit

from sro.domain.observation.gesture import Call, Gesture
from sro.domain.prompts.record import quoted_in
from sro.domain.shared.hosts import origin_of
from sro.domain.skill.workflow import Step, Workflow

MAILBOXES = frozenset({"mail.google.com"})


def is_mail_only(workflow: Workflow, by_id: Mapping[str, Gesture]) -> bool:
    if not workflow.steps:
        return False
    for step in workflow.steps:
        seen = {
            origin_of(by_id[cited].url or "")
            for cited in step.cites
            if cited in by_id and by_id[cited].url
        }
        if not seen and step.system:
            seen = {origin_of(step.system)}
        if not seen or not seen <= MAILBOXES:
            return False
    return True


def sends_mail(step: Step, by_id: Mapping[str, Gesture]) -> bool:
    return any(
        _pressed_send(by_id[one])
        for one in step.cites
        if one in by_id and on_the_mailbox(by_id[one])
    )


def on_the_mailbox(gesture: Gesture) -> bool:
    return (urlsplit(gesture.url or "").hostname or "") in MAILBOX_HOSTS


MAILBOX_HOSTS = frozenset({"mail.google.com", "outlook.office.com", "outlook.live.com"})


def _pressed_send(gesture: Gesture) -> bool:
    target = gesture.action.target
    if gesture.action.kind != "click" or target is None:
        return False
    name = " ".join((target.name or "").split()).lower()
    return (target.role or "button") == "button" and name.startswith("send")


_ADDRESS = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}")

_JOINED = r"(?:[\w-]|(?<=\d)[,./:](?=\d))"

_VALUE_LIKE = re.compile(
    r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}|" + _JOINED + r"*\d" + _JOINED + "*"
)

_SEND_CALL = re.compile(r"/sync/u/\d+/i/s")

_SENT_THREAD = re.compile(r"thread-f:(\d+)")

K_SENT_THREADS = 10

K_SEND_WINDOW_S = 120.0

REQUEST = "request"

MAIL_BODY: Final = "mail_body"

DRAFTED = "mail_draft"

WHICH_MAIL: Final = "which_mail"

DRAFT_QUESTIONS: Final = ("recipient", MAIL_BODY, WHICH_MAIL)

SEND_A_MAIL: Final = "mail_send"

REPLY_TO_A_MAIL: Final = "mail_reply"

FORWARD_A_MAIL: Final = "mail_forward"

ON_A_MAIL: Final = frozenset({REPLY_TO_A_MAIL, FORWARD_A_MAIL})

_BUILT_IN: Final = {
    SEND_A_MAIL: ("Send an email", "writes a new email to whoever the operator names"),
    REPLY_TO_A_MAIL: ("Reply to an email", "answers the email in the conversation"),
    FORWARD_A_MAIL: (
        "Forward an email",
        "passes the email in the conversation, and what it said, on to whoever the operator names",
    ),
}


def built_in(workflow_id: str, tenant: str) -> Workflow | None:
    said = _BUILT_IN.get(workflow_id)
    if said is None:
        return None
    title, does = said
    return Workflow(
        id=workflow_id,
        tenant=tenant,
        title=title,
        narrative=does,
        steps=[Step(order=0, says=title, system=f"https://{min(MAILBOXES)}")],
        signs_in=False,
        signs_out=False,
    )


def built_ins(tenant: str) -> tuple[Workflow, ...]:
    return tuple(one for key in _BUILT_IN if (one := built_in(key, tenant)) is not None)


@dataclass(frozen=True, slots=True)
class JobRecipient:
    address: str
    confirmed_by: str
    at: datetime


@dataclass(frozen=True, slots=True)
class Allowed:
    to: frozenset[str] = frozenset()
    bcc: frozenset[str] = frozenset()


@dataclass(frozen=True, slots=True)
class Checked:
    why: str = ""
    logged: str = ""
    recipient: bool = False
    to: tuple[str, ...] = ()
    bcc: tuple[str, ...] = ()


def mailboxes(text: str) -> tuple[str, ...] | None:
    found = getaddresses([text])
    if not found or any(not _ADDRESS.fullmatch(address) for _, address in found):
        return None
    return tuple(dict.fromkeys(address.casefold() for _, address in found))


def one_address_in(text: str, *, reply: bool) -> str:
    lines = text.replace("\r\n", "\n").split("\n")
    quoted = next((n for n, line in enumerate(lines) if line.lstrip().startswith(">")), None)
    if quoted is None and reply:
        return ""
    end = len(lines) if quoted is None else quoted
    while end and not lines[end - 1].strip():
        end -= 1
    if quoted is not None:
        while end and lines[end - 1].strip():
            end -= 1
    named = _named(" ".join(lines[:end]))
    if len(named) != 1:
        return ""
    (only,) = named
    return only[0] if only and len(only) == 1 else ""


def named_in(texts: Iterable[str]) -> frozenset[str]:
    return frozenset(one for text in texts for found in _named(text) for one in found or ())


def _named(text: str) -> set[tuple[str, ...] | None]:
    return {mailboxes(word.strip("<>()[]{},.;:!?'\"")) for word in text.split() if "@" in word}


def participants(conversation: Sequence[Mapping[str, object]]) -> frozenset[str]:
    headers = [str(one.get("from") or "") for one in conversation] + [
        str(one.get(key) or "")
        for one in conversation
        if one.get("sent") is True
        for key in ("to", "cc")
    ]
    return frozenset(address for header in headers for address in mailboxes(header) or ())


def sent_from(
    workflow: Workflow, by_id: Mapping[str, Gesture]
) -> tuple[tuple[float, tuple[str, ...]], ...]:
    found = []
    for step in workflow.steps:
        for cited in step.cites:
            gesture = by_id.get(cited)
            if gesture is None or not on_the_mailbox(gesture) or not _pressed_send(gesture):
                continue
            threads = tuple(
                dict.fromkeys(
                    format(int(number), "x")
                    for call in gesture.requests
                    if _sends(call)
                    for number in _SENT_THREAD.findall(_answer_of(call))
                )
            )
            found.append((gesture.at, threads if len(threads) <= K_SENT_THREADS else ()))
    return tuple(found)


def _answer_of(call: Call) -> str:
    return (call.response_body.text if call.response_body else "") or ""


def _sends(call: Call) -> bool:
    return (
        call.method.upper() == "POST"
        and call.status is not None
        and 200 <= call.status < 300
        and _SEND_CALL.fullmatch(urlsplit(call.url).path) is not None
    )


def check_draft(
    *,
    to: str,
    body: str,
    cited: Sequence[Mapping[str, object]],
    conversation: Sequence[Mapping[str, object]],
    values: Mapping[str, str],
    allowed: Allowed,
    request: Sequence[str] = (),
    vouched: Sequence[str] = (),
) -> Checked:
    wanted = mailboxes(to)
    if wanted is None:
        return Checked(
            "the mail's recipients could not be read: " + (to or "it names nobody"),
            "the recipients could not be read",
            recipient=True,
        )
    open_to = participants(conversation) | allowed.to | named_in(request)
    strangers = [one for one in wanted if one not in open_to | allowed.bcc]
    if strangers:
        return Checked(
            "the mail is addressed outside the conversation: " + ", ".join(strangers),
            f"{len(strangers)} recipient(s) outside the conversation",
            recipient=True,
        )
    addressed = tuple(one for one in wanted if one in open_to)
    if not addressed:
        return Checked(
            "the mail names nobody to send it to but a Bcc",
            "only a Bcc",
            recipient=True,
        )
    said = {
        str(one.get("id") or ""): f"{one.get('subject') or ''} {one.get('body') or ''}"
        for one in conversation
    } | {REQUEST: " ".join(request)}
    proven = _values_in((*values.values(), *vouched)) | _values_in(
        str(one.get("value") or "")
        for one in cited
        if quoted_in(str(one.get("value") or ""), said.get(str(one.get("message") or ""), ""))
    )
    loose = list(dict.fromkeys(t for t in _VALUE_LIKE.findall(body) if t.casefold() not in proven))
    if loose:
        return Checked(
            "the mail carries values nobody gave it: " + ", ".join(loose),
            f"{len(loose)} value(s) in the body nobody gave",
        )
    return Checked(to=addressed, bcc=tuple(one for one in wanted if one not in open_to))


def _values_in(texts: Iterable[str]) -> set[str]:
    return {token.casefold() for text in texts for token in _VALUE_LIKE.findall(text)}
