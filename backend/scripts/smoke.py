"""Does this deployment work from outside itself?

Every defect found on the first day of deploying was on an edge that *leaves*
the deployment, and every one of them looked correct in the code and worked on
a laptop:

- the trace pipeline had a provider and an exporter and never opened a span;
- a presigned artifact url named `minio:9000`, which no browser can resolve;
- `live_view_url` named `steel:3000`, the same mistake one service along;
- the CDP endpoint named a host, and Chrome refuses a Host that is not an
  address.

They share a shape. A url or a connection that stays inside the compose network
is exercised by everything, all the time. One that is handed to a browser is
exercised by nobody until an operator opens a page -- and then it fails as a
broken image, a frame that never loads, or a silence.

So this asks the questions only an outside caller can ask. It runs *in* the API
container, because it needs the app's own adapters to mint the urls under test,
and then it uses those urls the way a browser would: over the public address,
through the proxy, from end to end.

    docker compose -f infra/docker-compose.deploy.yml --env-file infra/.env.qa \
        exec -T api python scripts/smoke.py http://10.11.9.25:8088

Exits non-zero if anything is wrong, and says which thing. Safe to run against
a live deployment: it writes one small blob and deletes it, opens one browser
session and releases it, and touches nothing else.
"""

from __future__ import annotations

import asyncio
import ipaddress
import sys
from datetime import timedelta
from urllib.parse import urlsplit

import httpx

from sro.config import get_settings
from sro.container import build_container

PROBE_KEY = "probe/smoke.txt"
PROBE_BODY = b"written by scripts/smoke.py"

_PASS, _FAIL = "  ok   ", "  FAIL "
_failures: list[str] = []


def ok(what: str, detail: str = "") -> None:
    print(f"{_PASS}{what}{'  ' + detail if detail else ''}")


def bad(what: str, detail: str) -> None:
    _failures.append(what)
    print(f"{_FAIL}{what}  {detail}")


def _is_private_name(url: str) -> bool:
    """Whether this url names something only the compose network can resolve.

    A single label with no dot -- `minio`, `steel`, `api` -- is a container
    name. That is the whole bug class this script exists for.
    """
    host = urlsplit(url).hostname or ""
    if not host or host == "localhost":
        return False
    try:
        ipaddress.ip_address(host)
    except ValueError:
        return "." not in host
    return False


async def check_addresses(public: str) -> None:
    """What this deployment believes its own addresses are.

    `our_own_origins()` reads these to know which traffic is the system's own,
    and evidence is refused for them ahead of any tenant's policy. Left at
    their defaults, the console's own calls are captured and mined as
    warehouse work -- which has happened.
    """
    settings = get_settings()
    for name, value in (
        ("SRO_API_URL", settings.api_url),
        ("SRO_CONSOLE_URL", settings.console_url),
        ("SRO_S3_PUBLIC_ENDPOINT_URL", settings.s3_public_endpoint_url or settings.s3_endpoint_url),
        ("SRO_STEEL_PUBLIC_BASE_URL", settings.steel_public_base_url or settings.steel_base_url),
    ):
        if _is_private_name(value):
            bad(name, f"{value} — a name only this network can resolve")
        elif urlsplit(value).hostname in {"localhost", "127.0.0.1"} and "localhost" not in public:
            bad(name, f"{value} — localhost, on a host operators reach by another name")
        else:
            ok(name, value)


async def check_artifact(container: object, public: str) -> None:
    """A presigned url, fetched the way the console fetches a screenshot."""
    blobs = container.blobs  # type: ignore[attr-defined]
    uri = await blobs.put(PROBE_KEY, PROBE_BODY, content_type="text/plain")
    try:
        url = await blobs.presigned_url_for_uri(uri, expires_in=timedelta(minutes=5))
        if url is None:
            bad("artifact url", "none was produced")
            return
        if _is_private_name(url):
            bad("artifact url", f"{url[:60]} — a browser cannot resolve that host")
            return
        async with httpx.AsyncClient(timeout=15.0) as web:
            got = await web.get(url)
            if got.status_code != httpx.codes.OK or got.content != PROBE_BODY:
                bad("artifact fetch", f"{got.status_code}, {len(got.content)} bytes")
                return
            ok("artifact fetch", f"{urlsplit(url).netloc} → 200, contents match")
            # The signature covers the host and the path. If a proxy rewrote
            # either, this would be a 200 and the deployment would be serving
            # unsigned objects to anyone who guessed a key.
            tampered = await web.get(url + "X")
            if tampered.status_code == httpx.codes.FORBIDDEN:
                ok("artifact signature", "a tampered url is refused")
            else:
                bad("artifact signature", f"tampering answered {tampered.status_code}, wanted 403")
    finally:
        await blobs.forget(uri)


async def check_browser(container: object, public: str) -> None:
    """A real session, its live view, and the screencast socket behind it."""
    browser = container.browser  # type: ignore[attr-defined]
    authority = await browser._cdp_origin()
    host = authority.rsplit(":", 1)[0]
    try:
        ipaddress.ip_address(host)
        ok("cdp endpoint", f"{authority} — an address, which is all Chrome accepts")
    except ValueError:
        bad("cdp endpoint", f"{authority} — Chrome answers a named Host with 500")

    try:
        session = await browser.open()
    except Exception as exc:
        bad("browser session", f"{type(exc).__name__}: {str(exc)[:110]}")
        return

    try:
        url = session.live_view_url
        if _is_private_name(url):
            bad("live view url", f"{url} — a browser cannot resolve that host")
            return
        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as web:
            page = await web.get(url)
            if page.status_code != httpx.codes.OK:
                bad("live view fetch", f"{page.status_code}")
                return
            if "next-router" in str(page.headers).lower():
                bad("live view fetch", "the console answered it, so the route is wrong")
                return
            ok("live view fetch", f"{urlsplit(url).netloc} → 200 from the browser service")
        await _check_cast(page.text, public)
    finally:
        await browser.close(session.id)


async def _check_cast(page: str, public: str) -> None:
    """The screencast socket the live view opens. An iframe that loads and
    never paints is what a broken one looks like."""
    import re

    found = re.search(r"wss?://[^\"'\s]+", page)
    if not found:
        bad("screencast socket", "the live view named no socket")
        return
    url = found.group(0)
    if _is_private_name(url):
        bad("screencast socket", f"{url} — a browser cannot resolve that host")
        return
    try:
        import websockets

        async with websockets.connect(url, open_timeout=15, max_size=None) as socket:
            frame = await asyncio.wait_for(socket.recv(), timeout=10)
            ok("screencast socket", f"{urlsplit(url).netloc} → a frame of {len(frame)} bytes")
    except Exception as exc:
        bad("screencast socket", f"{url} — {type(exc).__name__}: {str(exc)[:80]}")


async def check_console(public: str) -> None:
    """The console, and what its bundle was built to talk to.

    `NEXT_PUBLIC_API_URL` is inlined at build time. A bundle carrying an
    absolute hostname is one image that serves one environment, and a bundle
    carrying a private name is a console that loads and fails every request.
    """
    async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as web:
        page = await web.get(public)
        if page.status_code != httpx.codes.OK:
            bad("console", f"{public} → {page.status_code}")
            return
        ok("console", f"{public} → 200")

        import re

        chunks = re.findall(r"/_next/static/chunks/[A-Za-z0-9_.-]+\.js", page.text)
        for chunk in dict.fromkeys(chunks):
            body = (await web.get(f"{public}{chunk}")).text
            for name in ("minio:", "steel:", "//api:", "postgres:"):
                if name in body:
                    bad("console bundle", f"{chunk} was built against {name}")
                    return
        ok("console bundle", f"{len(set(chunks))} chunks, no private hostname in any of them")


async def check_api(public: str) -> None:
    """The API through whatever is in front of it, with and without a token."""
    async with httpx.AsyncClient(timeout=20.0) as web:
        health = await web.get(f"{public}/api/health")
        if health.status_code != httpx.codes.OK:
            bad("api health", f"{health.status_code}")
        else:
            ok("api health", f"revision {health.json().get('revision', '?')}")

        unauthorised = await web.get(f"{public}/api/v1/workflows")
        if unauthorised.status_code == httpx.codes.UNAUTHORIZED:
            ok("api auth", "no credential is refused")
        else:
            bad("api auth", f"an unauthenticated call answered {unauthorised.status_code}")


async def check_worker(container: object) -> None:
    """Whether a worker is polling. Its container status cannot say: one image
    serves the API and the worker, and the worker serves no HTTP."""
    settings = get_settings()
    try:
        from sro.infrastructure.temporal.queues import DEFAULT_QUEUE
        from sro.infrastructure.temporal.worker import connect

        client = await connect(settings)
        described = await client.workflow_service.describe_task_queue(
            __import__(
                "temporalio.api.workflowservice.v1", fromlist=["DescribeTaskQueueRequest"]
            ).DescribeTaskQueueRequest(
                namespace=client.namespace,
                task_queue=__import__(
                    "temporalio.api.taskqueue.v1", fromlist=["TaskQueue"]
                ).TaskQueue(name=DEFAULT_QUEUE),
            )
        )
        pollers = list(described.pollers)
        if pollers:
            ok("worker", f"{len(pollers)} poller(s) on {DEFAULT_QUEUE}")
        else:
            bad("worker", f"nothing is polling {DEFAULT_QUEUE} — induction will never run")
    except Exception as exc:
        bad("worker", f"{type(exc).__name__}: {str(exc)[:90]}")


async def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    public = sys.argv[1].rstrip("/")
    print(f"smoke test against {public}\n")

    container = build_container()
    await check_addresses(public)
    await check_api(public)
    await check_console(public)
    await check_artifact(container, public)
    await check_browser(container, public)
    await check_worker(container)

    print()
    if _failures:
        print(f"{len(_failures)} check(s) failed: {', '.join(_failures)}")
        return 1
    print("every edge that leaves this deployment is reachable and correct")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
