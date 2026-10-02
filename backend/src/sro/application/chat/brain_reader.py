"""The brain reads a mail the way it reads a chat message, and starts nothing.

A dry turn: `start_job` runs only its checks. The last start the brain tried is the
reading -- its job and values when the checks passed (sure), or its job, values and
the required parameters it lacked when the only refusal was what was missing. When the
brain asked a question instead (`ask_operator`), or the start was refused for something the
sender can put right, the reader answers `MailAsked`: the question goes back the way a missing
value does (the ask chat and a drafted reply, sent only on the operator's press)."""

from __future__ import annotations

from dataclasses import dataclass, field

from sro.application.chat.brain import Brain
from sro.application.chat.brain_tools import _bounded, values_of
from sro.application.chat.feedback import RecordFeedback
from sro.application.chat.mailbox import MailAsked, Unread
from sro.application.context import RequestContext
from sro.domain.chat.brain_turn import Origin

_MISSING = "missing: "

# A refusal about the mail itself, not about a value the sender could supply: asking the sender
# would only invite them to talk the brain into it, so these are no request at all.
_ABOUT_THE_MAIL = (
    "that is not a job",
    "this job can't set",
    "is a secret",
    "is not in what was said",
)


@dataclass(frozen=True, slots=True)
class MailReading:
    workflow_id: str
    values: dict[str, str] = field(default_factory=dict)
    missing: tuple[str, ...] = ()
    sure: bool = False


class BrainReader:
    def __init__(self, brain: Brain, feedback: RecordFeedback | None = None) -> None:
        self._brain, self._feedback = brain, feedback

    async def read(
        self, ctx: RequestContext, *, text: str, earlier: str, sender: str, subject: str, offer: str
    ) -> MailReading | MailAsked | None:
        reply = await self._brain.turn(
            ctx,
            message=text,
            history=[f"operator: {earlier}"] if earlier else [],
            origin=Origin("mail", sender, subject),
            offer=offer,
            dry=True,
        )
        tried = [(call, result) for call, result in reply.steps if call.tool == "start_job"]
        asked = [
            str(call.args.get("question") or "").strip()
            for call, _ in reply.steps
            if call.tool == "ask_operator"
        ]
        question = next((one for one in reversed(asked) if one), "")
        if not tried:
            if question:
                return MailAsked(_bounded(question))
            if reply.failed:
                # Not "no job": the brain could not read it. The mail is left to be read again.
                raise Unread(reply.said)
            if reply.trouble and self._feedback is not None:
                # Out of steps or budget with no start is no job (and remembered as such: a mail
                # that does this every time must not be read again at every look).
                await self._feedback.mail_budget(ctx, offer, reply.trouble)
            return None
        # A dry "would" does not end the turn: the last start that passed its checks is the
        # reading; only when none passed, the last refusal (it may be a missing-only one).
        call, result = next(((c, r) for c, r in reversed(tried) if r.ok), tried[-1])
        values = values_of(call.args) or {}
        job = str(call.args.get("job_id") or "")
        if result.ok:
            return MailReading(job, values, (), True)
        if missing := _only_missing(result.error):
            # The brain committed to one job: what is missing does not make it unsure of the job.
            return MailReading(job, values, missing, True)
        if question:
            return MailAsked(_bounded(question))
        if askable(result.error):
            return MailAsked(f"I could not start this from the mail: {_bounded(result.error)}.")
        return None


def askable(error: str) -> bool:
    """A refusal the sender (or the operator) can put right: a value over its limit, nothing
    given for a job with only optional parameters, a job that sends mail. Not one about the mail
    itself: an unknown job or parameter, a secret, a value that is not the sender's words."""
    return bool(error.strip()) and not any(one in error for one in _ABOUT_THE_MAIL)


def _only_missing(error: str) -> tuple[str, ...]:
    """The refusal named nothing but missing parameters: anything else (a value not the
    sender's words, a mail-sending job, an unknown job) is not a reading.

    ponytail: names are split on ',' because `what_is_wrong` joins them with ', '; a parameter
    name containing a comma would split wrongly (the reader has no job facts to match against)."""
    parts = [one.strip() for one in error.split(";") if one.strip()]
    if len(parts) != 1 or not parts[0].startswith(_MISSING):
        return ()
    return tuple(n.strip() for n in parts[0][len(_MISSING) :].split(",") if n.strip())
