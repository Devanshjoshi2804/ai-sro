"""A day of watching, cut into pieces of work.

Nobody says when a task starts. What is available is when things happened, so a
piece of work is a run of activity on one host with no long pause in it -- and a
long pause is a person doing something else, which is exactly the boundary
wanted.

Pure, and deliberately crude. Every number here should move once there is a
week of real observation to move it against; none of them is a judgement the
system makes about a person.
"""

from __future__ import annotations

import json
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from urllib.parse import urlsplit

from sro.application.capture.decode import epoch_to_datetime
from sro.application.induction.diff import url_shape
from sro.domain.observation.candidate import Episode
from sro.domain.recording.background import is_background_traffic
from sro.domain.shared.identifiers import BatchId

IDLE = timedelta(minutes=3)
"""A pause longer than this ends the piece of work. Somebody who came back to
the same screen after lunch is doing it again, not still doing it."""

LONGEST = timedelta(minutes=30)
"""And a piece of work is bounded even without a pause, because a screen left
open all afternoon is not a task."""

_CALLS = ("xhr", "fetch", "")
"""What counts as the application talking. A stylesheet is not a step."""


@dataclass(frozen=True, slots=True)
class Observed:
    """One thing an extension saw, flattened to what segmentation needs."""

    at: datetime
    kind: str
    host: str
    batch_id: BatchId
    method: str = ""
    url: str = ""
    mutating: bool = False

    @property
    def is_call(self) -> bool:
        return self.kind == "request"

    @property
    def is_gesture(self) -> bool:
        return self.kind == "gesture"


@dataclass(frozen=True, slots=True)
class Segment:
    episode: Episode
    signature: str
    """What makes two of these the same task: the calls it made, in order, with
    their identifiers taken out. The same question induction asks when it
    aligns two demonstrations, asked with the same function -- a second opinion
    here would cluster things induction then refuses to align."""


def read(payload: bytes, batch_id: BatchId) -> tuple[Observed, ...]:
    """One uploaded batch, flattened. Malformed events are skipped rather than
    raising: this reads evidence that was accepted weeks ago by a version of an
    extension nobody can go back and fix."""
    return tuple(_flatten(payload, batch_id))


def segment(observed: Sequence[Observed]) -> tuple[Segment, ...]:
    """Pieces of work, in the order they happened.

    Each host on its own stream. A run used to end whenever the next event came
    from a different host, which reads a tab the operator is not working in as a
    boundary in the work they are: in a day of real recording, 30 of 37 run
    boundaries were that and nothing else. A mail client polling in the
    background would cut every task in the warehouse system in half.

    Episodes were already single-host -- the old rule guaranteed it by ending
    the run -- so this changes no episode's identity. What it changes is that a
    run now ends only for the reasons that are about the work: a pause, or a
    length no piece of work has.
    """
    by_host: dict[str, list[Observed]] = {}
    for one in observed:
        by_host.setdefault(one.host, []).append(one)
    pieces = [
        found
        for stream in by_host.values()
        for run in _runs(sorted(stream, key=lambda one: one.at))
        for block in _repetitions(run)
        for piece in _one_change_each(block)
        if (found := _segment(piece)) is not None
    ]
    return tuple(sorted(pieces, key=lambda piece: piece.episode.started_at))


def _one_change_each(run: Sequence[Observed]) -> Iterator[Sequence[Observed]]:
    """A run split so that no piece holds two changes.

    An operator working for eight minutes without a three-minute pause is one
    run today, however many separate things they did in it -- and a piece of
    work that big is a piece of work that never happens twice: the second time
    they came at it from a different screen, the signature differs, and the two
    doings never meet.

    The cut is the first thing the operator touched after something changed.
    What the application does by itself between the save and that touch -- the
    grid refreshing, the record being re-read -- belongs to the task that
    caused it. Nothing here is invented: the boundary is a POST somebody caused
    and the next thing they laid a finger on.

    A POST somebody *caused*: a keep-alive or a performance beacon is a POST on
    a timer, and cutting there halves whatever the operator was in the middle
    of. The first real pair this produced was a whole creation and a second
    "doing" that began at the third field of the same form.
    """
    at = 0
    changed = False
    for index, one in enumerate(run):
        if changed and one.is_gesture:
            yield run[at:index]
            at = index
            changed = False
        if one.is_call and one.mutating and not is_background_traffic(one.url):
            changed = True
    if at < len(run):
        yield run[at:]


def _repetitions(run: Sequence[Observed]) -> Iterator[Sequence[Observed]]:
    """A run that is one task done several times, cut back into the several.

    A pause is not the only boundary there is. Somebody working through a pile
    takes the next job off it without stopping, so twenty adjustments in an hour
    arrive as one run with no gap in it -- and the piece of work that gets
    counted is "twenty adjustments", seen once, which never reaches the number
    of times that makes a task worth offering. The most repetitive work in the
    warehouse was the work this was blindest to.

    Cut where the sequence of calls turns out to be one block repeated: the
    period of the sequence, by its own prefix function. Exact repetition only,
    which is deliberately timid -- a run with one extra click in the middle of
    the third doing is left whole rather than cut somewhere invented. Robotic
    process mining does this by finding the back edges of a control-flow graph
    over the log and tolerating noise between them (Leno et al., ICPM 2020);
    that is the same idea with a budget for imperfection, and it is where this
    should go when there is real observation to tune it against.
    """
    calls = [(index, one) for index, one in enumerate(run) if one.is_call]
    shapes = [f"{one.method.upper()} {url_shape(one.url)}" for _, one in calls]
    period = _period(shapes)
    if period is None:
        yield run
        return

    for start in range(0, len(calls) - period + 1, period):
        # From the gesture that caused this block's first call: a task begins
        # when somebody touches something, not when the page answers.
        at = calls[start][0]
        while at and run[at - 1].is_gesture:
            at -= 1
        end = calls[start + period][0] if start + period < len(calls) else len(run)
        while end and run[end - 1].is_gesture:
            end -= 1
        yield run[at:end]


def _period(shapes: Sequence[str]) -> int | None:
    """The length of the block this sequence repeats, if it repeats whole.

    The prefix function of string matching, over call shapes rather than
    characters: the shortest period is the length minus the longest border, and
    it is a real repetition only where it divides the length evenly and does so
    more than once.
    """
    if len(shapes) < 2:
        return None
    border = [0] * len(shapes)
    length = 0
    for index in range(1, len(shapes)):
        while length and shapes[index] != shapes[length]:
            length = border[length - 1]
        if shapes[index] == shapes[length]:
            length += 1
        border[index] = length

    period = len(shapes) - border[-1]
    if period == len(shapes) or len(shapes) % period:
        return None
    return period


def _runs(ordered: Sequence[Observed]) -> Iterator[list[Observed]]:
    """One host's stream cut into runs: a pause, or a length no work has.

    `one.host != run[0].host` is unreachable now -- the one caller partitions
    by host first, so every stream reaching here is one host's. Kept as the
    belt on "an episode is one host's", not as the reason for it: the reason is
    the partition above. Nothing else may cite this check as the guarantee that
    two episodes cannot overlap, because they now can and do.
    """
    run: list[Observed] = []
    for one in ordered:
        if run and (
            one.host != run[0].host or one.at - run[-1].at > IDLE or one.at - run[0].at > LONGEST
        ):
            yield run
            run = []
        run.append(one)
    if run:
        yield run


def _segment(run: Sequence[Observed]) -> Segment | None:
    calls = [one for one in run if one.is_call and not is_background_traffic(one.url)]
    gestures = [one for one in run if one.is_gesture]
    if not calls or not gestures:
        # Reading a screen is not a task, and traffic with nobody touching
        # anything is a page keeping itself alive.
        return None

    signature = _signature(calls)
    if not signature:
        return None

    return Segment(
        episode=Episode(
            started_at=run[0].at,
            ended_at=run[-1].at,
            host=run[0].host,
            batch_ids=tuple(dict.fromkeys(one.batch_id for one in run)),
            gestures=len(gestures),
            calls=len(calls),
            touched_from=gestures[0].at,
            touched_until=gestures[-1].at,
        ),
        signature=signature,
    )


def _signature(calls: Sequence[Observed]) -> str:
    """What makes two doings the same task.

    The changes it makes, where it makes any: a task is identified by what it
    did to the system, never by the route somebody took to get there. The same
    creation reached from a menu, from a search and from a bookmark is one task
    done three times, and before this it was three tasks done once each --
    which is the number that never earns anything.

    The reads are evidence of the same piece of work; they are just not what it
    *is*. That went for the ones before the change and now goes for the ones
    after it too, which is the same rule and used not to be.

    Including the trailing reads made the signature depend on how fast the
    operator clicked next. The segment is cut at the first thing they touch
    after something changed, so an operator who paused after saving kept the
    grid refresh and the re-reads inside it, and one who carried straight on
    did not. Two doings of the identical task, one signature `POST
    workOperations → GET workOperations → GET deviceClassFunctions → ...` and
    the other `POST workOperations`, neither ever reaching a second occurrence.
    That is the failure this function's first paragraph exists to prevent,
    arriving through the back door.

    Where nothing changed, the whole run identifies it: reading a screen is a
    task too, and it has nothing else to be known by.
    """
    changes = [one for one in calls if one.mutating]
    steps: list[str] = []
    for call in changes or calls:
        step = f"{call.method.upper()} {url_shape(call.url)}"
        if not steps or steps[-1] != step:
            steps.append(step)
    return " → ".join(steps)


def _flatten(payload: bytes, batch_id: BatchId) -> Iterator[Observed]:
    for line in payload.splitlines():
        if not line.strip():
            continue
        try:
            event = _loads(line)
        except ValueError:
            continue
        if event is None:
            continue
        one = _observed(event, batch_id)
        if one is not None:
            yield one


def _loads(line: bytes) -> Mapping[str, object] | None:
    parsed = json.loads(line)
    return parsed if isinstance(parsed, Mapping) else None


def _observed(event: Mapping[str, object], batch_id: BatchId) -> Observed | None:
    kind = event.get("kind")
    if kind == "gesture":
        gesture = event.get("gesture")
        if not isinstance(gesture, Mapping):
            return None
        url = str(gesture.get("url", ""))
        at = _seconds(gesture.get("at"))
        return (
            None
            if at is None
            else Observed(at=at, kind="gesture", host=_host(url), batch_id=batch_id, url=url)
        )

    if kind == "request":
        request = event.get("request")
        if not isinstance(request, Mapping):
            return None
        url = str(request.get("url", ""))
        at = _iso(request.get("started_at"))
        method = str(request.get("method", "")).upper()
        if at is None:
            return None
        return Observed(
            at=at,
            kind="request",
            host=_host(url),
            batch_id=batch_id,
            method=method,
            url=url,
            mutating=method not in ("GET", "HEAD", "OPTIONS"),
        )

    if kind == "page":
        url = str(event.get("url", ""))
        at = _iso(event.get("at"))
        return (
            None
            if at is None
            else Observed(at=at, kind="page", host=_host(url), batch_id=batch_id, url=url)
        )
    return None


def _seconds(raw: object) -> datetime | None:
    try:
        return epoch_to_datetime(float(raw))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def _iso(raw: object) -> datetime | None:
    """A protocol timestamp, or ``None`` for one that is not.

    ``fromisoformat`` parses an offset-less string too, silently returning a
    naive datetime -- and a naive one sorted against a gesture's always-aware,
    epoch-derived one raises `TypeError` rather than comparing. The protocol
    requires an offset; a string without one is exactly as malformed as one
    that fails to parse at all, and this file already skips those rather than
    crashing a whole sweep over one line an old extension build sent wrong.
    """
    if not isinstance(raw, str):
        return None
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else None


def _host(url: str) -> str:
    return (urlsplit(url).hostname or "").lower()
