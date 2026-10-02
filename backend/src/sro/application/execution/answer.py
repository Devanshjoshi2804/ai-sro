from __future__ import annotations

from dataclasses import dataclass, field, replace

from sro.application.induction.sites import parse_json, url_query_pairs

MOST_VALUES = 8

MAX_ROWS = 2000
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


@dataclass(frozen=True, slots=True)
class Answer:
    rows: int

    total: int | None = None

    partial: bool = False

    sample: tuple[dict[str, str], ...] = ()

    truncated: bool = False

    columns: tuple[str, ...] = ()

    distinct: dict[str, tuple[str, ...]] = field(default_factory=dict)

    labels: tuple[str, ...] = ()

    records: tuple[dict[str, str], ...] = ()
    """Every record read, whole -- `sample` is cut for display, and "is it in
    there" is not a question to ask of a cut."""

    narrowed_by: tuple[str, ...] = ()

    @property
    def counted(self) -> int | None:
        if self.total is not None:
            return self.total
        return None if self.partial else self.rows

    def sentence(self, subject: str) -> str:
        shown = ", ".join(_describe(row) for row in self.sample[:5])
        counted = self.counted

        if counted is None:
            return (
                f"At least {self.rows} {subject}, which is as many as one page holds: "
                f"{shown}. The system did not say how many there are altogether."
            )
        if counted == 0:
            return f"Nothing matched — no {subject} came back."
        if counted == 1 and self.sample:
            return f"One {subject}: {_describe(self.sample[0])}."

        more = counted - min(5, len(self.sample))
        tail = f", and {more} more" if more > 0 else ""
        return f"There are {counted} {subject}: {shown}{tail}."


def merge(answers: tuple[Answer, ...]) -> Answer | None:
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
        partial=False,
        sample=sample,
        truncated=any(answer.truncated for answer in real) or len(sample) >= MAX_ROWS,
        columns=first.columns,
        labels=labels,
        distinct=held,
        records=tuple(row for answer in real for row in answer.records)[:MAX_ROWS],
    )


def leading_with(answer: Answer, column: str) -> Answer:
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
        partial=_has_more(document) or (total is None and _is_a_page(len(records), url)),
        sample=sample,
        truncated=len(records) > MAX_ROWS,
        labels=tuple(_describe(row) for row in sample),
        columns=columns,
        distinct=held,
        records=tuple(_whole(record) for record in shown),
    )


_PAGING = ("next", "nextpage", "nextpagetoken", "nextcursor", "nexturl", "hasmore", "hasnext")


def _has_more(document: dict[str, object]) -> bool:
    """The server says there is another page, in any of the usual ways."""
    for key, value in document.items():
        if key == "data":
            continue
        if key.lower().replace("_", "") in _PAGING and value not in (False, None, "", 0):
            return True
        if isinstance(value, dict) and _has_more(value):
            return True
    return False


def _whole(record: dict[str, object]) -> dict[str, str]:
    return {key: str(value).strip() for key, value in record.items() if _sayable(value)}


def _total(document: dict[str, object], returned: int, url: str) -> int | None:
    asked = _numbers_we_sent(url)
    candidates = [
        int(value)
        for key, value in document.items()
        if key != "data" and isinstance(value, int) and not isinstance(value, bool)
        if value >= returned and value not in asked
    ]
    return candidates[0] if len(candidates) == 1 else None


def _numbers_we_sent(url: str) -> frozenset[int]:
    return frozenset(int(value) for _, value in url_query_pairs(url) if value.isdigit())


def _is_a_page(returned: int, url: str) -> bool:
    return returned > 0 and returned in _numbers_we_sent(url)


def _held(records: list[dict[str, object]]) -> dict[str, tuple[str, ...]]:
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
    seen: dict[str, int] = {}
    for record in records:
        for key, value in record.items():
            if _sayable(value) and not _is_a_link(value):
                seen[key] = seen.get(key, 0) + 1

    ranked = sorted(seen, key=lambda key: (_rank(key), len(key)))
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
    return isinstance(value, str) and value.startswith(("http://", "https://"))


def _row(record: dict[str, object], columns: tuple[str, ...]) -> dict[str, str]:
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
    return isinstance(value, str | int | float | bool) and str(value).strip() not in {"", "None"}


def _describe(row: dict[str, str]) -> str:
    values = list(row.values())
    if not values:
        return "(unnamed)"
    return values[0] if len(values) == 1 else f"{values[0]} ({values[1]})"
