"""One pass, end to end: pack, ask, check, resolve, store, age the pool."""

import asyncio
import json
import logging
from dataclasses import dataclass, field

from rig.checks import (
    K_MAX_SKEW,
    K_MIN_COVERAGE,
    Coverage,
    Rejection,
    coverage,
    validate,
)
from rig.identity import Resolution, resolve
from rig.models import Asker
from rig.pool import add_unclaimed, age_pool, pool_ids
from rig.records import Gesture, Intent
from rig.shape import shape_key
from rig.store import Store
from rig.umbrella import propose
from rig.values import frequencies_over, shared_values
from rig.window import Packed, as_evidence, pack, strength, tokens
from rig.workflows import Workflow, cited_ids, known_workflows, save_workflow

log = logging.getLogger("rig")

# One pass at a time, for the reason api._reading exists one route over: two
# concurrent callers both read `known_workflows` before either saves, so the
# same job is proposed twice, billed twice, and stored twice -- resolve() cannot
# see a row that has not been written yet. This pass costs a 150K-token call to
# the pro model, so the race is far more expensive here than it is there.
# ponytail: a process-local lock, because the rig is one process.
_mining = asyncio.Lock()


@dataclass
class MineResult:
    proposed: int = 0
    kept: int = 0
    rejections: list[Rejection] = field(default_factory=list)
    resolutions: list[Resolution] = field(default_factory=list)
    # Not optional: every pass measures its window, and an empty window
    # measures as zeroes rather than as nothing. A `| None` here put a
    # branch in the route that no pass can reach.
    coverage: Coverage = field(default_factory=lambda: Coverage(0.0, 0.0, 0.0))
    cost_usd: float = 0.0
    unpriced: bool = False
    window_size: int = 0
    # Evidence this pass did not read, and evidence it could not read. The
    # window drops what will not fit the budget; a pooled id whose gesture row
    # has since been deleted cannot be packed at all. Both are counted rather
    # than left to be inferred from a number that came out smaller than
    # expected.
    left_out: int = 0
    lost_pool: list[str] = field(default_factory=list)
    # The reading was concentrated in part of the window: K_MIN_COVERAGE or
    # K_MAX_SKEW, whichever it failed. Long-context citation bias is real and
    # model-specific, and this is the pass saying it happened.
    lopsided: bool = False


async def mine(store: Store, *, tenant: str, asker: Asker, model: str, kb: str = "") -> MineResult:
    async with _mining:
        return await _one_pass(store, tenant=tenant, asker=asker, model=model, kb=kb)


def _packed(gesture: Gesture, intent: Intent | None, linked: set[str]) -> Packed:
    """A pooled gesture as pack() would have built it. pack() takes the pool
    already packed -- it is the one input that does not arrive as a Gesture --
    and adds K_POOL_BONUS itself, so nothing here touches the strength."""
    evidence = as_evidence(gesture, intent)
    return Packed(
        gesture_id=gesture.id,
        at=gesture.at,
        evidence=evidence,
        strength=strength(gesture, intent, linked),
        tokens=tokens(json.dumps(evidence)),
    )


async def _one_pass(store: Store, *, tenant: str, asker: Asker, model: str, kb: str) -> MineResult:
    # Imported here, not at module scope: api.py reaches for rig.mine inside
    # its own route for the same reason, and a module-level pair would be a
    # cycle. These two rebuild a Gesture and an Intent from their rows -- and
    # note _row_to_gesture rehydrates the requests, which it once did not.
    from rig.api import _row_to_gesture, _row_to_intent

    rows = store.query("SELECT * FROM gestures WHERE tenant = ? ORDER BY at", (tenant,))
    gestures = [_row_to_gesture(row) for row in rows]
    intents = {
        row["gesture_id"]: _row_to_intent(row)
        for row in store.query("SELECT * FROM intents WHERE tenant = ?", (tenant,))
    }
    by_id = {gesture.id: gesture for gesture in gestures}

    crossings = shared_values(gestures, intents, frequencies_over(store, tenant))
    linked = {gid for ids in crossings.values() for gid in ids}

    # The pool stores ids; the window takes evidence. This join is the only
    # place the two meet, and a pooled id whose gesture row is gone joins to
    # nothing -- so it is named here rather than disappearing from a list
    # comprehension. Nothing deletes a gesture today, which is exactly why the
    # day something does, this is the only line that would have noticed.
    pooled_ids = pool_ids(store, tenant)
    lost = [gesture_id for gesture_id in pooled_ids if gesture_id not in by_id]
    if lost:
        log.warning("%d pooled gesture(s) have no row: %s", len(lost), ", ".join(lost))
    pooled = [
        _packed(by_id[gesture_id], intents.get(gesture_id), linked)
        for gesture_id in pooled_ids
        if gesture_id in by_id
    ]
    in_pool = set(pooled_ids)
    fresh = [gesture for gesture in gestures if gesture.id not in in_pool]

    known = known_workflows(store, tenant)
    summary = [
        {"id": w.id, "title": w.title, "systems": w.systems, "shape_key": w.shape_key}
        for w in known
    ]

    window = pack(fresh, intents, pooled, summary, kb, linked=linked)
    proposals, answer = await propose(
        window, crossings, summary, kb, asker=asker, model=model, tenant=tenant
    )

    result = MineResult(
        proposed=len(proposals),
        cost_usd=answer.cost_usd,
        unpriced=answer.unpriced,
        window_size=len(window.items),
        left_out=len(window.left_out),
        lost_pool=lost,
    )

    # checks.validate needs the system each cited gesture happened on, not just
    # the set of ids: a workflow that names a system none of its evidence
    # touched is the one lie an architecture built to find cross-system jobs
    # cannot afford. "" for a gesture whose system could not be established,
    # which validate reads as "unknown" rather than as a system of its own.
    evidence = {item.gesture_id: by_id[item.gesture_id].system or "" for item in window.items}

    kept: list[Workflow] = []
    for proposal in proposals:
        rejection = validate(proposal, evidence)
        if rejection is not None:
            result.rejections.append(rejection)
            continue
        proposal.shape_key = [
            list(entry) for entry in shape_key([by_id[c] for c in _ordered_cites(proposal)])
        ]
        # Resolved against what is stored plus what this pass has already kept,
        # and always before its own save -- which is what makes matching a
        # proposal against itself unreachable rather than guarded. `known`
        # alone was not enough: two proposals of one job inside a single pass
        # both read an empty store and both saved.
        resolution = resolve(proposal, known + kept)
        result.resolutions.append(resolution)
        if resolution.kind == "new":
            save_workflow(store, proposal)
            kept.append(proposal)

    result.kept = len(kept)
    result.coverage = coverage(kept, window)
    result.lopsided = (
        result.coverage.coverage < K_MIN_COVERAGE or abs(result.coverage.skew) > K_MAX_SKEW
    )

    claimed = {c for w in kept for c in cited_ids(w)}
    add_unclaimed(store, tenant, [item.gesture_id for item in window.items], claimed)
    # Exactly once, at the end of the pass: K_POOL_AGE counts passes, and a
    # second call here would halve it.
    age_pool(store, tenant)
    return result


def _ordered_cites(workflow: Workflow) -> list[str]:
    return [c for step in sorted(workflow.steps, key=lambda s: s.order) for c in step.cites]
