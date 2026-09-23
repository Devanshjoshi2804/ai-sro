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

LONGEST = timedelta(minutes=30)

_CALLS = ("xhr", "fetch", "")


@dataclass(frozen=True, slots=True)
class Observed:
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


def read(payload: bytes, batch_id: BatchId) -> tuple[Observed, ...]:
    return tuple(_flatten(payload, batch_id))


def segment(observed: Sequence[Observed]) -> tuple[Segment, ...]:
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
    calls = [(index, one) for index, one in enumerate(run) if one.is_call]
    shapes = [f"{one.method.upper()} {url_shape(one.url)}" for _, one in calls]
    period = _period(shapes)
    if period is None:
        yield run
        return

    for start in range(0, len(calls) - period + 1, period):
        at = calls[start][0]
        while at and run[at - 1].is_gesture:
            at -= 1
        end = calls[start + period][0] if start + period < len(calls) else len(run)
        while end and run[end - 1].is_gesture:
            end -= 1
        yield run[at:end]


def _period(shapes: Sequence[str]) -> int | None:
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
        return None

    signature = _signature(calls)
    if not signature:
        return None

    first_url = next((one.url for one in gestures if one.url), "")
    parts = urlsplit(first_url)
    starts_on = f"{parts.netloc}{parts.path}".rstrip("/") if parts.netloc else ""

    return Segment(
        episode=Episode(
            started_at=run[0].at,
            ended_at=run[-1].at,
            host=run[0].host,
            starts_on=starts_on,
            batch_ids=tuple(dict.fromkeys(one.batch_id for one in run)),
            gestures=len(gestures),
            calls=len(calls),
            touched_from=gestures[0].at,
            touched_until=gestures[-1].at,
        ),
        signature=signature,
    )


def _signature(calls: Sequence[Observed]) -> str:
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
    if not isinstance(raw, str):
        return None
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else None


def _host(url: str) -> str:
    return (urlsplit(url).hostname or "").lower()
