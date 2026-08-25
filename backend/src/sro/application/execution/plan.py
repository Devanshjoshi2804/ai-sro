"""Which step a run performs next, when some of them are done once per thing.

A run's log is positional: the first thing performed is position 0, the second
is position 1, and that is what makes "has this already been done" answerable
after a crash. Without loops the position and the step of the plan are the same
number, which is every skill taught before loops existed.

With a loop they part company, and the expansion cannot be computed up front:
how many times the body runs is the length of a list the system itself returns
partway through. So it is computed from what the run has learned so far, and it
grows as the run goes.
"""

from __future__ import annotations

from dataclasses import dataclass

from sro.domain.execution.run import Run
from sro.domain.skill.skill import SkillVersion


@dataclass(frozen=True, slots=True)
class Next:
    step_index: int
    iteration: int
    values: dict[str, str]
    """What this step is performed with: the run's own values, and the fields of
    the thing this time round the loop is acting on."""

    of: int = 1
    """How many iterations this loop has in total, for the run to say so."""


def next_step(version: SkillVersion, run: Run) -> Next | None:
    """The step at the run's next position, or None when there is nothing left.

    None also where the plan cannot be expanded yet -- but that cannot happen in
    practice: a loop's list is produced by a step *before* its body, so by the
    time the position reaches the body the count is known. If it ever does, the
    honest answer is to stop rather than to guess a count.
    """
    wanted = len(run.steps)
    position = 0
    step_index = 0
    while step_index < len(version.steps):
        loop = version.loop_at(step_index)
        if loop is None:
            if position == wanted:
                return Next(step_index=step_index, iteration=0, values=dict(run.values))
            position += 1
            step_index += 1
            continue

        bindings = run.iterations_of(loop.first_step)
        if bindings is None:
            return None
        for iteration, bound in enumerate(bindings):
            for body_step in loop.body:
                if position == wanted:
                    return Next(
                        step_index=body_step,
                        iteration=iteration,
                        values={**run.values, **bound},
                        of=len(bindings),
                    )
                position += 1
        step_index = loop.last_step + 1

    return None


def total_positions(version: SkillVersion, run: Run) -> int:
    """How many steps this run will perform, as far as it can be known now.

    A hint, not a contract: the count grows when a loop's list arrives. Used for
    saying "step 3 of 7" and nothing that decides anything.
    """
    total = 0
    step_index = 0
    while step_index < len(version.steps):
        loop = version.loop_at(step_index)
        if loop is None:
            total += 1
            step_index += 1
            continue
        bindings = run.iterations_of(loop.first_step)
        total += len(loop.body) * (len(bindings) if bindings is not None else 1)
        step_index = loop.last_step + 1
    return total
