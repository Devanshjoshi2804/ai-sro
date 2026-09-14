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
from sro.domain.observation.values import (
    frequencies_over,
    shared_values,
    worked_in_both,
)
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
    K_SITTING_GAP_S,
    Coverage,
    Rejection,
    coverage,
    one_occurrence,
    undeliverable,
    validate,
    work_only,
)
from sro.domain.skill.learned import LearnedParameter, parameters_across
from sro.domain.skill.passwords import with_passwords
from sro.domain.skill.presses import with_the_press
from sro.domain.skill.shape import in_time_order
from sro.domain.skill.umbrella import (
    K_EFFORT,
    WORKFLOW_SCHEMA,
    build_prompt,
    workflow_from,
)
from sro.domain.skill.workflow import Workflow, cited_ids, ordered_cites

__all__ = [
    "MineResult",
    "fill_in_passwords",
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
    read: int = 0
    """Gestures this sweep read before it mined, where a sweep did the reading.

    Zero from a pass asked for directly -- `MinePass` reads nothing, and a
    route's caller has its own reader. `MineLately` fills it in, because
    "nothing was kept" means one thing after a hundred fresh readings and
    another after none."""
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
    ours: frozenset[str] = frozenset(),
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
        # Before the reading, and cheap: the rule that adds a credential step
        # reached proposals the moment it was written, and a job already stored
        # is re-proposed as `same_job` and dropped -- so without this the fix
        # only ever helps whoever mines a sign-in for the first time after it.
        # Inside the lock, because it writes workflows this pass is about to
        # compare against.
        filled = await fill_in_passwords(uow, tenant_id=tenant_id)
        if filled:
            await uow.commit()
        return await _one_pass(
            uow,
            tenant_id=tenant_id,
            asker=asker,
            model=model,
            now=now,
            cap_usd=cap_usd,
            kb=kb,
            ours=ours,
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

    Returns how many parameters this pass TOUCHED -- the ones it named for the
    first time plus the ones whose range it widened -- so a pass can say it
    learnt something rather than only that it recognised something. A widening
    is learning: `seen_values` promises every value observed, and a pass that
    adds a third one to a control it already knew did real work and used to
    report nothing. Nothing is removed: a control that stopped varying may
    simply not have been reached this time, and forgetting a parameter on that
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
    widened = 0
    for parameter in found:
        existing = by_name.get(parameter.name) or _same_control(parameter, stored.parameters)
        if existing is None:
            fresh.append({"name": parameter.name, "seen_values": list(parameter.seen)})
            continue
        was = existing.get("seen_values")
        seen = [str(value) for value in was] if isinstance(was, list) else []
        added = [value for value in parameter.seen if value not in seen]
        if added:
            existing["seen_values"] = [*seen, *added]
            widened += 1
    if not fresh and not widened:
        return 0
    stored.parameters = [*stored.parameters, *fresh]
    # And the name stops describing the first doing. A title is minted from one
    # occurrence, values and all, and this is the only moment the system finds
    # out that one of those values varies -- so the job is renamed where it is
    # learnt rather than left reading "Create Customer Type DSS" over a
    # parameter that has since been DSS, DPP, CCD and CCF.
    stored.generalise_title()
    await uow.workflows.save(stored)
    return len(fresh) + widened


def _same_control(
    parameter: LearnedParameter, stored: list[dict[str, object]]
) -> dict[str, object] | None:
    """The stored parameter that is this one under the model's own name.

    `_by_control` names a control by its `item_id` -- `basePriority` -- and the
    model names the same control by the label the operator reads -- `Base
    Priority`. Neither is wrong and they never match as strings, so a job that
    the model declared parameters for grew a second parameter per control on
    its second doing. The real acme store carried `Create a Work Operation`
    with `Operation` beside `operationCode`, `Description` beside
    `longDescription` and `Base Priority` beside `basePriority`, which reaches
    a runner as six inputs to fill in for three fields.

    Matched on the values rather than the names, because the values are the
    evidence and the two names are two opinions about it. A learned parameter
    whose every observed value is already recorded against a stored one was
    read off the same typing.

    ponytail: two genuinely distinct controls that varied over the same value
    set -- two Yes/No toggles -- merge into one, and the second loses its
    `item_id` name. `planning.value_for` still finds it by `field_label`, so
    the cost is a machine name, not a parameter. Compare on the cited gesture
    ids instead if that ever bites.
    """
    wanted = set(parameter.seen)
    for candidate in stored:
        was = candidate.get("seen_values")
        if not isinstance(was, list):
            continue
        if wanted and wanted <= {str(value) for value in was}:
            return candidate
    return None


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
    ours: frozenset[str] = frozenset(),
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

    # ponytail: this reads the tenant's WHOLE HISTORY, not a day. Neither
    # `gestures_for` nor `intents_for` takes a time bound, so every pass
    # deserialises every gesture ever captured -- request and response bodies
    # included -- and `frequencies_over` and `shared_values` below then walk
    # all of it. That set only grows. Faithful to the rig, and defensible only
    # while a pass is dominated by one 150K-token model call; the ceiling is
    # the day the scan costs more than the call. The upgrade is the same seam
    # the reading loop names: a time-bounded read on `GestureRepository`, which
    # the rig had in SQL. The two are one fix, and fixing only the reading loop
    # fixes half of it.
    gestures = list(await uow.gestures.gestures_for(tenant_id))
    intents = {intent.gesture_id: intent for intent in await uow.gestures.intents_for(tenant_id)}
    by_id = {gesture.id: gesture for gesture in gestures}

    crossings = shared_values(gestures, intents, frequencies_over(gestures, intents))
    # Two ways a gesture can belong to work in another tab, and the second was
    # missing until 2026-09-14. A shared VALUE says the two systems carry the
    # same thing; a shared SITTING says somebody was working in both. The value
    # rule cannot see "read the mail, create what it asks for", because a mail
    # nobody typed into carries nothing across -- and on the real acme store it
    # linked 23 of 555 gestures where the browser's own timeline holds 219
    # inside a sitting that went to another system and came back.
    #
    # `K_SITTING_GAP_S` is the bound `checks` already uses for what counts as
    # one doing, tied to the extension's own tail. `ours` is this deployment,
    # which nobody works in.
    linked = {gesture_id for ids in crossings.values() for gesture_id in ids}
    linked |= worked_in_both(gestures, gap=K_SITTING_GAP_S, ours=ours)

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
            # Before anything reads the citations. A model told that an
            # operator repeats a job answers with one job citing every doing,
            # and `shape_key`, `learn_parameters` and `_by_control` are all
            # wrong about a workflow built that way -- see `one_occurrence`.
            # Narrowing first means `validate` judges the job that will
            # actually be stored, and refuses it for an uncited step if the
            # doing it kept cannot supply one.
            one_occurrence(proposal, by_id)
            # After the narrowing and before the judging. The credential
            # gesture is invisible to a model -- redaction leaves it no value
            # and no name to point at -- so the step that types a password is
            # added from the evidence rather than asked for, and it is judged
            # like any other step: `validate` sees a step citing a real
            # gesture of this doing.
            typed = with_passwords(proposal, by_id)
            if typed:
                logger.info(
                    "%s: %s credential step(s) the model could not see",
                    proposal.title,
                    typed,
                )
            # And the opposite failure: a gesture the model could see and
            # passed over. A step that cites the login card rather than the
            # Sign In button inside it runs, answers ok, and signs nobody in.
            pressed = with_the_press(proposal, by_id)
            if pressed:
                logger.info(
                    "%s: %s step(s) repointed at the control the operator pressed",
                    proposal.title,
                    pressed,
                )
            rejection = validate(proposal, evidence) or work_only(proposal, by_id, ours=ours)
            if rejection is not None:
                result.rejections.append(rejection)
                continue
            # Dropped rather than refused: the JOB is sound and only its
            # declaration of what varies is not, so refusing it would throw
            # away a working job over a spare field. Dropping leaves the job
            # runnable on the values its recording carries, which is what a
            # job with no parameters has always done, and a later pass
            # re-derives the parameter properly from a second doing.
            lost = undeliverable(proposal, by_id)
            if lost:
                logger.warning(
                    "%s: dropping parameter(s) no step can be given: %s",
                    proposal.title,
                    ", ".join(lost),
                )
                proposal.parameters = [
                    declared for declared in proposal.parameters if declared.get("name") not in lost
                ]
            # In time order, which is the order the browser's tail arrives in
            # and the only order a shape can be matched against. See
            # `shape.in_time_order`.
            proposal.shape_key = [
                list(entry) for entry in shape_key(in_time_order(proposal, by_id))
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
        # `claimed` is every cited id and is never narrowed to this pass's own
        # FRESH evidence: a pooled gesture is packed into the window beside the
        # fresh ones, so a pass can cite evidence that is only in the pool, and
        # a citation left in the pool ages out and retires despite having been
        # placed. The two arguments are siblings and only one of them is about
        # the window.
        #
        # Which narrowing matters, recorded so nobody hunts the other one
        # twice: narrowing `claimed` to the WINDOW's own ids changes nothing
        # and cannot be tested, because `validate` has already refused any
        # workflow citing an id outside `window.items`. Narrowing it to the
        # fresh ids is the failure above, and is what the test plants.
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
        # transaction.
        billed = _billed(pass_id, tenant_id, started_at, result)
        try:
            await uow.workflows.add_pass(billed)
        except Exception:
            # The session is already dead. Postgres refuses every statement on
            # a transaction that has raised -- InFailedSQLTransactionError --
            # so this write failed for the same reason the one above it did,
            # and its DBAPIError would replace the exception that caused it.
            #
            # The rollback costs nothing that is not already lost: Postgres
            # discarded this transaction's workflows the moment the statement
            # failed. Measured against the suite's own Postgres, before this:
            # `passes: 0, workflows: 0` and a DBAPIError in place of the real
            # one. The rig never met this because its `store.execute` opened a
            # connection per statement, so every save was its own committed
            # transaction and the bill after a failed one simply landed. One
            # session is the port's shape, and this is what that shape costs.
            await uow.rollback()
            await uow.workflows.add_pass(billed)
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
        learned_parameters=result.learned_parameters,
        coverage=result.coverage.coverage,
        skew=result.coverage.skew,
        lopsided=result.lopsided,
        window_size=result.window_size,
        left_out=result.left_out,
        error=result.error,
    )


async def fill_in_passwords(uow: UnitOfWork, *, tenant_id: TenantId) -> int:
    """Every stored job given the credential step nobody could cite, and how
    many changed.

    The pass above adds it to a PROPOSAL, which is right for a job being mined
    for the first time and does nothing at all for one already stored: a
    re-mine of a job the rig holds resolves as `same_job`, the proposal is
    dropped, and the stored steps -- the ones a run actually performs -- stay
    as they were. An operator whose sign-in job was mined last week would wait
    forever for a step that is only ever added to something thrown away.

    So it is applied to the store too, on the same rules, and it is idempotent:
    a job whose credential gesture is already cited is left exactly alone, so
    running this every pass costs a read.

    Beside `rekey_workflows` and for its reason -- a rule that changed after a
    job was mined has to reach the jobs mined before it, or the fix only helps
    whoever arrives next.
    """
    changed = 0
    for workflow in await uow.workflows.known(tenant_id):
        wanted = ordered_cites(workflow)
        if not wanted:
            continue
        # The whole doing, not only what is cited: the credential gesture is by
        # definition the one nothing cites, so a read narrowed to the citations
        # could never find it. Bounded by the span `with_passwords` then
        # applies -- this reads a tenant's gestures once per pass.
        #
        # ponytail: whole-store read per workflow; a `between(first, last)`
        # query when a tenant's day stops fitting comfortably in memory.
        by_id = {gesture.id: gesture for gesture in await uow.gestures.gestures_for(tenant_id)}
        if any(cited not in by_id for cited in wanted):
            continue
        # Both healings, and either one is a reason to save. `with_passwords`
        # adds the step a model cannot see; `with_the_press` repoints a step a
        # model aimed at the page instead of the button on it.
        if not with_passwords(workflow, by_id) + with_the_press(workflow, by_id):
            continue
        await uow.workflows.save(workflow)
        changed += 1
        logger.info("%s: healed the steps no model got right", workflow.title)
    return changed


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
        fresh = shape_key(in_time_order(workflow, by_id))
        if [list(triple) for triple in fresh] == workflow.shape_key:
            continue
        await uow.workflows.rekey(tenant_id, workflow.id, fresh)
        changed += 1
    if changed:
        await uow.commit()
    return changed
