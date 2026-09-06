"""The whole loop against a fake browser: door, planner, channel, verifier, record.

Task 10 step 1. Every one of the store's workflows is started dry over
`POST /v1/runs`, driven by a browser that answers every look and every perform
as a success and by a model that is not a model. What this proves is the chain
and the record it leaves; what it cannot prove is a real browser, a real WMS,
or a real plan -- those are the operator's run, written down in
`docs/new-agent-doc-arc/findings.md` under *A run performs*.

Runs against a COPY of `rig.db` in a temp directory, made with SQLite's own
backup so the copy is consistent with whatever the live file's WAL holds. The
live store is opened read-only and never written: it holds no runs and must
still hold none afterwards, which the last line checks.

    uv run python scripts/dry_run.py
"""

import asyncio
import base64
import json
import sqlite3
import sys
import tempfile
from collections.abc import Mapping
from contextlib import closing
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import httpx

from rig.api import build_app
from rig.channel import Answer as Reply
from rig.channel import FakeChannel
from rig.config import settings
from rig.locators import allowlist, primary_gesture, recorded_call, writes
from rig.models import Answer, Effort
from rig.records import Gesture
from rig.runner import _gestures_for
from rig.store import Store
from rig.wire import REDACTED
from rig.workflows import Workflow, known_workflows

TOKEN = "dry-run-not-a-secret"
DEVICE = "dev_test"  # what FakeChannel.online() answers
# The live rig's own tenant and store, from `.env`, so this script reads what
# the operator's rig reads rather than a second opinion about where it is.
TENANT = settings().tenant
LIVE_DB = Path(settings().db_path)

# 1x1 transparent PNG. The verifier needs a picture to exist, not to say
# anything: with no screenshot it answers `unclear` and the run stops.
PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


class Browser(FakeChannel):
    """A browser that is always where the step expects it and always succeeds.

    `page` is the screen the job under way was demonstrated on -- what the
    runner calls `starts_on` -- set before each run so `ui.url` answers a real
    address rather than a bare origin.

    `FakeChannel`'s script is a finite queue; a whole run needs an answer for
    every command it happens to send, so this answers by kind instead. Super is
    still called for its record of every envelope sent.
    """

    page = "about:blank"

    async def send(
        self,
        device_id: str,
        *,
        kind: str,
        payload: Mapping[str, object],
        run_id: str | None = None,
        deadline_s: float | None = None,
    ) -> Reply:
        await super().send(
            device_id, kind=kind, payload=payload, run_id=run_id, deadline_s=deadline_s
        )
        if kind == "ui.url":
            return Reply(ok=True, result={"url": self.page})
        if kind == "screenshot":
            return Reply(
                ok=True,
                result={
                    "image_base64": base64.b64encode(PNG).decode(),
                    "text_digest": "a fake browser: this screen is not real",
                },
            )
        if kind == "ui.perform":
            return Reply(ok=True, result={"performed": True, "matched_by": "component"})
        if kind == "http.send":
            return Reply(ok=True, result={"status": 200, "body": "{}", "headers": {}})
        return Reply(ok=True, result={})


class Model:
    """Not a model. Plans `ui.perform` with the primary gesture's own kind --
    `action: null`, which `planner.plan_step` falls back from -- and holds
    every verification. No call leaves the process and nothing is billed."""

    def __init__(self) -> None:
        self.asked = 0

    async def ask(
        self,
        *,
        model: str,
        instructions: str,
        evidence: str,
        schema: dict[str, Any],
        image: bytes | None = None,
        effort: Effort | None = None,
    ) -> Answer:
        await asyncio.sleep(0)
        self.asked += 1
        if "held" in schema["properties"]:
            return Answer(data={"held": True, "why": "a dry run against a fake browser"})
        return Answer(
            data={"kind": "ui.perform", "action": None, "value": None, "url": None, "why": "dry"}
        )


# What a withheld write actually is. Checked in order: a performance batch
# lives under the same `/wm/` path as the mutations and is not one.
INCIDENTAL = (
    ("sessionKeepAlive", "a session keep-alive"),
    ("webPerformanceEntries", "a performance-entry batch"),
    ("analytics.google.com", "an analytics beacon"),
    ("/v1/recordings/", "the recorder's own finish call"),
)


def what_it_is(url: str) -> str:
    for mark, says in INCIDENTAL:
        if mark in url:
            return says
    return "a WMS mutation" if "/wm/" in url else "an uncategorised call"


def unreached(
    workflow: Workflow, run: Mapping[str, Any], by_id: Mapping[str, Gesture]
) -> tuple[int, list[str]]:
    """Steps the run never got to, and the mutation each of those carries, as
    `METHOD host/path`. A run that stops early withholds only what it reached;
    the rest are writes nobody has been shown, which is the difference between
    "this job has no writes" and "this run did not get that far" -- and naming
    them is the difference between a count and something a reader can check.

    No query string: these urls carry session ids and cache-busters, and the
    one thing this line has to answer is which call it is.
    """
    done = {step["order"] for step in run["steps"]}
    rest = [step for step in workflow.steps if step.order not in done]
    named: list[str] = []
    for step in rest:
        call = recorded_call(step, by_id) if writes(step, by_id) else None
        if call is not None:
            where = urlsplit(call.url)
            named.append(f"{call.method.upper()} {where.netloc}{where.path}")
    return len(rest), named


def values_for(workflow: Workflow) -> dict[str, str]:
    """What the page's form prefills: each declared parameter's last seen
    value. `POST /v1/runs` 400s on a declared parameter with no value."""
    given: dict[str, str] = {}
    for parameter in workflow.parameters:
        name = parameter.get("name")
        seen = parameter.get("seen_values") or []
        if name:
            given[str(name)] = str(seen[-1]) if seen else ""
    return given


async def one_run(client: httpx.AsyncClient, workflow: Workflow) -> dict[str, Any]:
    started = await client.post(
        "/v1/runs",
        json={
            "workflow_id": workflow.id,
            "values": values_for(workflow),
            "live": False,
            "device_id": DEVICE,
            "allow_focus": True,
            "started_by": "scripts/dry_run.py",
        },
    )
    started.raise_for_status()
    run_id = started.json()["run_id"]
    for _ in range(20_000):
        await asyncio.sleep(0.001)
        got = await client.get(f"/v1/runs/{run_id}")
        got.raise_for_status()
        run: dict[str, Any] = got.json()
        if run["outcome"] != "running":
            return run
    raise TimeoutError(f"{run_id} never finished")


def spent(run: Mapping[str, Any]) -> str:
    """A run with no tokens did not ask a model, and saying `$0.0000` about it
    reads as a call that was free. It was not made."""
    if not (run["in_tokens"] or run["out_tokens"]):
        return "not asked"
    return f"${run['cost_usd']:.4f}" + ("?" if run["unpriced"] else "")


def tally(run: Mapping[str, Any]) -> str:
    counts: dict[str, int] = {}
    for step in run["steps"]:
        counts[step["verdict"]] = counts.get(step["verdict"], 0) + 1
    return " ".join(f"{verdict}:{n}" for verdict, n in sorted(counts.items())) or "-"


async def main() -> int:
    with tempfile.TemporaryDirectory() as scratch:
        copy = Path(scratch) / "rig.db"
        with (
            closing(sqlite3.connect(f"file:{LIVE_DB}?mode=ro", uri=True)) as live,
            closing(sqlite3.connect(copy)) as backup,
        ):
            live.backup(backup)
        store = Store(copy)
        store.migrate()
        app = build_app(
            store=store, asker=Model(), token=TOKEN, tenant=TENANT, read_on_ingest=False
        )
        app.state.channel = Browser()
        workflows = known_workflows(store, TENANT)

        # The same map the runner builds, for the questions a run's record
        # cannot answer on its own: what a step it never reached would have
        # sent, and which origins the job's evidence names.
        cited = {w.id: _gestures_for(store, w) for w in workflows}
        runs: list[tuple[Workflow, dict[str, Any]]] = []
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://rig",
            headers={"Authorization": f"Bearer {TOKEN}"},
        ) as client:
            devices = (await client.get("/v1/devices")).json()["devices"]
            print(f"the rig sees these browsers: {devices}\n")
            # Asked before a single run is started, so the per-workflow held
            # gate reads a store with no runs in it: a workflow that has never
            # run is served, and only an unproven one is withheld. Printed
            # further down, after the allowlists.
            served: list[dict[str, Any]] = (await client.get("/v1/shapes")).json()["shapes"]
            for workflow in workflows:
                first = primary_gesture(workflow.steps[0], cited[workflow.id])
                app.state.channel.page = (
                    (first.page_url or first.url or "about:blank") if first else "about:blank"
                )
                runs.append((workflow, await one_run(client, workflow)))

        print(f"{'workflow':44} {'steps':>5} {'withheld':>8} {'outcome':>8} {'cost':>10}  verdicts")
        print("-" * 110)
        for workflow, run in runs:
            print(
                f"{workflow.title[:44]:44} {len(run['steps']):>5}"
                f" {len(run['withheld']):>8} {run['outcome']:>8} {spent(run):>10}  {tally(run)}"
            )
        steps = sum(len(run["steps"]) for _, run in runs)
        withheld = sum(len(run["withheld"]) for _, run in runs)
        outcomes: dict[str, int] = {}
        for _, run in runs:
            outcomes[run["outcome"]] = outcomes.get(run["outcome"], 0) + 1
        print("-" * 110)
        for workflow, run in runs:
            # Why a run stopped is the one thing a table cannot hold and the
            # first thing a person asks.
            stopper = next(
                (s for s in run["steps"] if s["verdict"] not in ("held", "withheld")), None
            )
            if stopper is not None:
                left, mutating = unreached(workflow, run, cited[workflow.id])
                print(
                    f"  {workflow.title[:44]}: stopped at step {stopper['order']}"
                    f" of {len(workflow.steps)} ({stopper['verdict']}) -- {stopper['reason']};"
                    f" {left} later step(s) never reached,"
                    f" {len(mutating)} of them carry a recorded mutation"
                )
                for call in mutating:
                    print(f"      never withheld, never shown: {call}")
        print(
            f"{len(runs)} workflows / {steps} steps / {withheld} withheld /"
            f" {' '.join(f'{k}:{n}' for k, n in sorted(outcomes.items()))}"
        )
        print(
            "cost: no model was asked. Every plan and every verdict came from a fake in the"
            " same process, so these records carry no tokens -- the absence of a bill, not a"
            " cheap run."
        )

        # The writes a dry run did not send, whole. Nothing here is a token: a
        # withheld record carries no headers at all, the store was redacted at
        # its boundary, and anything a plan does send is filtered through
        # `wire.headers_without_markers` first. A marker that survives into a
        # body below is printed as it stands and counted.
        print("\n\nWHAT WAS WITHHELD -- what a person reads before pressing through to live")
        markers = 0
        kinds: dict[str, int] = {}
        for workflow, run in runs:
            print(f"\n=== {workflow.title}  ({workflow.id})")
            if not run["withheld"]:
                left, mutating = unreached(workflow, run, cited[workflow.id])
                reached = len(workflow.steps) - left
                print(
                    f"    nothing withheld: of the {reached} step(s) this run reached,"
                    f" none carries a recorded mutation"
                    + (
                        f"; not so for {len(mutating)} of the {left} it never reached"
                        if mutating
                        else ""
                    )
                )
                for call in mutating:
                    print(f"    never withheld, never shown: {call}")
            for held_back in run["withheld"]:
                what = what_it_is(str(held_back.get("url") or ""))
                kinds[what] = kinds.get(what, 0) + 1
                shown = json.dumps(held_back, indent=4, ensure_ascii=False)
                markers += shown.count(REDACTED)
                print(f"-- {what}")
                print(shown)
        print(
            f"\n{withheld} withheld writes: "
            + ", ".join(f"{n} x {what}" for what, n in sorted(kinds.items()))
        )
        print(f"redaction markers in the withheld writes: {markers}")

        # Which origins a run may reach at all: the job's own cited evidence and
        # nothing else. What a `refused` step would be measured against.
        print("\n\nALLOWLISTS -- the origins each job's own evidence names")
        alone = 0
        for workflow in workflows:
            origins = sorted(allowlist(workflow, cited[workflow.id]))
            alone += len(origins) == 1
            print(f"\n{workflow.title}: {len(origins)} origin(s)")
            for origin in origins:
                print(f"    {origin}")
        print(
            f"\n{alone} of {len(workflows)} workflows allow one origin and nothing else;"
            f" {len(workflows) - alone} allow more than one."
        )

        # What the extension is handed to match a live tail against: control
        # identities, hosts and parameter *names* with the index each was typed
        # at. No typed value is in a shape, so no line below can be a secret.
        print("\n\nSHAPES -- what the extension matches a live tail against")
        print(f"\nshapes served: {len(served)} of {len(workflows)} workflows")
        # `recognise.js`'s `tailWith` drops a scroll before the tail is
        # written, so a served shape whose prefix holds one can never be
        # matched against a live tail. The comparison below is therefore made
        # on the shape with its scrolls removed -- which is what the rig will
        # serve once `shapes.py` drops them too.
        scrollless = {
            shape["id"]: [t for t in shape["shape"] if t[1] != "anon|scroll"] for shape in served
        }
        for shape in served:
            named = ", ".join(f"{p['name']}@{p['at']}" for p in shape["parameters"])
            walkable = scrollless[shape["id"]]
            print(
                f"\n{shape['title']}: {len(shape['shape'])} triples,"
                f" {len(walkable)} without scrolls;"
                f" parameters: {named or 'none declared'}"
            )
            # `match()` is JavaScript; this is its K_OFFER_AFTER = 2 test in
            # Python. Two jobs sharing their first two triples cannot be told
            # apart by the tail the card is offered on.
            twins = [
                other["title"]
                for other in served
                if other["id"] != shape["id"] and scrollless[other["id"]][:2] == walkable[:2]
            ]
            print(
                f"    shares its first two steps with: {', '.join(twins)}"
                if twins
                else "    distinct at two"
            )

    with closing(sqlite3.connect(f"file:{LIVE_DB}?mode=ro", uri=True)) as live:
        left = live.execute("SELECT count(*) FROM runs").fetchone()[0]
    print(f"runs in the live {LIVE_DB.name} after this script: {left}")
    return 0 if left == 0 else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
