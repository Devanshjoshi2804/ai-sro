"""Which records a question actually named.

A lookup answers with a collection. The question was usually about ONE thing
in it -- "is there a customer type called KKYT" is a yes and a record, not a
hundred and ten of them -- and every surface was left to work that out from
the words for itself.

The panel tried, in JavaScript, twice. First by matching every word of the
question against every value, which promoted the forty records whose
description contains `type` ahead of the one called KKYT. Then by dropping the
words that match too much of the result, which is the right rule and was still
the wrong place: the console draws the same answers, a model reading one has
the same problem, and a rule with a copy per surface drifts on all of them.

So it is here, beside the reader. What it decides is narrow and says so: which
records a question NAMED. Not what the answer is -- that is the records -- and
not whether the operator meant something else, which nothing can know.

**Values, never field names.** `customer` and `type` are in every column name
on this endpoint and in none of the records. Matching names would pick every
record, which is the same as picking none.

**And never a word that describes the whole result.** A word matching most of
a collection is saying what the collection IS; a word matching a few is the
one somebody typed to find them. Measured on the deployment 2026-09-21: over
110 customer types, `type` appears in forty descriptions and `kkyt` in one.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence

K_TELLING = 0.25
"""How much of a result a word may pick out and still be said to name
something in it. Past a quarter it is describing the collection."""

K_SHORT = 2
"""Words this long or shorter are skipped. `is`, `a`, `of` -- and a two-letter
fragment matches inside half the values in a warehouse."""

NOT_TELLING = frozenset(
    {
        "the",
        "and",
        "for",
        "are",
        "was",
        "there",
        "that",
        "this",
        "with",
        "what",
        "which",
        "how",
        "many",
        "any",
        "does",
        "has",
        "have",
        "been",
        "called",
        "named",
        "show",
        "list",
        "get",
        "set",
        "all",
        "count",
        "from",
        "into",
        "exist",
        "exists",
        "please",
        "find",
        "look",
        "see",
    }
)
"""Words that are never about the data. Deliberately small: the real work is
done by how much of the result a word picks out, which needs no list and
cannot go stale as a vocabulary grows."""


def asked_for(question: str) -> tuple[str, ...]:
    """The words of a question that could name a record."""
    words = re.split(r"[^A-Za-z0-9]+", str(question or "").lower())
    return tuple(word for word in words if len(word) > K_SHORT and word not in NOT_TELLING)


def names(record: Mapping[str, object], words: Sequence[str]) -> bool:
    """Whether any VALUE of this record carries any of those words."""
    for value in record.values():
        if value is None or isinstance(value, dict | list):
            continue
        said = str(value).lower()
        if said and any(word in said for word in words):
            return True
    return False


def telling(words: Sequence[str], records: Sequence[Mapping[str, object]]) -> tuple[str, ...]:
    """The words that pick out a few of these records rather than most."""
    if not records:
        return tuple(words)
    most = max(1, int(len(records) * K_TELLING))
    kept = []
    for word in words:
        picks = sum(1 for record in records if names(record, (word,)))
        if 0 < picks <= most:
            kept.append(word)
    return tuple(kept)


def named(
    question: str, records: Sequence[Mapping[str, object]], subject: str = ""
) -> tuple[Mapping[str, object], ...]:
    """The records this question named, or none where it named no particular one.

    Empty is the ordinary answer: "how many customer types are there" names
    nothing in the collection and wants all of it.

    `subject` is what the collection IS -- "customer type", from the address
    the records came from. Its words are not search terms, for the reason
    field names are not: they describe the set rather than choose within it.
    Without this, "is there a CUSTOMER type called KKYT" also returns the one
    record whose description reads `Customer Outbound Orders`, which nobody
    asked about and which pushes the answer to second place.

    A word cut here is cut whatever `telling` would have made of it: `customer`
    picks out one record of forty-three, which is few enough to look
    distinguishing and is not.
    """
    of_the_set = set(asked_for(subject))
    words = telling(tuple(word for word in asked_for(question) if word not in of_the_set), records)
    if not words:
        return ()
    return tuple(record for record in records if names(record, words))


__all__ = ["K_SHORT", "K_TELLING", "NOT_TELLING", "asked_for", "named", "names", "telling"]
