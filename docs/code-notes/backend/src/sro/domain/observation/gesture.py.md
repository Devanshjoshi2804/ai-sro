# Notes for `backend/src/sro/domain/observation/gesture.py`

Comments and docstrings moved out of [`backend/src/sro/domain/observation/gesture.py`](../../../../../../../backend/src/sro/domain/observation/gesture.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/domain/observation/gesture.py#L1): Docstring

> What the rig keeps of a gesture, as the arithmetic reads it.
>
> Frozen, framework-free. The wire format the extension speaks is
> `sro.application.capture.rig_wire`; `correlate` there turns one into these.
> Every module in the domain that reads a control's identity, a typed value or
> a recorded call reads it from here and from nowhere else.

## `Component`, [line 17](../../../../../../../backend/src/sro/domain/observation/gesture.py#L17): Docstring

> What an ExtJS page knows about the control; None on plain HTML.

## `Component`, [line 23](../../../../../../../backend/src/sro/domain/observation/gesture.py#L23): Note on the line above

Code: `required: bool | None = None`

> Ext's own word for it: `allowBlank: false`. None where the component
> said nothing, which reads as optional.

## `Component`, [line 24](../../../../../../../backend/src/sro/domain/observation/gesture.py#L24): Note on the line above

Code: `chain: tuple[str, ...] = ()`

> The component's own ancestry -- `panel#clients textfield#clientCode` split
> into its parts, where `query` is the same thing already joined. X4's
> page-code payload and snapshot repair read this to re-find a control by
> ancestor rather than by the query string alone (§4.1).

## `Target`, [line 43](../../../../../../../backend/src/sro/domain/observation/gesture.py#L43): Note on the line above

Code: `required: bool | None = None`

> Whether the PAGE says this field must be filled -- `aria-required`, the
> HTML5 attribute, or a star on its label, whichever the form used. None
> where nothing said, which reads as optional: a page marking required
> fields by colour alone tells this system nothing, and guessing from a
> colour is how a run stops for a field nobody has to fill.

## `Target`, [line 46](../../../../../../../backend/src/sro/domain/observation/gesture.py#L46): Note on the line above

Code: `bounds: dict[str, float] = field(default_factory=dict, hash=False)`

> Excluded from the hash because a `dict` cannot be hashed and a `Target` is
> used as a value elsewhere. The rectangle the control occupied when
> captured, which is what a snapshot repair matches against once the DOM it
> was captured from is gone (§4.1).

## `Target`, [line 47](../../../../../../../backend/src/sro/domain/observation/gesture.py#L47): Note on the line above

Code: `attributes: dict[str, object] = field(default_factory=dict, hash=False)`

> Excluded from the hash for the same reason as `bounds` above. Value type is
> `object`, not `Any`: the wire's `rig_wire.Target.attributes` is `dict[str,
> Any]` because that module is JSON's one honest exception to the domain's
> `disallow_any_explicit`, but the domain has no such exception, and `object`
> costs nothing here since this field is only ever round-tripped, never
> inspected by key. Already redacted by `rig_wire.redact_attributes` before
> this ever sees it, so nothing here re-checks a credential -- this is the
> DOM's own attribute map, which X4's page-code payload matches a control by
> when `query` alone
> is ambiguous (§4.1).

## `AfterState`, [line 62](../../../../../../../backend/src/sro/domain/observation/gesture.py#L62): Docstring

> Pre-created for X4's UI-lane verification, which reads `Action.after` to
> know what a control should show once a step is done. E5 owns this file and
> this type -- the shape here (`value`, `visible`, `enabled`) is copied
> verbatim from E5's own brief, not designed here, so E5 lands the rest of it
> (`Gesture.prior`, the recorder's `stateOf`, `correlate`'s join) on top of a
> type already in its final shape rather than choosing between two
> definitions. X3 pre-created the same type once already and it was deleted
> as dead (nothing consumed it yet); X4 is the first real consumer.

## `Action`, [line 146](../../../../../../../backend/src/sro/domain/observation/gesture.py#L146): Docstring

> The gesture itself: what was done, to what, with what typed.

## `Action`, [line 153](../../../../../../../backend/src/sro/domain/observation/gesture.py#L153): Note on the line above

Code: `modifiers: tuple[str, ...] = ()`

> The held keys -- `shift`, `ctrl`, `alt`, `meta` -- the extension already
> captured and this used to drop. A run replaying the gesture needs them to
> reproduce a modified click or keypress rather than a bare one (§4.1).

## `Call`, [line 174](../../../../../../../backend/src/sro/domain/observation/gesture.py#L174): Docstring

> A recorded exchange, the part of it the belts read: never a response
> body's text beyond what `confirming_read` compares.

## `GestureBatch`, [line 218](../../../../../../../backend/src/sro/domain/observation/gesture.py#L218): Docstring

> What one upload said about itself.
>
> ``started_at`` and ``ended_at`` are the device's own clock for the window
> the batch covers, against ``received_at``'s server clock; ``recording_id``
> names which teaching recording a demonstration batch belongs to.
>
> Not `observation.batch.ObservationBatch`, which is the same upload as the
> capture pipeline records it: events in the blob store, typed identifiers,
> real datetimes. This is the miner's view of the same arrival -- the rig's
> counted tally, whose events landed in `gestures` -- and the two are
> separate tables. Both may describe one upload; neither is derived from the
> other.

## `passed_through`, [line 256](../../../../../../../backend/src/sro/domain/observation/gesture.py#L256): Docstring

> Whether this gesture ended on a different system from the one it
> happened on -- the browser moved the operator, the operator did not.
>
> A fact about a gesture, so it lives beside gestures. `checks.work_only`
> reads it to know a sign-in hop from a system somebody worked in, and
> `values.worked_in_both` reads it for the same distinction: a browser
> bouncing through an identity provider is not somebody using two tabs.

## `Call`, [line 177](../../../../../../../backend/src/sro/domain/observation/gesture.py#L177): Comment

Code: `request_id: str = ""`

> The rig's wire `request_id` is a required string, so a call that came off
> a batch always has one; "" is what a hand-built call has instead of None,
> which keeps the type a plain str for everything that reads it.

## `Outline`, [line 82](../../../../../../../backend/src/sro/domain/observation/gesture.py#L82): Class

> The screen a gesture was made on, as labels, roles and the role of each
> message on it -- never a value, and never what a message said (spec §4.6). Stored inside `gestures.gesture` like every other action
> field, so it needed no migration. `Action.outlines` holds the screens seen
> since the frame's previous gesture, the last being this gesture's own;
> `outline.last_outline` answers for a gesture that carried none.

## `Place`, [line 91](../../../../../../../backend/src/sro/domain/observation/gesture.py#L91): Class

> Richer capture (ADR 016). Every new field on `Target`, `Action` and
> `PageMark` is optional and defaulted, so a row stored before them loads
> unchanged. Nothing in identity (`target_identity`, `screen_of`,
> `shape_key`) reads any of them, and `seen.py` is the only place their text
> is sanitised.
