from __future__ import annotations

import re
from collections.abc import Iterable, Mapping, Sequence
from urllib.parse import urlsplit

from sro.domain.observation.gesture import Gesture
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


_ADDRESS = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


def addresses_in(texts: Iterable[str]) -> frozenset[str]:
    return frozenset(found.lower() for text in texts for found in _ADDRESS.findall(str(text or "")))


_VALUE_LIKE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}|\b[\w-]*\d[\w-]*\b")

_RECIPIENT_FIELD = re.compile(r"(to|cc|bcc)( recipients)?")


def participants(conversation: Sequence[Mapping[str, object]]) -> frozenset[str]:
    return addresses_in(
        str(one.get(key) or "") for one in conversation for key in ("from", "to", "cc")
    )


def sent_to(workflow: Workflow, by_id: Mapping[str, Gesture]) -> frozenset[str]:
    return addresses_in(
        by_id[cited].action.value or ""
        for step in workflow.steps
        for cited in step.cites
        if cited in by_id and _into_a_recipient_field(by_id[cited])
    )


def _into_a_recipient_field(gesture: Gesture) -> bool:
    target = gesture.action.target
    if gesture.action.kind != "type" or gesture.action.secret or target is None:
        return False
    name = " ".join((target.name or "").split()).lower()
    return on_the_mailbox(gesture) and _RECIPIENT_FIELD.fullmatch(name) is not None


def check_draft(
    *,
    to: str,
    body: str,
    cited: Sequence[Mapping[str, object]],
    conversation: Sequence[Mapping[str, object]],
    values: Mapping[str, str],
    sent_before: frozenset[str] = frozenset(),
) -> str:
    wanted = addresses_in([to])
    if not wanted:
        return "the mail names nobody to send it to"
    strangers = wanted - participants(conversation) - sent_before
    if strangers:
        return "the mail is addressed outside the conversation: " + ", ".join(sorted(strangers))
    said = {str(one.get("id") or ""): str(one.get("body") or "") for one in conversation}
    proven = _values_in(values.values())
    for one in cited:
        value, message = str(one.get("value") or ""), str(one.get("message") or "")
        if not quoted_in(value, said.get(message, "")):
            return f"the mail cites {value!r} to a message that does not say it"
        proven |= _values_in([value])
    loose = sorted({token for token in _VALUE_LIKE.findall(body) if token.casefold() not in proven})
    if loose:
        return "the mail carries values nobody gave it: " + ", ".join(loose)
    return ""


def _values_in(texts: Iterable[str]) -> set[str]:
    return {token.casefold() for text in texts for token in _VALUE_LIKE.findall(text)}
