"""What a run actually found, in words the person who asked can read.

A run that returns `GET …/warehouseTransportModes → 200` has answered nothing.
Somebody asked how many transport modes there are; the number was in the
response, the run threw it away, and the operator was sent to a page showing
them a URL and a status code.

So a read's answer is kept: how many records came back and enough of each to
recognise it. Deterministic -- counted and named from the payload, never
summarised by a model, because "16" has to be 16.

Bounded on purpose. This is an answer, not a copy of the customer's database:
a handful of rows, a handful of fields, short values. Anything longer is a
report, and a report is a different request.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace

from sro.application.induction.sites import parse_json, url_query_pairs

MOST_VALUES = 8
"""How many of a column's values to remember. Enough to recognise a flag or a
short code list, few enough that this stays an answer rather than an index."""

MAX_ROWS = 2000
"""How many records an answer carries back. Twenty-five was a sample and read
as one: "238 found · 25 carried back" is a table an operator cannot use, for a
question they asked in full. Bounded still -- an answer is not a copy of the
customer's database -- but bounded where a person stops scrolling, not where a
demonstration's first page happened to end."""
MAX_COLUMNS = 10
MAX_VALUE = 60

_IDENTIFYING = (
    "code",
    "name",
    "description",
    "id",
    "status",
    "type",
    "mode",
    "number",
)
"""Field names that tell one record from another, best first.

Description ahead of id, learned by showing an operator sixteen rows reading
`AF*!SG` while the screen beside them said `Air Freight`. A composite surrogate
key is how the system refers to a record; it is not how anybody else does."""


@dataclass(frozen=True, slots=True)
class Answer:
    rows: int
    """How many records came back in this response. Not the answer to "how
    many" unless :attr:`counted` says the response accounted for all of them."""

    total: int | None = None
    """How many exist, where the system said so.

    A collection endpoint answers with a page and, usually, with the size of
    the whole set beside it. Reading the page length as the answer is how "how
    many suppliers are there" came back as 50 -- which was the page size, and
    would have been 50 for a warehouse with five thousand.
    """

    partial: bool = False
    """The response was a page and nothing in it said how large the set is.

    Then there is no count to give, and saying so is the only honest answer:
    the page length is a fact about the request, not about the warehouse.
    """

    sample: tuple[dict[str, str], ...] = ()
    """Enough of the first records to recognise them."""

    truncated: bool = False

    columns: tuple[str, ...] = ()
    """The fields worth showing, in ranked order, decided once for the whole
    result. Carried because `jsonb` will not keep a row's key order and because
    a table needs to know its columns before it draws a header."""

    distinct: dict[str, tuple[str, ...]] = field(default_factory=dict)
    """A few values each column actually holds, including columns not shown.

    What a WMS stores is rarely the word somebody says: "parcel" is a flag
    spelled `Y`, and asking the system for `smallPackageFlag = parcel` returns
    nothing and reads as "there are none". These are the values to check a word
    against, and the options to offer when it matches none of them.
    """

    labels: tuple[str, ...] = ()
    """Each record as one line, in the order the fields were ranked.

    Carried separately because Postgres `jsonb` does not keep key order -- it
    sorts by key length -- so a row stored as an object comes back with the
    surrogate key first however carefully it was arranged. The ranking has to
    survive the round trip, so it is applied once, here, and kept as text."""

    @property
    def counted(self) -> int | None:
        """How many there are, or None when nobody can say from this response."""
        if self.total is not None:
            return self.total
        return None if self.partial else self.rows

    def sentence(self, subject: str) -> str:
        """One line, for a person who asked a question rather than a table."""
        shown = ", ".join(_describe(row) for row in self.sample[:5])
        counted = self.counted

        if counted is None:
            # The honest shape of a page: what was seen, and that it was not
            # all of it. An operator can act on "at least 50"; they cannot
            # recover from being told 50 when there are five thousand.
            return (
                f"At least {self.rows} {subject}, which is as many as one page holds: "
                f"{shown}. The system did not say how many there are altogether."
            )
        if counted == 0:
            # Not "there are no supplier": the entity is named in the singular
            # everywhere else in this system, and a count of nothing is the one
            # sentence where that reads as broken English.
            return f"Nothing matched — no {subject} came back."
        if counted == 1 and self.sample:
            return f"One {subject}: {_describe(self.sample[0])}."

        more = counted - min(5, len(self.sample))
        tail = f", and {more} more" if more > 0 else ""
        return f"There are {counted} {subject}: {shown}{tail}."


def merge(answers: tuple[Answer, ...]) -> Answer | None:
    """Several pages of one read, as one answer.

    The count comes from the first page's envelope, because that is what the
    system said existed when the reading started; the records are everything
    that came back. A collection that grew while it was being read shows more
    records than its own total, which is true and worth seeing.
    """
    real = [answer for answer in answers if answer is not None]
    if not real:
        return None
    first = real[0]
    held: dict[str, tuple[str, ...]] = {}
    for answer in real:
        for key, values in answer.distinct.items():
            merged = {*held.get(key, ()), *values}
            held[key] = tuple(sorted(merged)[:MOST_VALUES])
    sample = tuple(row for answer in real for row in answer.sample)[:MAX_ROWS]
    labels = tuple(label for answer in real for label in answer.labels)[:MAX_ROWS]
    return Answer(
        rows=sum(answer.rows for answer in real),
        total=first.total,
        # Read to the end, so nothing is missing however it started.
        partial=False,
        sample=sample,
        truncated=any(answer.truncated for answer in real) or len(sample) >= MAX_ROWS,
        columns=first.columns,
        labels=labels,
        distinct=held,
    )


def leading_with(answer: Answer, column: str) -> Answer:
    """The same answer, named by the field the question used.

    Asked for supplier TESTSUPPLIERSRO, the reply read "L4S 0A8 (APPLIANCE
    HAUS)" -- true, and not what anybody asked about. The ranking that picks a
    record's most identifying field cannot know which one the question named;
    the caller can, and does.
    """
    if column not in answer.columns:
        return answer
    columns = (column, *(other for other in answer.columns if other != column))
    sample = tuple({key: row[key] for key in columns if key in row} for row in answer.sample)
    return replace(
        answer,
        columns=columns,
        sample=sample,
        labels=tuple(_describe(row) for row in sample),
    )


def read_answer(body: str | None, *, url: str = "") -> Answer | None:
    """The records in a response, or None when there are none to speak of.

    ``url`` is the request that produced it, and it is what makes counting
    honest: `limit=50` in the query and `50` in the envelope are the same fact
    about what we asked for, so a total that merely echoes our own paging is
    not a total.
    """
    document = parse_json(body) if body else None
    if not isinstance(document, dict):
        return None

    data = document.get("data")
    records = data if isinstance(data, list) else [data] if isinstance(data, dict) else None
    if records is None:
        return None

    shown = [record for record in records[:MAX_ROWS] if isinstance(record, dict)]
    columns = _columns(shown)
    sample = tuple(_row(record, columns) for record in shown)
    held = _held(shown)
    total = _total(document, len(records), url)
    return Answer(
        rows=len(records),
        total=total,
        partial=total is None and _is_a_page(len(records), url),
        sample=sample,
        truncated=len(records) > MAX_ROWS,
        labels=tuple(_describe(row) for row in sample),
        columns=columns,
        distinct=held,
    )


def _total(document: dict[str, object], returned: int, url: str) -> int | None:
    """The size of the whole set, where the response states it.

    Recognised by what it must be rather than by what it is called, because
    every system names it something different -- `total`, `totalCount`,
    `recordCount`, `numFound`. It sits beside the records, it is a whole
    number, it cannot be smaller than the page it came with, and it is not one
    of the numbers we put in the request ourselves.
    """
    asked = _numbers_we_sent(url)
    candidates = [
        int(value)
        for key, value in document.items()
        if key != "data" and isinstance(value, int) and not isinstance(value, bool)
        if value >= returned and value not in asked
    ]
    # Two fields both qualifying is not a count anybody should act on: the
    # difference between them is exactly the kind of quiet wrong answer this
    # is here to prevent.
    return candidates[0] if len(candidates) == 1 else None


def _numbers_we_sent(url: str) -> frozenset[int]:
    """Whole numbers in the request's own query. `limit=50` coming back as `50`
    says nothing except that the server heard us."""
    return frozenset(int(value) for _, value in url_query_pairs(url) if value.isdigit())


def _is_a_page(returned: int, url: str) -> bool:
    """Whether this response is one page of something longer.

    True when the request asked for a page and got exactly that many records:
    a full page is the one case where the count of what came back tells you
    nothing about how much there is.
    """
    return returned > 0 and returned in _numbers_we_sent(url)


def _held(records: list[dict[str, object]]) -> dict[str, tuple[str, ...]]:
    """The values of the columns that have only a few.

    A column with three values across two hundred records is a category --
    something worth filtering by, and something a person recognises. A column
    with a different value in every record is an identifier, and offering to
    filter by one of those is offering somebody a needle from their own
    haystack. So a column that runs past the cap is dropped rather than
    truncated: a truncated set looks exactly like a small one.
    """
    seen: dict[str, set[str]] = {}
    for record in records[:200]:
        for key, value in record.items():
            if not _sayable(value):
                continue
            seen.setdefault(key, set()).add(str(value)[:MAX_VALUE])
    return {
        key: tuple(sorted(values))
        for key, values in seen.items()
        if values and len(values) <= MOST_VALUES
    }


def _columns(records: list[dict[str, object]]) -> tuple[str, ...]:
    """The fields worth showing, decided across the whole result rather than per row.

    A WMS record carries as much bookkeeping as content. The transport-mode
    payload has `dateLastModified`, `lastModifiedBy`, `palletBuildConsolidationBy`
    and `warehouseId` null in all twenty-three rows, and a `self_uri` repeating
    the address the request was made to: four empty columns and one useless one,
    which is how a table stops being read.

    So a column earns its place by having a value somewhere, and the ranking
    orders what survives.
    """
    seen: dict[str, int] = {}
    for record in records:
        for key, value in record.items():
            if _sayable(value) and not _is_a_link(value):
                seen[key] = seen.get(key, 0) + 1

    ranked = sorted(seen, key=lambda key: (_rank(key), len(key)))
    # And no column twice under two names. `resourceId` and `transportMode`
    # carry the same value in every row of this payload; showing both fills a
    # third of the table with a repeat.
    kept: list[str] = []
    printed: list[tuple[str, ...]] = []
    for column in ranked:
        values = tuple(str(record.get(column, "")) for record in records)
        if values in printed:
            continue
        printed.append(values)
        kept.append(column)
    return tuple(kept[:MAX_COLUMNS])


def _is_a_link(value: object) -> bool:
    """A self-referential URL is the address we already know, spelled out."""
    return isinstance(value, str) and value.startswith(("http://", "https://"))


def _row(record: dict[str, object], columns: tuple[str, ...]) -> dict[str, str]:
    """One record, as the columns the whole result agreed on."""
    return {
        column: str(record[column])[:MAX_VALUE]
        for column in columns
        if column in record and _sayable(record[column])
    }


def _rank(key: str) -> int:
    lowered = key.lower()
    for position, hint in enumerate(_IDENTIFYING):
        if hint in lowered:
            return position
    return len(_IDENTIFYING)


def _sayable(value: object) -> bool:
    """Scalars only, and nothing empty. A nested object is structure, not an
    answer, and rendering it turns a sentence into a wall."""
    return isinstance(value, str | int | float | bool) and str(value).strip() not in {"", "None"}


def _describe(row: dict[str, str]) -> str:
    values = list(row.values())
    if not values:
        return "(unnamed)"
    return values[0] if len(values) == 1 else f"{values[0]} ({values[1]})"
