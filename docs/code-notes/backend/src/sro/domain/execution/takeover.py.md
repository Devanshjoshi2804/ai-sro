# Notes for `backend/src/sro/domain/execution/takeover.py`

Why each part of a mid-job takeover (spec §7.6) is the way it is. Each note names the code it explains (function or class, then the line in the current file).

## module, [line 15](../../../../../../../backend/src/sro/domain/execution/takeover.py#L15): Note

Code: `OPERATOR = "operator"`

> The lane recorded for a write the operator made in their own browser before
> Steel took the job over. Not a `Lane`: no lane of this runtime sent it, and
> the mark and the step row say who did.

## `Took`, [line 25](../../../../../../../backend/src/sro/domain/execution/takeover.py#L25): Note

Code: `if self.since > self.through:`

> `since` and `through` are the recorder times of the first and last gesture
> the extension's match used. A span that ends before it begins is a caller's
> mistake, refused rather than read as "nothing was done".

## `Takeover.progress`, [line 38](../../../../../../../backend/src/sro/domain/execution/takeover.py#L38): Note

Code: `progress.sending(order, OPERATOR)`

> The run's first progress: every write the operator reached is marked as sent,
> and only the proven ones settle `done`. A `done` mark is immutable, so the
> runtime never sends it again; a mark left `sending` is in doubt, and a doubt
> is settled by a read-back or a question -- never by sending it again.

## `take_over`, [line 52](../../../../../../../backend/src/sro/domain/execution/takeover.py#L52): Note

Code: `reached = {gesture.id for gesture, _ in walkable(cited_pairs(workflow, by_id))[:matched]}`

> A write counts only when the recorded gesture that made its call is among the
> first `matched` walkable entries: what the operator has reached. A form they
> only filled is not a save, and its steps are simply replayed.

## `take_over`, [line 54](../../../../../../../backend/src/sro/domain/execution/takeover.py#L54): Note

Code: `(one for one in seen if one.tab_id == took.tab_id and one.at >= took.since),`

> Only this doing's gestures, from the operator's own tab: a save from an
> earlier doing of the same job, or from another tab, proves nothing about this
> one. The operator's tab itself is never touched -- Steel works in its own.

## `take_over`, [line 57](../../../../../../../backend/src/sro/domain/execution/takeover.py#L57): Note

Code: `uploaded = any(one.at >= took.through for one in theirs)`

> Nothing is `done` until the uploads reach the last gesture the match used.
> An upload still on its way is not evidence of absence, so a span the server
> has not fully seen leaves every write it reached in doubt.

## `take_over`, [line 71](../../../../../../../backend/src/sro/domain/execution/takeover.py#L71): Note

Code: `mine = next(`

> `write_confirmed` is the one rule for "the page's own call matches the
> recorded write", and only its `done` counts. A refusal (a 409 can mean the
> record exists), a 5xx or no answer is doubt, not "not written". Each of the
> operator's calls confirms one write: two saves of the same shape are not both
> proven by one POST.

## `take_over`, [line 84](../../../../../../../backend/src/sro/domain/execution/takeover.py#L84): Note

Code: `replay_from = 0`

> The run begins one past the last proven write that precedes every doubt. The
> steps before that write fed it, and replaying them would leave a second,
> unsaved form in Steel's tab; a doubt earlier than it keeps the run at the
> start, so that doubt is settled before anything after it runs.
