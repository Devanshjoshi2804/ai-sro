"""The brain reads a mail the way it reads a chat message, and starts nothing.

A dry turn: `start_job` runs only its checks. The last start the brain tried is the
reading -- its job and values when the checks passed (sure), or its job, values and
the required parameters it lacked when the only refusal was what was missing."""

from __future__ import annotations

from dataclasses import dataclass, field

from sro.application.chat.brain import Brain
from sro.application.chat.brain_tools import values_of
from sro.application.chat.mailbox import Unread
from sro.application.context import RequestContext
from sro.domain.chat.brain_turn import Origin

_MISSING = "missing: "


@dataclass(frozen=True, slots=True)
class MailReading:
    workflow_id: str
    values: dict[str, str] = field(default_factory=dict)
    missing: tuple[str, ...] = ()
    sure: bool = False


class BrainReader:
    def __init__(self, brain: Brain) -> None:
        self._brain = brain

    async def read(
        self, ctx: RequestContext, *, text: str, earlier: str, sender: str, subject: str, offer: str
    ) -> MailReading | None:
        reply = await self._brain.turn(
            ctx,
            message=text,
            history=[f"operator: {earlier}"] if earlier else [],
            origin=Origin("mail", sender, subject),
            offer=offer,
            dry=True,
        )
        tried = [(call, result) for call, result in reply.steps if call.tool == "start_job"]
        if not tried:
            if reply.failed or "budget" in reply.trouble:
                # Not "no job": the brain could not read it. The mail is left to be read again.
                raise Unread(reply.said)
            return None
        # A dry "would" does not end the turn: the last start that passed its checks is the
        # reading; only when none passed, the last refusal (it may be a missing-only one).
        call, result = next(((c, r) for c, r in reversed(tried) if r.ok), tried[-1])
        values = values_of(call.args) or {}
        job = str(call.args.get("job_id") or "")
        if result.ok:
            return MailReading(job, values, (), True)
        missing = _only_missing(result.error)
        # The brain committed to one job: what is missing does not make it unsure of the job.
        return MailReading(job, values, missing, True) if missing else None


def _only_missing(error: str) -> tuple[str, ...]:
    """The refusal named nothing but missing parameters: anything else (a value not the
    sender's words, a mail-sending job, an unknown job) is not a reading.

    ponytail: names are split on ',' because `what_is_wrong` joins them with ', '; a parameter
    name containing a comma would split wrongly (the reader has no job facts to match against)."""
    parts = [one.strip() for one in error.split(";") if one.strip()]
    if len(parts) != 1 or not parts[0].startswith(_MISSING):
        return ()
    return tuple(n.strip() for n in parts[0][len(_MISSING) :].split(",") if n.strip())
