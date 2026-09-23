# Notes for `backend/src/sro/application/execution/choices.py`

Comments and docstrings moved out of [`backend/src/sro/application/execution/choices.py`](../../../../../../../backend/src/sro/application/execution/choices.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/execution/choices.py#L1): Docstring

> What a field's dropdown holds, asked of the system now.
>
> The console draws a form for a task somebody asked for, and the fields that
> were dropdowns when it was taught are dropdowns here: this fetches their
> contents from the same endpoint the screen used, with the same session, and
> turns the records into something a person can pick from.
>
> Live, never cached from the demonstration. The addresses in this warehouse
> changed the afternoon after it was taught, and a list of what used to exist is
> a way of writing to a record that no longer does.

## module, [line 25](../../../../../../../backend/src/sro/application/execution/choices.py#L25): Note on the line above

Code: `MOST_ROWS = 50`

> Enough to choose from, few enough to render. A dropdown is not a report.

## `_fetch_plan`, [line 91](../../../../../../../backend/src/sro/application/execution/choices.py#L91): Docstring

> The listing call, with the headers the demonstration sent it.
>
> Kept on the options rather than found among the steps: the call that fills
> a dropdown is not one of the task's own steps, and looking for it there
> returned a plan with no session at all -- which fetched a login page and
> rendered as an empty list, the most misleading thing a dropdown can do.

## `_searched`, [line 95](../../../../../../../backend/src/sro/application/execution/choices.py#L95): Docstring

> The listing, asked for what somebody is typing into the field.
>
> The filter is the one the demonstration proved, with its own column swapped
> for the field being searched. The typed value goes in as it was typed:
> `as_a_filter` builds the term with `json.dumps` and the query string with
> `urlencode`, so both the JSON it sits inside and the URL it rides on are
> already its business.
>
> Escaping here as well was the double-encoding this file warns about, in the
> other dimension. Typing a quote into a dropdown searched for the backslash
> in front of it -- `ATTN "ALI"` went out as `ATTN "ALI"` -- so the field
> that most needed the search silently found nothing.

## `_showing`, [line 102](../../../../../../../backend/src/sro/application/execution/choices.py#L102): Docstring

> The demonstration's page size was the operator's window, not ours.
