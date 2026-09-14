"""What starts a run when nobody typed a sentence."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from types import MappingProxyType
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sro.domain.execution.run import Medium, RunId
from sro.domain.shared.errors import InvariantViolation
from sro.domain.shared.identifiers import DeviceId, PrincipalId, SkillId, TenantId, TriggerId
from sro.domain.trigger.cron import why_not
from sro.domain.trigger.watch import QUESTION, Watch


class TriggerKind(StrEnum):
    MANUAL = "manual"
    """A button. Kept as a kind so a trigger record exists for it: the run's
    parameters and its standing authorisation are then the same object whether
    a person or a clock started it."""

    SCHEDULE = "schedule"
    INBOUND = "inbound"
    """A mail or a chat message. Not built; named so that the shape it will take
    is decided once rather than invented under time pressure."""

    WATCH = "watch"
    """A mail the operator's own browser recognised. The same message as
    INBOUND arriving the other way round: nobody relays it, nothing is posted,
    the browser that already has the mailbox open evaluates the rule locally and
    speaks only when it matches. There is no server-side evaluation of one, by
    design -- which is why a watch without a device is refused."""


@dataclass(eq=False)
class Trigger:
    """A skill, the values to run it with, and the authority to do so.

    The authority is the part that matters. A scheduled write happens with
    nobody watching, so the name on it has to have been written down in advance
    -- and this is where. ``Run`` refuses an above-shadow write with no
    authoriser; a trigger that could not name one is refused at creation, which
    is hours or weeks before the first time it would have gone off.
    """

    id: TriggerId
    tenant_id: TenantId
    kind: TriggerKind
    created_by: PrincipalId
    created_at: datetime

    skill_id: SkillId | None = None
    """The taught skill this runs, where it runs one."""

    workflow_id: str | None = None
    """The mined job this runs, where it runs one.

    Exactly one of the two, checked below. A trigger is the authority to do a
    particular thing at a time nobody is watching, and a record that named two
    things -- or none -- would be authority over which?

    The rig's jobs were unreachable from here until this field existed: a
    workflow the miner learned, proved and earned could be started by a person
    accepting an offer in their own browser and by nothing else. A job that can
    only run while somebody is already doing it by hand is not automation.
    """

    parameters: Mapping[str, str] = field(default_factory=dict)
    from_message: tuple[str, ...] = ()
    """Parameters this trigger takes from whatever fires it, rather than from
    what it was created with -- the order number in a mail.

    Allowed, not required: everything left out of this stays the value the
    trigger was created with. The distinction is the whole safety of an inbound
    trigger, whose token is presented by a relay nobody in this tenant wrote.
    A message that could name any parameter could name the facility, and a read
    somebody authorised for one warehouse would answer about another.
    """

    asks: bool = False
    """This watch asks a question rather than running anything.

    A mail arrives saying "how many suppliers are set up at SG" and the answer
    is in the systems the operator works in, not in a job anybody demonstrated
    -- `umbrella` is explicit that looking something up is a step of a job and
    never a job, so there is no workflow for a trigger like this to name.

    So the one invariant below is relaxed for exactly this case: a trigger
    names a skill, or a job, or -- when it asks -- neither. It still names ONE
    thing to do; the thing is a lookup.

    The question itself is a VALUE and not a term: read out of the mail at
    match time in the operator's own browser, passed as a parameter, never
    written down. That is the same contract every other value read out of a
    mail is under, and it is what keeps this inside ADR 008's line rather than
    moving correspondence into the control plane. `watch.py` is where that
    argument is made in full.
    """

    watch: Watch | None = None
    """What makes a mail one of these, and where to read the values out of it.
    A watch trigger's ``from_message`` is derived from it rather than given
    separately: two lists of the same names are two lists that disagree."""

    cron: str | None = None
    timezone: str = "UTC"

    device_id: DeviceId | None = None
    """Run it in this operator's own browser. A scheduled run that names one
    happens only while that browser is connected, which is a property of a
    laptop and not a fault."""

    medium: Medium = Medium.NETWORK

    enabled: bool = True
    writes: bool = False
    """Whether the skill changes the system. Copied at creation rather than
    joined, for the same reason a run copies its stage: a skill re-induced into
    something that writes must not silently make an old trigger a writing one.
    """

    authorized_by: PrincipalId | None = None
    requires_confirmation: bool = True
    """A fire becomes a card somebody presses. False is auto-approve, and it is
    a per-trigger decision made by a named person -- never a global setting, and
    never a default for anything that writes."""

    may_take_focus: bool = False
    """Whether a run may pull the operator's tab to the front. Off, because
    stealing focus from somebody mid-sentence is how an extension gets
    uninstalled."""

    last_fired_at: datetime | None = None
    last_run_id: RunId | None = None
    disabled_reason: str | None = None

    inbound_token: str | None = None
    """What a mail relay or a chat webhook presents instead of a tenant
    credential -- there is no principal on the other end of an inbound
    message, only this trigger's own secret. Minted once at creation; nothing
    here rotates it."""

    def __post_init__(self) -> None:
        if self.created_at.tzinfo is None:
            raise InvariantViolation("Trigger.created_at must be timezone-aware")

        named = [name for name in (self.skill_id, self.workflow_id) if name]
        if self.asks:
            if named:
                raise InvariantViolation(
                    "a trigger that asks a question runs nothing: name neither"
                )
            if self.kind is not TriggerKind.WATCH:
                raise InvariantViolation(f"a {self.kind} trigger has no question to ask")
            if self.writes:
                # Structural rather than a promise. A read may not write, and
                # the one place a trigger could have claimed otherwise is here.
                raise InvariantViolation("a question writes nothing")
        elif len(named) != 1:
            raise InvariantViolation(
                "a trigger runs one thing: name a skill or a job, not "
                + ("both" if named else "neither")
            )

        if self.kind is TriggerKind.SCHEDULE:
            if not self.cron:
                raise InvariantViolation("a scheduled trigger needs a cron expression")
            reason = why_not(self.cron)
            if reason is not None:
                raise InvariantViolation(reason)
            try:
                ZoneInfo(self.timezone)
            except (ZoneInfoNotFoundError, ValueError) as unknown:
                raise InvariantViolation(f"{self.timezone!r} is not a time zone") from unknown
        elif self.cron:
            raise InvariantViolation(f"a {self.kind} trigger does not run on a schedule")

        if self.kind is TriggerKind.INBOUND:
            if not self.inbound_token:
                raise InvariantViolation("an inbound trigger needs a token to be reached by")
        elif self.inbound_token is not None:
            raise InvariantViolation(f"a {self.kind} trigger is not reached by a token")

        if self.kind is TriggerKind.WATCH:
            if self.watch is None:
                raise InvariantViolation("a watch trigger needs something to watch for")
            if self.device_id is None:
                # Nothing evaluates a watch except the browser that holds it.
                # One without a device is not a trigger that fires rarely, it
                # is a trigger that cannot fire at all.
                raise InvariantViolation("a watch with no browser watches nothing: name a device")
            if self.from_message:
                raise InvariantViolation(
                    "a watch names its values by where it reads them; there is no second list"
                )
            if self.asks and not any(value.name == QUESTION for value in self.watch.values):
                # Nothing to ask. A watch that asks a question has to say where
                # in the mail the question is, and a rule matching a sender
                # with no question marked would fire on every mail from them
                # and look up nothing.
                raise InvariantViolation(
                    f"a watch that asks needs a {QUESTION!r} value: where in the mail the "
                    "question is"
                )
        elif self.watch is not None:
            raise InvariantViolation(f"a {self.kind} trigger has nothing to watch for")

        if self.from_message and self.kind is not TriggerKind.INBOUND:
            raise InvariantViolation(
                f"a {self.kind} trigger fires with the values it was created with; "
                "only an inbound one is told anything"
            )
        if self.watch is not None:
            # After the check above, not instead of it: a watch is told things
            # by the mail it matched, and the names it may be told are exactly
            # the ones it was pointed at. `values_from` then needs to know
            # nothing about watches.
            self.from_message = self.watch.reads

        if self.writes and self.authorized_by is None:
            # The whole point of the record. Refused here, weeks before it
            # would have written to a warehouse with nobody's name on it.
            raise InvariantViolation(
                "a trigger for something that changes the system must name who authorised it"
            )
        if not self.writes and not self.requires_confirmation:
            # Not a rule about safety -- a read needs no confirming -- but about
            # the field meaning one thing.
            self.requires_confirmation = False

        self.parameters = MappingProxyType(dict(self.parameters))

    @property
    def runs(self) -> str:
        """What this trigger runs, as an id, whichever kind it is. One reader
        for a log line, a card and a console row -- three places that had no
        business each deciding which field to look in."""
        return (self.skill_id.value if self.skill_id else None) or str(self.workflow_id)

    def values_from(self, message: Mapping[str, str]) -> dict[str, str]:
        """What to run with, given what fired this.

        A name the trigger did not declare is dropped rather than refused: a
        relay that adds a field to its payload is not a reason for a mailbox
        rule that has worked for a year to stop.
        """
        told = {name: value for name, value in message.items() if name in self.from_message}
        return {**dict(self.parameters), **told}

    @property
    def is_scheduled(self) -> bool:
        return self.kind is TriggerKind.SCHEDULE and self.enabled

    @property
    def auto_approves(self) -> bool:
        return self.writes and not self.requires_confirmation

    def fired(self, at: datetime, run_id: RunId | None = None) -> None:
        """It went off.

        ``run_id`` is ``None`` where nothing started yet: a write that needs
        confirming became a card. The trigger has still fired, and a schedule
        that showed "never" while filling somebody's queue would be the screen
        disagreeing with the thing it describes.
        """
        if at.tzinfo is None:
            raise InvariantViolation("every timestamp is timezone-aware")
        self.last_fired_at = at
        self.last_run_id = run_id

    def disable(self, reason: str) -> None:
        """Stopped, with the reason attached. A trigger that was switched off
        and nobody remembers why gets switched back on."""
        if not reason.strip():
            raise InvariantViolation("a trigger disabled for no reason cannot be judged later")
        self.enabled = False
        self.disabled_reason = reason

    def enable(self) -> None:
        self.enabled = True
        self.disabled_reason = None

    def authorise(self, by: PrincipalId) -> None:
        self.authorized_by = by
