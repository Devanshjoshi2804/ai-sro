"""Host matching. One rule, because three copies of it disagreed once."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from urllib.parse import urlparse, urlsplit, urlunparse

# The marker a redaction leaves behind, in place of whatever it removed. Lives
# here, beside `system_of`, rather than in the wire module that first defined
# it: both a body redaction and a URL's origin are things more than one module
# in this codebase reads, and a rule two copies of which had already
# disagreed once is exactly the kind of thing this module exists to hold once.
REDACTED = "«redacted»"


_DEFAULT_PORTS = {"http": "80", "https": "443"}


def origin_of(url: str) -> str:
    """A url as the system it belongs to: host and port, default port dropped.

    `https://wms.acme.com:443` and `https://wms.acme.com` are one system, and
    a rule that cannot say so refuses half the pages on it. Port and not
    hostname alone, because an API on 8000 beside a console on 3000 is the
    ordinary shape of this deployment.

    Here rather than in `skill/checks.py`, where it was written, because the
    evidence plane needs the same idea of what one system is: the rule that
    links two systems by TIME has to agree with the rule that strikes a
    system from a job about whether a port makes two of them.
    """
    parsed = urlsplit(url)
    host = (parsed.hostname or "").rstrip(".")
    if not host:
        return ""
    if ":" in host:
        host = f"[{host}]"
    try:
        port = str(parsed.port) if parsed.port else ""
    except ValueError:
        return ""
    if port and port == _DEFAULT_PORTS.get(parsed.scheme.lower()):
        port = ""
    return f"{host}:{port}" if port else host


def system_of(url: str | None) -> str | None:
    if not url:
        return None
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        return None
    return f"{parsed.scheme}://{parsed.netloc}"


def page_of(url: str | None) -> str | None:
    """The screen a url names, without what identifies one visit to it.

    Scheme, host and path. The query and the fragment are dropped, and both of
    them are dropped for the same reason: they are where a system puts what is
    particular to one visit. Measured on real captured evidence, 2026-09-15 --

        https://mail.google.com/mail/u/0/?tab=rm&ogbl#inbox/FMfcgzQhWLST...
        https://bf56-…jdadelivers.com/portal/page?libraryContext=f4d6755a…

    -- one message id, one session token, and nothing that says which screen
    either of them is that the path does not already say.

    The scheme stays, so this is still a url. The extension reduces it further
    to host-and-path the moment it arrives (`nudge.page`), and that reduction
    parses what it is given: handed a bare `host/path` it would throw, catch,
    and return the empty string, which is every arrival offer silently gone.

    **Not for anything that navigates.** A warehouse addresses its screens BY
    fragment -- `…/portal?siteId=SG#wm.config/wm.config.partners.customers.types`
    -- so a run opening this would land on the portal root and plan against the
    wrong page. `run_workflow` keeps the whole url for that, deliberately.
    """
    if not url:
        return None
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        return None
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"


def same_screen(one: str | None, other: str | None) -> bool:
    """Whether two urls are the same screen of the same application.

    Scheme, host, path AND fragment; the query is dropped. `page_of` drops the
    fragment too, and for an application that keeps its routes there -- which
    is every ExtJS portal this system has met -- that makes every screen
    compare equal to every other. Measured on the deployment, 2026-09-17:

        .../portal?siteId=SG#wm.config/wm.config.warehouse.warehouse////
        .../portal?siteId=SG#wm.config/wm.config.partners.customers.types////

    `page_of` calls those the same page. They are the Warehouse screen and the
    Customer Types screen, and a rule that cannot tell them apart is a rule
    that reports arriving somewhere it never went.

    The query stays dropped, for `page_of`'s reason: it is where a session
    token and one visit's particulars live.
    """
    if not one or not other:
        return False
    mine, theirs = urlsplit(one), urlsplit(other)
    return (mine.scheme, mine.netloc, mine.path, mine.fragment) == (
        theirs.scheme,
        theirs.netloc,
        theirs.path,
        theirs.fragment,
    )


def screen_of(urls: Iterable[str | None]) -> str | None:
    """The screen these visits have in common: what every one of them agrees on.

    `page_of` throws away the query and the fragment because it cannot tell
    which parts of them name a screen. This can, when it is given more than one
    visit, and it needs no rule about either component -- the demonstrations
    say which parts vary. What they agree on is the screen; what differs is the
    particular, and the particular is precisely what must not be navigated to.

    The first url is the anchor: its scheme and host are the answer's, and a
    visit on a different host is not another demonstration of this screen and
    is ignored rather than allowed to erase everything.

    Component by component, except the query, which is per PARAMETER -- because
    a real one mixes both kinds in one string. Measured on the deployment's own
    evidence, 2026-09-15:

        …/portal/page?libraryContext=f4d6755ab6b6…&siteId=SG&menu=wm.config#…

    `libraryContext` is a session token and `siteId` and `menu` are the screen.
    Whole-or-nothing on the query would lose the menu to keep out the token, or
    keep the token to hold the menu. Per parameter loses neither.

    Raw segments rather than parsed pairs, so a value comes back spelled the way
    the browser spelled it: re-encoding a query is how a url that worked stops
    working.

    One demonstration agrees with itself, so a single url comes back whole. That
    is the honest answer and not a fallback -- with one doing there is nothing
    that says which half of it was the job.
    """
    seen = [urlparse(url) for url in urls if url]
    if not seen:
        return None
    anchor = seen[0]
    if not anchor.scheme or not anchor.netloc:
        return None
    same = [one for one in seen if (one.scheme, one.netloc) == (anchor.scheme, anchor.netloc)]

    path = anchor.path if all(one.path == anchor.path for one in same) else ""
    fragment = anchor.fragment if all(one.fragment == anchor.fragment for one in same) else ""
    others = [set(one.query.split("&")) if one.query else set() for one in same]
    query = "&".join(
        segment
        for segment in (anchor.query.split("&") if anchor.query else [])
        if all(segment in one for one in others)
    )
    return urlunparse((anchor.scheme, anchor.netloc, path, "", query, fragment))


def domain_matches(host: str, domain: str) -> bool:
    """RFC 6265 domain-match: the host itself, or a subdomain of it.

    A suffix test is not this. ``"evil-wms.acme.com".endswith("wms.acme.com")``
    is true, and that is how a lookalike host reaches a cookie -- or, here, past
    an exclusion.
    """
    host, domain = host.lower().rstrip("."), domain.lower().lstrip(".").rstrip(".")
    if not host or not domain:
        return False
    return host == domain or host.endswith(f".{domain}")


def headers_without_markers(headers: Mapping[str, str]) -> dict[str, str]:
    """The headers that can still be sent: a value the boundary struck out is
    not a credential the browser can use, it is the marker's own text. Beside
    REDACTED because everything that sends a recorded request needs the same
    rule -- the planner replaying a call, the verifier probing a confirming
    read, the lookup addressing an endpoint -- and a second copy is a second
    thing to forget."""
    return {name: value for name, value in headers.items() if REDACTED not in value}
