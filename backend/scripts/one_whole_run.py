"""A job, watched in a real browser and then done by the system, end to end.

Nothing in this repository has ever finished a workflow run. Four runs exist
across both real tenants and all four are `stopped`; the furthest any reached
was step 3 of 6. Every one died the same way, and not because the runner is
broken: `scripts/stub_device.py` refuses screenshots on purpose, so `verify`'s
third rung -- the one that looks at a picture -- has never executed once, and
a step that rung would have held reads `unclear` instead, which stops the run.

What this proves, and what it does not. It proves the chain: a real Chromium
with the real extension watching a real page, gestures uploaded to the real
backend over the real socket, a workflow standing on those gestures, and
`run_workflow` driving that same browser back through them with a real model
looking at real screenshots. It does NOT prove anything about a warehouse:
the page is a local form, and a page nobody has to log into is an easier page
than Blue Yonder.

The run is dry, and a dry run CAN finish: `run_workflow` ends `held` when every
step is `held` or `withheld`, so the typing step is verified for real and the
Save step is shown in full and withheld. A live run needs a person to tap
Approve in the panel, which is the half this still does not reach.

    make one-whole-run

Needs the API up (`make up && make api`) and a Chromium Playwright can load an
extension into. Nothing here is part of the product.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

EXTENSION = Path(__file__).resolve().parents[2] / "new-chrome-extension"
API = os.environ.get("SRO_API_URL", "http://localhost:8000")
TENANT = os.environ.get("SRO_TENANT", "rigproof")
CLIENT_CODE = "ACME-4471"

PAGE = """<!doctype html>
<html><body>
  <h1>Depot</h1>
  <form id="f">
    <label for="client">Client Code</label>
    <input id="client" name="clientCode" type="text">
    <button id="save" type="button">Save</button>
  </form>
  <script>
    // The component registry this WMS is built out of, as far as the recorder
    // reaches into it: `ui.perform`'s strongest locator asks
    // `Ext.ComponentQuery.query`, and the recorder reads `getCmp` for the
    // itemId and the field label. Same shape as the browser suite's fixture.
    window.Ext = {
      ComponentQuery: {
        query: (q) => {
          const byQuery = {
            'panel#clients textfield#clientCode': 'client',
            'panel#clients button#saveButton': 'save',
          };
          const id = byQuery[q];
          const dom = id ? document.getElementById(id) : null;
          return dom ? [{isVisible: () => true, el: {dom}, inputEl: {dom}}] : [];
        },
      },
      getCmp: (id) => ({
        'client': {xtype: 'textfield', itemId: 'clientCode', name: 'clientCode',
                   fieldLabel: 'Client Code',
                   ownerCt: {xtype: 'panel', itemId: 'clients'}},
        'save': {xtype: 'button', itemId: 'saveButton', text: 'Save',
                 ownerCt: {xtype: 'panel', itemId: 'clients'}},
      })[id] || null,
    };
    document.getElementById('save').addEventListener('click', async () => {
      // A real mutation with a real status, because that is what makes the
      // step a write: `writes()` reads the cited evidence's own call.
      await fetch('/api/orders', {
        method: 'POST',
        headers: {'content-type': 'application/json'},
        body: JSON.stringify({clientCode: document.getElementById('client').value}),
      });
      document.getElementById('f').insertAdjacentHTML(
        'afterend', '<p id="saved">Saved ' + document.getElementById('client').value + '</p>');
      window.__done = true;
    });
  </script>
</body></html>
"""


class _Depot(BaseHTTPRequestHandler):
    """The page the work happens on, and the one call it makes."""

    protocol_version = "HTTP/1.1"

    def log_message(self, *_: Any) -> None:
        return

    def _send(self, code: int, body: bytes, kind: str) -> None:
        self.send_response(code)
        self.send_header("content-type", kind)
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        self._send(200, PAGE.encode(), "text/html; charset=utf-8")

    def do_POST(self) -> None:
        length = int(self.headers.get("content-length") or 0)
        self.rfile.read(length)
        # 201, which is what every real create in both stores came back with.
        self._send(201, b'{"ok": true}', "application/json")


def call(path: str, token: str, body: dict[str, Any] | None = None) -> Any:
    # S310: every url is built from this file's own constants.
    request = urllib.request.Request(  # noqa: S310
        f"{API}{path}",
        data=None if body is None else json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method="GET" if body is None else "POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as answer:  # noqa: S310
            return json.loads(answer.read() or b"null")
    except urllib.error.HTTPError as refused:
        raise SystemExit(f"{path} answered {refused.code}: {refused.read()[:300]!r}") from refused


def _worker(context: Any) -> Any:
    return (
        context.service_workers[0]
        if context.service_workers
        else context.wait_for_event("serviceworker")
    )


def _ask(context: Any, worker: Any, message: dict[str, Any]) -> Any:
    page = context.new_page()
    page.goto(f"{worker.url.rsplit('/src/', 1)[0]}/src/options/options.html")
    answer = page.evaluate("async (message) => await chrome.runtime.sendMessage(message)", message)
    page.close()
    return answer


def _watch_this_tab(context: Any, worker: Any, page: Any) -> None:
    """Nothing is captured from a tab nobody pointed at."""
    page.bring_to_front()
    tab_id = worker.evaluate(
        "async () => (await chrome.tabs.query({active: true, lastFocusedWindow: true}))[0]?.id"
    )
    if tab_id is None:
        raise SystemExit("no active tab to watch")
    answer = _ask(context, worker, {"kind": "watch-tab", "tabId": tab_id})
    if "error" in answer:
        raise SystemExit(f"could not watch that tab: {answer}")


def _mint(tenant: str) -> str:
    import contextlib
    import io

    from sro.cli.mint import main as mint

    caught = io.StringIO()
    with contextlib.redirect_stdout(caught):
        mint([tenant, "one_whole_run", "--days", "1"])
    return caught.getvalue().strip()


async def _build_workflow(tenant: str, page_origin: str) -> str:
    """A two-step job standing on the two gestures just recorded.

    Built here rather than mined, deliberately. `mining_pass.mine` is proven on
    both real corpora and costs a 150K-token call; what this script is for is
    the half nothing has ever exercised, which is downstream of it. A
    hand-built workflow citing real gestures reaches `run_workflow` through
    exactly the same door a mined one does.
    """
    from sro.container import build_container
    from sro.domain.shared.identifiers import TenantId
    from sro.domain.skill.workflow import Step, Workflow

    container = build_container()
    tenant_id = TenantId(tenant)
    # The upload is a flush plus a round trip, so the evidence is not there the
    # instant the click returns. Waited for rather than slept on: a fixed sleep
    # is either a slow script or a flaky one, and there is no version of it
    # that is neither.
    typed = saved = None
    gestures: list[Any] = []
    for _ in range(40):
        async with container.unit_of_work() as uow:
            everything = await uow.gestures.gestures_for(tenant_id)
        # This depot and this doing. A previous run of this script left its own
        # gestures in the store on its own port, and taking the first match
        # built a job whose origin no tab was open on -- which is exactly the
        # refusal `run_workflow` gave: "no tab is open on 127.0.0.1:57647".
        # Newest first, and only from the page this run is driving.
        gestures = [
            gesture
            for gesture in reversed(everything)
            if gesture.action.target and (gesture.page_url or gesture.url).startswith(page_origin)
        ]
        typed = next(
            (g for g in gestures if g.action.kind == "type" and g.action.value == CLIENT_CODE),
            None,
        )
        saved = next(
            (
                g
                for g in gestures
                if g.action.kind == "click"
                and g.action.target is not None
                and g.action.target.component is not None
                and g.action.target.component.item_id == "saveButton"
            ),
            None,
        )
        if typed is not None and saved is not None:
            break
        await asyncio.sleep(0.5)
    if typed is None or saved is None:
        raise SystemExit(
            f"the browser recorded {len(gestures)} gesture(s) and not the two this needs:"
            f" typed={typed is not None} saved={saved is not None}"
        )
    async with container.unit_of_work() as uow:
        workflow = Workflow(
            id=f"wfl_proof_{int(time.time())}",
            tenant=tenant,
            title="Create a client",
            narrative="Type the client code into the depot form and save it.",
            systems=[page_origin],
            steps=[
                Step(
                    order=1,
                    says="Type the client code into the Client Code field.",
                    system=page_origin,
                    cites=[typed.id],
                    parameters=["clientCode"],
                ),
                Step(order=2, says="Click Save.", system=page_origin, cites=[saved.id]),
            ],
            parameters=[{"name": "clientCode", "seen_values": [CLIENT_CODE]}],
        )
        await uow.workflows.save(workflow)
        await uow.commit()
    return workflow.id


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tenant", default=TENANT)
    parser.add_argument("--port", type=int, default=63319, help="where the depot is served")
    parser.add_argument("--headed", action="store_true", help="watch it happen")
    parser.add_argument("--keep", action="store_true", help="leave the browser open at the end")
    args = parser.parse_args()

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:  # pragma: no cover - environment
        print("playwright is not installed here")
        return 1

    # A fixed port, so every run of this script leaves evidence on one origin
    # rather than scattering a job's worth across a new one each time.
    server = ThreadingHTTPServer(("127.0.0.1", args.port), _Depot)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    depot = f"http://127.0.0.1:{server.server_address[1]}"
    print(f"-- the work happens on {depot}")

    token = _mint(args.tenant)
    print(f"-- credential for {args.tenant}: {token[:12]}…")

    with sync_playwright() as play:
        profile = Path("/tmp/one-whole-run-profile")
        context = play.chromium.launch_persistent_context(
            str(profile),
            headless=not args.headed,
            channel="chromium",
            args=[f"--disable-extensions-except={EXTENSION}", f"--load-extension={EXTENSION}"],
        )
        try:
            worker = _worker(context)
            status = _ask(
                context,
                worker,
                {
                    "kind": "sign-in",
                    "apiUrl": API,
                    "consoleUrl": "",
                    "token": token,
                    "label": "one-whole-run",
                },
            )
            device = status.get("deviceId")
            if not status.get("capturing") or not device:
                raise SystemExit(f"the extension did not sign in: {status}")
            print(f"-- the extension registered as {device}")

            page = context.new_page()
            page.goto(depot)
            _watch_this_tab(context, worker, page)

            # The work, done by hand in a real browser.
            page.fill("#client", CLIENT_CODE)
            page.click("#save")
            page.wait_for_function("() => window.__done === true", timeout=15_000)
            _ask(context, worker, {"kind": "flush"})
            print("-- the work was done and the evidence flushed")

            # In a thread of its own: Playwright's sync API runs inside its own
            # event loop, and `asyncio.run` refuses to start a second one
            # there. The thread gets a clean loop and the container's
            # connections are opened and closed inside it.
            with ThreadPoolExecutor(max_workers=1) as pool:
                workflow_id = pool.submit(
                    lambda: asyncio.run(_build_workflow(args.tenant, depot))
                ).result()
            print(f"-- a job now stands on that evidence: {workflow_id}")

            run = call(
                "/v1/workflow-runs",
                token,
                {
                    "workflow_id": workflow_id,
                    "device_id": device,
                    "values": {"clientCode": "ENVEYO-9"},
                    "live": False,
                },
            )
            print(f"-- run {run['id']} started; the browser is being driven")

            for _ in range(120):
                run = call(f"/v1/workflow-runs/{run['id']}", token)
                if run["outcome"] != "running":
                    break
                # Playwright's own loop has to keep turning or the page the run
                # is driving never repaints.
                page.wait_for_timeout(500)

            print(f"\n== outcome: {run['outcome']}")
            for step in run["steps"]:
                print(
                    f"   step {step['order']}: {step['verdict']}"
                    f" by {step.get('verdict_by')} -- {step.get('reason')}"
                )
            for held_back in run["withheld"]:
                # `step`, not `order`: `_withheld` names the step under the key
                # a person reading the panel sees.
                print(
                    f"   withheld from step {held_back.get('step')}:"
                    f" {held_back.get('method')} {held_back.get('url')}"
                )
            if args.keep:
                input("-- press return to close the browser")
            return 0 if run["outcome"] == "held" else 2
        finally:
            context.close()
            server.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
