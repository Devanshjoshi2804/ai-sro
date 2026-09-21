"""What the operator did after a step failed, taken as the repair for it.

A run's only self-repair is the locator ladder: when the job's own identity for
a control misses and a weaker rung finds it, the run writes that down and the
next run tries it first. That heals a control that MOVED. It does nothing at
all for a step that fails the same way every time on a control that is exactly
where the job says it is.

Measured on the deployment 2026-09-19. `Delete a Customer Type` failed four
times in twenty minutes, every time on its first step -- *"the filter dropdown
is not open on the screen"* -- and every time the operator did that click by
hand a moment later and carried on. All of it was captured: the tab was
watched, the gestures are in the store, and the miner read them a minute
later. Nothing reached the failing step, because mining resolves a whole new
demonstration into the existing job rather than repairing one step of it.

**So the rescue is the lesson.** A person who fixes by hand the exact thing a
run could not do has just demonstrated the repair, on the same screen, seconds
later. This is the rule for recognising that, and it is deliberately narrow:

**After the run, never during it.** A run drives the browser, and what it
drives is recorded like anything else. Only gestures after `finished_at` can
be the operator's own.

**Soon, or not at all.** `K_SOON` is minutes, not hours: the person who picks
the job up again after lunch is doing today's work, not correcting this run.

**On the screen the step was on.** A gesture in another system is somebody
getting on with something else.

**The first one, and only if it names a control.** The operator's next act is
the one that answers "what should this step have done"; a scroll or a click on
nothing names no control and teaches nothing.

**Never the job's own answer.** Where the job's recorded identity for that step
already matches what they clicked, there is nothing to learn: the step knew the
control and failed for another reason, and writing it down would be the job
telling itself what it already says.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from sro.domain.execution.evidence import locators_for
from sro.domain.execution.learned_step import K_NAME, LearnedStep
from sro.domain.observation.gesture import Gesture
from sro.domain.shared.hosts import origin_of
from sro.domain.skill.workflow import Step

K_SOON = 300.0
"""How long after a run a gesture can still be its repair, in seconds.

Five minutes. Long enough for somebody to read the card, look at the screen and
do the thing; short enough that the next morning's work is not read as a
correction to last night's failure."""

BY_HAND = "by_hand"
"""What wrote this locator down, where the ladder writes `sight` or `css_path`.

On the row so a person reading `workflow_learned_history` can tell a job that
healed itself from one a human repaired -- and so that the day this rule is
wrong about something, every row it wrote can be found."""


def rescued_by(
    step: Step,
    failed_at: str,
    since: float,
    gestures: Sequence[Gesture],
    cited: Mapping[str, Gesture],
) -> LearnedStep | None:
    """The control the operator used after this step failed, as a locator.

    `since` is the run's own end, as a gesture clock reads it; `failed_at` is
    the origin the step was working on.
    """
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
    """Whether the job's own evidence for this step already names that control."""
    for one in step.cites:
        gesture = cited.get(one)
        if gesture is None:
            continue
        for rung in locators_for(gesture):
            if rung.strategy == strategy and rung.query == query:
                return True
    return False


__all__ = ["BY_HAND", "K_SOON", "rescued_by"]
