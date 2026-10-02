"""The brain reads a mail the way it reads a chat message, and starts nothing.

A dry turn: `start_job` runs only its checks. The last start the brain tried is the
reading -- its job and values when the checks passed (sure), or its job, values and
the required parameters it lacked when the only refusal was what was missing."""

from __future__ import annotations

from dataclasses import dataclass, field

from sro.application.chat.brain import Brain
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
            return None
        call, result = tried[-1]
        given = call.args.get("values")
        values = {
            str(k): str(v).strip()
            for k, v in (given.items() if isinstance(given, dict) else ())
            if str(v).strip()
        }
        job = str(call.args.get("job_id") or "")
        if result.ok:
            return MailReading(job, values, (), True)
        missing = _only_missing(result.error)
        return MailReading(job, values, missing, False) if missing else None


def _only_missing(error: str) -> tuple[str, ...]:
    """The refusal named nothing but missing parameters: anything else (a value not the
    sender's words, a mail-sending job, an unknown job) is not a reading."""
    parts = [one.strip() for one in error.split(";") if one.strip()]
    if len(parts) != 1 or not parts[0].startswith(_MISSING):
        return ()
    return tuple(n.strip() for n in parts[0][len(_MISSING) :].split(",") if n.strip())
