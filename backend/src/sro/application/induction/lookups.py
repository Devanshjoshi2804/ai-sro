"""Turning a remembered id into a lookup somebody can actually answer.

The diff finds that both demonstrations sent one address id. Asking about it is
better than replaying it and worse than not needing to ask: the operator picked
that address off a screen, and the screen is in the recording.

So the record they picked is found in the listing that showed it, and the
fields beside the id are examined. A field is usable when the demonstration
proves three things about it: the listing carried it, the write sent the same
value, and no other record in that listing had that value. The last one is what
makes it a way of finding the record rather than a fact about it -- there are
forty addresses in Ontario and one called APPLIANCE HAUS.

Where no such field exists the id stays a question for a human, because a
lookup that cannot identify one record is a lookup that picks the wrong one.
"""

from __future__ import annotations

from dataclasses import dataclass

from sro.application.induction import jsonutil
from sro.application.induction.diff import Choice
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
class PlannedLookup:
    """A field that was a dropdown, and the call that filled it."""

    choice: Choice
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
    choices: tuple[Choice, ...],
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

    ``run_a``/``run_b`` are the paired steps, which is what a choice's index
    refers to. ``others`` is every other doing the candidate holds -- searched
    for the listing too, since the two aligned doings can hold nothing but the
    write. ``screens`` is the whole recording: the click that chose the record
    is usually one of the steps alignment dropped as exploration, and that
    click is the best evidence there is about how a person finds it.
    """
    runs = (run_a, run_b, *others)
    planned: list[PlannedLookup] = []
    for choice in choices:
        found = _plan_one(choice, runs, run_a, taken, screens or run_a, system, facility)
        if found is not None:
            planned.append(found)
    return tuple(planned)


def _plan_one(
    choice: Choice,
    runs: tuple[tuple[ActionFrame, ...], ...],
    run_a: tuple[ActionFrame, ...],
    taken: set[str],
    screens: tuple[ActionFrame, ...],
    system: str,
    facility: str,
) -> PlannedLookup | None:
    listing = _listing_of(runs, choice.value, choice.step_index)
    if listing is None:
        return None
    request, records = listing

    picked = next((r for r in records if choice.value in [str(v) for v in r.values()]), None)
    if picked is None:  # pragma: no cover - _listing_of found it in one of them
        return None

    take = next((key for key, value in picked.items() if str(value) == choice.value), None)
    if take is None:  # pragma: no cover - as above
        return None

    sent = _sent_by_the_write(run_a, choice)
    usable = [
        (key, str(value))
        for key, value in picked.items()
        if key != take
        and str(value).strip()
        and sent.get(key) == str(value)
        and _unique(records, key, str(value))
    ]
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
        choice=choice,
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


def _listing_of(
    runs: tuple[tuple[ActionFrame, ...], ...], value: str, step_index: int | None
) -> tuple[CapturedRequest, list[dict[str, object]]] | None:
    """The read that showed this value, and the records it returned.

    Searched across every doing the candidate holds, not only the two that
    aligned. The pair that aligns is chosen for being the same task twice, and
    that is a different question from which doing happened to have the dialog
    open -- in the evidence this was written against, the two aligned doings
    hold one call each and the address listing is in neither.

    ``step_index`` bounds the search in the aligned runs, where a step index
    means something. In the other doings it does not, so the bound is that
    doing's own first mutating request: the same rule -- before the write --
    said without reference to an alignment those frames were never part of.
    """
    for at, run in enumerate(runs):
        upto = step_index if at < 2 and step_index is not None else _first_mutation(run)
        for frame in run[:upto]:
            for request in frame.requests:
                if request.is_mutation or is_background_traffic(request.url):
                    continue
                records = _records(request)
                if any(value in [str(v) for v in record.values()] for record in records):
                    return request, records
    return None


def _first_mutation(run: tuple[ActionFrame, ...]) -> int:
    for index, frame in enumerate(run):
        if any(request.is_mutation for request in frame.requests):
            return index
    return len(run)


def _records(request: CapturedRequest) -> list[dict[str, object]]:
    document = parse_json(request.response_text)
    data = document.get("data") if isinstance(document, dict) else None
    return [record for record in data if isinstance(record, dict)] if isinstance(data, list) else []


def _sent_by_the_write(run: tuple[ActionFrame, ...], choice: Choice) -> dict[str, str]:
    """The write's own payload, flattened to field name and value.

    A field the write does not send is not part of how the operator identified
    the record -- it is something the screen happened to show them.
    """
    frame = run[choice.step_index]
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
