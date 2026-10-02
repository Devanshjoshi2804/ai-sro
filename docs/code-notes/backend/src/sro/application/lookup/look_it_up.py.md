# Notes for `backend/src/sro/application/lookup/look_it_up.py`

Comments and docstrings moved out of [`backend/src/sro/application/lookup/look_it_up.py`](../../../../../../../backend/src/sro/application/lookup/look_it_up.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 13](../../../../../../../backend/src/sro/application/lookup/look_it_up.py#L13): Note on the line above

Code: `K_RAN_OUT = ("timeout", "timed out", "deadline")`

> What the channel says when nobody answered in time. The extension's own
> words, matched here rather than translated -- `unreachable` is a browser that
> said no and this is one that said nothing, and they want different sentences.

## `LookItUp.execute`, [line 31](../../../../../../../backend/src/sro/application/lookup/look_it_up.py#L31): Comment

Code: `if not planned.plan.ready:`

> Nothing here knows how to look it up, which is the case the
> proposal below is genuinely for: it says what the knowledge base
> has and offers to work the screen out once.

## `what_was_found`, [line 60](../../../../../../../backend/src/sro/application/lookup/look_it_up.py#L60): Docstring

> The sentence above the table, for a surface that draws no table.
>
> Deliberately thin. What the answer SAYS is in the records, and a sentence
> claiming to summarise them would be this system inventing a number: the
> table is the answer and this is its label.

## `what_was_found`, [line 64](../../../../../../../backend/src/sro/application/lookup/look_it_up.py#L64): Comment

Code: `if any(ran_out(one.detail) for one in found.looked):`

> Name the browser where the browser is what did not answer. "I could
> not read that. timeout" is a sentence about this system's plumbing;
> the person reading it can see their own browser and can do something
> about it.

## `what_was_found`, [line 67](../../../../../../../backend/src/sro/application/lookup/look_it_up.py#L67): Comment

Code: `said = [_said(one) for one in answered if one.read is not None and not one.lookup.find]`

> The reader's own sentence, where it read records. Where the lookup carries
> the value an existence question asked about (`find`), the verdict is
> `existence_across`'s, one per value over every lookup that could hold it,
> a failed one included: yes if any read holds an equal record, no only if
> every one was whole and lacked it, else "could not tell".
>
> `Answer.sentence` is deterministic -- counted and named from the payload,
> never summarised by a model, because "16" has to be 16 -- and it is the
> line somebody asking a question wanted instead of a table. "Read from
> /data/WM/wm/customerTypes" was this door describing its own plumbing.

