# Notes for `backend/src/sro/application/skill/job_facts.py`

Notes for [`backend/src/sro/application/skill/job_facts.py`](../../../../../../../backend/src/sro/application/skill/job_facts.py). Each note names the code it explains (function or class, then the line in the current file) and says what the code does and why.

## `JobFacts`, [line 20](../../../../../../../backend/src/sro/application/skill/job_facts.py#L20): Docstring

> What the runtime loads for one job, and the compile check over it. `aliases`
> is empty until R2 stores them.

## `job_facts`, [line 29](../../../../../../../backend/src/sro/application/skill/job_facts.py#L29): Docstring

> Called inside an open unit of work. One ledger read and one gesture read for
> every job, then one `learned_for` and one `broken_for` per job.
>
> Ceiling: N+1 queries for N jobs. Upgrade path: batch `learned_for` and
> `broken_for` by tenant when a tenant holds hundreds of jobs.

## `runnable_jobs`, [line 50](../../../../../../../backend/src/sro/application/skill/job_facts.py#L50): Docstring

> Only a job that compiles is offered (spec §3). The one filter every offer
> path goes through: the chat door (`read_utterance`, which the panel's ask
> and the chat both reach) and the mail door (`FromTheMail`). A job that does
> not compile is logged with its reason codes, so the operator reading the
> log sees why a request did not match it; its reasons also show on the
> console's job page.
>
> The model is only ever shown runnable jobs, so a mail asking for a job that
> cannot run is read as asking for none: the reader cannot name a job it was
> not shown. The log line is per job at load time for that reason.
