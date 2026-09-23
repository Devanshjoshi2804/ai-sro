# Notes for `backend/src/sro/domain/observation/attempts.py`

Comments and docstrings moved out of [`backend/src/sro/domain/observation/attempts.py`](../../../../../../../backend/src/sro/domain/observation/attempts.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/domain/observation/attempts.py#L1): Docstring

> Something a person asked this system for, and what came of it.
>
> Everything this system records, it records as STATE. A run is a row because a
> run was created; an offer is a row because an offer was made; an approval is a
> row because somebody approved. `/v1/audit` reads a tenant's day by joining
> those four tables, and it is a good account of everything that worked.
>
> **Nothing at all is written when nothing happens.** An operator presses "Yes,
> do it" and a gate refuses before a run is created; they answer a question and
> the thread cannot use the answer; they press Undo on a run with nothing to take
> back. In every one of those the person did something, the system decided, and
> the only trace is an HTTP status on a request nobody kept -- so the question a
> support engineer is actually asked, *I pressed it and nothing happened*, cannot
> be answered from anything this system stores.
>
> Logs carry it now, and logs are the wrong shelf for it: they rotate, they are
> per-process, and reading one tenant's day out of them means grepping a
> collector somebody else operates. This is the same fact on the shelf the audit
> is already on.
>
> **An attempt, not an event.** The word matters, because it sets what belongs
> here: a thing a PERSON asked for, and the answer. Not every state change --
> those have their own rows and this is not a second copy of them; not every
> decision the system makes on its own, which is what the log is for. If nobody
> was waiting on it, it is not an attempt.
>
> **Ids and a short reason, never a value.** Same rule as the telemetry plane
> beside it: what somebody typed belongs in the run that used it, where the
> approval machinery governs who may read it back. An attempt says a run was
> refused and why it was refused; it does not say what the customer was called.

## module, [line 5](../../../../../../../backend/src/sro/domain/observation/attempts.py#L5): Note on the line above

Code: `K_WHY = 400`

> How much of a reason is kept. Long enough for the sentence a refusal
> already carries -- these are written for a person, not parsed -- and short
> enough that nothing can put a stack trace or a page of prose in this column.

## module, [line 10](../../../../../../../backend/src/sro/domain/observation/attempts.py#L10): Note on the line above

Code: `NOTHING = "nothing"`

> What came of it.
>
> `refused` is the system declining on purpose and able to say why. `failed` is
> it trying and breaking. `nothing` is the one this exists for: the request was
> accepted, nothing objected, and no state changed -- a press on an offer that
> had already expired, an undo with nothing to take back. Those three were one
> silence.

## `Attempt`, [line 16](../../../../../../../backend/src/sro/domain/observation/attempts.py#L16): Docstring

> One thing somebody asked for, and the answer.

## `Attempt`, [line 21](../../../../../../../backend/src/sro/domain/observation/attempts.py#L21): Note on the line above

Code: `asked_for: str`

> What they were trying to do, in this system's own words -- "press an
> offer", "approve a write", "undo a run". A fixed vocabulary would be a
> second list to keep in step with the doors; what keeps this honest is that
> it is written at the door, by the door, and never by a model.

## `Attempt`, [line 23](../../../../../../../backend/src/sro/domain/observation/attempts.py#L23): Note on the line above

Code: `came_of: str`

> One of `OUTCOMES`.

## `Attempt`, [line 25](../../../../../../../backend/src/sro/domain/observation/attempts.py#L25): Note on the line above

Code: `principal: str = ""`

> Who asked. Empty where a door has no person behind it -- a trigger, a
> sweep -- which is itself worth recording: an attempt nobody made is a
> system acting on its own, and somebody reading a day wants to know which
> of the two they are looking at.

## `Attempt`, [line 27](../../../../../../../backend/src/sro/domain/observation/attempts.py#L27): Note on the line above

Code: `why: str = ""`

> The refusal's own sentence, or what nothing means here. Empty on a
> plain `done`, because "it worked" is what `came_of` already says.

## `Attempt`, [line 29](../../../../../../../backend/src/sro/domain/observation/attempts.py#L29): Note on the line above

Code: `about: dict[str, str] = field(default_factory=dict)`

> The ids this was about -- run, workflow, thread, device, offer. The same
> closed vocabulary the log lines carry, for the same reason: this row leaves
> the tenant's own deployment whenever somebody exports an audit.

## `as_row`, [line 36](../../../../../../../backend/src/sro/domain/observation/attempts.py#L36): Docstring

> The attempt as a store writes it, with the reason bounded here.
>
> Bounded in the domain rather than at the column, so a caller that hands in
> a page of prose is trimmed by the same rule wherever it is stored, and a
> store that forgot its own limit cannot be the thing that decides.
