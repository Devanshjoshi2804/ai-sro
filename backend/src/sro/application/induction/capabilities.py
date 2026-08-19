"""Everything a demonstration proved, not only the thing it was about.

An operator teaching "create a transport mode" opens the screen, and the screen
lists the existing ones before they touch anything. That list is a GET, it
answered 200, and its response is in the recording -- so the system already has
the evidence to answer "how many transport modes are there" and was making the
operator teach it a second time to get it.

The rule stays what it has always been: nothing is invented. A capability is
claimed only where a real request was made and a real response came back. What
changes is that the *incidental* calls stop being thrown away because they were
not what the operator had in mind.

Only reads are claimed this way, and deliberately. A write that happened without
anybody meaning to teach it is the one thing that must never quietly become a
skill somebody can run.
"""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlsplit

from sro.application.execution.answer import read_answer
from sro.application.induction.sites import parse_json
from sro.domain.recording.background import is_background_traffic
from sro.domain.recording.events import ActionFrame
from sro.domain.recording.network import CapturedRequest

_ASSETS = (".png", ".jpg", ".gif", ".svg", ".css", ".js", ".woff", ".ico")


@dataclass(frozen=True, slots=True)
class ReadCapability:
    """A read this demonstration performed, that answers a question about an entity."""

    request: CapturedRequest
    entity: str
    """The entity as the endpoint names it, normalised: ``warehouseTransportModes``
    and ``transport_mode`` are the same subject asked about two ways."""

    rows: int
    """How many records came back in the response the demonstration captured.
    A collection is what answers "how many"; a single record answers "what
    is". Both are useful, and telling them apart costs one length check."""

    counted: int | None = None
    """How many existed when this was demonstrated, where the response said so.

    ``None`` when it came back as one page of something longer -- and then
    nothing about that afternoon is worth repeating as a number, because the
    length of a page is a fact about the request."""

    @property
    def is_collection(self) -> bool:
        return self.rows >= 0


def normalise(name: str) -> str:
    """A name reduced to what it is about.

    ``warehouseTransportModes``, ``transport_modes`` and ``transportMode`` all
    become ``transportmode``: Blue Yonder prefixes the site-scoped variant of a
    resource with `warehouse`, and pluralises collections, and neither is a
    different subject.
    """
    lowered = "".join(character for character in name.lower() if character.isalnum())
    for prefix in ("warehouse", "wm", "data"):
        if lowered.startswith(prefix) and len(lowered) > len(prefix) + 2:
            lowered = lowered[len(prefix) :]
    return lowered[:-1] if lowered.endswith("s") else lowered


def reads_about(frames: tuple[ActionFrame, ...], entity: str) -> tuple[ReadCapability, ...]:
    """Reads this demonstration made about the entity it was about.

    Scoped to the entity on purpose. A screen fetches its policies, its unit
    conversions and its user's preferences before it shows anything, and turning
    every one of those into something an operator can ask for would bury the two
    that mean something under a dozen that do not.
    """
    wanted = normalise(entity)
    found: dict[str, ReadCapability] = {}

    for frame in frames:
        for request in frame.requests:
            if not _is_a_read(request):
                continue
            resource = _resource_of(request.url)
            if not resource or wanted not in normalise(resource):
                continue
            counted = read_answer(request.response_text, url=request.url)
            if counted is None:
                continue
            rows = counted.rows
            if not _records_of(request, frames):
                # The name is not enough. `/rpux/filter/columns/WMSupplier`
                # ends in the entity, answers 200, and returns five rows -- of
                # column definitions. A skill built from it told an operator
                # there were five suppliers, which is the confident wrong
                # answer this system exists to not give.
                continue
            # First one wins: a screen that fetches the same list twice taught
            # one capability, not two.
            found.setdefault(
                normalise(resource),
                ReadCapability(request, resource, rows, counted=counted.counted),
            )

    # The subject itself, ahead of everything merely named after it.
    # `warehouseTransportModeUoms` contains `transportmode` and is a list of
    # unit conversions -- it was empty, it sorted first, and the skill built
    # from it announced that there were 0 transport modes while seventeen were
    # on screen. Containment finds the candidates; only equality identifies the
    # subject.
    return tuple(sorted(found.values(), key=lambda read: (normalise(read.entity) != wanted,)))


def _records_of(request: CapturedRequest, frames: tuple[ActionFrame, ...]) -> bool:
    """Whether this response carries the entity's own records.

    Judged against what the demonstration wrote, because that payload is the
    entity as the system itself describes it: a supplier has a
    `supplierNumber`, an `addressName`, a `clientId`. A response sharing none of
    those field names is about something else, whatever its URL says.

    Where the demonstration wrote nothing there is nothing to compare against,
    and the read is taken at its word -- a reading recording is all reads, and
    refusing every one of them would leave nothing at all.
    """
    shape = _written_shape(frames)
    if not shape:
        return True
    return len(shape & _record_fields(request.response_text)) >= 2


def _written_shape(frames: tuple[ActionFrame, ...]) -> frozenset[str]:
    """The field names the demonstration sent when it changed the entity."""
    for frame in frames:
        for request in frame.requests:
            if not request.is_mutation or not request.succeeded:
                continue
            document = parse_json(request.request_text)
            payload = document.get("data") if isinstance(document, dict) else None
            if isinstance(payload, dict):
                return frozenset(payload)
            if isinstance(document, dict):
                return frozenset(document)
    return frozenset()


def _record_fields(text: str | None) -> frozenset[str]:
    document = parse_json(text) if text else None
    data = document.get("data") if isinstance(document, dict) else None
    if isinstance(data, list):
        data = data[0] if data and isinstance(data[0], dict) else None
    return frozenset(data) if isinstance(data, dict) else frozenset()


def _is_a_read(request: CapturedRequest) -> bool:
    if request.method.upper() != "GET" or request.status is None:
        return False
    if not 200 <= request.status < 300:
        return False
    if is_background_traffic(request.url):
        return False
    path = urlsplit(request.url).path.lower()
    return not path.endswith(_ASSETS)


def _resource_of(url: str) -> str:
    """The last path segment that names a thing rather than an instance."""
    segments = [segment for segment in urlsplit(url).path.split("/") if segment]
    for segment in reversed(segments):
        if any(character.isalpha() for character in segment):
            return segment
    return ""


def wrote_to(frames: tuple[ActionFrame, ...]) -> str | None:
    """The collection the demonstration changed, if it changed one.

    The counterpart of a create is a read of the same collection. Blue Yonder's
    screen creates in `transportModes` and then refreshes `warehouseTransportModes`
    -- the site's own view of it -- so a read claimed from what the screen
    happened to fetch answers a narrower question than the write acts on, and
    says nothing about the difference.
    """
    for frame in reversed(frames):
        for request in frame.requests:
            if request.is_mutation and request.status and 200 <= request.status < 300:
                collection = _collection_of(request.url)
                if collection:
                    return collection
    return None


def _collection_of(url: str) -> str:
    """The collection a call acted on, never the record inside it.

    `PUT /wm/addresses/A000144886` acts on the addresses collection. Reading the
    last segment gave `A000144886`, and that id was then offered to an operator
    as one of two collections their question might mean, and written into a
    skill summary as "writes to A000144886, which is a wider collection".
    """
    for segment in reversed([s for s in urlsplit(url).path.split("/") if s]):
        if any(character.isalpha() for character in segment) and not _is_a_record(segment):
            return segment
    return ""


def _is_a_record(segment: str) -> bool:
    """A record's id names the record, not the collection it lives in."""
    return any(character.isdigit() for character in segment) or len(segment) > 24
