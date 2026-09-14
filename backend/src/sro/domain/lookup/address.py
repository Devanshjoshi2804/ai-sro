"""Where a planned lookup actually goes on the wire.

A plan names a knowledge key -- `/data/WM/wm/suppliers`, or the route hash
`#wm.config/wm.config.partners.suppliers////` -- and neither is something a
browser can open. The knowledge base holds no host: `api-endpoints.json`
catalogues paths, and a deployment is whatever host that tenant's operator
signs into.

So an address is RESOLVED FROM WHERE THIS DEPLOYMENT HAS ALREADY BEEN. The
same evidence discipline as everything else here: a lookup reaches a host
because a gesture was recorded against that host, never because a host was
assembled out of parts. Two consequences worth stating, because both look like
limitations until the alternative is written down:

**A screen is a url somebody was on, not a url built from a route.** The real
page is `.../portal/page?libraryContext=f4d675...&siteId=SG&menu=wm.config
#wm.config.partners.suppliers////`, and `libraryContext` is a session token
this side cannot invent. Assembling `origin + hash` produces a url that loads
the shell and not the screen. Reusing the recorded one is the only honest
option, and when its token has expired the answer says the page did not come
up -- which is a true answer, where a confidently wrong url is not.

**A read may not write, checked again here.** The planner cannot express a
write, and this refuses anything that is not a recorded GET. Two belts,
because this is the half that reaches somebody's warehouse.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from sro.domain.execution.planning import LIVE_FETCHABLE_HEADERS
from sro.domain.lookup.plan import Lookup
from sro.domain.observation.gesture import Gesture
from sro.domain.shared.hosts import REDACTED, headers_without_markers


@dataclass(frozen=True, slots=True)
class Address:
    """One lookup, as something the extension can be asked to do."""

    url: str
    headers: dict[str, str] = field(default_factory=dict)
    live_headers: tuple[str, ...] = ()
    """Names the extension reads off the live page. The recorder strikes these
    out at the boundary, so what is stored is the marker's own text; the tab
    the operator is signed into has the real value."""

    struck: tuple[str, ...] = ()
    """Struck out, with no live source. Not an error on its own -- the call
    goes without them and the system may well answer -- but the first thing to
    look at when it does not."""

    seen_at: float | None = None
    """When the evidence this address came from was recorded. A month-old
    session still names the right host; its session token may be spent."""


def address_for(lookup: Lookup, gestures: Iterable[Gesture]) -> Address | None:
    """Where this lookup goes, or nothing if this deployment has not been there."""
    seen = list(gestures)
    if lookup.how == "call":
        return _call_address(lookup, seen)
    return _screen_address(lookup, seen)


def _call_address(lookup: Lookup, gestures: list[Gesture]) -> Address | None:
    """The newest successful GET of this exact path, re-aimed at the question.

    Newest because a session moves: the last call that worked carries the
    headers the system wanted most recently. Exact path, because a prefix match
    would answer `/suppliers` with `/suppliers/count` -- a different question
    with a plausible-looking answer, which is the failure this whole module is
    arranged against.
    """
    worked = [
        call
        for gesture in gestures
        for call in gesture.requests
        if call.method.upper() == "GET"
        and urlsplit(call.url).path == lookup.target
        and call.status is not None
        and 200 <= call.status < 300
        and not call.failure_reason
    ]
    if not worked:
        return None
    call = max(worked, key=lambda one: one.started_at or 0.0)
    struck_out = [name for name, value in call.request_headers.items() if REDACTED in value]
    return Address(
        url=_with_params(call.url, lookup.params),
        headers=headers_without_markers(call.request_headers),
        live_headers=tuple(n for n in struck_out if n.lower() in LIVE_FETCHABLE_HEADERS),
        struck=tuple(n for n in struck_out if n.lower() not in LIVE_FETCHABLE_HEADERS),
        seen_at=call.started_at,
    )


def _screen_address(lookup: Lookup, gestures: list[Gesture]) -> Address | None:
    """The newest page url whose fragment names this route.

    Matched on the route name alone. The catalogue writes
    `#wm.config/wm.config.partners.suppliers////` -- the menu and the route --
    where the application's url carries `menu=wm.config` in the query and only
    `#wm.config.partners.suppliers////` after the hash. One screen, spelled
    differently by the two sides, so the comparison is over the part they
    agree on.
    """
    wanted = _route_name(lookup.target)
    if not wanted:
        return None
    on_it = [
        gesture
        for gesture in gestures
        if gesture.url and _route_name(urlsplit(gesture.url).fragment) == wanted
    ]
    if not on_it:
        return None
    seen = max(on_it, key=lambda gesture: gesture.at)
    return Address(url=seen.url or "", seen_at=seen.at)


def _route_name(route: str) -> str:
    """A route as the screen it names, however either side spells it.

    The catalogue writes `#<menu>/<route>////`; the application's url carries
    the menu in its query and only `#<route>////` after the hash. So the last
    non-empty segment is the screen in both spellings -- the leading `#` and
    the menu are the catalogue's, and the trailing separators are the
    application's own padding for parameters the screen was opened without.
    """
    segments = [part.strip() for part in route.lstrip("#").split("/") if part.strip()]
    return segments[-1].lower() if segments else ""


def _with_params(url: str, params: dict[str, str]) -> str:
    """The recorded url, asking the question that was planned.

    The recorded query is a previous operator's question -- `siteId=SG` from
    whenever this was captured -- and the plan's parameters are this one's, so
    the plan wins on any name they share. Names it does not mention are kept:
    dropping `libraryContext` or a paging parameter the system requires turns
    a working call into a 400.
    """
    if not params:
        return url
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query.update(params)
    return urlunsplit(parts._replace(query=urlencode(query)))
