"""A job that is nothing but mail, done as mail rather than as clicks.

Mined mail jobs used to be replayed through Gmail's page, and a mailbox is the
worst place to drive a browser: one step carries the recipients, the subject
and the body, and a click cannot carry any of them. Measured on the deployment
2026-09-23 -- three runs of `Reply to Email` refused with "a click cannot
carry a value", three of `Compose and Send Email` ended "state unknown after a
write" because nothing on a screen can say a mail went.

The mailbox has an API, and the deployment already talks to it for everything
else mail does -- reading requests, reading replies, sending the draft to
whoever asked. So a job whose every step is in the mailbox is not run on the
page at all: a model writes the mail, the operator reads it, and their press
sends it through the connector, whose answer is the verdict.

Pure: what counts as a mail job, what the model is asked, and who may be
written to. The reading, the drafting and the sending are the application's.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping

from sro.domain.observation.gesture import Gesture
from sro.domain.shared.hosts import origin_of
from sro.domain.skill.workflow import Workflow

MAILBOXES = frozenset({"mail.google.com"})
"""The mailbox the connector reads and writes, as a host -- which is what
`origin_of` answers, scheme and all left off. One, because the connector is
Gmail's; a second provider is a second connector before it is a line here."""


def is_mail_only(workflow: Workflow, by_id: Mapping[str, Gesture]) -> bool:
    """Whether every step of this job happened in the mailbox.

    Read off the evidence each step cites, and the step's own system where it
    cites nothing this store still holds. A job with one step anywhere else --
    a sign-in, a warehouse screen -- is not a mail job: its mail half is read
    by the gather rung, and the rest is a page that has to be driven.
    """
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
    """Every email address named anywhere in these, lowercased."""
    return frozenset(found.lower() for text in texts for found in _ADDRESS.findall(str(text or "")))


def recipient_allowed(to: str, known: frozenset[str]) -> bool:
    """Whether every address the model put in `to` was already on the page.

    A mail sent to an address nobody gave is the one mistake this job cannot
    take back, so the rule is the evidence's: an address in the run's values
    or in the conversation being answered, and nothing else. `to` may list
    several; every one of them has to pass.
    """
    wanted = addresses_in([to])
    return bool(wanted) and wanted <= known
