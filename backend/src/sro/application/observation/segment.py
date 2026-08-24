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
    """Pieces of work, in the order they happened."""
    ordered = sorted(observed, key=lambda one: one.at)
    return tuple(segment for run in _runs(ordered) if (segment := _segment(run)) is not None)


def _runs(ordered: Sequence[Observed]) -> Iterator[list[Observed]]:
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
        ),
        signature=signature,
    )


def _signature(calls: Sequence[Observed]) -> str:
    """The calls, in order, without their identifiers -- and without immediate
    repeats, because a grid that pages twice is the same step done twice."""
    steps: list[str] = []
    for call in calls:
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
