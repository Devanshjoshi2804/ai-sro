from __future__ import annotations

from dataclasses import dataclass

from sro.domain.execution.run import Run
from sro.domain.skill.skill import SkillVersion


@dataclass(frozen=True, slots=True)
class Next:
    step_index: int
    iteration: int
    values: dict[str, str]

    of: int = 1


def next_step(version: SkillVersion, run: Run) -> Next | None:
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
