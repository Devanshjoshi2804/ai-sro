from __future__ import annotations

import logging
import secrets
from collections import Counter
from collections.abc import Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass, field, replace
from datetime import datetime
from typing import cast

from sro.application.intent.spend import over_cap
from sro.application.observation.chores import decide, evidence_of, evidenced, judged, verdict
from sro.application.ports.locks import AccountLocks
from sro.application.ports.model import Asker
from sro.application.ports.repositories import UnitOfWork
from sro.application.shared.asking import ask
from sro.domain.execution.compose import normal
from sro.domain.execution.uses_edges import uses_edges
from sro.domain.observation.driving import was_our_own_driving
from sro.domain.observation.gesture import Gesture, Intent
from sro.domain.observation.identity import Resolution, resolve, shape_key
from sro.domain.observation.mining import MiningPass
from sro.domain.observation.pool import K_MINE_ATTEMPTS, RETIRED_DRIVING
from sro.domain.observation.values import (
    frequencies_over,
    shared_values,
    worked_in_both,
)
from sro.domain.observation.window import (
    K_POOL_WAIT,
    Packed,
    Window,
    arrange,
    as_evidence,
    evidence_tokens,
    pack,
    strength,
)
from sro.domain.prompts.mine import MINE
from sro.domain.shared.errors import NotFound
from sro.domain.shared.hosts import origin_of
from sro.domain.shared.identifiers import TenantId
from sro.domain.shared.prices import Answer
from sro.domain.skill.checks import (
    K_MAX_SKEW,
    K_MIN_COVERAGE,
    K_SITTING_GAP_S,
    Coverage,
    Rejection,
    coverage,
    credentials_typed,
    one_occurrence,
    signs_in_to,
    undeliverable,
    validate,
    work_only,
)
from sro.domain.skill.learned import (
    K_PARAMETERS_RULE,
    TYPING,
    LearnedParameter,
    Occurrence,
    control_key,
    control_names,
    parameters_across,
    placed_doings,
    same_control,
    typed_across,
)
from sro.domain.skill.passwords import with_passwords
from sro.domain.skill.presses import with_the_press
from sro.domain.skill.repeats import detect as repeated_block
from sro.domain.skill.shape import cited_pairs, in_time_order, keeping_fields, typed_at
from sro.domain.skill.signing_in import Logins, recorded_logins
from sro.domain.skill.tabs import MAIN, tab_roles
from sro.domain.skill.umbrella import mining_blocks, workflow_from
from sro.domain.skill.workflow import Step, Workflow, cited_ids, ordered_cites
from sro.whose import attribute

__all__ = [
    "K_BRING_IN_TRIES",
    "MineResult",
    "bring_in_parameters",
    "decide_tabs",
    "fill_in_passwords",
    "learn_parameters",
    "mine",
    "mining_lock",
    "new_pass_id",
    "propose",
    "rekey_workflows",
    "shipped",
]

K_BRING_IN_TRIES = 3

logger = logging.getLogger(__name__)


def new_pass_id() -> str:
    return "pas_" + secrets.token_hex(16)


@dataclass
class MineResult:
    pass_id: str = ""
    proposed: int = 0
    kept: int = 0
    learned_parameters: int = 0
    rejections: list[Rejection] = field(default_factory=list)
    resolutions: list[Resolution] = field(default_factory=list)
    coverage: Coverage = field(default_factory=lambda: Coverage(0.0, 0.0, 0.0))
    in_tokens: int = 0
    out_tokens: int = 0
    thought_tokens: int = 0
    cost_usd: float = 0.0
    unpriced: bool = False
    error: str | None = None
    read: int = 0
    window_size: int = 0
    left_out: int = 0
    lost_pool: list[str] = field(default_factory=list)
    lopsided: bool = False
    unplaced: int = 0
    dropped: int = 0


async def propose(
    window: Window,
    crossings: dict[str, list[str]],
    known: list[dict[str, object]],
    kb: str,
    *,
    asker: Asker,
    tenant: str,
) -> tuple[list[Workflow], Answer]:
    day = [item.evidence for item in arrange(window.items)]
    answer = await ask(asker, MINE, trusted={}, untrusted=mining_blocks(day, crossings, known, kb))
    if answer.data is None:
        return [], answer

    raw = cast(list[object], answer.data["workflows"])

    proposed = [workflow_from(item, tenant) for item in raw]
    return [w for w in proposed if w is not None], answer


async def mine(
    uow: UnitOfWork,
    *,
    tenant_id: TenantId,
    asker: Asker,
    locks: AccountLocks,
    now: datetime,
    cap_usd: float,
    kb: str = "",
    ours: frozenset[str] = frozenset(),
) -> MineResult:
    async with locks.hold_named(mining_lock(tenant_id)):
        why = await over_cap(uow, tenant_id, now=now, cap_usd=cap_usd)
        if why:
            logger.warning("%s for %s, nothing mined", why, tenant_id.value)
            return MineResult(error=why)
        if await fill_in_passwords(uow, tenant_id=tenant_id):
            await uow.commit()
        else:
            await uow.rollback()
        return await _one_pass(
            uow,
            tenant_id=tenant_id,
            asker=asker,
            now=now,
            kb=kb,
            ours=ours,
        )


async def learn_parameters(
    uow: UnitOfWork,
    *,
    tenant_id: TenantId,
    known_id: str,
    doings: Sequence[Workflow],
    by_id: Mapping[str, Gesture],
    intents: Mapping[str, Intent],
    logins: Logins,
) -> int:
    try:
        stored = await uow.workflows.get(tenant_id, known_id, lock=True)
    except NotFound:
        return 0
    if stored.signs_in is None or stored.signs_out is None:
        return 0
    read = cited_ids(stored).union(*(cited_ids(doing) for doing in doings))
    if set(await uow.workflows.placed_on(tenant_id, known_id)) <= read:
        await uow.workflows.ruled(tenant_id, known_id, K_PARAMETERS_RULE)
    occurrences = [(stored, by_id, intents), *((doing, by_id, intents) for doing in doings)]
    typed: list[dict[str, object]] = [
        {"names": list(one.names), "key": one.key, "seen_values": list(one.seen)}
        for one in typed_across(occurrences)
    ]
    tied = _tied(stored.parameters, cited_pairs(stored, by_id))
    untied, holders = _pools(stored.parameters, typed)
    folded = _folded(stored.parameters, untied, holders)
    repaired = tied or len(folded) != len(stored.parameters)
    stored.parameters = folded

    found = [] if stored.chore else shipped(occurrences, by_id, logins)
    if not found:
        if repaired:
            await uow.workflows.save(stored)
        return 0
    fresh: list[dict[str, object]] = []
    widened = 0
    named = False
    told = False
    for parameter in found:
        existing = _known_by(parameter, stored.parameters) or _same_control(
            parameter, untied, holders
        )
        if existing is None:
            fresh.append(
                {
                    "name": parameter.name,
                    "names": list(parameter.names),
                    "key": parameter.key,
                    "seen_values": list(parameter.seen),
                    "in_all": parameter.in_all,
                    **({"required": parameter.required} if parameter.said is not None else {}),
                }
            )
            continue
        known = _names_of(existing)
        existing["names"] = [*known, *[one for one in parameter.names if one not in known]]
        existing["key"] = str(existing.get("key") or "") or parameter.key
        named = named or existing["names"] != known
        if parameter.said is not None and existing.get("required") != parameter.required:
            existing["required"] = parameter.required
            told = True
        was = existing.get("seen_values")
        seen = [str(value) for value in was] if isinstance(was, list) else []
        added = [value for value in parameter.seen if value not in seen]
        if added:
            existing["seen_values"] = [*seen, *added]
            widened += 1
    if not fresh and not widened and not repaired and not named and not told:
        return 0
    stored.parameters = _folded([*stored.parameters, *fresh], untied, holders)
    stored.generalise_title()
    await uow.workflows.save(stored)
    return len(fresh) + widened


def shipped(
    occurrences: Sequence[Occurrence], by_id: Mapping[str, Gesture], logins: Logins
) -> list[LearnedParameter]:
    """Every control the code rule makes a parameter, less the box the recorded
    sign-in types its username into on the system it signs in to."""
    read = set().union(*(cited_ids(one) for one, _, _ in occurrences))
    systems = {origin_of(by_id[one].system or "") for one in read if one in by_id} - {""}
    return [
        parameter
        for parameter in parameters_across(occurrences)
        if not {(system, normal(name)) for system in systems for name in parameter.names}
        & logins.labels
    ]


def _tied(parameters: list[dict[str, object]], cited: list[tuple[Gesture, Step]]) -> bool:
    """Ties each parameter that names no control to the one its step types it
    into, so it is only ever matched by that control and never by a value."""
    typing = [pair for pair in cited if pair[0].action.kind in TYPING]
    tied = False
    for parameter in parameters:
        at = None if _controlled(parameter) else typed_at(typing, parameter)
        if at is None:
            continue
        gesture = typing[at][0]
        names, key = control_names(gesture), control_key(gesture)
        if names or key:
            parameter["names"], parameter["key"] = list(names), key
            tied = True
    return tied


def _names_of(parameter: dict[str, object]) -> list[str]:
    listed = parameter.get("names")
    known = [str(one) for one in listed] if isinstance(listed, list) else []
    said = str(parameter.get("name") or "")
    return known if said in known or not said else [said, *known]


def _known_by(
    parameter: LearnedParameter, stored: list[dict[str, object]]
) -> dict[str, object] | None:
    for candidate in stored:
        if same_control(
            _names_of(candidate),
            list(parameter.names),
            key=str(candidate.get("key") or ""),
            theirs=parameter.key,
        ):
            return candidate
    return None


def _folded(
    parameters: list[dict[str, object]],
    untied: list[dict[str, object]],
    holders: list[dict[str, object]],
) -> list[dict[str, object]]:
    kept: list[dict[str, object]] = []
    for parameter in parameters:
        already = next(
            (
                one
                for one in kept
                if _one_control(one, parameter) or _held(one, parameter, untied, holders)
            ),
            None,
        )
        if already is None:
            kept.append(parameter)
            continue
        known = _names_of(already)
        already["names"] = [*known, *[one for one in _names_of(parameter) if one not in known]]
        already["key"] = str(already.get("key") or "") or str(parameter.get("key") or "")
        was, theirs = already.get("seen_values"), parameter.get("seen_values")
        seen = [str(value) for value in was] if isinstance(was, list) else []
        more = [str(value) for value in theirs] if isinstance(theirs, list) else []
        already["seen_values"] = [*seen, *[one for one in more if one not in seen]]
    return kept


def _values_of(parameter: dict[str, object]) -> set[str]:
    seen = parameter.get("seen_values")
    return {str(value) for value in seen} if isinstance(seen, list) else set()


def _controlled(parameter: dict[str, object]) -> bool:
    return bool(parameter.get("names") or parameter.get("key"))


def _one_control(one: dict[str, object], other: dict[str, object]) -> bool:
    return same_control(
        _names_of(one),
        _names_of(other),
        key=str(one.get("key") or ""),
        theirs=str(other.get("key") or ""),
    )


def _pools(
    parameters: list[dict[str, object]], typed: list[dict[str, object]]
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    """Every control known to have typed something: each field the doings
    typed into, fixed ones included, and each entry naming a control; and the
    entries naming no control whose name names none of those. An entry named
    after a control is that control's, never another's by value. Taken once,
    before any fold changes an entry: an entry folded into a field carries
    values that field never typed."""
    holders = [*typed, *(one for one in parameters if _controlled(one))]
    untied = [
        one
        for one in parameters
        if not _controlled(one) and not any(_one_control(one, held) for held in holders)
    ]
    return untied, holders


def _held_by(
    untied: dict[str, object],
    untieds: list[dict[str, object]],
    holders: list[dict[str, object]],
) -> dict[str, object] | None:
    """The one control that typed this entry's value, when exactly one control
    typed it and this is the only entry naming no control that holds what that
    control typed. Otherwise the value cannot say which, and nothing matches."""
    values = _values_of(untied)
    typed = [one for one in holders if values & _values_of(one)]
    if not typed or not all(_one_control(typed[0], one) for one in typed):
        return None
    alike = [one for one in untieds if _values_of(one) & _values_of(typed[0])]
    return typed[0] if len(alike) == 1 and alike[0] is untied else None


def _held(
    one: dict[str, object],
    other: dict[str, object],
    untieds: list[dict[str, object]],
    holders: list[dict[str, object]],
) -> bool:
    if _controlled(one) == _controlled(other):
        return False
    untied, control = (other, one) if _controlled(one) else (one, other)
    held = _held_by(untied, untieds, holders)
    return held is not None and _one_control(held, control)


def _same_control(
    parameter: LearnedParameter,
    untieds: list[dict[str, object]],
    holders: list[dict[str, object]],
) -> dict[str, object] | None:
    for candidate in untieds:
        held = _held_by(candidate, untieds, holders)
        if held is not None and same_control(
            _names_of(held), parameter.names, key=str(held.get("key") or ""), theirs=parameter.key
        ):
            return candidate
    return None


async def _grow(
    uow: UnitOfWork,
    *,
    tenant_id: TenantId,
    known_id: str,
    proposal: Workflow,
    by_id: dict[str, Gesture],
) -> None:
    try:
        stored = await uow.workflows.get(tenant_id, known_id, lock=True)
    except NotFound:
        return
    if credentials_typed(proposal, by_id) - credentials_typed(stored, by_id):
        logger.info("%s: not grown -- the doing types a credential the job never did", stored.title)
        return
    await uow.workflows.place(tenant_id, stored.id, tuple(ordered_cites(stored)))
    stored.steps, moved = keeping_fields(stored, proposal.steps, by_id)
    stored.shape_key = [list(entry) for entry in shape_key(in_time_order(stored, by_id))]
    await uow.workflows.grew(stored, moved=moved)
    await decide(uow, tenant_id, stored, by_id)
    logger.info(
        "%s: grew to %d step(s) from a doing that contained it",
        stored.title,
        len(stored.steps),
    )


def _packed(gesture: Gesture, intent: Intent | None, linked: set[str]) -> Packed:
    evidence = as_evidence(gesture, intent)
    return Packed(
        gesture_id=gesture.id,
        at=gesture.at,
        evidence=evidence,
        strength=strength(gesture, intent, linked),
        tokens=evidence_tokens(evidence),
        stream_id=gesture.stream_id,
    )


async def _one_pass(
    uow: UnitOfWork,
    *,
    tenant_id: TenantId,
    asker: Asker,
    now: datetime,
    kb: str,
    ours: frozenset[str] = frozenset(),
) -> MineResult:
    started_at = now.isoformat()
    pass_id = new_pass_id()
    attribute(tenant=tenant_id.value, pass_id=pass_id)

    gestures = list(await uow.gestures.gestures_for(tenant_id))
    everything = {gesture.id: gesture for gesture in gestures}
    intents = {intent.gesture_id: intent for intent in await uow.gestures.intents_for(tenant_id)}
    driven = {gesture_id for gesture_id, intent in intents.items() if was_our_own_driving(intent)}
    if driven:
        logger.info(
            "%s: %d gesture(s) left out of this pass -- this browser's own driving",
            tenant_id.value,
            len(driven),
        )
        gestures = [gesture for gesture in gestures if gesture.id not in driven]
    by_id = {gesture.id: gesture for gesture in gestures}

    crossings = shared_values(gestures, intents, frequencies_over(gestures, intents))
    linked = {gesture_id for ids in crossings.values() for gesture_id in ids}
    linked |= worked_in_both(gestures, gap=K_SITTING_GAP_S, ours=ours)

    stored_cites = await uow.workflows.placed(tenant_id)
    carried = await uow.pool.waiting(tenant_id)
    ours_driving = tuple(entry.gesture_id for entry in carried if entry.gesture_id in driven)
    if ours_driving:
        await uow.pool.retire(tenant_id, ours_driving, reason=RETIRED_DRIVING)
        logger.info(
            "%s: %d pooled gesture(s) retired -- this browser's own driving",
            tenant_id.value,
            len(ours_driving),
        )
        carried = tuple(entry for entry in carried if entry.gesture_id not in driven)
    pooled_ids = [entry.gesture_id for entry in carried]
    lost = [gesture_id for gesture_id in pooled_ids if gesture_id not in by_id]
    if lost:
        logger.warning("%d pooled gesture(s) have no gesture row: %s", len(lost), ", ".join(lost))
    pooled: list[Packed] = []
    for entry in carried:
        gesture = by_id.get(entry.gesture_id)
        if gesture is None or gesture.id in stored_cites:
            continue
        item = _packed(gesture, intents.get(entry.gesture_id), linked)
        item.strength += entry.waited * K_POOL_WAIT
        pooled.append(item)
    in_pool = set(pooled_ids)
    retired = {entry.gesture_id for entry in await uow.pool.retired(tenant_id)}
    fresh = [
        gesture
        for gesture in gestures
        if gesture.id not in in_pool
        and gesture.id not in retired
        and gesture.id not in stored_cites
    ]
    read = frozenset(entry.gesture_id for entry in carried if entry.age > 0)
    unread = {gesture.id for gesture in fresh} | {
        item.gesture_id for item in pooled if item.gesture_id not in read
    }

    known = list(await uow.workflows.known(tenant_id))
    known = [
        replace(one, shape_key=[list(entry) for entry in shape_key(in_time_order(one, by_id))])
        if cited_ids(one) & by_id.keys()
        else one
        for one in known
    ]
    lands = {
        one.id: where
        for one in known
        if one.signs_in and (where := signs_in_to(one, by_id)) is not None
    }
    summary: list[dict[str, object]] = [
        {"id": w.id, "title": w.title, "systems": w.systems, "shape_key": w.shape_key}
        for w in known
    ]

    window = pack(fresh, intents, pooled, summary, kb, linked=linked, read=read)
    if unread.isdisjoint(item.gesture_id for item in window.items):
        logger.info("%s: every gesture has been mined; the model is not asked", tenant_id.value)
        idle = MineResult(pass_id=pass_id, lost_pool=lost)
        await uow.workflows.add_pass(_billed(pass_id, tenant_id, started_at, idle))
        await uow.commit()
        return idle
    proposals, answer = await propose(
        window, crossings, summary, kb, asker=asker, tenant=tenant_id.value
    )

    residue = (answer.data or {}).get("unplaced")

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
        left_out=len(
            unread
            - ({item.gesture_id for item in window.items} if answer.data is not None else set())
        ),
        unplaced=len(residue) if isinstance(residue, list) else 0,
        dropped=answer.dropped,
        lost_pool=lost,
    )

    try:
        evidence = {item.gesture_id: by_id[item.gesture_id].system or "" for item in window.items}
        shown = {item.gesture_id: by_id[item.gesture_id] for item in window.items}

        kept: list[Workflow] = []
        placed: list[Workflow] = []
        for proposal in proposals:
            one_occurrence(proposal, by_id)
            typed = with_passwords(proposal, shown)
            if typed:
                logger.info(
                    "%s: %s credential step(s) the model could not see",
                    proposal.title,
                    typed,
                )
            pressed = with_the_press(proposal, shown)
            if pressed:
                logger.info(
                    "%s: %s step(s) repointed at the control the operator pressed",
                    proposal.title,
                    pressed,
                )
            for order, used in uses_edges(proposal, by_id).items():
                for step in proposal.steps:
                    if step.order == order:
                        step.uses = used
                        logger.info(
                            "%s: step %s uses the answer from step(s) %s",
                            proposal.title,
                            order,
                            ", ".join(str(one) for one in used),
                        )
            roles = tab_roles(proposal, by_id)
            for step in proposal.steps:
                step.tab = roles.get(step.order, MAIN)
            proposal.repeat = repeated_block(proposal, by_id)
            if proposal.repeat is not None:
                logger.info(
                    "%s: steps %s-%s are done once per thing",
                    proposal.title,
                    proposal.repeat.first_step,
                    proposal.repeat.last_step,
                )
            rejection = validate(proposal, evidence) or work_only(proposal, by_id, ours=ours)
            if rejection is not None:
                result.rejections.append(rejection)
                logger.info(
                    "%s: refused -- %s (%s)",
                    rejection.workflow_title,
                    rejection.reason,
                    rejection.detail,
                )
                continue
            proposal.signs_in, proposal.signs_out = judged(proposal, everything) or (None, None)
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
            proposal.shape_key = [
                list(entry) for entry in shape_key(in_time_order(proposal, by_id))
            ]
            where = signs_in_to(proposal, by_id) if proposal.signs_in else None
            if where is not None:
                lands[proposal.id] = where
            resolution = resolve(proposal, known + kept, signs_in_to=lands)
            if resolution.kind == "fragment":
                fragment = Rejection(
                    proposal.title, "fragment of a known job", resolution.workflow_id or ""
                )
                result.rejections.append(fragment)
                logger.info(
                    "%s: refused -- %s (%s)",
                    fragment.workflow_title,
                    fragment.reason,
                    fragment.detail,
                )
                continue
            result.resolutions.append(resolution)
            logger.info(
                "%s: %s%s",
                proposal.title,
                {
                    "new": "kept, nothing like it was stored",
                    "same_job": "recognised as a job already stored",
                    "same_occurrence": "this evidence has been read before",
                }.get(resolution.kind, resolution.kind),
                f" -- {resolution.workflow_id} at {resolution.score:.2f}"
                if resolution.workflow_id
                else "",
            )
            placed.append(proposal)
            if resolution.kind == "new":
                proposal.pass_id = pass_id
                await uow.workflows.save(proposal)
                kept.append(proposal)
                result.learned_parameters += await learn_parameters(
                    uow,
                    tenant_id=tenant_id,
                    known_id=proposal.id,
                    doings=(),
                    by_id=by_id,
                    intents=intents,
                    logins=recorded_logins([*known, *kept], by_id),
                )
            elif resolution.workflow_id:
                await uow.workflows.place(
                    tenant_id, resolution.workflow_id, tuple(ordered_cites(proposal))
                )
            if resolution.kind == "same_job" and resolution.workflow_id:
                result.learned_parameters += await learn_parameters(
                    uow,
                    tenant_id=tenant_id,
                    known_id=resolution.workflow_id,
                    doings=(proposal,),
                    by_id=by_id,
                    intents=intents,
                    logins=recorded_logins([*known, *kept], by_id),
                )
                if resolution.contains:
                    await _grow(
                        uow,
                        tenant_id=tenant_id,
                        known_id=resolution.workflow_id,
                        proposal=proposal,
                        by_id=everything,
                    )

        result.kept = len(kept)
        result.coverage = coverage(placed, window)
        result.lopsided = result.error is None and (
            result.coverage.coverage < K_MIN_COVERAGE or abs(result.coverage.skew) > K_MAX_SKEW
        )

        claimed = frozenset(c for w in placed for c in cited_ids(w)) | (in_pool & stored_cites)
        await uow.pool.add_unclaimed(
            tenant_id,
            window_ids=tuple(item.gesture_id for item in window.items) + tuple(window.left_out),
            claimed=claimed,
        )
        packed = tuple(item.gesture_id for item in window.items)
        if answer.data is not None:
            await uow.pool.age(tenant_id, shown=packed)
        elif answer.in_tokens:
            gone = await uow.pool.age(tenant_id, shown=packed, failed=True)
            logger.warning(
                "%s: the answer could not be used, so its %d gesture(s) stay unread; "
                "%d retired unminable after %d unusable answers",
                tenant_id.value,
                len(packed),
                gone,
                K_MINE_ATTEMPTS,
            )
    finally:
        billed = _billed(pass_id, tenant_id, started_at, result)
        try:
            await uow.workflows.add_pass(billed)
        except Exception:
            await uow.rollback()
            await uow.workflows.add_pass(billed)
        await uow.commit()
    return result


def _billed(pass_id: str, tenant_id: TenantId, started_at: str, result: MineResult) -> MiningPass:
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
        unplaced=result.unplaced,
        dropped=result.dropped,
        error=result.error,
    )


async def fill_in_passwords(uow: UnitOfWork, *, tenant_id: TenantId) -> int:
    healed: list[Workflow] = []
    by_id = {gesture.id: gesture for gesture in await uow.gestures.gestures_for(tenant_id)}
    for listed in await uow.workflows.known(tenant_id):
        if not evidenced(listed, by_id) or not (
            _healed(deepcopy(listed), by_id) or judged(listed, by_id) not in (None, verdict(listed))
        ):
            continue
        workflow = await uow.workflows.get(tenant_id, listed.id, lock=True)
        if await _mend(uow, tenant_id, workflow, by_id):
            healed.append(workflow)
    if healed:
        logins = recorded_logins(await uow.workflows.known(tenant_id), by_id)
        cites = tuple(sorted({one for job in healed for one in ordered_cites(job)}))
        intents = {
            one.gesture_id: one for one in await uow.gestures.intents_for(tenant_id, ids=cites)
        }
        for workflow in healed:
            await learn_parameters(
                uow,
                tenant_id=tenant_id,
                known_id=workflow.id,
                doings=(),
                by_id=by_id,
                intents=intents,
                logins=logins,
            )
    return len(healed)


async def _mend(
    uow: UnitOfWork, tenant_id: TenantId, workflow: Workflow, by_id: dict[str, Gesture]
) -> bool:
    healed = _healed(workflow, by_id)
    if healed:
        await uow.workflows.save(workflow)
        logger.info("%s: healed %d step(s) no model got right", workflow.title, healed)
    return await decide(uow, tenant_id, workflow, by_id) or bool(healed)


def _healed(workflow: Workflow, by_id: dict[str, Gesture]) -> int:
    found = repeated_block(workflow, by_id)
    changed = with_passwords(workflow, by_id) + with_the_press(workflow, by_id)
    if workflow.repeat != found:
        workflow.repeat = found
        changed += 1
    return changed


def mining_lock(tenant_id: TenantId) -> str:
    return f"mining:{tenant_id.value}"


async def decide_tabs(uow: UnitOfWork, tenant_id: TenantId, jobs: Sequence[Workflow]) -> int:
    by_id = await evidence_of(uow, tenant_id, jobs)
    decided = 0
    for job in jobs:
        roles = tab_roles(job, by_id)
        for step in job.steps:
            if step.tab is None:
                decided += await uow.workflows.decide_tab(
                    tenant_id, job.id, step.order, roles.get(step.order, MAIN)
                )
    return decided


async def rekey_workflows(uow: UnitOfWork, *, tenant_id: TenantId) -> int:
    changed = 0
    for workflow in await uow.workflows.known(tenant_id):
        wanted = ordered_cites(workflow)
        if not wanted:
            continue
        by_id = {
            gesture.id: gesture
            for gesture in await uow.gestures.gestures_for(tenant_id, ids=tuple(wanted))
        }
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


async def bring_in_parameters(
    uow: UnitOfWork, tenant_id: TenantId, jobs: Sequence[Workflow], failed: Counter[str]
) -> int:
    known = await uow.workflows.known(tenant_id)
    placed = {job.id: await uow.workflows.placed_on(tenant_id, job.id) for job in jobs}
    by_id = await evidence_of(uow, tenant_id, known)
    missing = tuple(sorted({one for ids in placed.values() for one in ids} - by_id.keys()))
    if missing:
        by_id.update(
            {one.id: one for one in await uow.gestures.gestures_for(tenant_id, ids=missing)}
        )
    read = {one for job in jobs for one in ordered_cites(job)}.union(*placed.values())
    intents = {
        one.gesture_id: one
        for one in await uow.gestures.intents_for(tenant_id, ids=tuple(sorted(read)))
    }
    logins = recorded_logins(known, by_id)
    brought = 0
    for job in jobs:
        try:
            held = await uow.workflows.get(tenant_id, job.id, lock=True)
            if await uow.workflows.ruled(tenant_id, job.id, K_PARAMETERS_RULE):
                brought += await learn_parameters(
                    uow,
                    tenant_id=tenant_id,
                    known_id=job.id,
                    doings=placed_doings(held, placed[job.id], by_id, intents),
                    by_id=by_id,
                    intents=intents,
                    logins=logins,
                )
            await uow.commit()
        except NotFound:
            await uow.rollback()
        except Exception:
            await uow.rollback()
            failed[job.id] += 1
            logger.exception(
                "%s: could not bring in its parameters (%d of %d tries%s)",
                job.title,
                failed[job.id],
                K_BRING_IN_TRIES,
                "; not tried again" if failed[job.id] >= K_BRING_IN_TRIES else "",
            )
    return brought
