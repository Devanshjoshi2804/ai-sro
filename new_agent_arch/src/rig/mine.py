"""One pass, end to end: pack, ask, check, resolve, store, age the pool."""

import json
import logging
import secrets
from dataclasses import dataclass, field
from datetime import UTC, datetime

from rig.checks import (
    K_MAX_SKEW,
    K_MIN_COVERAGE,
    Coverage,
    Rejection,
    coverage,
    validate,
)
from rig.identity import Resolution, resolve
from rig.models import Asker, one_at_a_time
from rig.parameters import parameters_across
from rig.pool import add_unclaimed, age_pool, waiting
from rig.records import Gesture, Intent
from rig.shape import shape_key
from rig.store import Store
from rig.umbrella import propose
from rig.values import frequencies_over, shared_values
from rig.window import K_POOL_WAIT, Packed, as_evidence, evidence_tokens, pack, strength
from rig.workflows import Workflow, cited_ids, known_workflows, save_workflow

log = logging.getLogger("rig")

# One pass at a time, for the reason api._reading exists one route over: two
# concurrent callers both read `known_workflows` before either saves, so the
# same job is proposed twice, billed twice, and stored twice -- resolve() cannot
# see a row that has not been written yet. This pass costs a 150K-token call to
# the pro model, so the race is far more expensive here than it is there.
# ponytail: a process-local lock, because the rig is one process.


def new_pass_id() -> str:
    return "pas_" + secrets.token_hex(16)


@dataclass
class MineResult:
    # The pass is the thing with a cost, so it is the thing with an id. Every
    # workflow this pass kept carries it, and the bill for a day of mining is
    # SUM(cost_usd) FROM passes -- not from workflows, where the same figure
    # was written once per workflow found.
    pass_id: str = ""
    proposed: int = 0
    kept: int = 0
    learned_parameters: int = 0
    """Parameters a job gained because this pass saw it done a second time.

    A pass that keeps nothing has still learnt something if it recognised a job
    and found out what varies in it -- which is the difference between watching
    the same work twice and understanding it."""
    rejections: list[Rejection] = field(default_factory=list)
    resolutions: list[Resolution] = field(default_factory=list)
    # Not optional: every pass measures its window, and an empty window
    # measures as zeroes rather than as nothing. A `| None` here put a
    # branch in the route that no pass can reach.
    coverage: Coverage = field(default_factory=lambda: Coverage(0.0, 0.0, 0.0))
    in_tokens: int = 0
    out_tokens: int = 0
    # Part of out_tokens, as on Answer: K_EFFORT = "high" exists to spend these.
    thought_tokens: int = 0
    cost_usd: float = 0.0
    unpriced: bool = False
    # What the model said went wrong, when something did. A pass that was
    # refused and a pass that honestly found nothing are the same result
    # without this -- the distinction the rest of this codebase keeps.
    error: str | None = None
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
    """One reading of one tenant's day.

    `kb` is empty at every call site in this repo, and stays a parameter on
    purpose -- the decision, recorded here so it is not mistaken for the
    K_EFFORT / K_POOL_DAYS shape a third time.

    It differs from those two in the way that matters: it is not a tuned
    constant whose value nobody justified, it is an INPUT whose absence costs
    nothing and whose presence is already paid for correctly. window.pack
    subtracts tokens(kb) from the budget before it fills anything, so a caller
    that passes a knowledge base gets a smaller window rather than a prompt
    over the 200K price boundary. Removing it would delete that subtraction and
    the only seam a knowledge base can enter the prompt through, to save four
    signatures a `str`.

    What is genuinely undecided is not this parameter. 296 knowledge-base
    exchange files exist as data, and nothing has specified WHICH of them a
    given window should be shown -- all of them is far past the budget, and
    "the relevant ones" is a retrieval design with its own measurements to
    make. Wiring the whole corpus in to avoid an empty string would be that
    decision made by accident. It is left empty, and it is left named.
    """
    async with one_at_a_time("mining"):
        return await _one_pass(store, tenant=tenant, asker=asker, model=model, kb=kb)


def _learn_parameters(
    store: Store,
    tenant: str,
    known_id: str,
    proposal: Workflow,
    by_id: dict[str, Gesture],
    intents: dict[str, Intent],
) -> int:
    """Diff a job's two doings and keep what they disagree about.

    Returns how many parameters the job now has that it did not before, so a
    pass can say it learnt something rather than only that it recognised
    something. Nothing is removed: a control that stopped varying may simply
    not have been reached this time, and forgetting a parameter on that
    evidence would be worse than carrying one too many.

    ponytail: read-modify-write across two connections against an INSERT OR
    REPLACE. `one_at_a_time("mining")` is an asyncio.Lock keyed per event loop,
    so it serialises passes inside ONE process and nothing between two -- a
    `trial.sh` running beside a serving API can lose a widening. The lost
    update is a parameter value, not a workflow, and the next doing of the job
    re-derives it; a real fix is a transaction around the read and the save,
    worth doing when anything actually mines concurrently.
    """
    stored = next((w for w in known_workflows(store, tenant) if w.id == known_id), None)
    if stored is None:
        return 0
    found = parameters_across([(stored, by_id, intents), (proposal, by_id, intents)])
    if not found:
        return 0
    # A third doing widens what an existing parameter has been given rather
    # than being discarded. This always diffs the STORED steps -- doing #1 --
    # against the proposal, so a name already present used to be skipped
    # outright and `Parameter.seen`'s promise of "every value observed" was
    # two values, forever. A parameter's range is the useful part of it: a
    # runner asked for `$statusCombo` wants to know it has been Active, Closed
    # and Staged, not only the first two.
    by_name = {p["name"]: p for p in stored.parameters if isinstance(p, dict) and "name" in p}
    fresh: list[dict[str, object]] = []
    widened = False
    for parameter in found:
        existing = by_name.get(parameter.name)
        if existing is None:
            fresh.append({"name": parameter.name, "seen_values": list(parameter.seen)})
            continue
        seen = existing.get("seen_values")
        seen = list(seen) if isinstance(seen, list) else []
        added = [value for value in parameter.seen if value not in seen]
        if added:
            existing["seen_values"] = [*seen, *added]
            widened = True
    if not fresh and not widened:
        return 0
    stored.parameters = [*stored.parameters, *fresh]
    save_workflow(store, stored)
    return len(fresh)


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
        tokens=evidence_tokens(evidence),
    )


async def _one_pass(store: Store, *, tenant: str, asker: Asker, model: str, kb: str) -> MineResult:
    started_at = datetime.now(tz=UTC).isoformat()
    pass_id = new_pass_id()

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

    crossings = shared_values(gestures, intents, frequencies_over(gestures, intents))
    linked = {gid for ids in crossings.values() for gid in ids}

    # The pool stores ids; the window takes evidence. This join is the only
    # place the two meet, and a pooled id whose gesture row is gone joins to
    # nothing -- so it is named here rather than disappearing from a list
    # comprehension. Nothing deletes a gesture today, which is exactly why the
    # day something does, this is the only line that would have noticed.
    carried = waiting(store, tenant)
    pooled_ids = [entry.gesture_id for entry in carried]
    lost = [gesture_id for gesture_id in pooled_ids if gesture_id not in by_id]
    if lost:
        log.warning("%d pooled gesture(s) have no row: %s", len(lost), ", ".join(lost))
    # Waiting earns priority. A flat carry-over bonus reorders nothing, so the
    # window showed the same strongest items every pass: on a 3,240-gesture
    # all-tabs day, passes two through ten packed the identical 468 and ten
    # passes had shown 19% of the day. K_POOL_WAIT per pass waited is what
    # rotates the day through the window. pack() adds its flat K_POOL_BONUS on
    # top of whatever strength arrives here.
    pooled = []
    for entry in carried:
        gesture = by_id.get(entry.gesture_id)
        if gesture is None:
            continue
        item = _packed(gesture, intents.get(entry.gesture_id), linked)
        item.strength += entry.waited * K_POOL_WAIT
        pooled.append(item)
    # `pooled_ids` is the LIVE pool, so a retired gesture lands in `fresh` and is
    # packed at its own strength. That is what retirement means here -- see
    # pool.K_POOL_AGE: the entry loses K_POOL_BONUS after six readings, not its
    # place in the window. Excluding retired ids from `fresh` too would make a
    # gesture the budget dropped six times unreadable forever, and nothing ever
    # un-retires.
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
        pass_id=pass_id,
        proposed=len(proposals),
        in_tokens=answer.in_tokens,
        out_tokens=answer.out_tokens,
        thought_tokens=answer.thought_tokens,
        cost_usd=answer.cost_usd,
        unpriced=answer.unpriced,
        error=answer.error,
        window_size=len(window.items),
        left_out=len(window.left_out),
        lost_pool=lost,
    )

    try:
        # checks.validate needs the system each cited gesture happened on, not just
        # the set of ids: a workflow that names a system none of its evidence
        # touched is the one lie an architecture built to find cross-system jobs
        # cannot afford. "" for a gesture whose system could not be established,
        # which validate reads as "unknown" rather than as a system of its own.
        evidence = {item.gesture_id: by_id[item.gesture_id].system or "" for item in window.items}

        kept: list[Workflow] = []
        # Every proposal that survived validate, whether or not it was saved. A
        # proposal that resolved onto a stored workflow still read the window and
        # still cited real gestures -- it produced no new row, which is not the
        # same as having explained nothing. Measured: an identity re-run proposed
        # three, kept none, and reported coverage 0.00 with lopsided=True while
        # having read the whole window correctly. `kept` answers "what is new";
        # this answers "what was accounted for", and coverage and the pool both
        # want the second.
        placed: list[Workflow] = []
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
            placed.append(proposal)
            if resolution.kind == "new":
                proposal.pass_id = pass_id
                save_workflow(store, proposal)
                kept.append(proposal)
            elif resolution.kind == "same_job" and resolution.workflow_id:
                # The same job, done again, on different evidence -- which is
                # the only thing that can tell a parameter from a constant. One
                # doing of "Create Work Activity TEST1" cannot say whether
                # TEST1 names this activity or every activity; two doings that
                # disagree about it can. Recorded on the stored workflow rather
                # than the proposal, because the proposal is about to be
                # discarded and the job is what learns.
                learnt = _learn_parameters(
                    store, tenant, resolution.workflow_id, proposal, by_id, intents
                )
                if learnt:
                    result.learned_parameters += learnt

        result.kept = len(kept)
        result.coverage = coverage(placed, window)
        # Only where a model answered. A refused pass cited nothing, so coverage
        # is 0.0 and this read True on every one of them -- the `passes` table
        # publishing a citation-bias verdict on a reading that never happened,
        # which is the table a person actually reads. Recoverable from `error`;
        # nobody should have to.
        result.lopsided = result.error is None and (
            result.coverage.coverage < K_MIN_COVERAGE or abs(result.coverage.skew) > K_MAX_SKEW
        )

        claimed = {c for w in placed for c in cited_ids(w)}
        # window.left_out is pooled beside what the pass read and could not place.
        # Evidence the budget dropped never got a FIRST look, which is a worse case
        # than the 74% recall the pool exists for, not an exempt one -- and left
        # unpooled it earns no K_POOL_BONUS, so on the next pass it competes on
        # exactly the terms that already lost it. Past one window's worth of
        # evidence that is the same tail losing forever while `left_out` reports it
        # every time.
        #
        # Safe against a double add: pack() puts each candidate in `items` or in
        # `left_out`, never both, and add_unclaimed's INSERT OR IGNORE leaves an
        # already-pooled gesture -- one that was pooled and still did not fit --
        # with the age it has earned rather than restarting its clock. It goes on
        # ageing like any other entry and retires named on K_POOL_AGE, which
        # retired_entries still accounts for.
        add_unclaimed(
            store, tenant, [item.gesture_id for item in window.items] + window.left_out, claimed
        )
        # Exactly once, and only on a pass that got an answer. K_POOL_AGE is six
        # READINGS of patience; counting attempts meant six 503s -- or an expired
        # key, or a model name the API 404s, which findings.md records as the
        # shipped default -- retired the whole pool having read nothing at all. A
        # second call here would halve it, and a refused one spends it for free.
        #
        # `answer.error` is the line because it is exactly "no answer came back":
        # models.GeminiAsker sets it for a raised call, a blocked response and text
        # that would not parse, and leaves it None for every answer the model
        # actually produced. A schema-valid answer that found no workflows is a
        # reading like any other -- the pool was shown, considered and not cited,
        # which is the case it ages for.
        if result.error is None:
            # Only what the window actually showed. An entry the budget left
            # out was not read and has not used up its patience -- ageing it
            # anyway retired 2,630 of a 3,240-gesture day unread.
            age_pool(store, tenant, [item.gesture_id for item in window.items])
    finally:
        # In a finally, so the row exists whatever the work above did. It is
        # the only record left of a call that cost money, and it was written
        # last: anything raising after the model answered -- a store that fell
        # over mid-save -- lost the bill entirely, while leaving the workflows
        # already saved pointing at a pass_id with no row behind it.
        _save_pass(store, tenant, started_at, result)
    return result


def _save_pass(store: Store, tenant: str, started_at: str, result: MineResult) -> None:
    """One row per reading of the day, written whether it found anything or
    not -- including when it was refused, which is the only record left of a
    call that cost money and returned nothing."""
    store.execute(
        "INSERT INTO passes (id, tenant, started_at, in_tokens, out_tokens, thought_tokens,"
        " cost_usd, unpriced, proposed, kept, rejected, coverage, skew, lopsided, error)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            result.pass_id,
            tenant,
            started_at,
            result.in_tokens,
            result.out_tokens,
            result.thought_tokens,
            result.cost_usd,
            int(result.unpriced),
            result.proposed,
            result.kept,
            len(result.rejections),
            result.coverage.coverage,
            result.coverage.skew,
            int(result.lopsided),
            result.error,
        ),
    )


def _ordered_cites(workflow: Workflow) -> list[str]:
    return [c for step in sorted(workflow.steps, key=lambda s: s.order) for c in step.cites]


def rekey_workflows(store: Store, tenant: str) -> int:
    """Every stored workflow's shape key recomputed from its cited gestures,
    and how many changed.

    The key is what `identity.resolve` compares a new proposal against. When
    the rule that makes it changes -- the text rung stopped taking page copy
    -- keys mined before the change no longer match keys mined after, and a
    job the rig already holds could be proposed again as a new one. Run once
    at startup; a key that already agrees is left alone.
    """
    from rig.api import _row_to_gesture  # api imports this module for its route

    changed = 0
    for workflow in known_workflows(store, tenant):
        wanted = _ordered_cites(workflow)
        if not wanted:
            continue
        marks = ",".join("?" * len(wanted))
        rows = store.query(
            f"SELECT * FROM gestures WHERE tenant = ? AND id IN ({marks})",
            (tenant, *wanted),
        )
        by_id = {row["id"]: _row_to_gesture(row) for row in rows}
        # Only over the whole evidence. A key recomputed over the survivors of
        # a pruned batch would be shorter than the job -- and an empty one
        # matches nothing, which is the duplicate this exists to prevent.
        if any(c not in by_id for c in wanted):
            continue
        fresh = [list(entry) for entry in shape_key([by_id[c] for c in wanted])]
        if fresh == workflow.shape_key:
            continue
        store.execute(
            "UPDATE workflows SET shape_key = ? WHERE tenant = ? AND id = ?",
            (json.dumps(fresh, ensure_ascii=False), tenant, workflow.id),
        )
        changed += 1
    return changed
