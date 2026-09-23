# Notes for `backend/src/sro/domain/execution/uses_edges.py`

Comments and docstrings moved out of [`backend/src/sro/domain/execution/uses_edges.py`](../../../../../../../backend/src/sro/domain/execution/uses_edges.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/domain/execution/uses_edges.py#L1): Docstring

> Which earlier step a later one took its value FROM, read off the evidence.
>
> `Step.uses` is CrewAI's `Task.context` and it has existed with nothing to write
> it. This writes it, and the rule is the one the whole codebase keeps: the edge
> is discovered rather than guessed, and where the evidence does not settle it
> nothing is claimed.
>
> **A value the SERVER made.** The signal is not "step five typed something step
> two also had" -- a job that types one code into two screens would read as a
> dependency, and it is one parameter typed twice. It is "step five typed
> something that did not exist until step two was answered": a key in step two's
> response record whose value was not in step two's own request. An id the
> warehouse minted. The later step could not have known it any other way, and
> that is precisely what a dependency is.
>
> **Per doing, and every doing.** A generated id differs between demonstrations
> -- record 111 on Tuesday and 222 on Wednesday -- so the match is made inside
> one doing and required in all of them. That is what makes this strong rather
> than a coincidence: a constant that happened to appear twice matches once and
> fails the next doing, and two doings that both track the answer they were given
> are not a coincidence anybody has to rule out.
>
> Cites are paired by POSITION, which is how they are written: a step cites one
> gesture per doing, in the order the doings happened, and `_bodies_of` reads
> them the same way. A step whose cites do not line up with another's -- a
> different number of doings -- contributes only the positions both have.
>
> Pure. Nothing here reads a store, and nothing here decides what a run does with
> an edge; `run_workflow._what_earlier_steps_made` is that half.

## module, [line 10](../../../../../../../backend/src/sro/domain/execution/uses_edges.py#L10): Note on the line above

Code: `K_SHORTEST = 3`

> How long a value must be before it can carry a dependency.
>
> `0`, `-1` and `SG` appear all over a warehouse form, and an edge drawn from one
> is an edge drawn from a coincidence. Three characters is the shortest thing an
> id ever is, and short enough to keep the real ones.

## `uses_edges`, [line 13](../../../../../../../backend/src/sro/domain/execution/uses_edges.py#L13): Docstring

> For each step, the earlier steps whose answer it used. Empty where none.
>
> Only backwards, which needs no check here -- the loop only ever looks at
> steps already passed -- and `checks.validate` refuses a forward edge anyway,
> so a producer that emitted one would be caught rather than trusted.

## `_every_doing_took_it`, [line 29](../../../../../../../backend/src/sro/domain/execution/uses_edges.py#L29): Docstring

> Whether every doing this pair shares took a value that doing produced.
>
> `all`, and never over an empty list: a pair with no doing in common has
> demonstrated nothing about each other, and `all(())` is True, which would
> make an edge out of two steps that were never recorded together.

## `_made_by`, [line 36](../../../../../../../backend/src/sro/domain/execution/uses_edges.py#L36): Docstring

> Per doing, the values this step's answer carried that its request did not.
>
> The difference is the whole rule. A value the request sent and the response
> gave back is the operator's own coming round again; one only the response
> has is one the warehouse minted, and nothing downstream could have known it
> before this step ran.
>
> One entry per DOING and not per call, so it pairs with `_took`: a doing is
> what the two steps share, and a step whose gesture made three requests made
> them all in the same doing.

## `_took`, [line 56](../../../../../../../backend/src/sro/domain/execution/uses_edges.py#L56): Docstring

> Per doing, the values this step put in: typed into a control, or sent.
>
> Both, because a step reaches a value two ways and the evidence records them
> differently -- an operator pasting an id into a box, and a page posting one
> it held.

## `_writes`, [line 73](../../../../../../../backend/src/sro/domain/execution/uses_edges.py#L73): Docstring

> The calls that could have MINTED something: mutations, with an answer.
>
> A read is excluded, and it is the case that matters rather than a tidiness.
> The confirming read-back this system relies on everywhere -- `GET
> /api/orders?latest=1` after the POST -- answers with exactly the record
> that was just sent, and its own request has no body to subtract, so every
> value the operator typed reads as a value the warehouse minted. That is the
> other half of the same measurement: on `rigproof`, `OFFER-1` and `PO-99001`
> were typed into the form and came back as the server's own work.

## `_record`, [line 81](../../../../../../../backend/src/sro/domain/execution/uses_edges.py#L81): Docstring

> A body as its leaf values, keyed, flattened one level.
>
> Strings only and never short ones: an edge drawn from `0` or `SG` is an
> edge drawn from a coincidence.

## `uses_edges`, [line 22](../../../../../../../backend/src/sro/domain/execution/uses_edges.py#L22): Comment

Code: `if set(step.cites) & set(earlier.cites):`

> Never a step that stands on the same evidence. Two steps citing
> one gesture are one thing the operator did, narrated twice -- and
> `_made_by` and `_took` then read the SAME call from both sides,
> so the "dependency" is a step on itself. Measured on `rigproof`
> 2026-09-19: the only edge in three tenants' stores was exactly
> this, `Create a client` step 2 on step 1, both citing one click.

## `_took`, [line 61](../../../../../../../backend/src/sro/domain/execution/uses_edges.py#L61): Comment

Code: `if isinstance(typed, str) and typed.strip():`

> No length rule here, deliberately. `_record` keeps the one that
> matters, on the side that PRODUCES a value -- so nothing short can
> ever be matched however it arrived, and a second copy of the rule
> here would be a line no test can reach and a number to keep in step.
