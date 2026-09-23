# Notes for `backend/src/sro/application/knowledge/learn_from_run.py`

Comments and docstrings moved out of [`backend/src/sro/application/knowledge/learn_from_run.py`](../../../../../../../backend/src/sro/application/knowledge/learn_from_run.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/knowledge/learn_from_run.py#L1): Docstring

> What a run proved, written back as knowledge.
>
> This is the half of the loop that makes the store more than a scrape. The
> catalogue says an endpoint exists; a verified run says what it answers, for this
> tenant, at this facility, today. Evidence outranks arrival order, so a later
> re-scrape cannot undo it -- see ``domain/knowledge/supersede.py``.
>
> Only from a run that verified. A step that failed its assertions proves nothing
> about the system except that the skill and the system disagree, and recording
> that as knowledge would teach the store the skill's bugs.

## `_worth_recording`, [line 35](../../../../../../../backend/src/sro/application/knowledge/learn_from_run.py#L35): Docstring

> Sent, answered, and checked. Anything less is not evidence about the WMS.
>
> A withheld shadow write in particular says nothing: the request was built
> and never left, so its status is unknown rather than good.

## `_control_claims`, [line 66](../../../../../../../backend/src/sro/application/knowledge/learn_from_run.py#L66): Docstring

> Which locator actually found each control, run after run.
>
> A skill carries several ways to find a control, strongest first, and the
> driver takes the first that resolves. Which one won was recorded on the run
> and read by nobody -- so a step that has quietly fallen through to its
> last-resort CSS path, or that no locator finds at all any more and only a
> model looking at the screen can reach, looks exactly like a step that works.
> It does work. It is also one screen change from not working, and the system
> knew and said nothing.
>
> Two things a run has to have before it says anything here:
>
> **It checked.** A step whose post-conditions nothing evaluated -- it asserts
> none, or none of them can be seen from a browser, or the screen could not be
> read -- proves the gesture landed and nothing else. `ok` is true for a step
> with no assertions and the run comes out SUCCEEDED, so "verified" has to be
> asked for rather than inferred from the absence of a failure.
>
> **It agreed with itself.** A loop's body is one step done once per thing in
> the list, and eleven iterations matching as taught with one falling back is
> a race or a page that had not settled, not a control that moved. A run whose
> own iterations disagree about which locator found a control has no answer to
> record, so it records none.

## `_agreed`, [line 92](../../../../../../../backend/src/sro/application/knowledge/learn_from_run.py#L92): Docstring

> What each step of the plan found its control by, where the run is sure.
>
> Keyed by the step of the version, not by the position in the run's log: a
> looped step appears at as many positions as there were things in the list,
> and they are all observations of one control.

## `_claim`, [line 50](../../../../../../../backend/src/sro/application/knowledge/learn_from_run.py#L50): Comment

Code: `key=f"{step.method} {path}",`

> Keyed by what was done, not by which skill did it: two skills calling
> the same endpoint are two observations of one fact.

## `_claim`, [line 62](../../../../../../../backend/src/sro/application/knowledge/learn_from_run.py#L62): Comment

Code: `evidence=EvidenceLevel.REPRODUCED,`

> Reproduced rather than round-trip: the run made the call and checked
> the answer, which is not the same as creating, reading back, changing
> and deleting. Claiming the higher level here would be the exact
> inflation the knowledge base's own audit was written about.

## `_control_claims`, [line 73](../../../../../../../backend/src/sro/application/knowledge/learn_from_run.py#L73): Comment

Code: `key=f"control {taught.describe()}",`

> The control, not the skill: two skills clicking one button are two
> observations of where that button is, the same way two skills
> calling one endpoint are two observations of what it answers.
