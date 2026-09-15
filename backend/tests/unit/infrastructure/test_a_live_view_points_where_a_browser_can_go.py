"""`live_view_url` is the one string this client builds for somebody else.

Everything else `SteelClient` does is between this process and Steel, and both
are on the same private network. The live view is different: it goes into an
API response and the console puts it in an iframe that an operator watches
their own teaching session through.

Deployed, that browser has never heard of `steel`. The url was
`http://steel:3000/v1/sessions/debug`, which resolves on the compose network
and nowhere a person is sitting, and it failed as a frame that never loaded.

The same mistake as the presigned url one service along, found the same way:
by asking what leaves the deployment.
"""

from __future__ import annotations

from urllib.parse import urlsplit

from sro.infrastructure.steel.client import SteelClient

INSIDE = "http://steel:3000"
OUTSIDE = "http://10.11.9.25:8088"

# What Steel answers a create with, with its own DOMAIN in the urls.
SESSION: dict[str, object] = {
    "id": "5ce1a1ff-0000-4000-8000-000000000001",
    "status": "live",
    "debugUrl": "http://10.11.9.25:8088/v1/sessions/debug",
    "sessionViewerUrl": "http://10.11.9.25:8088/",
}


def _viewer_url(public: str | None) -> str:
    """The one line under test: the base this client puts in front of the path
    Steel chose. Driven directly rather than through `open()`, which also takes
    the browser, polls for liveness and asks Chrome for its debugger -- none of
    which is what was wrong."""
    steel = SteelClient(INSIDE, "http://steel:9223", public_base_url=public)
    return steel._viewer(SESSION)


def test_the_live_view_names_the_address_a_browser_can_reach() -> None:
    url = _viewer_url(OUTSIDE)

    assert urlsplit(url).netloc == "10.11.9.25:8088"
    assert "steel:3000" not in url, "a private name reached a browser"


def test_it_keeps_the_path_steel_chose() -> None:
    """Only the base is ours. Steel decides which screen the viewer is, and
    `debugUrl` is deliberately the bare player rather than Steel's own console
    with its Release Session button inside our teaching screen."""
    assert urlsplit(_viewer_url(OUTSIDE)).path == "/v1/sessions/debug"


def test_one_address_is_still_one_address() -> None:
    """A laptop, where Steel is reached by the same name either way."""
    assert urlsplit(_viewer_url(None)).netloc == "steel:3000"
