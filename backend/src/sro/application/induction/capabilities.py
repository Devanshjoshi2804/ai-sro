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
    """How many records came back. A collection is what answers "how many"; a
    single record answers "what is". Both are useful, and telling them apart
    costs one length check."""

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
            rows = _rows(request.response_text)
            if rows is None:
                continue
            # First one wins: a screen that fetches the same list twice taught
            # one capability, not two.
            found.setdefault(normalise(resource), ReadCapability(request, resource, rows))

    # The subject itself, ahead of everything merely named after it.
    # `warehouseTransportModeUoms` contains `transportmode` and is a list of
    # unit conversions -- it was empty, it sorted first, and the skill built
    # from it announced that there were 0 transport modes while seventeen were
    # on screen. Containment finds the candidates; only equality identifies the
    # subject.
    return tuple(sorted(found.values(), key=lambda read: (normalise(read.entity) != wanted,)))


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


def _rows(text: str | None) -> int | None:
    """How many records the response carried, or None if it is not one.

    ``None`` means this is not a resource read at all -- HTML, an empty body, a
    payload with no recognisable records -- and a capability is not claimed from
    something we cannot read.
    """
    document = parse_json(text) if text else None
    if not isinstance(document, dict):
        return None
    data = document.get("data")
    if isinstance(data, list):
        return len(data)
    return 1 if isinstance(data, dict) else None


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
                return _resource_of(request.url)
    return None
