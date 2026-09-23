from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from urllib.parse import urlsplit

from sro.application.induction import jsonutil
from sro.application.induction.headers import build_header_plans
from sro.application.induction.sites import (
    JsonBodySite,
    filter_terms_of,
    parse_json,
    without_clocks,
)
from sro.domain.recording.background import is_background_traffic
from sro.domain.recording.events import ActionFrame
from sro.domain.recording.network import CapturedRequest
from sro.domain.skill.lookup import Options

MOST_FIELDS = 3


@dataclass(frozen=True, slots=True)
class Wanted:
    field: str
    values: tuple[str, ...]

    step_index: int


@dataclass(frozen=True, slots=True)
class PlannedLookup:
    field: str
    request: CapturedRequest

    options: Options
    shown: str


def filtered_on(request: CapturedRequest) -> str | None:
    columns = {term["column"] for term in filter_terms_of(request.url) if term.get("column")}
    return columns.pop() if len(columns) == 1 else None


def plan(
    wanted: tuple[Wanted, ...],
    run_a: tuple[ActionFrame, ...],
    run_b: tuple[ActionFrame, ...],
    *,
    screens: tuple[ActionFrame, ...] = (),
    others: tuple[tuple[ActionFrame, ...], ...] = (),
    system: str = "",
    facility: str = "",
) -> tuple[PlannedLookup, ...]:
    runs = (run_a, run_b, *others)
    planned: list[PlannedLookup] = []
    for one in wanted:
        found = _plan_one(one, runs, run_a, screens or run_a, system, facility)
        if found is not None:
            planned.append(found)
    return tuple(planned)


def _plan_one(
    wanted: Wanted,
    runs: tuple[tuple[ActionFrame, ...], ...],
    run_a: tuple[ActionFrame, ...],
    screens: tuple[ActionFrame, ...],
    system: str,
    facility: str,
) -> PlannedLookup | None:
    reads = [_listing_of(runs, value, wanted.step_index) for value in wanted.values]
    found = [read for read in reads if read is not None]
    if len(found) != len(reads) or not found:
        return None
    if not all(_same_collection(read.url, found[0][0].url) for read, _ in found):
        return None

    value = wanted.values[0]
    request, records = found[0]

    row = _picked(records, value)
    if row is None:  # pragma: no cover - _listing_of found it in one of them
        return None
    picked, take = row

    listing_url = request.url
    widest = max(
        (
            found
            for run in runs
            for other, found in _reads_in(run)
            if _same_collection(other.url, listing_url) and _holds(found, (value,))
        ),
        key=len,
        default=records,
    )

    sent = _sent_by_the_write(run_a, wanted.step_index)
    usable = [
        (key, str(held))
        for key, held in picked.items()
        if key != take
        and str(held).strip()
        and sent.get(key) == str(held)
        and _unique(widest, key, str(held))
    ]

    column = _searched_column(runs, wanted.values, wanted.step_index, listing_url)
    proven: list[tuple[str, str]] = []
    if column is not None and str(picked.get(column, "")).strip() and column != take:
        proven = [(column, str(picked[column]))]
        usable = [p for p in usable if p[0] != column]

    if not proven and not usable:
        return None

    on_screen = [pair for pair in usable if _seen_on_screen(screens, pair[1])]
    usable = proven + on_screen + [pair for pair in usable if pair not in on_screen]

    label = tuple(key for key, _ in usable[:MOST_FIELDS])
    return PlannedLookup(
        field=wanted.field,
        request=request,
        options=Options(
            url=without_clocks(request.url),
            label=label,
            value=take,
            search=_search_column(proven, listing_url, label),
            headers=build_header_plans(request, target_system=system, facility=facility),
        ),
        shown=" — ".join(value for _, value in usable[:MOST_FIELDS]),
    )


def _search_column(
    proven: list[tuple[str, str]], listing_url: str, label: tuple[str, ...]
) -> str | None:
    if proven:
        return proven[0][0]
    return label[0] if not filter_terms_of(listing_url) else None


def _seen_on_screen(run: tuple[ActionFrame, ...], value: str) -> bool:
    wanted = _flat(value)
    if not wanted:
        return False
    for frame in run:
        target = frame.action.target
        shown = (
            frame.action.value or "",
            (target.accessible_name or "") if target else "",
            (target.text or "") if target else "",
        )
        if any(_flat(text) == wanted for text in shown):
            return True
    return False


def _flat(text: str) -> str:
    return " ".join(text.split()).casefold()


def _reads_in(
    frames: tuple[ActionFrame, ...],
) -> Iterator[tuple[CapturedRequest, list[dict[str, object]]]]:
    for frame in frames:
        for request in frame.requests:
            if not request.is_mutation:
                yield request, _records(request)


def _reads(
    runs: tuple[tuple[ActionFrame, ...], ...], step_index: int | None
) -> Iterator[tuple[CapturedRequest, list[dict[str, object]]]]:
    for at, run in enumerate(runs):
        upto = step_index if at < 2 and step_index is not None else _first_mutation(run)
        for request, records in _reads_in(run[:upto]):
            if not is_background_traffic(request.url):
                yield request, records


def _holds(records: list[dict[str, object]], values: tuple[str, ...]) -> bool:
    return any(value in [str(v) for v in record.values()] for record in records for value in values)


def _listing_of(
    runs: tuple[tuple[ActionFrame, ...], ...], value: str, step_index: int | None
) -> tuple[CapturedRequest, list[dict[str, object]]] | None:
    found = [pair for pair in _reads(runs, step_index) if _holds(pair[1], (value,))]
    if not found:
        return None
    first = found[0]
    return next(
        (
            pair
            for pair in found
            if _same_collection(pair[0].url, first[0].url)
            and _identifying_column(pair[0], pair[1], value) is not None
        ),
        first,
    )


def _picked(records: list[dict[str, object]], value: str) -> tuple[dict[str, object], str] | None:
    for record in records:
        take = next((key for key, held in record.items() if str(held) == value), None)
        if take is not None:
            return record, take
    return None


def _identifying_column(
    request: CapturedRequest, records: list[dict[str, object]], value: str
) -> str | None:
    column = filtered_on(request)
    row = _picked(records, value)
    if column is None or row is None:
        return None
    record, take = row
    return column if column != take and str(record.get(column, "")).strip() else None


def _searched_column(
    runs: tuple[tuple[ActionFrame, ...], ...],
    values: tuple[str, ...],
    step_index: int | None,
    collection: str,
) -> str | None:
    named = {
        column
        for request, records in _reads(runs, step_index)
        if _same_collection(request.url, collection)
        and _holds(records, values)
        and (column := filtered_on(request)) is not None
    }
    return named.pop() if len(named) == 1 else None


def _same_collection(url: str, other: str) -> bool:
    return urlsplit(url).path == urlsplit(other).path


def _first_mutation(run: tuple[ActionFrame, ...]) -> int:
    for index, frame in enumerate(run):
        if any(request.is_mutation for request in frame.requests):
            return index
    return len(run)


def _records(request: CapturedRequest) -> list[dict[str, object]]:
    document = parse_json(request.response_text)
    data = document.get("data") if isinstance(document, dict) else None
    return [record for record in data if isinstance(record, dict)] if isinstance(data, list) else []


def _sent_by_the_write(run: tuple[ActionFrame, ...], step_index: int) -> dict[str, str]:
    frame = run[step_index]
    sent: dict[str, str] = {}
    for request in frame.requests:
        if not request.is_mutation:
            continue
        document = parse_json(request.request_text)
        if document is None:
            continue
        for pointer, leaf in jsonutil.leaves(document):
            sent[JsonBodySite(pointer).pointer.rsplit("/", 1)[-1]] = str(leaf)
    return sent


def _unique(records: list[dict[str, object]], key: str, value: str) -> bool:
    return sum(1 for record in records if str(record.get(key, "")) == value) == 1
