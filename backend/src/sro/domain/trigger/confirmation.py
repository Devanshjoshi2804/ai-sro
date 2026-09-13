"""A fire that is waiting for somebody to say yes.

A manual trigger needs none of this: the click that fires it is the
confirmation. A schedule and an inbound message both go off with nobody there
to ask, and until now the only honest options were auto-approve -- chosen by a
named person, for one trigger -- or refusing to create the trigger at all.
`CreateTrigger` said so in as many words: *a write has nowhere to ask for
confirmation yet*.

This is the nowhere. The fire becomes an item, somebody answers it, and the run
starts then and with their name on it.

What it is not is a queue that drains itself. Nothing here starts a run because
time passed; an item nobody answered expires, and expiring is a decision to do
nothing rather than a decision deferred. The alternative -- a write that happens
because everybody was on holiday -- is the failure this whole ladder exists to
prevent.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import StrEnum
from types import MappingProxyType

from sro.domain.execution.run import RunId
from sro.domain.shared.errors import InvariantViolation
from sro.domain.shared.identifiers import (
    ConfirmationId,
    PrincipalId,
    SkillId,
    TenantId,
    TriggerId,
)

ANSWER_WITHIN = timedelta(hours=24)
"""How long an unanswered fire stays answerable.

Long enough to survive a night and a weekend morning; short enough that
approving one is still approving *this* mail rather than something that
arrived on Tuesday. A warehouse instruction nobody looked at for a week is not
an instruction any more, and asking somebody to judge one is asking them to
guess at what was true then.
"""


class Answer(StrEnum):
    WAITING = "waiting"
    APPROVED = "approved"
    DECLINED = "declined"

    EXPIRED = "expired"
    """Nobody answered in time. Its own answer rather than an absence: "we chose
    not to" and "we never looked" are different things to read a month later,
    and only one of them is worth changing how the team works."""


@dataclass(eq=False)
class Confirmation:
    """One fire, and what somebody decided about it."""

    id: ConfirmationId
    tenant_id: TenantId
    trigger_id: TriggerId
    asked_at: datetime
    expires_at: datetime

    skill_id: SkillId | None = None
    workflow_id: str | None = None
    """What the fire would run. Exactly one, the same rule `Trigger` keeps and
    for the same reason: a card is a person being asked to authorise one
    particular thing, and one that named two would be asking about which?"""

    values: Mapping[str, str] = field(default_factory=dict)
    """What the run would go with, frozen at the moment it was asked.

    Not re-read from the trigger when somebody answers: what they are approving
    is what is written on the card in front of them. A trigger edited in
    between would otherwise turn a yes to one thing into a yes to another.
    """

    because: str = ""
    """What made this fire -- the mail's subject, the schedule's name. The one
    sentence somebody reads before deciding."""

    answer: Answer = Answer.WAITING
    answered_at: datetime | None = None
    answered_by: PrincipalId | None = None
    run_id: RunId | None = None
    note: str = ""

    def __post_init__(self) -> None:
        named = [name for name in (self.skill_id, self.workflow_id) if name]
        if len(named) != 1:
            raise InvariantViolation(
                "a confirmation asks about one thing: name a skill or a job, not "
                + ("both" if named else "neither")
            )
        for name, at in (("asked_at", self.asked_at), ("expires_at", self.expires_at)):
            if at.tzinfo is None:
                raise InvariantViolation(f"Confirmation.{name} must be timezone-aware")
        if self.expires_at <= self.asked_at:
            raise InvariantViolation("a confirmation that has already expired asks nothing")
        self.values = MappingProxyType(dict(self.values))

    @property
    def runs(self) -> str:
        """What this card would run, as an id, whichever kind it is."""
        return (self.skill_id.value if self.skill_id else None) or str(self.workflow_id)

    def waiting_at(self, now: datetime) -> bool:
        """Whether somebody can still answer this.

        Expiry is read rather than swept, for the same reason a grant's is: an
        item that has run out must stop being answerable the moment it does,
        and a job that has not run yet is not a thing to base that on.
        """
        return self.answer is Answer.WAITING and now < self.expires_at

    def approve(self, by: PrincipalId, at: datetime, run_id: RunId) -> None:
        self._require_waiting(at)
        self.answer = Answer.APPROVED
        self.answered_by = by
        self.answered_at = at
        self.run_id = run_id

    def decline(self, by: PrincipalId, at: datetime, note: str = "") -> None:
        self._require_waiting(at)
        self.answer = Answer.DECLINED
        self.answered_by = by
        self.answered_at = at
        self.note = note

    def expire(self, at: datetime) -> None:
        """Nobody answered. Recorded rather than deleted: a fire that was asked
        about and left is evidence about how a team is working, and a row that
        disappeared would be evidence of nothing."""
        if self.answer is not Answer.WAITING:
            return
        self.answer = Answer.EXPIRED
        self.answered_at = at

    def _require_waiting(self, at: datetime) -> None:
        if self.answer is not Answer.WAITING:
            raise InvariantViolation(f"this was already {self.answer}")
        if at >= self.expires_at:
            # Answering one that has run out is not a late yes, it is a yes to
            # something nobody has looked at since. The trigger fires again if
            # it is still true.
            raise InvariantViolation(
                "this expired without an answer; nothing was run and nothing can be now"
            )
