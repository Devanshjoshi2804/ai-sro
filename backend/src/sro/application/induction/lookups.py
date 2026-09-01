"""Turning a remembered id into a lookup somebody can actually answer.

The diff finds that both demonstrations sent one address id. Asking about it is
better than replaying it and worse than not needing to ask: the operator picked
that address off a screen, and the screen is in the recording.

So the record they picked is found in the listing that showed it, and the
fields beside the id are examined. Two things can make a field usable, and
either is enough.

The first is that the write sent it: the listing carried the field, the write
sent the same value, and no other record in the collection had that value. The
last one is what makes it a way of finding the record rather than a fact about
it -- there are forty addresses in Ontario and one called APPLIANCE HAUS.

The second is that the operator searched by it. A read filtered on
`addressName` is the demonstration saying, in the application's own words, how
a human finds this record here. That evidence beats uniqueness, and it is the
only evidence there is for a value that was picked rather than typed: the
create sends `codAddressId` and nothing else off that record, so the write-sent
rule can never be satisfied for it. Where both apply the searched column leads,
because it is the one a person was seen using.

Where no such field exists the id stays a question for a human, because a
lookup that cannot identify one record is a lookup that picks the wrong one.
"""

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
"""How many of the record's fields to show in the list.

Not one. Four addresses in this warehouse share the line the operator picked
by, and a dropdown of four identical rows is a coin toss -- the name and the
street beside it are what tell them apart.
"""


@dataclass(frozen=True, slots=True)
class Wanted:
    """A value the skill will ask for, and the step that sent it.

    A constant the operator chose twice and a value that differed between
    doings arrive here as the same thing, because they are the same thing: an
    id nobody memorised, picked off a screen the recording still holds. Whether
    the skill will vary it is a question about the parameter, not about where
    its value comes from.
    """

    field: str
    values: tuple[str, ...]
    """What was picked. One value for a constant; one per run for a value that
    varied, every one of which must be explainable or this is not one list."""

    step_index: int


@dataclass(frozen=True, slots=True)
class PlannedLookup:
    """A field that was a dropdown, and the call that filled it."""

    field: str
    request: CapturedRequest
    """The listing the operator picked from, as the demonstration fetched it."""

    options: Options
    shown: str
    """What the picked record looked like on the screen, for the reviewer."""


def filtered_on(request: CapturedRequest) -> str | None:
    """The column this read was filtered on, where exactly one was.

    The operator typed a name into a dialog and the application turned it into
    `query=[{"column":"addressName","operator":"EQ","value":"test"}]`. That URL
    is the only place in the evidence that says how a human finds this record
    in this system -- better than any field that merely happens to be unique,
    because a person was seen using it.

    ``None`` for two columns as well as none: two answers about how a record is
    found is not evidence, and the rule is that disagreement refuses.
    """
    columns = {term["column"] for term in filter_terms_of(request.url) if term.get("column")}
    return columns.pop() if len(columns) == 1 else None


def plan(
    wanted: tuple[Wanted, ...],
    run_a: tuple[ActionFrame, ...],
    run_b: tuple[ActionFrame, ...],
    taken: set[str],
    *,
    screens: tuple[ActionFrame, ...] = (),
    others: tuple[tuple[ActionFrame, ...], ...] = (),
    system: str = "",
    facility: str = "",
) -> tuple[PlannedLookup, ...]:
    """A lookup for every chosen id the demonstration can explain.

    ``run_a``/``run_b`` are the paired steps, which is what a wanted value's
    index refers to. ``others`` is every other doing the candidate holds --
    searched for the listing too, since the two aligned doings can hold nothing
    but the write. ``screens`` is the whole recording: the click that chose the
    record is usually one of the steps alignment dropped as exploration, and
    that click is the best evidence there is about how a person finds it.
    """
    runs = (run_a, run_b, *others)
    planned: list[PlannedLookup] = []
    for one in wanted:
        found = _plan_one(one, runs, run_a, taken, screens or run_a, system, facility)
        if found is not None:
            planned.append(found)
    return tuple(planned)


def _plan_one(
    wanted: Wanted,
    runs: tuple[tuple[ActionFrame, ...], ...],
    run_a: tuple[ActionFrame, ...],
    taken: set[str],
    screens: tuple[ActionFrame, ...],
    system: str,
    facility: str,
) -> PlannedLookup | None:
    value = wanted.values[0]
    listing = _listing_of(runs, value, wanted.step_index)
    if listing is None:
        return None
    request, records = listing

    picked = next((r for r in records if value in [str(v) for v in r.values()]), None)
    if picked is None:  # pragma: no cover - _listing_of found it in one of them
        return None

    take = next((key for key, held in picked.items() if str(held) == value), None)
    if take is None:  # pragma: no cover - as above
        return None

    # A filtered read returns one row, and every field on one row is trivially
    # the only one of its kind. What tells records apart is what the collection
    # looks like unfiltered, so uniqueness is judged against the widest read of
    # it any doing made -- but only among the reads that hold the record itself.
    # Page two of a listing is wider and does not contain the picked row, so
    # judging against it makes every field on that row unique nowhere and
    # rejects the lot. Where there is no wider read the narrow result stands:
    # the operator picks from the dropdown, so an ambiguous label costs a second
    # look, not a wrong write.
    #
    # Every read counts here, including ones after a write. How many addresses
    # are in BURLINGTON is a fact about the collection, not about what the
    # operator did in what order, and the grid refreshing after the save is a
    # perfectly good witness to it. Bounding this the way the evidence questions
    # are bounded hides the duplicates and calls a shared value unique -- which
    # is the exact mistake judging against the widest read exists to prevent.
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
    if column is not None and str(picked.get(column, "")).strip() and column != take:
        # An operator's own search names the column. It goes first and it goes
        # in whether or not the write sends it: the write sends the id and
        # nothing else off this record, so requiring the write to send the
        # identifying field is requiring the impossible for every value that
        # was picked rather than typed.
        usable = [(column, str(picked[column]))] + [p for p in usable if p[0] != column]

    if not usable:
        # Nothing on that screen tells one record from another in words. The id
        # stays a question rather than becoming a lookup that guesses.
        return None

    # What the operator actually clicked, where the recording shows it. They
    # chose that address by reading "UNIT 7 BUILDING A" off a dropdown, and a
    # field a human was seen using beats one that merely happens to be unique.
    on_screen = [pair for pair in usable if _seen_on_screen(screens, pair[1])]
    usable = on_screen + [pair for pair in usable if pair not in on_screen]

    label = tuple(key for key, _ in usable[:MOST_FIELDS])
    return PlannedLookup(
        field=wanted.field,
        request=request,
        options=Options(
            url=without_clocks(request.url),
            label=label,
            value=take,
            search=label[0],
            headers=build_header_plans(request, target_system=system, facility=facility),
        ),
        shown=" — ".join(value for _, value in usable[:MOST_FIELDS]),
    )


def _seen_on_screen(run: tuple[ActionFrame, ...], value: str) -> bool:
    """Whether the demonstration shows a human handling this value.

    Typed into a field, or the text of a control they clicked. Compared with
    whitespace flattened, because a dropdown renders `UNIT  7  BUILDING A` as
    `UNIT 7 BUILDING A` and those are the same address.
    """
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
    """Every read these frames made, with the records it returned.

    No bound and no judgement: this is what the application answered, which is
    all a question about the data itself needs.
    """
    for frame in frames:
        for request in frame.requests:
            if not request.is_mutation:
                yield request, _records(request)


def _reads(
    runs: tuple[tuple[ActionFrame, ...], ...], step_index: int | None
) -> Iterator[tuple[CapturedRequest, list[dict[str, object]]]]:
    """The reads that are evidence of what the operator did, with their records.

    One definition, because two rules used to have two: which read showed the
    record and which column a person searched by are the same question --
    what did they do, and in what order, before the write -- and answering it
    from different halves of the evidence is how they drift apart. How wide the
    collection is is *not* that question, and is deliberately not asked here.

    A read is evidence when it did not change anything, was not the browser
    talking to itself on a timer, and happened before the write. ``step_index``
    bounds the aligned runs, where a step index means something. In the other
    doings it does not, so the bound is that doing's own first mutating request:
    the same rule -- before the write -- said without reference to an alignment
    those frames were never part of.
    """
    for at, run in enumerate(runs):
        upto = step_index if at < 2 and step_index is not None else _first_mutation(run)
        for request, records in _reads_in(run[:upto]):
            if not is_background_traffic(request.url):
                yield request, records


def _holds(records: list[dict[str, object]], values: tuple[str, ...]) -> bool:
    """Whether this read returned a record the operator picked."""
    return any(value in [str(v) for v in record.values()] for record in records for value in values)


def _listing_of(
    runs: tuple[tuple[ActionFrame, ...], ...], value: str, step_index: int | None
) -> tuple[CapturedRequest, list[dict[str, object]]] | None:
    """The read that showed this value, and the records it returned.

    Searched across every doing the candidate holds, not only the two that
    aligned. The pair that aligns is chosen for being the same task twice, and
    that is a different question from which doing happened to have the dialog
    open -- in the evidence this was written against, the two aligned doings
    hold one call each and the address listing is in neither.
    """
    for request, records in _reads(runs, step_index):
        if _holds(records, (value,)):
            return request, records
    return None


def _searched_column(
    runs: tuple[tuple[ActionFrame, ...], ...],
    values: tuple[str, ...],
    step_index: int | None,
    collection: str,
) -> str | None:
    """The column the doings searched these records by, where they agree.

    Every doing that filtered at all is asked. A doing that scrolled instead is
    silent rather than dissenting -- it has no opinion about how the record is
    found, and silence is not disagreement. Two doings naming different columns
    is disagreement, and plans nothing.

    Only reads of the collection the record came from get a vote. A carriers
    listing filtered on `name` happens to carry `codAddressId`, and letting it
    speak would re-aim the ADDRESS query at a column only the CARRIERS endpoint
    was ever shown to accept.

    Asked about every value, not only the first: two doings that picked
    different records only ever disagree through the reads that found them, and
    a doing's read holds its own doing's record, never the other's.
    """
    named = {
        column
        for request, records in _reads(runs, step_index)
        if _same_collection(request.url, collection)
        and _holds(records, values)
        and (column := filtered_on(request)) is not None
    }
    return named.pop() if len(named) == 1 else None


def _same_collection(url: str, other: str) -> bool:
    """Two reads of the same thing. The path is the collection; the query is
    which slice of it somebody happened to ask for."""
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
    """The write's own payload, flattened to field name and value.

    A field the write does not send is not part of how the operator identified
    the record -- it is something the screen happened to show them.
    """
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
