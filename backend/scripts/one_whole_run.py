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
from typing import Any, ClassVar

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
      // The read a page performs to show what it just saved. Not decoration:
      // `confirming_read` is what lets `verify` reach rung 2 and settle a
      // write by STATE rather than by a picture, and only a state belt's
      // verdict is an effect a job can earn autonomy with. A page that never
      // reads back can be driven correctly forever and never earn anything.
      const back = await fetch('/api/orders?latest=1');
      const saved = await back.json();
      document.getElementById('f').insertAdjacentHTML(
        'afterend', '<p id="saved">Saved ' + saved.clientCode + '</p>');
      window.__done = true;
    });
  </script>
</body></html>
"""


class _Depot(BaseHTTPRequestHandler):
    """The page the work happens on, and the one call it makes."""

    protocol_version = "HTTP/1.1"

    writes: ClassVar[list[str]] = []
    """Every mutation this depot was actually sent. The operator's own doing is
    the first; anything after it came from the run, which is the only evidence
    that a write really went out rather than being reported as though it had."""

    def log_message(self, *_: Any) -> None:
        return

    def _send(self, code: int, body: bytes, kind: str) -> None:
        self.send_response(code)
        self.send_header("content-type", kind)
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path.startswith("/api/orders"):
            latest = json.loads(_Depot.writes[-1]) if _Depot.writes else {}
            self._send(200, json.dumps(latest).encode(), "application/json")
            return
        self._send(200, PAGE.encode(), "text/html; charset=utf-8")

    def do_POST(self) -> None:
        length = int(self.headers.get("content-length") or 0)
        body = self.rfile.read(length)
        _Depot.writes.append(body.decode("utf-8", "replace"))
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


def _approve_in_the_panel(context: Any, worker: Any, run_id: str) -> None:
    """Press Approve, in the real panel, as this browser.

    The half nothing in this repository had ever exercised. A parked run is a
    live Chrome holding a warehouse write open, and every approval this system
    has recorded was tapped with the tenant's bare credential naming no browser
    -- the supervisor's-console path, which skips `approver_is_the_driver`
    entirely. This is the other one: the panel never holds the rig's bearer, so
    the press goes to the worker, which sends the run id with this device's own
    `?device_id=` and `X-Device-Secret`.

    Through the button rather than the message behind it. `run-card.js` draws
    Approve only on a step whose outcome is `awaiting` AND only while the run is
    live, and the panel only draws the card at all once the worker has adopted
    the run -- `commands.js` writes `source: "rig"` for every command arriving
    on the rig's channel, whoever started it. Sending `approve-rig-run` by hand
    would prove the backend door and skip every one of those.
    """
    panel = context.new_page()
    panel.goto(f"{worker.url.rsplit('/src/', 1)[0]}/src/panel/panel.html")
    approve = panel.get_by_role("button", name="Approve")
    try:
        approve.wait_for(timeout=90_000)
    except Exception as never:
        panel.close()
        raise SystemExit(
            f"the panel never offered Approve for {run_id}; the run parked somewhere"
            f" the panel could not see it: {never}"
        ) from never
    print("-- the panel is asking; pressing Approve as this browser")
    approve.click()
    # Left open: the panel polls the run, and closing it here would take the
    # only thing watching the write it just let out.
    return


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
    parser.add_argument(
        "--runs",
        type=int,
        default=1,
        help="how many times to do the job. K_EARNED_RUNS live runs whose every"
        " write a state belt verified is what retires the approval tap, so"
        " --live --runs 4 is the whole ladder: three taps, then none.",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="let the write out, after a person presses Approve in the panel",
    )
    parser.add_argument("--keep", action="store_true", help="leave the browser open at the end")
    parser.add_argument(
        "--via-trigger",
        action="store_true",
        help="start each run by firing a trigger that names the job, rather than by"
        " pressing /v1/workflow-runs. Always live: a trigger's job is started live"
        " because a dry scheduled run sends nothing and verifies nothing.",
    )
    args = parser.parse_args()
    if args.via_trigger:
        # Not a flag the mode respects -- a job a trigger starts is started
        # live, always. Said here rather than silently overridden.
        args.live = True

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

            worst = 0
            for attempt in range(args.runs):
                # The operator's own doing is the first write this depot saw.
                # Anything after it came from a run.
                by_hand = len(_Depot.writes)
                value = f"ENVEYO-{attempt + 1}"

                if args.via_trigger:
                    # The whole point of this mode: nothing here says
                    # "workflow-runs". A trigger names the job, the device and
                    # the values, and firing it is all this script does. What
                    # starts the run is `FireTrigger` -> `start_job_for` ->
                    # the dispatcher -> the API's own door, which is the path
                    # a schedule at 3am takes with nobody in the room.
                    trigger = call(
                        "/v1/triggers",
                        token,
                        {
                            "workflow_id": workflow_id,
                            "kind": "manual",
                            "device_id": device,
                            "parameters": {"clientCode": value},
                            # A job is a write by the honest reading, so it
                            # needs a name behind it; `auto_approve` is about
                            # the CARD, not about the run's own approval tap,
                            # which is still pressed in the panel below.
                            "authorized_by": True,
                            "auto_approve": True,
                            "may_take_focus": True,
                        },
                    )
                    fired = call(f"/v1/triggers/{trigger['id']}/fire", token, {})
                    if fired.get("skipped") or not fired.get("run_id"):
                        raise SystemExit(f"the trigger started nothing: {fired}")
                    print(
                        f"\n-- run {attempt + 1} of {args.runs}: fired trigger"
                        f" {trigger['id']} -> {fired['run_id']}, asking for {value}"
                    )
                    run = call(f"/v1/workflow-runs/{fired['run_id']}", token)
                else:
                    run = call(
                        "/v1/workflow-runs",
                        token,
                        {
                            "workflow_id": workflow_id,
                            "device_id": device,
                            "values": {"clientCode": value},
                            "live": args.live,
                        },
                    )
                    print(
                        f"\n-- run {attempt + 1} of {args.runs}: {run['id']}"
                        f" {'live' if args.live else 'dry'}, asking for {value}"
                    )

                tapped = False
                for _ in range(240):
                    run = call(f"/v1/workflow-runs/{run['id']}", token)
                    if run["outcome"] != "running":
                        break
                    # A live run parks on the write and waits for a person.
                    # This is the person -- until the job has EARNED the right
                    # to write unasked, at which point nothing parks and this
                    # never fires. That is the whole ladder, and the only way
                    # to see it is to run the same job until it climbs.
                    if (
                        args.live
                        and not tapped
                        and any(s["verdict"] == "awaiting" for s in run["steps"])
                    ):
                        _approve_in_the_panel(context, worker, run["id"])
                        tapped = True
                    # Playwright's own loop has to keep turning or the page the
                    # run is driving never repaints.
                    page.wait_for_timeout(500)

                print(f"== outcome: {run['outcome']}" + ("" if tapped else "  (nobody was asked)"))
                for step in run["steps"]:
                    print(
                        f"   step {step['order']}: {step['verdict']}"
                        f" by {step.get('verdict_by')} -- {step.get('reason')}"
                    )
                for held_back in run["withheld"]:
                    # `step`, not `order`: `_withheld` names the step under the
                    # key a person reading the panel sees.
                    print(
                        f"   withheld from step {held_back.get('step')}:"
                        f" {held_back.get('method')} {held_back.get('url')}"
                    )
                sent = _Depot.writes[by_hand:]
                print(
                    f"   writes the depot actually received from the run: {len(sent)}"
                    + (f" -- {sent[0]}" if sent else "")
                )
                if run["outcome"] != "held":
                    worst = 2

            if args.keep:
                input("-- press return to close the browser")
            return worst
        finally:
            context.close()
            server.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
