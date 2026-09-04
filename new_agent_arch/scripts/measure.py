"""Task 9 — run the miner over real evidence and write down what happened.

Not part of the build and not imported by anything: an instrument. It takes a
store of already-read gestures (or ingests raw capture and reads it, which
costs money), copies it once per run so every run starts from the same
evidence, mines each copy, and prints the numbers the bet is settled on.

The number that matters is `cross-system`: how many kept workflows stand on
evidence that happened on more than one scheme+host. Everything else on the
page is context for that one line.

    RIG_GEMINI_API_KEY=... uv run python scripts/measure.py \
        --db /path/to/read/rig.db --runs 3 --model gemini-3.8-flash

`config.mine_model` is "gemini-3.1-pro", which the API rejects with a 404 --
models.list() offers only "gemini-3.1-pro-preview". Name the model here.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sqlite3
from collections import Counter
from pathlib import Path
from typing import Any

from rig.api import read_new_gestures, save_batch
from rig.mine import MineResult, mine
from rig.models import GeminiAsker
from rig.pool import pool_ids, retired_entries
from rig.store import Store
from rig.wire import parse_batch
from rig.workflows import Workflow, cited_ids, known_workflows


class Recorder:
    """Delegates to the real asker and keeps every Answer.

    The rig now stores `thought_tokens` on both `intents` and `passes` and
    /v1/spend adds them up, so this is no longer the only way to see what the
    model was paid to think. It is kept for what those tables still cannot
    say: the bill PER CALL, alongside the model that was asked, which is what
    a measurement run compares across models.
    """

    def __init__(self, inner: Any) -> None:
        self.inner = inner
        self.calls: list[tuple[str, Any]] = []

    async def ask(self, **kwargs: Any) -> Any:
        answer = await self.inner.ask(**kwargs)
        self.calls.append((kwargs["model"], answer))
        return answer

    def spent(self, since: int = 0) -> dict[str, Any]:
        """The bill for the calls made since `since`.

        `written` and `thought` are reported apart because only their sum is
        billed: a pass whose visible answer is 5,000 tokens can carry 40,000
        thought ones, and a report quoting the visible half explains nothing
        about the invoice. `unpriced_calls` is the count that says how much of
        `cost_usd` is a guess -- a model name missing from PRICES prices at
        zero, which is the one failure `cost_usd` alone cannot show.
        """
        calls = self.calls[since:]
        return {
            "calls": len(calls),
            "in_tokens": sum(a.in_tokens for _, a in calls),
            "written_tokens": sum(a.out_tokens - a.thought_tokens for _, a in calls),
            "thought_tokens": sum(a.thought_tokens for _, a in calls),
            "cost_usd": round(sum(a.cost_usd for _, a in calls), 6),
            "unpriced_calls": sum(1 for _, a in calls if a.unpriced),
        }


def ingest(store: Store, acme: Path, tenant: str) -> None:
    """Raw ndjson capture -> gestures. One file, one batch."""
    for path in sorted(acme.glob("*.ndjson")):
        events = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
        batch, rejected = parse_batch(
            {
                "batch_id": f"bat_acme_{path.stem}",
                "device_id": "dev_acme",
                # The capture's own clock is on each event; the envelope's is
                # never read again, so it only has to parse.
                "started_at": "2026-08-31T18:44:19+00:00",
                "ended_at": "2026-08-31T18:45:18+00:00",
                "mode": "passive",
                "events": events,
            }
        )
        accepted, had_it, snapshots = save_batch(store, batch, tenant, len(rejected))
        print(
            f"  {path.name}: {len(events)} events -> {accepted} gestures"
            f" (rejected {len(rejected)}, snapshots ignored {snapshots}"
            f"{', already had it' if had_it else ''})"
        )


def copy_store(src: Path, dst: Path) -> Store:
    """A byte-identical starting point per run, WAL included -- a plain file
    copy takes the database without whatever is still sitting in its WAL."""
    dst.unlink(missing_ok=True)
    source = sqlite3.connect(src)
    target = sqlite3.connect(dst)
    with target:
        source.backup(target)
    source.close()
    target.close()
    store = Store(dst)
    # The captured store predates `passes`, `pool` and `workflows`.
    store.migrate()
    return store


def keep_only(store: Store, tenant: str, prefix: str) -> int:
    """Drop every gesture not from a batch whose id starts with `prefix`.

    The captured store carries two hand-made proof gestures on a second,
    invented host. Left in, the one number this whole exercise turns on would
    be answered by evidence somebody typed.
    """
    before = store.query("SELECT count(*) AS n FROM gestures WHERE tenant = ?", (tenant,))[0]["n"]
    store.execute("DELETE FROM gestures WHERE batch_id NOT LIKE ?", (prefix + "%",))
    store.execute(
        "DELETE FROM intents WHERE gesture_id NOT IN (SELECT id FROM gestures)",
    )
    after = store.query("SELECT count(*) AS n FROM gestures WHERE tenant = ?", (tenant,))[0]["n"]
    return before - after


def systems_of(store: Store, tenant: str) -> dict[str, str]:
    return {
        row["id"]: row["system"] or ""
        for row in store.query("SELECT id, system FROM gestures WHERE tenant = ?", (tenant,))
    }


def report(
    store: Store,
    tenant: str,
    label: str,
    result: MineResult,
    kept: list[Workflow],
    systems: dict[str, str],
) -> dict[str, Any]:
    """Everything one pass is entitled to claim, and the receipts."""
    print(f"\n{'=' * 72}\n{label}\n{'=' * 72}")
    total = len(systems)
    print(f"  window        {result.window_size} of {total} gestures, {result.left_out} left out")
    if result.error:
        print(f"  ERROR         {result.error}")
    print(f"  proposed      {result.proposed}")
    print(f"  kept          {result.kept}")
    for rejection in result.rejections:
        print(
            f"  rejected      {rejection.reason}: {rejection.detail} ({rejection.workflow_title})"
        )
    for resolution in result.resolutions:
        if resolution.kind != "new":
            print(
                f"  resolved      {resolution.kind} -> {resolution.workflow_id}"
                f" (score {resolution.score:.2f}, contains={resolution.contains})"
            )

    cross = 0
    print("\n  --- what it kept ---")
    for workflow in kept:
        cites = cited_ids(workflow)
        touched = {systems[c] for c in cites if systems.get(c)}
        crossed = len(touched) > 1
        cross += crossed
        print(f"  * {workflow.title}")
        print(f"      steps {len(workflow.steps)}, cites {len(cites)}")
        print(f"      claims  {workflow.systems}")
        mark = "  <-- CROSS-SYSTEM" if crossed else ""
        print(f"      stands on {sorted(touched)}{mark}")
        if workflow.unproven:
            print(f"      unproven {len(workflow.unproven)}: {workflow.unproven[:3]}")
    print(f"\n  CROSS-SYSTEM WORKFLOWS: {cross}")

    c = result.coverage
    print(
        f"\n  coverage      {c.coverage:.2f}  skew {c.skew:+.2f}  gini {c.gini:.2f}"
        f"  lopsided={result.lopsided}"
    )

    live = pool_ids(store, tenant)
    retired = retired_entries(store, tenant)
    reasons = Counter(entry.reason for entry in retired)
    print(f"  pool          {len(live)} live, {len(retired)} retired {dict(reasons)}")
    if result.lost_pool:
        print(f"  lost pool     {result.lost_pool}")

    claimed = {c for workflow in kept for c in cited_ids(workflow)}
    accounted = claimed | set(live) | {entry.gesture_id for entry in retired}
    stranded = set(systems) - accounted
    print(f"  stranded      {len(stranded)}" + (f" {sorted(stranded)[:5]}" if stranded else ""))

    print(f"\n  tokens        {result.in_tokens} in, {result.out_tokens} out")
    print(f"  cost          ${result.cost_usd:.4f}  unpriced={result.unpriced}")
    if total:
        print(f"  per gesture   ${result.cost_usd / total:.6f}")
    return {
        "label": label,
        "cross": cross,
        "kept": result.kept,
        "proposed": result.proposed,
        "cost": result.cost_usd,
        "in": result.in_tokens,
        "out": result.out_tokens,
        "coverage": c.coverage,
        "skew": c.skew,
        "gini": c.gini,
        "shapes": [tuple(tuple(e) for e in w.shape_key) for w in kept],
        "cited": claimed,
        "titles": [w.title for w in kept],
    }


async def run(args: argparse.Namespace) -> None:
    key = os.environ.get("RIG_GEMINI_API_KEY", "")
    if not key:
        raise SystemExit("RIG_GEMINI_API_KEY is not set")
    asker = Recorder(GeminiAsker(key))
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    # Never the store the caller named: --acme ingests into it, and a capture
    # store that took a run's writes is no longer the thing every other run
    # starts from.
    source = out / "source.db"
    if args.db:
        copy_store(Path(args.db), source)
    else:
        Store(source).migrate()
    if args.acme:
        store = Store(source)
        print("=== INGEST ===")
        ingest(store, Path(args.acme), args.tenant)
        print("=== READ (one model call per unread gesture, billed) ===")
        read = await read_new_gestures(store, asker, args.intent_model, args.tenant)
        print(f"  {read} gestures read")
        print(f"  reading cost {asker.spent()}")
        asker.calls.clear()

    summaries: list[dict[str, Any]] = []
    for index in range(args.runs):
        store = copy_store(source, out / f"run{index}.db")
        dropped = keep_only(store, args.tenant, args.batches)
        if index == 0 and dropped:
            print(f"dropped {dropped} gesture(s) from batches not matching {args.batches}*")
        systems = systems_of(store, args.tenant)
        if index == 0:
            print(f"evidence: {len(systems)} gestures on {sorted(set(systems.values()))}")
        mark = len(asker.calls)
        result = await mine(store, tenant=args.tenant, asker=asker, model=args.model, kb="")
        kept = [w for w in known_workflows(store, args.tenant) if w.pass_id == result.pass_id]
        summaries.append(
            report(store, args.tenant, f"{args.model} run {index + 1}", result, kept, systems)
        )
        print(f"  usage         {json.dumps(asker.spent(mark))}")

        if index == 0 and args.again:
            mark = len(asker.calls)
            again = await mine(store, tenant=args.tenant, asker=asker, model=args.model, kb="")
            kept2 = [w for w in known_workflows(store, args.tenant) if w.pass_id == again.pass_id]
            report(
                store,
                args.tenant,
                f"{args.model} run 1, SECOND pass (identity)",
                again,
                kept2,
                systems,
            )
            print(f"  usage         {json.dumps(asker.spent(mark))}")

    if len(summaries) > 1:
        print(f"\n{'=' * 72}\nACROSS RUNS\n{'=' * 72}")
        shapes = Counter(shape for s in summaries for shape in s["shapes"])
        plural = sum(1 for count in shapes.values() if count > len(summaries) // 2)
        print(f"  distinct shapes {len(shapes)}; held by a plurality of runs: {plural}")
        for a in range(len(summaries)):
            for b in range(a + 1, len(summaries)):
                one, two = summaries[a]["cited"], summaries[b]["cited"]
                overlap = len(one & two) / len(one | two) if (one | two) else 0.0
                print(f"  citation jaccard run {a + 1} vs {b + 1}: {overlap:.2f}")
    print(
        "\n  totals: "
        + json.dumps(
            {
                "passes": len(summaries),
                "rig_says_usd": round(sum(s["cost"] for s in summaries), 6),
                "cross_system": sum(s["cross"] for s in summaries),
                "kept": sum(s["kept"] for s in summaries),
            }
        )
    )
    print("  every model call this process made: " + json.dumps(asker.spent()))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", help="a store whose gestures are already read")
    parser.add_argument("--acme", help="a directory of *.ndjson capture to ingest and read")
    parser.add_argument("--out", default="measure-out", help="where run copies go")
    parser.add_argument("--tenant", default="acme")
    parser.add_argument("--model", default="gemini-3.1-pro")
    parser.add_argument("--intent-model", default="gemini-3.8-flash")
    parser.add_argument("--runs", type=int, default=1)
    parser.add_argument("--batches", default="bat_acme_", help="keep only batches with this prefix")
    parser.add_argument("--again", action="store_true", help="mine run 1's store a second time")
    args = parser.parse_args()
    if not args.db and not args.acme:
        parser.error("one of --db or --acme")
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
