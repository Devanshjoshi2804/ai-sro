from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from urllib.parse import urlsplit

from sro.domain.observation.gesture import Gesture
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


MAIL_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {
        "to": {"type": "string"},
        "subject": {"type": "string"},
        "body": {"type": "string"},
    },
    "required": ["to", "subject", "body"],
    "propertyOrdering": ["to", "subject", "body"],
}

MAIL_INSTRUCTIONS = """You are writing one email a warehouse operator will read before it is sent.

You are given the job this email does, the values the operator gave for it,
and -- where it answers one -- the conversation it replies to.

Write the email the job describes. Use the operator's values exactly as given:
a code, a quantity or an address is copied, never paraphrased. Where it replies
to a conversation, answer the latest message in it, in the same language, and
address it to whoever the job's values name or, failing that, to whoever sent
the message being answered.

Never invent a recipient. `to` is an address that appears in the values or in
the conversation, or it is empty -- an empty `to` is how you say you do not
know who this goes to, and the operator will be asked.

Plain text. No placeholders, no signature block beyond the operator's name if
you know it, and nothing the values and the conversation do not support."""

_ADDRESS = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


def addresses_in(texts: Iterable[str]) -> frozenset[str]:
    return frozenset(found.lower() for text in texts for found in _ADDRESS.findall(str(text or "")))


def recipient_allowed(to: str, known: frozenset[str]) -> bool:
    wanted = addresses_in([to])
    return bool(wanted) and wanted <= known
