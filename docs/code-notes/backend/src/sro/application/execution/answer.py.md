# Notes for `backend/src/sro/application/execution/answer.py`

Comments and docstrings moved out of [`backend/src/sro/application/execution/answer.py`](../../../../../../../backend/src/sro/application/execution/answer.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/execution/answer.py#L1): Docstring

> What a run actually found, in words the person who asked can read.
>
> A run that returns `GET …/warehouseTransportModes → 200` has answered nothing.
> Somebody asked how many transport modes there are; the number was in the
> response, the run threw it away, and the operator was sent to a page showing
> them a URL and a status code.
>
> So a read's answer is kept: how many records came back and enough of each to
> recognise it. Deterministic -- counted and named from the payload, never
> summarised by a model, because "16" has to be 16.
>
> Bounded on purpose. This is an answer, not a copy of the customer's database:
> a handful of rows, a handful of fields, short values. Anything longer is a
> report, and a report is a different request.

## module, [line 7](../../../../../../../backend/src/sro/application/execution/answer.py#L7): Note on the line above

Code: `MOST_VALUES = 8`

> How many of a column's values to remember. Enough to recognise a flag or a
> short code list, few enough that this stays an answer rather than an index.

## module, [line 9](../../../../../../../backend/src/sro/application/execution/answer.py#L9): Note on the line above

Code: `MAX_ROWS = 2000`

> How many records an answer carries back. Twenty-five was a sample and read
> as one: "238 found · 25 carried back" is a table an operator cannot use, for a
> question they asked in full. Bounded still -- an answer is not a copy of the
> customer's database -- but bounded where a person stops scrolling, not where a
> demonstration's first page happened to end.

## module, [line 13](../../../../../../../backend/src/sro/application/execution/answer.py#L13): Note on the line above

Code: `_IDENTIFYING = (`

> Field names that tell one record from another, best first.
>
> Description ahead of id, learned by showing an operator sixteen rows reading
> `AF*!SG` while the screen beside them said `Air Freight`. A composite surrogate
> key is how the system refers to a record; it is not how anybody else does.

## `Answer`, [line 27](../../../../../../../backend/src/sro/application/execution/answer.py#L27): Note on the line above

Code: `rows: int`

> How many records came back in this response. Not the answer to "how
> many" unless :attr:`counted` says the response accounted for all of them.

## `Answer`, [line 29](../../../../../../../backend/src/sro/application/execution/answer.py#L29): Note on the line above

Code: `total: int | None = None`

> How many exist, where the system said so.
>
> A collection endpoint answers with a page and, usually, with the size of
> the whole set beside it. Reading the page length as the answer is how "how
> many suppliers are there" came back as 50 -- which was the page size, and
> would have been 50 for a warehouse with five thousand.

## `Answer`, [line 31](../../../../../../../backend/src/sro/application/execution/answer.py#L31): Note on the line above

Code: `partial: bool = False`

> The response was a page and nothing in it said how large the set is.
>
> Then there is no count to give, and saying so is the only honest answer:
> the page length is a fact about the request, not about the warehouse.

## `Answer`, [line 33](../../../../../../../backend/src/sro/application/execution/answer.py#L33): Note on the line above

Code: `sample: tuple[dict[str, str], ...] = ()`

> Enough of the first records to recognise them.

## `Answer`, [line 37](../../../../../../../backend/src/sro/application/execution/answer.py#L37): Note on the line above

Code: `columns: tuple[str, ...] = ()`

> The fields worth showing, in ranked order, decided once for the whole
> result. Carried because `jsonb` will not keep a row's key order and because
> a table needs to know its columns before it draws a header.

## `Answer`, [line 39](../../../../../../../backend/src/sro/application/execution/answer.py#L39): Note on the line above

Code: `distinct: dict[str, tuple[str, ...]] = field(default_factory=dict)`

> A few values each column actually holds, including columns not shown.
>
> What a WMS stores is rarely the word somebody says: "parcel" is a flag
> spelled `Y`, and asking the system for `smallPackageFlag = parcel` returns
> nothing and reads as "there are none". These are the values to check a word
> against, and the options to offer when it matches none of them.

## `Answer`, [line 41](../../../../../../../backend/src/sro/application/execution/answer.py#L41): Note on the line above

Code: `labels: tuple[str, ...] = ()`

> Each record as one line, in the order the fields were ranked.
>
> Carried separately because Postgres `jsonb` does not keep key order -- it
> sorts by key length -- so a row stored as an object comes back with the
> surrogate key first however carefully it was arranged. The ranking has to
> survive the round trip, so it is applied once, here, and kept as text.

## `merge`, [line 72](../../../../../../../backend/src/sro/application/execution/answer.py#L72): Docstring

> Several pages of one read, as one answer.
>
> The count comes from the first page's envelope, because that is what the
> system said existed when the reading started; the records are everything
> that came back. A collection that grew while it was being read shows more
> records than its own total, which is true and worth seeing.

## `leading_with`, [line 97](../../../../../../../backend/src/sro/application/execution/answer.py#L97): Docstring

> The same answer, named by the field the question used.
>
> Asked for supplier TESTSUPPLIERSRO, the reply read "L4S 0A8 (APPLIANCE
> HAUS)" -- true, and not what anybody asked about. The ranking that picks a
> record's most identifying field cannot know which one the question named;
> the caller can, and does.

## `read_answer`, [line 110](../../../../../../../backend/src/sro/application/execution/answer.py#L110): Docstring

> The records in a response, or None when there are none to speak of.
>
> ``url`` is the request that produced it, and it is what makes counting
> honest: `limit=50` in the query and `50` in the envelope are the same fact
> about what we asked for, so a total that merely echoes our own paging is
> not a total.

## `_total`, [line 157](../../../../../../../backend/src/sro/application/execution/answer.py#L157): Docstring

> The size of the whole set, where the response states it.
>
> Recognised by what it must be rather than by what it is called, because
> every system names it something different -- `total`, `totalCount`,
> `recordCount`, `numFound`. It sits beside the records, it is a whole
> number, it cannot be smaller than the page it came with, and it is not one
> of the numbers we put in the request ourselves.

## `_numbers_we_sent`, [line 168](../../../../../../../backend/src/sro/application/execution/answer.py#L168): Docstring

> Whole numbers in the request's own query. `limit=50` coming back as `50`
> says nothing except that the server heard us.

## `_is_a_page`, [line 172](../../../../../../../backend/src/sro/application/execution/answer.py#L172): Docstring

> Whether this response is one page of something longer.
>
> True when the request asked for a page and got exactly that many records:
> a full page is the one case where the count of what came back tells you
> nothing about how much there is.

## `_held`, [line 176](../../../../../../../backend/src/sro/application/execution/answer.py#L176): Docstring

> The values of the columns that have only a few.
>
> A column with three values across two hundred records is a category --
> something worth filtering by, and something a person recognises. A column
> with a different value in every record is an identifier, and offering to
> filter by one of those is offering somebody a needle from their own
> haystack. So a column that runs past the cap is dropped rather than
> truncated: a truncated set looks exactly like a small one.

## `_columns`, [line 190](../../../../../../../backend/src/sro/application/execution/answer.py#L190): Docstring

> The fields worth showing, decided across the whole result rather than per row.
>
> A WMS record carries as much bookkeeping as content. The transport-mode
> payload has `dateLastModified`, `lastModifiedBy`, `palletBuildConsolidationBy`
> and `warehouseId` null in all twenty-three rows, and a `self_uri` repeating
> the address the request was made to: four empty columns and one useless one,
> which is how a table stops being read.
>
> So a column earns its place by having a value somewhere, and the ranking
> orders what survives.

## `_is_a_link`, [line 209](../../../../../../../backend/src/sro/application/execution/answer.py#L209): Docstring

> A self-referential URL is the address we already know, spelled out.

## `_row`, [line 213](../../../../../../../backend/src/sro/application/execution/answer.py#L213): Docstring

> One record, as the columns the whole result agreed on.

## `_sayable`, [line 229](../../../../../../../backend/src/sro/application/execution/answer.py#L229): Docstring

> Scalars only, and nothing empty. A nested object is structure, not an
> answer, and rendering it turns a sentence into a wall.

## `Answer.counted`, [line 48](../../../../../../../backend/src/sro/application/execution/answer.py#L48): Docstring

> How many there are, or None when nobody can say from this response.

## `Answer.sentence`, [line 53](../../../../../../../backend/src/sro/application/execution/answer.py#L53): Docstring

> One line, for a person who asked a question rather than a table.

## `Answer.sentence`, [line 58](../../../../../../../backend/src/sro/application/execution/answer.py#L58): Comment

Code: `return (`

> The honest shape of a page: what was seen, and that it was not
> all of it. An operator can act on "at least 50"; they cannot
> recover from being told 50 when there are five thousand.

## `Answer.sentence`, [line 63](../../../../../../../backend/src/sro/application/execution/answer.py#L63): Comment

Code: `return f"Nothing matched — no {subject} came back."`

> Not "there are no supplier": the entity is named in the singular
> everywhere else in this system, and a count of nothing is the one
> sentence where that reads as broken English.

## `merge`, [line 87](../../../../../../../backend/src/sro/application/execution/answer.py#L87): Comment

Code: `partial=False,`

> Read to the end, so nothing is missing however it started.

## `_total`, [line 165](../../../../../../../backend/src/sro/application/execution/answer.py#L165): Comment

Code: `return candidates[0] if len(candidates) == 1 else None`

> Two fields both qualifying is not a count anybody should act on: the
> difference between them is exactly the kind of quiet wrong answer this
> is here to prevent.

## `_columns`, [line 198](../../../../../../../backend/src/sro/application/execution/answer.py#L198): Comment

Code: `kept: list[str] = []`

> And no column twice under two names. `resourceId` and `transportMode`
> carry the same value in every row of this payload; showing both fills a
> third of the table with a repeat.
