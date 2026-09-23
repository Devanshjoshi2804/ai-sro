from __future__ import annotations

import logging
import secrets
from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from datetime import datetime

from sro.application.intent.spend import over_cap
from sro.application.ports.model import Asker
from sro.application.ports.repositories import UnitOfWork
from sro.application.shared.locks import one_at_a_time
from sro.domain.execution.uses_edges import uses_edges
from sro.domain.observation.driving import was_our_own_driving
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
    signs_in,
    undeliverable,
    validate,
    work_only,
)
from sro.domain.skill.learned import LearnedParameter, parameters_across, same_control
from sro.domain.skill.passwords import with_passwords
from sro.domain.skill.presses import with_the_press
from sro.domain.skill.repeats import detect as repeated_block
from sro.domain.skill.shape import in_time_order, where_steps_moved
from sro.domain.skill.umbrella import (
    K_EFFORT,
    WORKFLOW_SCHEMA,
    build_prompt,
    workflow_from,
)
from sro.domain.skill.workflow import Workflow, cited_ids, ordered_cites
from sro.whose import attribute

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
    answer = await asker.ask(
        model=model,
        instructions="",
        evidence=build_prompt(window, crossings, known, kb),
        schema=WORKFLOW_SCHEMA,
        effort=K_EFFORT,
    )
    if answer.data is None:
        return [], answer

    raw = answer.data.get("workflows")
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
    async with one_at_a_time(f"mining:{tenant_id.value}"):
        why = await over_cap(uow, tenant_id, now=now, cap_usd=cap_usd)
        if why:
            logger.warning("%s for %s, nothing mined", why, tenant_id.value)
            return MineResult(error=why)
        filled = await fill_in_passwords(uow, tenant_id=tenant_id)
        if filled:
            await uow.commit()
        return await _one_pass(
            uow,
            tenant_id=tenant_id,
            asker=asker,
            model=model,
            now=now,
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
    try:
        stored = await uow.workflows.get(tenant_id, known_id)
    except NotFound:
        return 0
    folded = _folded(stored.parameters)
    repaired = len(folded) != len(stored.parameters)
    stored.parameters = folded

    found = parameters_across([(stored, by_id, intents), (proposal, by_id, intents)])
    if not found:
        if repaired:
            await uow.workflows.save(stored)
        return 0
    by_name = {str(p["name"]): p for p in stored.parameters if "name" in p}
    fresh: list[dict[str, object]] = []
    widened = 0
    named = False
    told = False
    for parameter in found:
        existing = (
            by_name.get(parameter.name)
            or _known_by(parameter, stored.parameters)
            or _same_control(parameter, stored.parameters)
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
    stored.parameters = _folded([*stored.parameters, *fresh])
    stored.generalise_title()
    await uow.workflows.save(stored)
    return len(fresh) + widened


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


def _folded(parameters: list[dict[str, object]]) -> list[dict[str, object]]:
    kept: list[dict[str, object]] = []
    for parameter in parameters:
        names = _names_of(parameter)
        key = str(parameter.get("key") or "")
        already = next(
            (
                one
                for one in kept
                if same_control(_names_of(one), names, key=str(one.get("key") or ""), theirs=key)
                or _same_typing(one, parameter)
            ),
            None,
        )
        if already is None:
            kept.append(parameter)
            continue
        known = _names_of(already)
        already["names"] = [*known, *[one for one in names if one not in known]]
        already["key"] = str(already.get("key") or "") or key
        was, theirs = already.get("seen_values"), parameter.get("seen_values")
        seen = [str(value) for value in was] if isinstance(was, list) else []
        more = [str(value) for value in theirs] if isinstance(theirs, list) else []
        already["seen_values"] = [*seen, *[one for one in more if one not in seen]]
    return kept


def _values_of(parameter: dict[str, object]) -> set[str]:
    seen = parameter.get("seen_values")
    return {str(value) for value in seen} if isinstance(seen, list) else set()


def _same_typing(one: dict[str, object], other: dict[str, object]) -> bool:
    mine, theirs = _values_of(one), _values_of(other)
    if not mine or not theirs:
        return False
    return mine <= theirs or theirs <= mine


def _same_control(
    parameter: LearnedParameter, stored: list[dict[str, object]]
) -> dict[str, object] | None:
    wanted = set(parameter.seen)
    for candidate in stored:
        was = candidate.get("seen_values")
        if not isinstance(was, list):
            continue
        if wanted and wanted <= {str(value) for value in was}:
            return candidate
    return None


async def _grow(
    uow: UnitOfWork,
    *,
    tenant_id: TenantId,
    known_id: str,
    proposal: Workflow,
    by_id: Mapping[str, Gesture],
) -> None:
    try:
        stored = await uow.workflows.get(tenant_id, known_id)
    except NotFound:
        return
    moved = where_steps_moved(stored.steps, proposal.steps, by_id)
    stored.steps = list(proposal.steps)
    stored.signs_in = proposal.signs_in
    stored.shape_key = [list(entry) for entry in shape_key(in_time_order(stored, by_id))]
    await uow.workflows.grew(stored, moved=moved)
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
    model: str,
    now: datetime,
    kb: str,
    ours: frozenset[str] = frozenset(),
) -> MineResult:
    started_at = now.isoformat()
    pass_id = new_pass_id()
    attribute(tenant=tenant_id.value, pass_id=pass_id)

    gestures = list(await uow.gestures.gestures_for(tenant_id))
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

    carried = await uow.pool.waiting(tenant_id)
    pooled_ids = [entry.gesture_id for entry in carried]
    lost = [gesture_id for gesture_id in pooled_ids if gesture_id not in by_id]
    if lost:
        logger.warning("%d pooled gesture(s) have no row: %s", len(lost), ", ".join(lost))
    pooled: list[Packed] = []
    for entry in carried:
        gesture = by_id.get(entry.gesture_id)
        if gesture is None:
            continue
        item = _packed(gesture, intents.get(entry.gesture_id), linked)
        item.strength += entry.waited * K_POOL_WAIT
        pooled.append(item)
    in_pool = set(pooled_ids)
    fresh = [gesture for gesture in gestures if gesture.id not in in_pool]

    known = list(await uow.workflows.known(tenant_id))
    known = [
        replace(one, shape_key=[list(entry) for entry in shape_key(in_time_order(one, by_id))])
        if cited_ids(one) & by_id.keys()
        else one
        for one in known
    ]
    summary: list[dict[str, object]] = [
        {"id": w.id, "title": w.title, "systems": w.systems, "shape_key": w.shape_key}
        for w in known
    ]

    window = pack(fresh, intents, pooled, summary, kb, linked=linked)
    proposals, answer = await propose(
        window, crossings, summary, kb, asker=asker, model=model, tenant=tenant_id.value
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
        left_out=len(window.left_out),
        unplaced=len(residue) if isinstance(residue, list) else 0,
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
            proposal.signs_in = signs_in(proposal, by_id)
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
            resolution = resolve(proposal, known + kept)
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
            elif resolution.kind == "same_job" and resolution.workflow_id:
                result.learned_parameters += await learn_parameters(
                    uow,
                    tenant_id=tenant_id,
                    known_id=resolution.workflow_id,
                    proposal=proposal,
                    by_id=by_id,
                    intents=intents,
                )
                if resolution.contains:
                    await _grow(
                        uow,
                        tenant_id=tenant_id,
                        known_id=resolution.workflow_id,
                        proposal=proposal,
                        by_id=by_id,
                    )

        result.kept = len(kept)
        result.coverage = coverage(placed, window)
        result.lopsided = result.error is None and (
            result.coverage.coverage < K_MIN_COVERAGE or abs(result.coverage.skew) > K_MAX_SKEW
        )

        claimed = frozenset(c for w in placed for c in cited_ids(w))
        await uow.pool.add_unclaimed(
            tenant_id,
            window_ids=tuple(item.gesture_id for item in window.items) + tuple(window.left_out),
            claimed=claimed,
        )
        if result.error is None:
            await uow.pool.age(tenant_id, shown=tuple(item.gesture_id for item in window.items))
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
        error=result.error,
    )


async def fill_in_passwords(uow: UnitOfWork, *, tenant_id: TenantId) -> int:
    changed = 0
    by_id = {gesture.id: gesture for gesture in await uow.gestures.gestures_for(tenant_id)}
    for workflow in await uow.workflows.known(tenant_id):
        wanted = ordered_cites(workflow)
        if not wanted:
            continue
        if any(cited not in by_id for cited in wanted):
            continue
        found = repeated_block(workflow, by_id)
        changed_here = with_passwords(workflow, by_id) + with_the_press(workflow, by_id)
        if workflow.repeat != found:
            workflow.repeat = found
            changed_here += 1
        marked = signs_in(workflow, by_id)
        if workflow.signs_in != marked:
            workflow.signs_in = marked
            changed_here += 1
        if not changed_here:
            continue
        await uow.workflows.save(workflow)
        changed += 1
        logger.info("%s: healed the steps no model got right", workflow.title)
    return changed


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
