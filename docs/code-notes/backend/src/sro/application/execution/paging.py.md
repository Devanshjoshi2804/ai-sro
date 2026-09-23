# Notes for `backend/src/sro/application/execution/paging.py`

Comments and docstrings moved out of [`backend/src/sro/application/execution/paging.py`](../../../../../../../backend/src/sro/application/execution/paging.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/execution/paging.py#L1): Docstring

> Fetching all of something, when the system hands it over a page at a time.
>
> "How many suppliers are there" is answerable from one page, because the
> envelope says how many exist. "Which ones are they" is not: the operator asked
> for the suppliers and got the first fifty, with the rest behind a page number
> nobody in a warehouse should have to know about.
>
> So a read that came back paged is followed to the end. The paging is the
> system's own -- the parameters the demonstration used are the parameters this
> walks, in the dialect that endpoint proved it speaks -- and it stops at a limit
> rather than trusting a `total` it was told, because a collection that grows
> while it is being read would otherwise never finish.

## module, [line 8](../../../../../../../backend/src/sro/application/execution/paging.py#L8): Note on the line above

Code: `MOST_PAGES = 40`

> A ceiling on politeness, not on correctness. Forty pages of fifty is two
> thousand records -- past that this is a report, not an answer, and hammering a
> warehouse's API to render a table nobody will scroll is not a service.

## `Paging`, [line 16](../../../../../../../backend/src/sro/application/execution/paging.py#L16): Docstring

> How this endpoint was seen to page, read off the request it made.

## `Paging`, [line 21](../../../../../../../backend/src/sro/application/execution/paging.py#L21): Note on the line above

Code: `first_page: int = 0`

> The page number the demonstrated call itself asked for.
>
> Counted from, rather than assumed to be zero. Against a one-based API the
> first "next" page was page one -- the page already in hand -- so every row
> on it was counted twice and the total was reported a page out.

## `how_it_pages`, [line 28](../../../../../../../backend/src/sro/application/execution/paging.py#L28): Docstring

> The paging parameters this call carried, if any.

## `next_page`, [line 45](../../../../../../../backend/src/sro/application/execution/paging.py#L45): Docstring

> The same call, asking for what comes after what has been read.
>
> ``None`` when this endpoint showed no way to ask -- and then one page is
> all there is to have, which the answer says rather than implies.
