# Notes for `backend/src/sro/application/induction/narration.py`

Comments and docstrings moved out of [`backend/src/sro/application/induction/narration.py`](../../../../../../../backend/src/sro/application/induction/narration.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/induction/narration.py#L1): Docstring

> Narration lined up against frames.
>
> **Narration labels; evidence decides.** What the operator said becomes a note on
> a step, a branch a reviewer is asked about, and a flag that a human belongs in
> the loop. It never becomes a parameter, a step, or a request: those come from
> the two-run diff, which is the whole reason this system does not guess.
>
> The distinction is kept in the data too. A step's ``intent`` stays derived from
> what was observed; the words go in ``narration``. One field holding either would
> make a transcript indistinguishable from evidence at review time.

## module, [line 8](../../../../../../../backend/src/sro/application/induction/narration.py#L8): Note on the line above

Code: `_BRANCH_MARKERS = (`

> Spoken conditionals. A branch is *proposed* from these, never taken: the
> demonstration only ever walked one path, so the other one has no evidence.

## `StepNarration`, [line 34](../../../../../../../backend/src/sro/application/induction/narration.py#L34): Note on the line above

Code: `branch_hint: str | None = None`

> Something the operator said would happen differently. Surfaced for a
> reviewer to confirm; never an executable path.

## `align`, [line 39](../../../../../../../backend/src/sro/application/induction/narration.py#L39): Docstring

> What was said during each frame's window.
>
> A frame's window runs from when it happened to when the next one did; the
> last frame's window stays open, because the operator's summing-up ("and that
> is the adjustment queued for approval") arrives after the final click and is
> the most useful sentence in the recording.

## `_branch_hint`, [line 60](../../../../../../../backend/src/sro/application/induction/narration.py#L60): Docstring

> The first sentence that describes a path this demonstration did not take.
