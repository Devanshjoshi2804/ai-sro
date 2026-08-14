"""What a finished run says about the skill that produced it.

A run either proves the skill still works, or proves it is drifting from the
system it was taught on. The distinction is not "did it succeed": a run that
succeeded only because a model looked at the screen and found the button
somewhere new succeeded *and* told us the recipe is stale.
"""

from __future__ import annotations

from sro.domain.execution.run import Medium, Run, RunStatus, StepDisposition
from sro.domain.skill.track_record import Verdict

__all__ = ["Verdict", "judge"]


def judge(run: Run) -> Verdict:
    if run.status is not RunStatus.SUCCEEDED:
        return Verdict.FAILED

    dispositions = {step.disposition for step in run.steps}
    if dispositions <= {StepDisposition.WITHHELD, StepDisposition.SKIPPED}:
        return Verdict.WITHHELD

    for step in run.steps:
        if step.assertion_failures:
            return Verdict.FAILED
        if step.medium is not Medium.NETWORK or step.escalated_from is not None:
            return Verdict.DEGRADED
    return Verdict.CLEAN
