from __future__ import annotations

from collections.abc import Mapping, Sequence

from sro.domain.execution.evidence import locators_for
from sro.domain.execution.learned_step import K_NAME, LearnedStep
from sro.domain.observation.gesture import Gesture
from sro.domain.shared.hosts import origin_of
from sro.domain.skill.workflow import Step

K_SOON = 300.0

BY_HAND = "by_hand"


def rescued_by(
    step: Step,
    failed_at: str,
    since: float,
    gestures: Sequence[Gesture],
    cited: Mapping[str, Gesture],
) -> LearnedStep | None:
    origin = origin_of(failed_at)
    if not origin:
        return None
    after = sorted(
        (
            one
            for one in gestures
            if since < one.at <= since + K_SOON
            and origin_of(one.url or one.system or "") == origin
            and one.action.target is not None
        ),
        key=lambda one: one.at,
    )
    if not after:
        return None
    rungs = locators_for(after[0])
    if not rungs:
        return None
    strongest = rungs[0]
    if _already_says(step, cited, strongest.strategy, strongest.query):
        return None
    return LearnedStep(step.order, strongest.strategy, strongest.query[:K_NAME], BY_HAND)


def _already_says(step: Step, cited: Mapping[str, Gesture], strategy: str, query: str) -> bool:
    for one in step.cites:
        gesture = cited.get(one)
        if gesture is None:
            continue
        for rung in locators_for(gesture):
            if rung.strategy == strategy and rung.query == query:
                return True
    return False


__all__ = ["BY_HAND", "K_SOON", "rescued_by"]
