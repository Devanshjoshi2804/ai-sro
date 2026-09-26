# Notes for `backend/src/sro/application/skill/job_facts.py`

Notes for [`backend/src/sro/application/skill/job_facts.py`](../../../../../../../backend/src/sro/application/skill/job_facts.py). Each note names the code it explains (function or class, then the line in the current file) and says what the code does and why.

## `_SAID`, [line 20](../../../../../../../backend/src/sro/application/skill/job_facts.py#L20): Constant

> The reason codes last logged for each (tenant, job), so a job that cannot run
> is logged once per change and not on every mail tick or chat sentence.
>
> ponytail: process-local memory, one entry per job ever compiled in this
> process, and each process logs its own first sighting. Upgrade path: keep the
> last codes on the job row when the log must be exactly once across workers.

## `JobFacts`, [line 24](../../../../../../../backend/src/sro/application/skill/job_facts.py#L24): Docstring

> What the runtime loads for one job, and the compile check over it. `aliases`
> is empty until R2 stores them.

## `_say_once`, [line 33](../../../../../../../backend/src/sro/application/skill/job_facts.py#L33): Docstring

> Logs "cannot run: <codes>" when a job's reasons change, and forgets a job that
> compiles again so its next breakage is logged afresh. Only the job-level view
> is logged: a start's compile, with its own values and start point, is the
> run's business and is said in the start's refusal.

## `job_facts`, [line 42](../../../../../../../backend/src/sro/application/skill/job_facts.py#L42): Docstring

> Called inside an open unit of work, by every reader of a job's runnability:
> the chat and mail doors (which show the reader every job and answer a
> non-runnable pick with its reasons), the start (the one gate every start path
> passes), the console's job list and `make recipe`. `now` decides which
> broken lanes have cooled down (`K_BROKEN_COOL_DOWN`), the same way the run
> itself decides.
>
> ponytail: 2N+2 queries for N jobs -- one ledger read and one gesture read,
> then one `learned_for` and one `broken_for` per job -- on every mail tick
> per operator and every chat sentence. Upgrade path: batch `learned_for` and
> `broken_for` by tenant when a tenant holds hundreds of jobs.
>
> `declared` (C2 round 0b): the knowledge base's field limits for this job,
> read once per job through the same helpers `_ask_for_values`
> (`application.execution.workflow_runs`) already used for a pending
> question -- `names_of`, `screen_for` and `declared_limits`
> (`application.execution.declared`) -- so every caller of `job_facts`, not
> only the one that was already asking, compiles a job whose `Compiled
> .fields` carry a knowledge-base-only limit (spec's controller amendment,
> 2026-09-26: the stricter of page and knowledge base wins, and a limit the
> page never shows is still enforced). Skipped when the job declares no
> parameters, since `declared_limits` has nothing to look up.
