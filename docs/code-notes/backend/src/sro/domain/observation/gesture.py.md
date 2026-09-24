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

## `Target`, [line 36](../../../../../../../backend/src/sro/domain/observation/gesture.py#L36): Note on the line above

Code: `required: bool | None = None`

> Whether the PAGE says this field must be filled -- `aria-required`, the
> HTML5 attribute, or a star on its label, whichever the form used. None
> where nothing said, which reads as optional: a page marking required
> fields by colour alone tells this system nothing, and guessing from a
> colour is how a run stops for a field nobody has to fill.

## `Action`, [line 42](../../../../../../../backend/src/sro/domain/observation/gesture.py#L42): Docstring

> The gesture itself: what was done, to what, with what typed.

## `Call`, [line 61](../../../../../../../backend/src/sro/domain/observation/gesture.py#L61): Docstring

> A recorded exchange, the part of it the belts read: never a response
> body's text beyond what `confirming_read` compares.

## `GestureBatch`, [line 103](../../../../../../../backend/src/sro/domain/observation/gesture.py#L103): Docstring

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

## `passed_through`, [line 142](../../../../../../../backend/src/sro/domain/observation/gesture.py#L142): Docstring

> Whether this gesture ended on a different system from the one it
> happened on -- the browser moved the operator, the operator did not.
>
> A fact about a gesture, so it lives beside gestures. `checks.work_only`
> reads it to know a sign-in hop from a system somebody worked in, and
> `values.worked_in_both` reads it for the same distinction: a browser
> bouncing through an identity provider is not somebody using two tabs.

## `Call`, [line 64](../../../../../../../backend/src/sro/domain/observation/gesture.py#L64): Comment

Code: `request_id: str = ""`

> The rig's wire `request_id` is a required string, so a call that came off
> a batch always has one; "" is what a hand-built call has instead of None,
> which keeps the type a plain str for everything that reads it.
