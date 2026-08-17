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

from dataclasses import dataclass

from sro.application.induction.sites import parse_json

MAX_ROWS = 25
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
    """How many records the system returned. The answer to "how many"."""

    sample: tuple[dict[str, str], ...]
    """Enough of the first records to recognise them."""

    truncated: bool

    columns: tuple[str, ...] = ()
    """The fields worth showing, in ranked order, decided once for the whole
    result. Carried because `jsonb` will not keep a row's key order and because
    a table needs to know its columns before it draws a header."""

    labels: tuple[str, ...] = ()
    """Each record as one line, in the order the fields were ranked.

    Carried separately because Postgres `jsonb` does not keep key order -- it
    sorts by key length -- so a row stored as an object comes back with the
    surrogate key first however carefully it was arranged. The ranking has to
    survive the round trip, so it is applied once, here, and kept as text."""

    def sentence(self, subject: str) -> str:
        """One line, for a person who asked a question rather than a table."""
        if self.rows == 0:
            return f"There are no {subject}."
        if self.rows == 1 and self.sample:
            return f"One {subject}: {_describe(self.sample[0])}."
        shown = ", ".join(_describe(row) for row in self.sample[:5])
        more = f", and {self.rows - min(5, len(self.sample))} more" if self.rows > 5 else ""
        return f"There are {self.rows} {subject}: {shown}{more}."


def read_answer(body: str | None) -> Answer | None:
    """The records in a response, or None when there are none to speak of."""
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
    return Answer(
        rows=len(records),
        sample=sample,
        truncated=len(records) > MAX_ROWS,
        labels=tuple(_describe(row) for row in sample),
        columns=columns,
    )


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
