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

import httpx

from sro.infrastructure.steel.client import SteelClient, cdp_origin, websocket_debugger_url

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


# -- the CDP endpoint Chrome will actually answer ------------------------------


async def test_the_cdp_authority_is_an_address_because_chrome_refuses_a_name() -> None:
    """Chrome answers every `/json/*` request and every devtools websocket
    whose Host is a name with

        500 Host header is specified and is not an IP address or localhost.

    It is a DNS-rebinding guard. On a compose network the host IS a name, so
    this deployment could reach Chrome's port and could not use it -- and
    nothing noticed until the first browser session was opened, because
    `localhost:9223` on a laptop has an IP for a host and walks past the check.
    """
    authority = await cdp_origin("http://localhost:9223")

    host, _, port = authority.rpartition(":")
    assert host == "127.0.0.1", "a name here is a 500 from Chrome"
    assert port == "9223", "the port is not Chrome's to choose"


async def test_a_host_that_does_not_resolve_is_left_as_it_was_written() -> None:
    """The connection that follows fails on its own and names what it could
    not reach, which is a better error than one about DNS."""
    assert await cdp_origin("http://nothing.invalid:9223") == "nothing.invalid:9223"


async def test_an_http_cdp_url_becomes_chrome_s_websocket_on_an_address() -> None:
    """Chrome's `webSocketDebuggerUrl` has no port (`ws://localhost/devtools/...`),
    so following it verbatim dialled port 80 and failed with ECONNREFUSED
    (S5 review I5). The path is Chrome's; the authority is the resolved one."""
    asked: list[str] = []

    def handle(request: httpx.Request) -> httpx.Response:
        asked.append(request.url.host)
        return httpx.Response(
            200, json={"webSocketDebuggerUrl": "ws://localhost/devtools/browser/g"}
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        url = await websocket_debugger_url("http://localhost:9223", client)

    assert url == "ws://127.0.0.1:9223/devtools/browser/g"
    assert asked == ["127.0.0.1"], "a name in the Host header is a 500 from Chrome"


async def test_a_websocket_cdp_url_keeps_its_path_and_gets_an_address() -> None:
    """What the pool hands out is already a websocket url; only its host is
    resolved, so the same function serves both shapes."""

    def refuse(request: httpx.Request) -> httpx.Response:
        raise AssertionError("a websocket url needs no /json/version")

    async with httpx.AsyncClient(transport=httpx.MockTransport(refuse)) as client:
        url = await websocket_debugger_url("ws://localhost:9223/devtools/browser/g", client)

    assert url == "ws://127.0.0.1:9223/devtools/browser/g"
