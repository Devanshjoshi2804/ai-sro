# Notes for `backend/src/sro/domain/execution/takeover.py`

Why each part of a mid-job takeover (spec §7.6) is the way it is. Each note names the code it explains (function or class, then the line in the current file).

## module, [line 17](../../../../../../../backend/src/sro/domain/execution/takeover.py#L17): Note

Code: `OPERATOR = "operator"`

> The lane recorded for a write the operator made in their own browser before
> Steel took the job over. Not a `Lane`: no lane of this runtime sent it, and
> the mark and the step row say who did.

## `Took`, [line 27](../../../../../../../backend/src/sro/domain/execution/takeover.py#L27): Note

Code: `if self.since > self.through:`

> `since` and `through` are the recorder times of the first and last gesture
> the extension's match used. A span that ends before it begins is a caller's
> mistake, refused rather than read as "nothing was done".

## `Takeover.progress`, [line 40](../../../../../../../backend/src/sro/domain/execution/takeover.py#L40): Note

Code: `progress.sending(order, OPERATOR)`

> The run's first progress: every write the operator reached is marked as sent,
> and only the proven ones settle `done`. A `done` mark is immutable, so the
> runtime never sends it again; a mark left `sending` is in doubt, and a doubt
> is settled by a read-back or a question -- never by sending it again.

## `take_over`, [line 55](../../../../../../../backend/src/sro/domain/execution/takeover.py#L55): Note

Code: `reached = {gesture.id for gesture, _ in walkable(cited_pairs(workflow, by_id))[:matched]}`

> What the operator reached by the extension's count. A reached write the
> uploads cannot settle is in doubt; a form they only filled is not a save,
> and its steps are simply replayed. The count is not the only witness: see
> the note on `could`.

## `take_over`, [line 57](../../../../../../../backend/src/sro/domain/execution/takeover.py#L57): Note

Code: `uploaded = any(one.at >= took.through for one in since)`

> Nothing is proven until the uploads reach the last gesture the match used.
> An upload still on its way is not evidence of absence.

## `take_over`, [line 59](../../../../../../../backend/src/sro/domain/execution/takeover.py#L59): Note

Code: `(_seen(call), uploaded and one.tab_id == took.tab_id and one.at <= took.through)`

> A call can PROVE a write only from the operator's own tab, inside the span
> the match used, [since, through] (spec §7.6 "in that span"). Every call of
> the pressing browser since `since`, on any tab, is still read as a WITNESS:
> a save made past a stale offer's count, or in a popup, is a write that may
> have happened, and it is never ignored.

## `take_over`, [line 66](../../../../../../../backend/src/sro/domain/execution/takeover.py#L66): Note

Code: `claims = [`

> A write is confirmed only by its own call: `same_call` (same method, path
> shape, host and body keys as the recording) carrying that step's own values
> -- the parameters its body slots are known to take (`wanted_by`). Shape and
> order never attribute a call: one save's 201 once proved another save that
> had been refused. A call two steps could both own proves neither, and a
> write whose values are not known (demonstrated once) cannot be proven by a
> call at all -- it is read back or asked about.

## `take_over`, [line 74](../../../../../../../backend/src/sro/domain/execution/takeover.py#L74): Note

Code: `could = [`

> Every call that may be this write: its shape, and either its own or owned
> by no step. A write is `done` when one of them is its own, in the span, and
> accepted. An own 4xx in the span proves that call did not write, so it
> confirms nothing and leaves nothing in doubt; anything else that may be this
> write -- or a reached write the uploads say nothing about -- is in doubt,
> settled by a read-back or a question and never sent again.

## `take_over`, [line 86](../../../../../../../backend/src/sro/domain/execution/takeover.py#L86): Note

Code: `replay_from = 0`

> The run begins one past the last proven write that precedes every write not
> proven. The steps before that write fed it, and replaying them would leave
> a second, unsaved form in Steel's tab; an earlier doubt, or an earlier write
> the operator's refusal proved unmade, keeps the run at the start.
