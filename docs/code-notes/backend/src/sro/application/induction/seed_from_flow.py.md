# Notes for `backend/src/sro/application/induction/seed_from_flow.py`

Comments and docstrings moved out of [`backend/src/sro/application/induction/seed_from_flow.py`](../../../../../../../backend/src/sro/application/induction/seed_from_flow.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/induction/seed_from_flow.py#L1): Docstring

> A recorded call cascade, taught without anyone demonstrating it again.
>
> Blue Yonder gives this system no API docs and no tools of its own -- what stands
> in for them is `knowledge-base/http/flows/*.json`, built by driving the real
> application once and keeping the exchange. A flow is shaped enough like a
> demonstration that it does not need a second induction path: one synthetic
> frame per recorded call, fed to the same `UnderstandRecording` a single live
> teach already goes through. What it produces is trusted the same amount a
> single demonstration always was -- shadow, proposed parameters, every write
> withheld until somebody reviews it -- never promoted further just for having
> come from evidence instead of a click.

## `_addressable_values`, [line 24](../../../../../../../backend/src/sro/application/induction/seed_from_flow.py#L24): Docstring

> Every value this call sent somewhere a diff would call addressable.
>
> Not a substring search: ``clientId="----"`` is not "typed" by a call that
> merely mentions ``----`` somewhere in a query string it shares with every
> other call in the file (a real collision in the recorded corpus, on the
> generic placeholder Blue Yonder itself uses). A URL path segment, a query
> value, and a JSON body leaf are the only places `diff.py`'s own two-run
> comparison ever looks either -- reusing exactly that vocabulary instead of
> a second, cruder one closes off everything past those three.

## `flow_to_events`, [line 33](../../../../../../../backend/src/sro/application/induction/seed_from_flow.py#L33): Docstring

> One demonstration's worth of events, read out of a recorded cascade.
>
> One frame per call, never one more: a frame with a typed value and no
> request of its own still becomes a step, and a step with no network plan
> wants a live browser to replay -- exactly what this exists to avoid. So the
> call that first carries an ``applied`` field's value *is* the typing of it,
> the same self-referential frame the single-demonstration path already
> proves out: `typed_values()` finds its own action's value in its own
> request and recovers the parameter without a second, separate step.
>
> Not every file under ``http/flows/`` is this shape -- a terser one records
> a read-only dashboard's calls flat, with no nested request or response at
> all. Nothing here is a task to replay either way, so a call missing that
> shape empties the whole flow rather than seeding a skill from half of it.

## `Seeded`, [line 109](../../../../../../../backend/src/sro/application/induction/seed_from_flow.py#L109): Note on the line above

Code: `skipped: str | None = None`

> Why nothing was seeded. Not an error: a flow already claimed by a skill,
> or one with nothing a task could be named from, is ordinary -- a sweep that
> treated either as a failure would log a wall of noise for a corpus that
> grows a file at a time.
