"""Replay stored batches through correlate into the evidence plane.

Written as a one-off: the 397 batches predate the ingest wiring, so their events
are in the blob store and nothing read them out. Reads the payload that was
actually stored (already redacted), so a gesture cites what the blob holds.

**Skips a batch already in `gesture_batches`, and that is not an optimisation.**
`correlate` mints a fresh `new_gesture_id()` every time it reads an event, so a
batch replayed twice lands twice with different ids, and nothing refuses it --
`add_gestures` only catches an id it has already seen. The evidence doubles and
every doubled gesture is mined as a second doing of the same job. Without this
the script could be run exactly once per store, and there was nothing in it
saying so.

That mattered on 2026-09-14: four days were observed and never reached the
evidence plane -- `new` 2026-09-02 alone was 127 batches and 0 gestures, which
is where `Create a supplier` was done. The model path was never shown it, and
the deletion argument in `docs/new-agent-doc-arc/two-miners-one-day.md` rests
on that gap being closed rather than explained away.
"""

import asyncio
import json
import sys
from pathlib import Path

import asyncpg

from sro.application.capture.rig_wire import Batch as WireBatch
from sro.application.observation.correlate import correlate
from sro.container import build_container
from sro.domain.observation.gesture import GestureBatch


def _database_url() -> str:
    """The address the app reads, taken the same way the app takes it."""
    return next(
        line.split("=", 1)[1].strip()
        for line in Path(".env").read_text().splitlines()
        if line.startswith("SRO_DATABASE_URL=")
    )


async def main(tenant: str) -> None:
    c = build_container()
    db = await asyncpg.connect(_database_url().replace("postgresql+asyncpg://", "postgresql://"))
    rows = await db.fetch(
        "select id, device_id, started_at, ended_at, mode, recording_id, uri"
        " from observation_batches where tenant_id=$1 order by started_at",
        tenant,
    )
    already = {
        r["batch_id"]
        for r in await db.fetch("select batch_id from gesture_batches where tenant_id=$1", tenant)
    }
    fresh = [r for r in rows if r["id"] not in already]
    print(
        f"{len(rows)} batches for {tenant}: {len(already)} already in the evidence plane,"
        f" {len(fresh)} to replay"
    )
    rows = fresh
    done = gestures_total = unreadable = failed = 0
    async with c.unit_of_work() as uow:
        for r in rows:
            try:
                raw = await c.blobs.get(r["uri"].split("/", 3)[3])
                events, bad = [], 0
                for line in raw.decode().splitlines():
                    if not line.strip():
                        continue
                    try:
                        events.append(json.loads(line))
                    except ValueError:
                        bad += 1
                readable = []
                for e in events:
                    try:
                        readable.append(
                            WireBatch.model_validate(
                                {
                                    "batch_id": r["id"],
                                    "device_id": r["device_id"],
                                    "started_at": r["started_at"].isoformat(),
                                    "ended_at": r["ended_at"].isoformat(),
                                    "mode": r["mode"],
                                    "recording_id": r["recording_id"],
                                    "events": [e],
                                }
                            ).events[0]
                        )
                    except ValueError:
                        bad += 1
                wire = WireBatch(
                    batch_id=r["id"],
                    device_id=r["device_id"],
                    started_at=r["started_at"].isoformat(),
                    ended_at=r["ended_at"].isoformat(),
                    mode=r["mode"],
                    recording_id=r["recording_id"],
                    events=readable,
                )
                gs, _c, _m, _s = correlate(wire, tenant)
                await uow.gestures.add_batch(
                    GestureBatch(
                        batch_id=r["id"],
                        device_id=r["device_id"],
                        tenant=tenant,
                        mode=r["mode"],
                        received_at=r["started_at"].isoformat(),
                        started_at=r["started_at"].isoformat(),
                        ended_at=r["ended_at"].isoformat(),
                        recording_id=r["recording_id"],
                        accepted=len(gs),
                        rejected=bad,
                    )
                )
                if gs:
                    await uow.gestures.add_gestures(tuple(gs))
                done += 1
                gestures_total += len(gs)
                unreadable += bad
            except Exception as exc:
                failed += 1
                if failed <= 3:
                    print(f"  FAILED {r['id'][-20:]}: {type(exc).__name__}: {exc}")
        await uow.commit()
    print(
        f"batches {done} ok / {failed} failed · gestures {gestures_total}"
        f" · unreadable events {unreadable}"
    )
    await db.close()


asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "acme"))
