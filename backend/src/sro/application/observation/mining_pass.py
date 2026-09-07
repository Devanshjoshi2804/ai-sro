"""One pass, end to end: pack, ask, check, resolve, store, age the pool.

Ported from `new_agent_arch/src/rig/mine.py` in full, plus `propose` from
`new_agent_arch/src/rig/umbrella.py`. Everything above `propose` in that second
file is `sro.domain.skill.umbrella`, which is pure; `propose` asks a model, so
it is here with the use case that pays for it.

**Not `observation/mine.py`.** That name is taken, and by a different miner:
`MineObservations` clusters a week of observation into task candidates with no
model in the loop at all. This is the model-first rig's pass -- one window, one
call, one `mining_passes` row -- and the two have nothing in common but the
verb. Two miners, two files, and neither one importing the other.
"""

from __future__ import annotations

import logging
import secrets
from dataclasses import dataclass, field
from datetime import datetime

from sro.application.intent.spend import over_cap
from sro.application.ports.model import Asker
from sro.application.ports.repositories import UnitOfWork
from sro.application.shared.locks import one_at_a_time
from sro.domain.observation.gesture import Gesture, Intent
from sro.domain.observation.identity import Resolution, resolve, shape_key
from sro.domain.observation.mining import MiningPass
from sro.domain.observation.values import frequencies_over, shared_values
from sro.domain.observation.window import (
    K_POOL_WAIT,
    Packed,
    Window,
    as_evidence,
    evidence_tokens,
    pack,
    strength,
)
from sro.domain.shared.errors import NotFound
from sro.domain.shared.identifiers import TenantId
from sro.domain.shared.prices import Answer
from sro.domain.skill.checks import (
    K_MAX_SKEW,
    K_MIN_COVERAGE,
    Coverage,
    Rejection,
    coverage,
    validate,
)
from sro.domain.skill.learned import parameters_across
from sro.domain.skill.umbrella import (
    K_EFFORT,
    WORKFLOW_SCHEMA,
    build_prompt,
    workflow_from,
)
from sro.domain.skill.workflow import Workflow, cited_ids, ordered_cites

__all__ = [
    "MineResult",
    "learn_parameters",
    "mine",
    "new_pass_id",
    "propose",
    "rekey_workflows",
]

logger = logging.getLogger(__name__)


def new_pass_id() -> str:
    return "pas_" + secrets.token_hex(16)


@dataclass
class MineResult:
    # The pass is the thing with a cost, so it is the thing with an id. Every
    # workflow this pass kept carries it, and the bill for a day of mining is
    # SUM(cost_usd) over the passes -- not over the workflows, where the same
    # figure was written once per workflow found.
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
    # What the model said went wrong, when something did -- and what the cap
    # said, when it was the cap. A pass that was refused and a pass that
    # honestly found nothing are the same result without this.
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


async def propose(
    window: Window,
    crossings: dict[str, list[str]],
    known: list[dict[str, object]],
    kb: str,
    *,
    asker: Asker,
    model: str,
    tenant: str,
) -> tuple[list[Workflow], Answer]:
    """One pass. Returns what it proposed and what the call cost.

    One sample. Plurality voting over repeated samples gained 0.4% at twenty
    times the cost in published work, and that paper's thesis is that voting
    helps LESS as models get stronger. `K_EFFORT` is the knob that replaced it.
    """
    answer = await asker.ask(
        model=model,
        # build_prompt already opens and closes with INSTRUCTIONS -- stating the
        # task at both ends is the measured decision, and the prompt owns it.
        # Passing it here as well sent it three times, twice adjacently.
        instructions="",
        evidence=build_prompt(window, crossings, known, kb),
        schema=WORKFLOW_SCHEMA,
        effort=K_EFFORT,
    )
    if answer.data is None:
        return [], answer

    raw = answer.data.get("workflows")
    # The schema is advisory. A model that returned `workflows` as a string, or
    # as a bare number, costs the pass and not the process -- and this guard is
    # `propose`'s own, one level above every check `workflow_from` makes.
    if not isinstance(raw, list):
        return [], answer

    proposed = [workflow_from(item, tenant) for item in raw]
    return [w for w in proposed if w is not None], answer


async def mine(
    uow: UnitOfWork,
    *,
    tenant_id: TenantId,
    asker: Asker,
    model: str,
    now: datetime,
    cap_usd: float,
    kb: str = "",
) -> MineResult:
    """One reading of one tenant's day.

    One pass at a time, for the reason the reading loop takes a lock one module
    over: two concurrent callers both read the known workflows before either
    saves, so the same job is proposed twice, billed twice and stored twice --
    `resolve` cannot see a row that has not been written yet. This pass costs a
    150K-token call to the pro model, so the race is far more expensive here
    than it is there.

    Keyed by tenant, like the reading lock and for the same reason: what the
    lock is for is two passes racing over one tenant's workflows, and a single
    global name would make two DIFFERENT tenants take turns for nothing.

    ponytail: a process-local lock. Claim rows in the database if this ever
    becomes more than one process.

    `uow` is already open: the pass commits its own writes and never enters or
    leaves the block, so the caller owns the session.

    `kb` is empty at every call site in this repo, and stays a parameter on
    purpose -- the decision, recorded here so it is not mistaken for the
    K_EFFORT / K_POOL_DAYS shape a third time.

    It differs from those two in the way that matters: it is not a tuned
    constant whose value nobody justified, it is an INPUT whose absence costs
    nothing and whose presence is already paid for correctly. `window.pack`
    subtracts tokens(kb) from the budget before it fills anything, so a caller
    that passes a knowledge base gets a smaller window rather than a prompt
    over the 200K price boundary. Removing it would delete that subtraction and
    the only seam a knowledge base can enter the prompt through, to save four
    signatures a `str`.

    What is genuinely undecided is not this parameter. 296 knowledge-base
    exchange files exist as data, and nothing has specified WHICH of them a
    given window should be shown -- all of them is far past the budget, and
    "the relevant ones" is a retrieval design with its own measurements to
    make. It is left empty, and it is left named.
    """
    async with one_at_a_time(f"mining:{tenant_id.value}"):
        return await _one_pass(
            uow, tenant_id=tenant_id, asker=asker, model=model, now=now, cap_usd=cap_usd, kb=kb
        )


async def learn_parameters(
    uow: UnitOfWork,
    *,
    tenant_id: TenantId,
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

    ponytail: read-modify-write inside one pass's transaction, where the rig
    had it across two connections. `one_at_a_time` serialises passes inside ONE
    process and nothing between two, so a second process mining the same tenant
    can still lose a widening. The lost update is a parameter value, not a
    workflow, and the next doing of the job re-derives it.
    """
    try:
        stored = await uow.workflows.get(tenant_id, known_id)
    except NotFound:
        return 0
    found = parameters_across([(stored, by_id, intents), (proposal, by_id, intents)])
    if not found:
        return 0
    # A third doing widens what an existing parameter has been given rather
    # than being discarded. This always diffs the STORED steps -- doing #1 --
    # against the proposal, so a name already present used to be skipped
    # outright and `seen_values`' promise of "every value observed" was two
    # values, forever. A parameter's range is the useful part of it: a runner
    # asked for `$statusCombo` wants to know it has been Active, Closed and
    # Staged, not only the first two.
    by_name = {str(p["name"]): p for p in stored.parameters if "name" in p}
    fresh: list[dict[str, object]] = []
    widened = False
    for parameter in found:
        existing = by_name.get(parameter.name)
        if existing is None:
            fresh.append({"name": parameter.name, "seen_values": list(parameter.seen)})
            continue
        was = existing.get("seen_values")
        seen = [str(value) for value in was] if isinstance(was, list) else []
        added = [value for value in parameter.seen if value not in seen]
        if added:
            existing["seen_values"] = [*seen, *added]
            widened = True
    if not fresh and not widened:
        return 0
    stored.parameters = [*stored.parameters, *fresh]
    await uow.workflows.save(stored)
    return len(fresh)


def _packed(gesture: Gesture, intent: Intent | None, linked: set[str]) -> Packed:
    """A pooled gesture as `pack` would have built it. `pack` takes the pool
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


async def _one_pass(
    uow: UnitOfWork,
    *,
    tenant_id: TenantId,
    asker: Asker,
    model: str,
    now: datetime,
    cap_usd: float,
    kb: str,
) -> MineResult:
    why = await over_cap(uow, tenant_id, now=now, cap_usd=cap_usd)
    if why:
        # Before anything is read and long before anything is asked. This is
        # the most expensive call in the system, so a cap checked after the
        # window is packed is a cap that has already paid for the pass it
        # stops. No `mining_passes` row either: the row exists to record a call
        # that cost money, and this pass never made one.
        logger.warning("%s for %s, nothing mined", why, tenant_id.value)
        return MineResult(error=why)

    # The caller's clock, not the server's, so a test can move it and so the
    # day a pass is billed to is the day its caller meant.
    started_at = now.isoformat()
    pass_id = new_pass_id()

    gestures = list(await uow.gestures.gestures_for(tenant_id))
    intents = {intent.gesture_id: intent for intent in await uow.gestures.intents_for(tenant_id)}
    by_id = {gesture.id: gesture for gesture in gestures}

    crossings = shared_values(gestures, intents, frequencies_over(gestures, intents))
    linked = {gesture_id for ids in crossings.values() for gesture_id in ids}

    # The pool stores ids; the window takes evidence. This join is the only
    # place the two meet, and a pooled id whose gesture row is gone joins to
    # nothing -- so it is named here rather than disappearing from a list
    # comprehension. Nothing deletes a gesture today, which is exactly why the
    # day something does, this is the only line that would have noticed.
    carried = await uow.pool.waiting(tenant_id)
    pooled_ids = [entry.gesture_id for entry in carried]
    lost = [gesture_id for gesture_id in pooled_ids if gesture_id not in by_id]
    if lost:
        logger.warning("%d pooled gesture(s) have no row: %s", len(lost), ", ".join(lost))
    # Waiting earns priority. A flat carry-over bonus reorders nothing, so the
    # window showed the same strongest items every pass: on a 3,240-gesture
    # all-tabs day, passes two through ten packed the identical 468 and ten
    # passes had shown 19% of the day. K_POOL_WAIT per pass waited is what
    # rotates the day through the window. `pack` adds its flat K_POOL_BONUS on
    # top of whatever strength arrives here.
    pooled: list[Packed] = []
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

    known = list(await uow.workflows.known(tenant_id))
    summary: list[dict[str, object]] = [
        {"id": w.id, "title": w.title, "systems": w.systems, "shape_key": w.shape_key}
        for w in known
    ]

    window = pack(fresh, intents, pooled, summary, kb, linked=linked)
    proposals, answer = await propose(
        window, crossings, summary, kb, asker=asker, model=model, tenant=tenant_id.value
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
        # `validate` needs the system each cited gesture happened on, not just
        # the set of ids: a workflow that names a system none of its evidence
        # touched is the one lie an architecture built to find cross-system jobs
        # cannot afford. "" for a gesture whose system could not be established,
        # which `validate` reads as "unknown" rather than as a system of its own.
        evidence = {item.gesture_id: by_id[item.gesture_id].system or "" for item in window.items}

        kept: list[Workflow] = []
        # Every proposal that survived `validate`, whether or not it was saved. A
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
                list(entry) for entry in shape_key([by_id[c] for c in ordered_cites(proposal)])
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
                await uow.workflows.save(proposal)
                kept.append(proposal)
            elif resolution.kind == "same_job" and resolution.workflow_id:
                # The same job, done again, on different evidence -- which is
                # the only thing that can tell a parameter from a constant. One
                # doing of "Create Work Activity TEST1" cannot say whether
                # TEST1 names this activity or every activity; two doings that
                # disagree about it can. Recorded on the stored workflow rather
                # than the proposal, because the proposal is about to be
                # discarded and the job is what learns.
                result.learned_parameters += await learn_parameters(
                    uow,
                    tenant_id=tenant_id,
                    known_id=resolution.workflow_id,
                    proposal=proposal,
                    by_id=by_id,
                    intents=intents,
                )

        result.kept = len(kept)
        result.coverage = coverage(placed, window)
        # Only where a model answered. A refused pass cited nothing, so coverage
        # is 0.0 and this read True on every one of them -- the passes table
        # publishing a citation-bias verdict on a reading that never happened,
        # which is the table a person actually reads. Recoverable from `error`;
        # nobody should have to.
        result.lopsided = result.error is None and (
            result.coverage.coverage < K_MIN_COVERAGE or abs(result.coverage.skew) > K_MAX_SKEW
        )

        claimed = frozenset(c for w in placed for c in cited_ids(w))
        # `window.left_out` is pooled beside what the pass read and could not place.
        # Evidence the budget dropped never got a FIRST look, which is a worse case
        # than the 74% recall the pool exists for, not an exempt one -- and left
        # unpooled it earns no K_POOL_BONUS, so on the next pass it competes on
        # exactly the terms that already lost it. Past one window's worth of
        # evidence that is the same tail losing forever while `left_out` reports it
        # every time.
        #
        # Safe against a double add: `pack` puts each candidate in `items` or in
        # `left_out`, never both, and `add_unclaimed` leaves an already-pooled
        # gesture -- one that was pooled and still did not fit -- with the age it
        # has earned rather than restarting its clock.
        #
        # `claimed` is every cited id and is never narrowed to this window's
        # own: a pooled gesture is packed into the window beside the fresh ones,
        # so a pass can cite evidence that is only in the pool, and a citation
        # left in the pool ages out and retires despite having been placed. The
        # two arguments are siblings and only one of them is about the window.
        await uow.pool.add_unclaimed(
            tenant_id,
            window_ids=tuple(item.gesture_id for item in window.items) + tuple(window.left_out),
            claimed=claimed,
        )
        # Exactly once, and only on a pass that got an answer. K_POOL_AGE is six
        # READINGS of patience; counting attempts meant six 503s -- or an expired
        # key, or a model name the API 404s, which findings.md records as the
        # shipped default -- retired the whole pool having read nothing at all. A
        # second call here would halve it, and a refused one spends it for free.
        #
        # `answer.error` is the line because it is exactly "no answer came back":
        # the Gemini asker sets it for a raised call, a blocked response and text
        # that would not parse, and leaves it None for every answer the model
        # actually produced. A schema-valid answer that found no workflows is a
        # reading like any other -- the pool was shown, considered and not cited,
        # which is the case it ages for.
        if result.error is None:
            # Only what the window actually showed. An entry the budget left
            # out was not read and has not used up its patience -- ageing it
            # anyway retired 2,630 of a 3,240-gesture day unread.
            await uow.pool.age(tenant_id, shown=tuple(item.gesture_id for item in window.items))
    finally:
        # In a finally, so the row exists whatever the work above did. It is
        # the only record left of a call that cost money, and it was written
        # last: anything raising after the model answered -- a store that fell
        # over mid-save -- lost the bill entirely, while leaving the workflows
        # already saved pointing at a pass_id with no row behind it.
        #
        # The commit is here rather than after the block for the same reason:
        # on the happy path the workflows, the pool and the bill land in one
        # transaction, and on the raising path the bill still lands.
        await uow.workflows.add_pass(_billed(pass_id, tenant_id, started_at, result))
        await uow.commit()
    return result


def _billed(pass_id: str, tenant_id: TenantId, started_at: str, result: MineResult) -> MiningPass:
    """One row per reading of the day, written whether it found anything or
    not -- including when it was refused, which is the only record left of a
    call that cost money and returned nothing."""
    return MiningPass(
        id=pass_id,
        tenant=tenant_id.value,
        started_at=started_at,
        in_tokens=result.in_tokens,
        out_tokens=result.out_tokens,
        thought_tokens=result.thought_tokens,
        cost_usd=result.cost_usd,
        unpriced=result.unpriced,
        proposed=result.proposed,
        kept=result.kept,
        rejected=len(result.rejections),
        coverage=result.coverage.coverage,
        skew=result.coverage.skew,
        lopsided=result.lopsided,
        error=result.error,
    )


async def rekey_workflows(uow: UnitOfWork, *, tenant_id: TenantId) -> int:
    """Every stored workflow's shape key recomputed from its cited gestures,
    and how many changed.

    The key is what `identity.resolve` compares a new proposal against. When
    the rule that makes it changes -- the text rung stopped taking page copy
    -- keys mined before the change no longer match keys mined after, and a
    job the rig already holds could be proposed again as a new one. Run once
    at startup; a key that already agrees is left alone, and a pass that
    changes nothing writes nothing.
    """
    changed = 0
    for workflow in await uow.workflows.known(tenant_id):
        wanted = ordered_cites(workflow)
        if not wanted:
            continue
        by_id = {
            gesture.id: gesture
            for gesture in await uow.gestures.gestures_for(tenant_id, ids=tuple(wanted))
        }
        # Only over the whole evidence. A key recomputed over the survivors of
        # a pruned batch would be shorter than the job -- and an empty one
        # matches nothing, which is the duplicate this exists to prevent.
        if any(cited not in by_id for cited in wanted):
            continue
        fresh = shape_key([by_id[cited] for cited in wanted])
        if [list(triple) for triple in fresh] == workflow.shape_key:
            continue
        await uow.workflows.rekey(tenant_id, workflow.id, fresh)
        changed += 1
    if changed:
        await uow.commit()
    return changed
