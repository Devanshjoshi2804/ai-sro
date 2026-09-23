from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
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
REFERENCE = "PO-88213"

PAGE = """<!doctype html>
<html><body>
  <h1>Depot</h1>
  <form id="f">
    <label for="client">Client Code</label>
    <input id="client" name="clientCode" type="text">
    <label for="reference">Reference</label>
    <input id="reference" name="reference" type="text">
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
            'panel#clients textfield#referenceCode': 'reference',
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
        'reference': {xtype: 'textfield', itemId: 'referenceCode', name: 'reference',
                      fieldLabel: 'Reference',
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
        body: JSON.stringify({
          clientCode: document.getElementById('client').value,
          reference: document.getElementById('reference').value,
        }),
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
    protocol_version = "HTTP/1.1"

    writes: ClassVar[list[str]] = []

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
        made = f"ORD-{len(_Depot.writes):04d}"
        self._send(201, json.dumps({"ok": True, "id": made}).encode(), "application/json")


def call(
    path: str, token: str, body: dict[str, Any] | None = None, *, method: str | None = None
) -> Any:
    request = urllib.request.Request(  # noqa: S310
        f"{API}{path}",
        data=None if body is None else json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method=method or ("GET" if body is None else "POST"),
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
    return


def _offered_in_the_panel(
    context: Any, worker: Any, page: Any, *, title: str, accept: bool = False
) -> str | None:
    panel = context.new_page()
    panel.goto(f"{worker.url.rsplit('/src/', 1)[0]}/src/panel/panel.html")
    asked = panel.get_by_text(re.compile(rf"{re.escape(title)}.*(finish|do) it\?"))

    for attempt in range(1, 4):
        page.goto(page.url)
        page.fill("#client", f"OFFER-{attempt}")
        page.fill("#reference", f"PO-99{attempt:03d}")
        page.click("#save")
        page.wait_for_function("() => window.__done === true", timeout=15_000)
        _ask(context, worker, {"kind": "flush"})
        try:
            asked.wait_for(timeout=20_000)
            break
        except Exception:
            pass

    made = worker.evaluate(
        "async () => ((await chrome.storage.local.get('sro.nudges'))['sro.nudges'] || [])"
        ".find((n) => n.source === 'rig') || null"
    )
    if made is None:
        panel.close()
        raise SystemExit(f"nothing was offered after doing {title!r} by hand again")
    drawn = panel.locator('li[data-kind="nudge"][data-state="open"]').count() > 0
    print(
        f"-- the worker offered {made['title']!r} off this browser's own gestures"
        f" -- matched {made['k']} gestures in, values {json.dumps(made['values'])}"
    )
    print(f"   the panel has drawn it: {drawn}")
    if accept:
        started = _accepted_in_the_panel(panel, made)
        panel.close()
        return started
    if not accept and made.get("missing"):
        walk = worker.evaluate(
            "async () => Object.values("
            "(await chrome.storage.local.get('sro.tails'))['sro.tails'] || {})[0] || []"
        )
        print(f"   and it has to ask for: {', '.join(made['missing'])}")
        print(f"   the walk it matched ended: {json.dumps(walk[-4:])}")
    panel.close()
    return None


def _accepted_in_the_panel(panel: Any, made: dict[str, Any]) -> str:
    card = panel.locator('li[data-kind="nudge"][data-state="open"]').first
    try:
        card.wait_for(timeout=15_000)
    except Exception as never:
        where = panel.evaluate(
            "async () => {"
            " const [a] = await chrome.tabs.query({active: true, currentWindow: true});"
            " const all = await chrome.tabs.query({currentWindow: true});"
            " return {active: a ? {id: a.id, url: (a.url || '').slice(0, 50)} : null,"
            "         tabs: all.map((t) => ({id: t.id, url: (t.url || '').slice(0, 40)}))};"
            "}"
        )
        raise SystemExit(
            f"the offer is in storage for tab {made.get('tabId')} and the panel drew"
            f" no open card. Its window holds: {json.dumps(where)}"
        ) from never
    boxes = card.locator("input")
    for index in range(boxes.count()):
        box = boxes.nth(index)
        asked = box.get_attribute("placeholder") or f"field {index}"
        box.fill(f"ACCEPTED-{index + 1}")
        print(f"   the card asked for {asked}, and it is typed in")
    yes = card.get_by_role("button", name=re.compile(r"Yes, (finish|do) it"))
    yes.wait_for(timeout=10_000)
    print("-- pressing Yes in the panel, as the browser the offer was made to")
    yes.click()
    note = panel.locator("#thread-note, .said, #note").first
    for _ in range(60):
        text = (note.text_content() or "") if note.count() else ""
        if "started" in text or "nothing started" in text:
            print(f"   the panel says: {text.strip()!r}")
            break
        panel.wait_for_timeout(500)
    started = panel.evaluate(
        "async () => (await chrome.storage.local.get('sro.activeRun'))['sro.activeRun']"
    )
    if not started or not started.get("runId"):
        raise SystemExit("the press started nothing this browser is driving")
    print(f"-- the offer was accepted and it started {started['runId']}")
    return str(started["runId"])


def _watch(
    context: Any,
    worker: Any,
    page: Any,
    token: str,
    run_id: str,
    by_hand: int,
    live: bool,
) -> int:
    run: dict[str, Any] = {"outcome": "running", "steps": []}
    tapped = False
    for _ in range(240):
        run = call(f"/v1/workflow-runs/{run_id}", token)
        if run["outcome"] != "running":
            break
        if live and not tapped and any(s["verdict"] == "awaiting" for s in run["steps"]):
            _approve_in_the_panel(context, worker, run_id)
            tapped = True
        page.wait_for_timeout(500)

    print(f"== outcome: {run['outcome']}" + ("" if tapped else "  (nobody was asked)"))
    for step in run["steps"]:
        print(
            f"   step {step['order']}: {step['verdict']}"
            f" by {step.get('verdict_by')} -- {step.get('reason')}"
        )
    for held_back in run["withheld"]:
        print(
            f"   withheld from step {held_back.get('step')}:"
            f" {held_back.get('method')} {held_back.get('url')}"
        )
    sent = _Depot.writes[by_hand:]
    print(
        f"   writes the depot actually received from the run: {len(sent)}"
        + (f" -- {sent[0]}" if sent else "")
    )
    return 2 if run["outcome"] != "held" else 0


def _fired_by_the_worker(
    token: str, workflow_id: str, device: str, value: str, page: Any
) -> dict[str, Any]:
    trigger = call(
        "/v1/triggers",
        token,
        {
            "workflow_id": workflow_id,
            "kind": "schedule",
            "cron": "* * * * *",
            "device_id": device,
            "parameters": {"clientCode": value, "reference": REFERENCE},
            "authorized_by": True,
            "auto_approve": True,
            "may_take_focus": True,
        },
    )
    print(f"\n-- on a clock: trigger {trigger['id']} every minute, asking for {value}")
    print("   nothing in this script will start it; the worker has to")
    try:
        for _ in range(180):
            runs = call(f"/v1/workflow-runs?workflow_id={workflow_id}&limit=5", token)
            if runs:
                started = runs[0]
                print(f"-- the worker started {started['id']} by itself")
                return dict(started)
            page.wait_for_timeout(1000)
        raise SystemExit(
            "the worker never fired it. `make status` says which commit it is on:"
            " a worker older than `start_job` skips a job trigger every time"
        )
    finally:
        call(f"/v1/triggers/{trigger['id']}", token, None, method="DELETE")
        print(f"   the schedule is removed: {trigger['id']}")


def _mint(tenant: str) -> str:
    import contextlib
    import io

    from sro.cli.mint import main as mint

    caught = io.StringIO()
    with contextlib.redirect_stdout(caught):
        mint([tenant, "one_whole_run", "--days", "1"])
    return caught.getvalue().strip()


async def _build_workflow(tenant: str, page_origin: str) -> str:
    from sro.container import build_container
    from sro.domain.shared.identifiers import TenantId
    from sro.domain.skill.workflow import Step, Workflow

    container = build_container()
    tenant_id = TenantId(tenant)
    typed = saved = None
    gestures: list[Any] = []
    for _ in range(40):
        async with container.unit_of_work() as uow:
            everything = await uow.gestures.gestures_for(tenant_id)
        gestures = [
            gesture
            for gesture in reversed(everything)
            if gesture.action.target and (gesture.page_url or gesture.url).startswith(page_origin)
        ]
        typed = next(
            (g for g in gestures if g.action.kind == "type" and g.action.value == CLIENT_CODE),
            None,
        )
        referenced = next(
            (g for g in gestures if g.action.kind == "type" and g.action.value == REFERENCE),
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
        if typed is not None and referenced is not None and saved is not None:
            break
        await asyncio.sleep(0.5)
    if typed is None or referenced is None or saved is None:
        raise SystemExit(
            f"the browser recorded {len(gestures)} gesture(s) and not the three this needs:"
            f" typed={typed is not None} referenced={referenced is not None}"
            f" saved={saved is not None}"
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
                Step(
                    order=2,
                    says="Type the reference into the Reference field.",
                    system=page_origin,
                    cites=[referenced.id],
                    parameters=["reference"],
                ),
                Step(order=3, says="Click Save.", system=page_origin, cites=[saved.id]),
            ],
            parameters=[
                {"name": "clientCode", "seen_values": [CLIENT_CODE]},
                {"name": "reference", "seen_values": [REFERENCE]},
            ],
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
        "--offer",
        action="store_true",
        help="do the same work by hand a second time and read the offer the panel"
        " makes off this browser's own gestures, before running anything",
    )
    parser.add_argument(
        "--accept",
        action="store_true",
        help="press Yes on the offer the panel makes and follow the run it starts."
        " Implies --offer, and runs nothing else: the point is that the run was"
        " started by a person answering an offer rather than by this script.",
    )
    parser.add_argument(
        "--via-schedule",
        action="store_true",
        help="put the job on a cron and wait for the Temporal worker to fire it."
        " The one link nothing has proved: the worker is not the process holding"
        " the socket to that Chrome, so it has to ask the one that does.",
    )
    parser.add_argument(
        "--via-trigger",
        action="store_true",
        help="start each run by firing a trigger that names the job, rather than by"
        " pressing /v1/workflow-runs. Always live: a trigger's job is started live"
        " because a dry scheduled run sends nothing and verifies nothing.",
    )
    args = parser.parse_args()
    if args.accept:
        args.offer = True
        args.runs = 0
    if args.via_trigger or args.via_schedule:
        args.live = True
    if args.via_schedule:
        args.runs = 1

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:  # pragma: no cover - environment
        print("playwright is not installed here")
        return 1

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

            page.fill("#client", CLIENT_CODE)
            page.fill("#reference", REFERENCE)
            page.click("#save")
            page.wait_for_function("() => window.__done === true", timeout=15_000)
            _ask(context, worker, {"kind": "flush"})
            print("-- the work was done and the evidence flushed")

            with ThreadPoolExecutor(max_workers=1) as pool:
                workflow_id = pool.submit(
                    lambda: asyncio.run(_build_workflow(args.tenant, depot))
                ).result()
            print(f"-- a job now stands on that evidence: {workflow_id}")

            if args.offer:
                accepted = _offered_in_the_panel(
                    context, worker, page, title="Create a client", accept=args.accept
                )
                if accepted is not None:
                    worst = _watch(
                        context,
                        worker,
                        page,
                        token,
                        accepted,
                        by_hand=len(_Depot.writes),
                        live=True,
                    )
                    if args.keep:
                        input("-- press return to close the browser")
                    return worst

            worst = 0
            for attempt in range(args.runs):
                by_hand = len(_Depot.writes)
                value = f"ENVEYO-{attempt + 1}"

                if args.via_schedule:
                    run = _fired_by_the_worker(token, workflow_id, device, value, page)
                elif args.via_trigger:
                    trigger = call(
                        "/v1/triggers",
                        token,
                        {
                            "workflow_id": workflow_id,
                            "kind": "manual",
                            "device_id": device,
                            "parameters": {"clientCode": value, "reference": REFERENCE},
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
                            "values": {"clientCode": value, "reference": REFERENCE},
                            "live": args.live,
                        },
                    )
                    print(
                        f"\n-- run {attempt + 1} of {args.runs}: {run['id']}"
                        f" {'live' if args.live else 'dry'}, asking for {value}"
                    )

                if _watch(context, worker, page, token, run["id"], by_hand, args.live):
                    worst = 2

            if args.keep:
                input("-- press return to close the browser")
            return worst
        finally:
            context.close()
            server.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
