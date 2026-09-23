# Notes for `backend/src/sro/application/intent/plan_task.py`

Comments and docstrings moved out of [`backend/src/sro/application/intent/plan_task.py`](../../../../../../../backend/src/sro/application/intent/plan_task.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/intent/plan_task.py#L1): Docstring

> What the knowledge base says a task would involve, when nothing was taught.
>
> A proposal is not a skill. It cites screens, endpoints and form models rather
> than two demonstrations, so it has no evidence that anybody ever performed it
> successfully -- which is exactly the difference `docs/12` draws around generated
> workflows. It is shown to an operator, and the honest next move is usually
> "teach me this once".
>
> Nothing here is executable. Turning a proposal into something that runs means
> giving it provenance, and provenance comes from doing the task, not from reading
> about it.

## `_step`, [line 88](../../../../../../../backend/src/sro/application/intent/plan_task.py#L88): Comment

Code: `prefix = "known to be wrong: " if entry.body.get("falsified") else "watch out: "`

> A falsified claim is included on purpose: "this looked true and
> was not" is the warning an operator most needs before trying it.
