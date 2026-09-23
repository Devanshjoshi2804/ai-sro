# Notes for `backend/src/sro/domain/execution/verdict.py`

Comments and docstrings moved out of [`backend/src/sro/domain/execution/verdict.py`](../../../../../../../backend/src/sro/domain/execution/verdict.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/domain/execution/verdict.py#L1): Docstring

> What a finished run says about the skill that produced it.
>
> A run either proves the skill still works, or proves it is drifting from the
> system it was taught on. The distinction is not "did it succeed": a run that
> succeeded only because a model looked at the screen and found the button
> somewhere new succeeded *and* told us the recipe is stale.

## module, [line 12](../../../../../../../backend/src/sro/domain/execution/verdict.py#L12): Note on the line above

Code: `_CLEAN_MEDIA = frozenset({Medium.NETWORK, Medium.TOOL})`

> The rungs a run can be clean at.
>
> Both are calls whose result comes back to be checked. A gesture is not among
> them because a gesture means the recorded call no longer works: the skill has
> drifted from the system it was taught on, and a run that got there by clicking
> has not shown that the skill still holds.
>
> A tool call carries no such signal, which is the argument for it being here.
> What it also carries is no demonstration -- nobody watched `send_message` work,
> so its post-conditions are somebody's writing rather than two runs agreeing.
> That is not answered here. It is answered by the rule every other step meets:
> a write with no assertion makes the version unverifiable, and an unverifiable
> version never reaches the top of the ladder however clean its runs are.

## `apply_verdict`, [line 33](../../../../../../../backend/src/sro/domain/execution/verdict.py#L33): Docstring

> Judge a finished run against the skill it performed, and let the ladder move.
>
> One function, called by every use case that finishes a run's story --
> `FinishRun` when a run ends on its own, `CallRunWrong` again later when the
> person who watched it run says the result was wrong -- because a skill's
> rung must not depend on which of them happened to be the one that ran. The
> second of those is revising the first's answer about one run, never adding
> a second run to the record, which is what `revising` is for.
>
> This codebase already refuses a second opinion on `url_shape`, on
> `blank_inputs`, on the escalation table; two hand-synced copies of
> promote-and-demote is that same defect: a future change to either would
> have to be remembered and hand-applied to the other, and nothing would
> catch a miss except behavioural surprise.

## `_nothing_answered`, [line 49](../../../../../../../backend/src/sro/domain/execution/verdict.py#L49): Docstring

> Whether every step that did not work failed for want of anything to answer it.
>
> Strict in both directions, because this is the branch that excuses a run.
> One step that reached the system and got the wrong answer makes the whole
> run evidence again -- a skill does not get to hide a real failure behind a
> later closed laptop. And a run with no failed step at all, stopped before it
> started or killed mid-flight, is not excused either: nobody established that
> the system was unreachable, and "we do not know" is not "not our fault".

## `judge`, [line 16](../../../../../../../backend/src/sro/domain/execution/verdict.py#L16): Comment

Code: `if run.wrong_because is not None:`

> Before anything the steps say. A run can be clean at every rung and still
> have made the wrong record, and the person who was looking at it is the
> only one who could ever know.

## `apply_verdict`, [line 38](../../../../../../../backend/src/sro/domain/execution/verdict.py#L38): Comment

Code: `version.record_run(verdict, now, revising=revising)`

> `revising` is the verdict this same run was already counted under, where
> the caller is judging a run somebody else finished. One run is one run:
> counting both entries left a version claiming two attempts for one, with
> `total_runs` and `clean_runs` overstating for good and `earn` able to
> promote on the strength of a clean run the operator was in the middle of
> calling wrong.

## `apply_verdict`, [line 39](../../../../../../../backend/src/sro/domain/execution/verdict.py#L39): Comment

Code: `version.earn(verdict, now)`

> The ladder climbs itself. Nobody has time to notice that a skill has
> earned the next rung, and a stage that waits for someone to notice is a
> fact about their afternoon rather than about the skill.

## `apply_verdict`, [line 40](../../../../../../../backend/src/sro/domain/execution/verdict.py#L40): Comment

Code: `if version.track_record.should_demote and version.stage.rung > PromotionStage.SHADOW.rung:`

> Demotion is automatic and needs no human, which is exactly why it is
> bounded by a small number: confirming a few runs costs an operator
> minutes, and a broken autonomous skill keeps writing.
