"""Does the pool put a whole day in front of the model, or the same slice forever?

The corpus fits one window at the full budget, so `left_out` is 0 and the
carry-over pool never bites. Constraining the budget makes it bite exactly as a
genuine all-tabs day would. No model calls: this is `pack` and the pool alone,
which is the point -- the question is about the packer, and a model in the loop
would make the answer cost money and stop being reproducible.

This exists because the numbers it prints were published without it. A table in
`docs/new-agent-doc-arc/findings.md` claimed 100% coverage in seven passes and
a `new-vs-last` equal to the window on every pass; an independent reviewer
reconstructing the method from prose got pass 10 and a disjointness that breaks
at pass 2, and there was no committed script to arbitrate between them. A
measurement nobody else can run is an anecdote.

    uv run python scripts/rotate.py                       # the published run
    uv run python scripts/rotate.py --budget 40000        # a wider window
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from rig.api import _row_to_gesture, _row_to_intent
from rig.mine import _packed
from rig.pool import add_unclaimed, age_pool, waiting
from rig.store import Store
from rig.values import frequencies_over, shared_values
from rig.window import K_POOL_WAIT, pack


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default="rig.db")
    parser.add_argument("--tenant", default="acme")
    parser.add_argument("--budget", type=int, default=20_000)
    parser.add_argument("--passes", type=int, default=12)
    args = parser.parse_args()

    store = Store(args.db)
    store.migrate()
    rows = store.query("SELECT * FROM gestures WHERE tenant = ? ORDER BY at", (args.tenant,))
    gestures = [_row_to_gesture(row) for row in rows]
    intents = {
        intent.gesture_id: intent
        for intent in (
            _row_to_intent(row)
            for row in store.query("SELECT * FROM intents WHERE tenant = ?", (args.tenant,))
        )
    }
    if not gestures:
        print(f"no gestures for {args.tenant} in {args.db}")
        return 1

    # A fresh pool, so the run does not depend on what a previous mining pass
    # happened to leave behind. Every gesture starts unclaimed: that is the
    # state a day of capture with nothing yet mined is actually in.
    store.execute("DELETE FROM pool WHERE tenant = ?", (args.tenant,))
    add_unclaimed(store, args.tenant, [gesture.id for gesture in gestures], set())

    print(f"{len(gestures)} gesture(s), budget {args.budget:,} tokens\n")
    by_id = {gesture.id: gesture for gesture in gestures}
    crossings = shared_values(gestures, intents, frequencies_over(gestures, intents))
    linked = {gid for ids in crossings.values() for gid in ids}

    seen: set[str] = set()
    last: set[str] = set()
    covered_at = None
    for number in range(1, args.passes + 1):
        # The same join `_one_pass` does, and for the same reason: the pool
        # stores ids, the window takes evidence, and `waited * K_POOL_WAIT` is
        # the whole mechanism under test. `known` is empty on purpose -- a
        # summary of already-mined workflows costs budget and would make the
        # number depend on what a previous run happened to find.
        carried = waiting(store, args.tenant)
        pooled = []
        for entry in carried:
            gesture = by_id.get(entry.gesture_id)
            if gesture is None:
                continue
            item = _packed(gesture, intents.get(entry.gesture_id), linked)
            item.strength += entry.waited * K_POOL_WAIT
            pooled.append(item)
        in_pool = {entry.gesture_id for entry in carried}
        fresh = [gesture for gesture in gestures if gesture.id not in in_pool]

        window = pack(fresh, intents, pooled, [], "", budget=args.budget, linked=linked)
        shown = {item.gesture_id for item in window.items}
        seen |= shown
        share = 100 * len(seen) / len(gestures)
        print(
            f"pass {number:2d}: window {len(shown):4d}  new-vs-last {len(shown - last):4d}"
            f"  left_out {len(gestures) - len(shown):4d}  seen {len(seen):4d}/{len(gestures)}"
            f" {share:4.0f}%"
        )
        age_pool(store, args.tenant, list(shown))
        last = shown
        if covered_at is None and len(seen) == len(gestures):
            covered_at = number
            break

    unshown = [
        row["gesture_id"]
        for row in store.query(
            "SELECT gesture_id FROM pool WHERE tenant = ? AND retired = 1", (args.tenant,)
        )
        if row["gesture_id"] not in seen
    ]
    print()
    if covered_at:
        print(f"covered {len(seen)}/{len(gestures)} of a real day in {covered_at} passes")
    else:
        print(f"covered {len(seen)}/{len(gestures)} in {args.passes} passes -- NOT the whole day")
    print(f"retired without ever being shown: {len(unshown)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
