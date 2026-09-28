from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from sro.domain.execution.mail_job import (
    MAILBOX_HOSTS,
    on_the_mailbox,
    sends_mail,
    wrote_the_mailbox,
)
from sro.domain.observation.gesture import Gesture
from sro.domain.skill.workflow import Step, Workflow

K_EXAMPLES = 5

K_TEXT = 200

K_LEAST = 24

K_MAILBOXES = tuple(sorted(MAILBOX_HOSTS))


@dataclass(frozen=True, slots=True)
class AskedBy:
    text: str
    at: float


def mails_behind(workflow: Workflow, by_id: Mapping[str, Gesture]) -> tuple[AskedBy, ...]:
    found: dict[str, AskedBy] = {}
    for step in sorted(workflow.steps, key=lambda one: one.order):
        for cited in step.cites:
            gesture = by_id.get(cited)
            if gesture is None or not from_a_mailbox(gesture):
                continue
            said = _said(gesture)
            if said is None:
                continue
            was = found.get(said)
            found[said] = AskedBy(text=said, at=max(gesture.at, was.at if was else gesture.at))
    newest = sorted(found.values(), key=lambda one: one.at, reverse=True)
    return tuple(newest[:K_EXAMPLES])


def texts(mails: Sequence[AskedBy]) -> list[str]:
    return [one.text for one in mails]


def from_a_mailbox(gesture: Gesture) -> bool:
    where = f"{gesture.system or ''} {gesture.url or ''}"
    return any(host in where for host in K_MAILBOXES)


def only_reads_the_mail(step: Step, by_id: Mapping[str, Gesture]) -> bool:
    cited = [by_id[one] for one in step.cites if one in by_id]
    if not cited or not all(on_the_mailbox(gesture) for gesture in cited):
        return False
    return not sends_mail(step, by_id)


def by_hand(workflow: Workflow, step: Step, by_id: Mapping[str, Gesture]) -> bool:
    if not only_reads_the_mail(step, by_id) or _leads_to_a_send(workflow, step, by_id):
        return False
    return any(
        wrote_the_mailbox(by_id[one]) and _said(by_id[one]) is None
        for one in step.cites
        if one in by_id
    )


def _leads_to_a_send(workflow: Workflow, step: Step, by_id: Mapping[str, Gesture]) -> bool:
    for later in sorted(workflow.steps, key=lambda one: one.order):
        if later.order <= step.order:
            continue
        if sends_mail(later, by_id):
            return True
        if not only_reads_the_mail(later, by_id):
            return False
    return False


def _said(gesture: Gesture) -> str | None:
    target = gesture.action.target
    said = " ".join(((target.name if target else None) or "").split())
    if len(said) < K_LEAST:
        return None
    return said if len(said) <= K_TEXT else said[:K_TEXT] + "…"


__all__ = ["K_EXAMPLES", "K_LEAST", "K_TEXT", "AskedBy", "by_hand", "mails_behind", "texts"]
