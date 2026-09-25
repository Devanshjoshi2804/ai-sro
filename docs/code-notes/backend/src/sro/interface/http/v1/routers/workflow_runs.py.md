# Notes for `backend/src/sro/interface/http/v1/routers/workflow_runs.py`

Comments and docstrings moved out of [`backend/src/sro/interface/http/v1/routers/workflow_runs.py`](../../../../../../../../../backend/src/sro/interface/http/v1/routers/workflow_runs.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## `start_workflow_run`, [line 140](../../../../../../../../../backend/src/sro/interface/http/v1/routers/workflow_runs.py#L140): Comment

Code: `await container.record_attempt().execute(`

> The press itself, before anything the run does. What the run then makes
> of it is the run's own row; this is the record that somebody asked --
> and `undoes_run` is what makes an undo legible as the press it is rather
> than as another run of a delete.

## `get_workflow_run`, [line 209](../../../../../../../../../backend/src/sro/interface/http/v1/routers/workflow_runs.py#L209): Comment

Code: `return WorkflowRunModel.of(run, await reader.undo_for(ctx, run))`

> And whether anything this tenant has been seen doing takes back what it
> made. Asked here rather than in the model: it reads the tenant's jobs and
> their evidence, and a response model that went to a repository would be a
> response model with a session.

## `approve_workflow_step`, [line 324](../../../../../../../../../backend/src/sro/interface/http/v1/routers/workflow_runs.py#L324): Comment

Code: `await container.record_attempt().execute(`

> `resumed` is whether the tap actually released anything. A second tap on
> a card that has already gone through answers 200 and moves nothing --
> which, from the person tapping it, is a button that did nothing.
