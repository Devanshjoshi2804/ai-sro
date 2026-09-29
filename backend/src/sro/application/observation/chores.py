from __future__ import annotations

import logging
import math
from collections.abc import Mapping, Sequence
from copy import deepcopy

from sro.application.ports.repositories import UnitOfWork
from sro.domain.observation.gesture import Gesture
from sro.domain.shared.identifiers import TenantId
from sro.domain.skill.checks import K_SITTING_GAP_S, signs_in, signs_out
from sro.domain.skill.passwords import with_passwords
from sro.domain.skill.presses import with_the_press
from sro.domain.skill.workflow import Workflow, ordered_cites

__all__ = ["decide", "decide_sign_ins", "evidence_of", "evidenced", "judged", "verdict"]

logger = logging.getLogger(__name__)


def evidenced(workflow: Workflow, by_id: Mapping[str, Gesture]) -> bool:
    wanted = ordered_cites(workflow)
    return bool(wanted) and all(cited in by_id for cited in wanted)


def _sitting(workflow: Workflow, by_id: Mapping[str, Gesture]) -> dict[str, Gesture]:
    wanted = set(ordered_cites(workflow))
    times = [by_id[one].at for one in wanted]
    first, last = min(times), max(times) + K_SITTING_GAP_S
    return {
        gesture.id: gesture
        for gesture in by_id.values()
        if gesture.id in wanted or first <= gesture.at <= last
    }


def judged(workflow: Workflow, by_id: Mapping[str, Gesture]) -> tuple[bool, bool] | None:
    if not evidenced(workflow, by_id):
        return None
    seen = _sitting(workflow, by_id)
    healed = deepcopy(workflow)
    with_passwords(healed, seen)
    with_the_press(healed, seen)
    return signs_in(healed, seen), signs_out(healed, seen)


def verdict(workflow: Workflow) -> tuple[bool | None, bool | None]:
    return workflow.signs_in, workflow.signs_out


async def decide(
    uow: UnitOfWork, tenant_id: TenantId, workflow: Workflow, by_id: Mapping[str, Gesture]
) -> bool:
    now = judged(workflow, by_id)
    if now is None or now == verdict(workflow):
        return False
    written = await uow.workflows.decide(tenant_id, workflow, signs_in=now[0], signs_out=now[1])
    if written:
        logger.info(
            "%s: decided from its evidence -- signs in: %s, signs out: %s",
            workflow.title,
            now[0],
            now[1],
        )
    return written


async def evidence_of(
    uow: UnitOfWork, tenant_id: TenantId, jobs: Sequence[Workflow]
) -> dict[str, Gesture]:
    cited = tuple(sorted({one for job in jobs for one in ordered_cites(job)}))
    if not cited:
        return {}
    seen = {
        gesture.id: gesture for gesture in await uow.gestures.gestures_for(tenant_id, ids=cited)
    }
    for job in jobs:
        times = [seen[one].at for one in ordered_cites(job) if one in seen]
        if not times:
            continue
        around = await uow.gestures.gestures_for(
            tenant_id,
            after=math.nextafter(min(times), -math.inf),
            before=max(times) + K_SITTING_GAP_S,
        )
        seen.update({gesture.id: gesture for gesture in around})
    return seen


async def decide_sign_ins(uow: UnitOfWork, tenant_id: TenantId, jobs: Sequence[Workflow]) -> int:
    by_id = await evidence_of(uow, tenant_id, jobs)
    decided = 0
    for job in jobs:
        decided += await decide(uow, tenant_id, job, by_id)
    return decided
