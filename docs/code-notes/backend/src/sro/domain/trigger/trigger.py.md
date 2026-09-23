# Notes for `backend/src/sro/domain/trigger/trigger.py`

Comments and docstrings moved out of [`backend/src/sro/domain/trigger/trigger.py`](../../../../../../../backend/src/sro/domain/trigger/trigger.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/domain/trigger/trigger.py#L1): Docstring

> What starts a run when nobody typed a sentence.

## `TriggerKind`, [line 19](../../../../../../../backend/src/sro/domain/trigger/trigger.py#L19): Note on the line above

Code: `MANUAL = "manual"`

> A button. Kept as a kind so a trigger record exists for it: the run's
> parameters and its standing authorisation are then the same object whether
> a person or a clock started it.

## `TriggerKind`, [line 22](../../../../../../../backend/src/sro/domain/trigger/trigger.py#L22): Note on the line above

Code: `INBOUND = "inbound"`

> A mail or a chat message. Not built; named so that the shape it will take
> is decided once rather than invented under time pressure.

## `TriggerKind`, [line 24](../../../../../../../backend/src/sro/domain/trigger/trigger.py#L24): Note on the line above

Code: `ARRIVAL = "arrival"`

> A page the operator landed on. The same shape as a watch -- a rule their
> own browser holds and applies, speaking only when it matches -- with the
> page they are standing on in place of the mail they are reading.
>
> It exists because nothing started a run on its own. A job could be
> recognised and a browser could be driven, and the only things that joined
> them were a person pressing a button, a console, and a clock.

## `TriggerKind`, [line 26](../../../../../../../backend/src/sro/domain/trigger/trigger.py#L26): Note on the line above

Code: `WATCH = "watch"`

> A mail the operator's own browser recognised. The same message as
> INBOUND arriving the other way round: nobody relays it, nothing is posted,
> the browser that already has the mailbox open evaluates the rule locally and
> speaks only when it matches. There is no server-side evaluation of one, by
> design -- which is why a watch without a device is refused.

## `Trigger`, [line 30](../../../../../../../backend/src/sro/domain/trigger/trigger.py#L30): Docstring

> A skill, the values to run it with, and the authority to do so.
>
> The authority is the part that matters. A scheduled write happens with
> nobody watching, so the name on it has to have been written down in advance
> -- and this is where. ``Run`` refuses an above-shadow write with no
> authoriser; a trigger that could not name one is refused at creation, which
> is hours or weeks before the first time it would have gone off.

## `Trigger`, [line 37](../../../../../../../backend/src/sro/domain/trigger/trigger.py#L37): Note on the line above

Code: `skill_id: SkillId | None = None`

> The taught skill this runs, where it runs one.

## `Trigger`, [line 39](../../../../../../../backend/src/sro/domain/trigger/trigger.py#L39): Note on the line above

Code: `workflow_id: str | None = None`

> The mined job this runs, where it runs one.
>
> Exactly one of the two, checked below. A trigger is the authority to do a
> particular thing at a time nobody is watching, and a record that named two
> things -- or none -- would be authority over which?
>
> The rig's jobs were unreachable from here until this field existed: a
> workflow the miner learned, proved and earned could be started by a person
> accepting an offer in their own browser and by nothing else. A job that can
> only run while somebody is already doing it by hand is not automation.

## `Trigger`, [line 42](../../../../../../../backend/src/sro/domain/trigger/trigger.py#L42): Note on the line above

Code: `from_message: tuple[str, ...] = ()`

> Parameters this trigger takes from whatever fires it, rather than from
> what it was created with -- the order number in a mail.
>
> Allowed, not required: everything left out of this stays the value the
> trigger was created with. The distinction is the whole safety of an inbound
> trigger, whose token is presented by a relay nobody in this tenant wrote.
> A message that could name any parameter could name the facility, and a read
> somebody authorised for one warehouse would answer about another.

## `Trigger`, [line 44](../../../../../../../backend/src/sro/domain/trigger/trigger.py#L44): Note on the line above

Code: `asks: bool = False`

> This watch asks a question rather than running anything.
>
> A mail arrives saying "how many suppliers are set up at SG" and the answer
> is in the systems the operator works in, not in a job anybody demonstrated
> -- `umbrella` is explicit that looking something up is a step of a job and
> never a job, so there is no workflow for a trigger like this to name.
>
> So the one invariant below is relaxed for exactly this case: a trigger
> names a skill, or a job, or -- when it asks -- neither. It still names ONE
> thing to do; the thing is a lookup.
>
> The question itself is a VALUE and not a term: read out of the mail at
> match time in the operator's own browser, passed as a parameter, never
> written down. That is the same contract every other value read out of a
> mail is under, and it is what keeps this inside ADR 008's line rather than
> moving correspondence into the control plane. `watch.py` is where that
> argument is made in full.

## `Trigger`, [line 46](../../../../../../../backend/src/sro/domain/trigger/trigger.py#L46): Note on the line above

Code: `arrival: Arrival | None = None`

> The page whose arrival fires this, where it is an arrival trigger.
>
> Beside `watch` rather than inside it: both are rules a browser evaluates,
> and neither type has a field the other's data would fit in -- a watch
> carries terms about a mail, an arrival carries one page. Collapsing them
> into "a local rule" would make the refusals below say "a local rule needs
> something local", which is a sentence nobody can act on.

## `Trigger`, [line 48](../../../../../../../backend/src/sro/domain/trigger/trigger.py#L48): Note on the line above

Code: `watch: Watch | None = None`

> What makes a mail one of these, and where to read the values out of it.
> A watch trigger's ``from_message`` is derived from it rather than given
> separately: two lists of the same names are two lists that disagree.

## `Trigger`, [line 53](../../../../../../../backend/src/sro/domain/trigger/trigger.py#L53): Note on the line above

Code: `device_id: DeviceId | None = None`

> Run it in this operator's own browser. A scheduled run that names one
> happens only while that browser is connected, which is a property of a
> laptop and not a fault.

## `Trigger`, [line 58](../../../../../../../backend/src/sro/domain/trigger/trigger.py#L58): Note on the line above

Code: `writes: bool = False`

> Whether the skill changes the system. Copied at creation rather than
> joined, for the same reason a run copies its stage: a skill re-induced into
> something that writes must not silently make an old trigger a writing one.

## `Trigger`, [line 61](../../../../../../../backend/src/sro/domain/trigger/trigger.py#L61): Note on the line above

Code: `requires_confirmation: bool = True`

> A fire becomes a card somebody presses. False is auto-approve, and it is
> a per-trigger decision made by a named person -- never a global setting, and
> never a default for anything that writes.

## `Trigger`, [line 63](../../../../../../../backend/src/sro/domain/trigger/trigger.py#L63): Note on the line above

Code: `may_take_focus: bool = False`

> Whether a run may pull the operator's tab to the front. Off, because
> stealing focus from somebody mid-sentence is how an extension gets
> uninstalled.

## `Trigger`, [line 69](../../../../../../../backend/src/sro/domain/trigger/trigger.py#L69): Note on the line above

Code: `inbound_token: str | None = None`

> What a mail relay or a chat webhook presents instead of a tenant
> credential -- there is no principal on the other end of an inbound
> message, only this trigger's own secret. Minted once at creation; nothing
> here rotates it.

## `Trigger.runs`, [line 153](../../../../../../../backend/src/sro/domain/trigger/trigger.py#L153): Docstring

> What this trigger runs, as an id, whichever kind it is. One reader
> for a log line, a card and a console row -- three places that had no
> business each deciding which field to look in.

## `Trigger.values_from`, [line 156](../../../../../../../backend/src/sro/domain/trigger/trigger.py#L156): Docstring

> What to run with, given what fired this.
>
> A name the trigger did not declare is dropped rather than refused: a
> relay that adds a field to its payload is not a reason for a mailbox
> rule that has worked for a year to stop.

## `Trigger.fired`, [line 168](../../../../../../../backend/src/sro/domain/trigger/trigger.py#L168): Docstring

> It went off.
>
> ``run_id`` is ``None`` where nothing started yet: a write that needs
> confirming became a card. The trigger has still fired, and a schedule
> that showed "never" while filling somebody's queue would be the screen
> disagreeing with the thing it describes.

## `Trigger.disable`, [line 174](../../../../../../../backend/src/sro/domain/trigger/trigger.py#L174): Docstring

> Stopped, with the reason attached. A trigger that was switched off
> and nobody remembers why gets switched back on.

## `Trigger.__post_init__`, [line 84](../../../../../../../backend/src/sro/domain/trigger/trigger.py#L84): Comment

Code: `raise InvariantViolation("a question writes nothing")`

> Structural rather than a promise. A read may not write, and
> the one place a trigger could have claimed otherwise is here.

## `Trigger.__post_init__`, [line 114](../../../../../../../backend/src/sro/domain/trigger/trigger.py#L114): Comment

Code: `raise InvariantViolation("an arrival with no browser sees nobody arrive")`

> Nothing evaluates an arrival except the browser the operator
> is standing in. One with no device is not a trigger that
> fires rarely; it is one that cannot fire at all.

## `Trigger.__post_init__`, [line 122](../../../../../../../backend/src/sro/domain/trigger/trigger.py#L122): Comment

Code: `raise InvariantViolation("a watch with no browser watches nothing: name a device")`

> Nothing evaluates a watch except the browser that holds it.
> One without a device is not a trigger that fires rarely, it
> is a trigger that cannot fire at all.

## `Trigger.__post_init__`, [line 78](../../../../../../../backend/src/sro/domain/trigger/trigger.py#L78): Comment

Code: `raise InvariantViolation(`

> Nothing to ask. A watch that asks a question has to say where
> in the mail the question is, and a rule matching a sender
> with no question marked would fire on every mail from them
> and look up nothing.

## `Trigger.__post_init__`, [line 141](../../../../../../../backend/src/sro/domain/trigger/trigger.py#L141): Comment

Code: `self.from_message = self.watch.reads`

> After the check above, not instead of it: a watch is told things
> by the mail it matched, and the names it may be told are exactly
> the ones it was pointed at. `values_from` then needs to know
> nothing about watches.

## `Trigger.__post_init__`, [line 86](../../../../../../../backend/src/sro/domain/trigger/trigger.py#L86): Comment

Code: `raise InvariantViolation(`

> The whole point of the record. Refused here, weeks before it
> would have written to a warehouse with nobody's name on it.

## `Trigger.__post_init__`, [line 148](../../../../../../../backend/src/sro/domain/trigger/trigger.py#L148): Comment

Code: `self.requires_confirmation = False`

> Not a rule about safety -- a read needs no confirming -- but about
> the field meaning one thing.
