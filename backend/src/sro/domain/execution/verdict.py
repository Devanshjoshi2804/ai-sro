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

_CLEAN_MEDIA = frozenset({Medium.NETWORK, Medium.TOOL})
"""The rungs a run can be clean at.

Both are calls whose result comes back to be checked. A gesture is not among
them because a gesture means the recorded call no longer works: the skill has
drifted from the system it was taught on, and a run that got there by clicking
has not shown that the skill still holds.

A tool call carries no such signal, which is the argument for it being here.
What it also carries is no demonstration -- nobody watched `send_message` work,
so its post-conditions are somebody's writing rather than two runs agreeing.
That is not answered here. It is answered by the rule every other step meets:
a write with no assertion makes the version unverifiable, and an unverifiable
version never reaches the top of the ladder however clean its runs are."""


def judge(run: Run) -> Verdict:
    # Before anything the steps say. A run can be clean at every rung and still
    # have made the wrong record, and the person who was looking at it is the
    # only one who could ever know.
    if run.wrong_because is not None:
        return Verdict.FAILED
    if run.status is not RunStatus.SUCCEEDED:
        return Verdict.UNREACHABLE if _nothing_answered(run) else Verdict.FAILED

    dispositions = {step.disposition for step in run.steps}
    if dispositions <= {StepDisposition.WITHHELD, StepDisposition.SKIPPED}:
        return Verdict.WITHHELD

    for step in run.steps:
        if step.assertion_failures:
            return Verdict.FAILED
        if step.medium not in _CLEAN_MEDIA or step.escalated_from is not None:
            return Verdict.DEGRADED
    return Verdict.CLEAN


def _nothing_answered(run: Run) -> bool:
    """Whether every step that did not work failed for want of anything to answer it.

    Strict in both directions, because this is the branch that excuses a run.
    One step that reached the system and got the wrong answer makes the whole
    run evidence again -- a skill does not get to hide a real failure behind a
    later closed laptop. And a run with no failed step at all, stopped before it
    started or killed mid-flight, is not excused either: nobody established that
    the system was unreachable, and "we do not know" is not "not our fault".
    """
    did_not_work = [step for step in run.steps if not step.ok]
    return bool(did_not_work) and all(step.unreachable for step in did_not_work)
