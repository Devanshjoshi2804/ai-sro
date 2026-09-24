from __future__ import annotations

from collections.abc import Iterable, Mapping
from urllib.parse import urlparse, urlsplit, urlunparse

REDACTED = "«redacted»"


_DEFAULT_PORTS = {"http": "80", "https": "443"}


def origin_of(url: str) -> str:
    parsed = urlsplit(url)
    if not parsed.netloc:
        parsed = urlsplit(f"//{url}")
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
    if not url:
        return None
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        return None
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"


def same_screen(one: str | None, other: str | None) -> bool:
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
    host, domain = host.lower().rstrip("."), domain.lower().lstrip(".").rstrip(".")
    if not host or not domain:
        return False
    return host == domain or host.endswith(f".{domain}")


def headers_without_markers(headers: Mapping[str, str]) -> dict[str, str]:
    return {name: value for name, value in headers.items() if REDACTED not in value}
