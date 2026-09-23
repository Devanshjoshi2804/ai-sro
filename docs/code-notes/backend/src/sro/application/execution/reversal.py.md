# Notes for `backend/src/sro/application/execution/reversal.py`

Comments and docstrings moved out of [`backend/src/sro/application/execution/reversal.py`](../../../../../../../backend/src/sro/application/execution/reversal.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/execution/reversal.py#L1): Docstring

> Whether what a run made can be taken back, and by which skill.
>
> A visible undo is the strongest thing an agentic surface has, because trust is
> knowing you can recover from a mistake. It is also where this design could most
> easily begin guessing, so it does not: an undo is offered on three facts or not
> at all.
>
>   - the run's write was a POST to some resource shape, and
>   - a runnable skill in this tenant's library DELETEs that same shape, and
>   - the run read back the identifier that skill needs.
>
> `url_shape` answers the middle one and is the same function induction uses to
> decide two calls are the same call. Nothing here is proposed as a reverse
> because it looked like one.
>
> Most tasks will have no undo for a long time, because nobody demonstrates
> deleting things. That is honest: the fallback is the operator fixing it while
> we watch, which is what they were going to do anyway.

## `Reversal`, [line 15](../../../../../../../backend/src/sro/application/execution/reversal.py#L15): Note on the line above

Code: `version: int`

> The version this undo was validated against -- `skill.runnable`, the one
> place "may this skill actually be asked to run" is answered.
>
> Carried out to the panel and back in on the press, for the same reason the
> preview carries one (ADR 014): a press that cannot name the version it was
> offered against runs whatever happens to be newest by the time it lands,
> which is a version nobody validated and nobody was shown.

## `Reversal`, [line 17](../../../../../../../backend/src/sro/application/execution/reversal.py#L17): Note on the line above

Code: `removes: str`

> What the delete step this found says it does, in the words of the
> demonstration it came from.
>
> `Undo that` is one press and stays one press -- that is the design. But one
> press with no idea what is about to be deleted is not something this design
> ever argued for, and the reversal skill's own steps and values are never
> rendered anywhere. This is the smallest honest answer: the intent of the
> step that does the deleting, shown beside the identifying values the panel
> already has, before the button is pressed rather than after.

## `reversal_for`, [line 22](../../../../../../../backend/src/sro/application/execution/reversal.py#L22): Docstring

> The skill that would undo what this run made, or ``None``.
>
> The first skill in the tenant's library that answers all three facts wins.
> Two skills that both delete the same shape is not a case this refuses to
> handle by picking the first -- it is a case nobody has produced yet.

## `_what_it_made`, [line 49](../../../../../../../backend/src/sro/application/execution/reversal.py#L49): Docstring

> The shape of the one resource this run created, if it created one.

## `_shapes_for`, [line 60](../../../../../../../backend/src/sro/application/execution/reversal.py#L60): Docstring

> The shape(s) a DELETE might match against what a run made.
>
> Most REST deletes name the record in the path -- `.../workOperations/
> $operation_id` -- so what has to match the bare `POST .../workOperations`
> that made the record is that shape with its trailing identifier set aside,
> not the record's own address. That segment is dropped before `url_shape`
> runs rather than after: `url_shape` only recognises an identifier by the
> digits in it, and a skill's own placeholder carries none.
>
> Not every DELETE names a record that way, though: a singleton resource, or
> one identified in the body or the query string rather than the path,
> deletes at the very same shape the POST that made it used. Both are the
> same call in the sense `url_shape` already exists to answer -- there is no
> reason in the design for one form to count and the other not -- so both
> are handed back and either is accepted.

## `reversal_for`, [line 30](../../../../../../../backend/src/sro/application/execution/reversal.py#L30): Comment

Code: `continue`

> `runnable` is the one place "may this skill actually be asked to
> run" is answered. Offering a version it would refuse teaches an
> operator that the button lies.

## `reversal_for`, [line 34](../../../../../../../backend/src/sro/application/execution/reversal.py#L34): Comment

Code: `continue`

> Either the delete needs nothing identifiable (so it is not
> addressing the one record this run made), or it needs
> something this run never read back. A button that cannot
> name what it would remove is worse than no button.

## `_what_it_made`, [line 56](../../../../../../../backend/src/sro/application/execution/reversal.py#L56): Comment

Code: `return None`

> Nothing written, or several things. A run that made two records is
> not one this can offer to unmake with a single press.
