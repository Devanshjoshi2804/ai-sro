# Notes for `backend/src/sro/application/lookup/naming.py`

Comments and docstrings moved out of [`backend/src/sro/application/lookup/naming.py`](../../../../../../../backend/src/sro/application/lookup/naming.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/lookup/naming.py#L1): Docstring

> Which records a question actually named.
>
> A lookup answers with a collection. The question was usually about ONE thing
> in it -- "is there a customer type called KKYT" is a yes and a record, not a
> hundred and ten of them -- and every surface was left to work that out from
> the words for itself.
>
> The panel tried, in JavaScript, twice. First by matching every word of the
> question against every value, which promoted the forty records whose
> description contains `type` ahead of the one called KKYT. Then by dropping the
> words that match too much of the result, which is the right rule and was still
> the wrong place: the console draws the same answers, a model reading one has
> the same problem, and a rule with a copy per surface drifts on all of them.
>
> So it is here, beside the reader -- which is in `application` for the reason
> that file's own docstring gives, and this followed it rather than being left
> in `domain` naming things out of a payload on its own. What it decides is
> narrow and says so: which records a question NAMED. Not what the answer is --
> that is the records -- and not whether the operator meant something else,
> which nothing can know.
>
> **Values, never field names.** `customer` and `type` are in every column name
> on this endpoint and in none of the records. Matching names would pick every
> record, which is the same as picking none.
>
> **And never a word that describes the whole result.** A word matching most of
> a collection is saying what the collection IS; a word matching a few is the
> one somebody typed to find them. Measured on the deployment 2026-09-21: over
> 110 customer types, `type` appears in forty descriptions and `kkyt` in one.

## module, [line 6](../../../../../../../backend/src/sro/application/lookup/naming.py#L6): Note on the line above

Code: `K_TELLING = 0.25`

> How much of a result a word may pick out and still be said to name
> something in it. Past a quarter it is describing the collection.

## module, [line 8](../../../../../../../backend/src/sro/application/lookup/naming.py#L8): Note on the line above

Code: `K_SHORT = 2`

> Words this long or shorter are skipped. `is`, `a`, `of` -- and a two-letter
> fragment matches inside half the values in a warehouse.

## module, [line 10](../../../../../../../backend/src/sro/application/lookup/naming.py#L10): Note on the line above

Code: `NOT_TELLING = frozenset(`

> Words that are never about the data. Deliberately small: the real work is
> done by how much of the result a word picks out, which needs no list and
> cannot go stale as a vocabulary grows.

## `asked_for`, [line 50](../../../../../../../backend/src/sro/application/lookup/naming.py#L50): Docstring

> The words of a question that could name a record.

## `names`, [line 55](../../../../../../../backend/src/sro/application/lookup/naming.py#L55): Docstring

> Whether any VALUE of this record carries any of those words.

## `telling`, [line 65](../../../../../../../backend/src/sro/application/lookup/naming.py#L65): Docstring

> The words that pick out a few of these records rather than most.

## `named`, [line 77](../../../../../../../backend/src/sro/application/lookup/naming.py#L77): Docstring

> The records this question named, or none where it named no particular one.
>
> Empty is the ordinary answer: "how many customer types are there" names
> nothing in the collection and wants all of it.
>
> `subject` is what the collection IS -- "customer type", from the address
> the records came from. Its words are not search terms, for the reason
> field names are not: they describe the set rather than choose within it.
> Without this, "is there a CUSTOMER type called KKYT" also returns the one
> record whose description reads `Customer Outbound Orders`, which nobody
> asked about and which pushes the answer to second place.
>
> A word cut here is cut whatever `telling` would have made of it: `customer`
> picks out one record of forty-three, which is few enough to look
> distinguishing and is not.
