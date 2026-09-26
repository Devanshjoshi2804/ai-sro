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


_ADDRESS = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


def addresses_in(texts: Iterable[str]) -> frozenset[str]:
    return frozenset(found.lower() for text in texts for found in _ADDRESS.findall(str(text or "")))


def recipient_allowed(to: str, known: frozenset[str]) -> bool:
    wanted = addresses_in([to])
    return bool(wanted) and wanted <= known
