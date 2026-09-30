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
> ponytail: 2N+4 queries for N jobs where at least one declares a
> parameter, else 2N+2 -- one ledger read, one gesture read and (round 1)
> one field-claim read and one form-claim read (`kb_rows`, tenant-wide, not
> per job), then one `learned_for` and one `broken_for` per job -- on every
> mail tick per operator and every chat sentence. Upgrade path: batch
> `learned_for` and `broken_for` by tenant when a tenant holds hundreds of
> jobs.
>
> `declared` (C2 round 0b, corrected round 1 I2): the knowledge base's field
> limits for this job, so every caller of `job_facts`, not only the pending
> question `ask_for_values` (`application.execution.workflow_runs`) already
> asked, compiles a job whose `Compiled.fields` carry a knowledge-base-only
> limit (spec's controller amendment, 2026-09-26: the stricter of page and
> knowledge base wins, and a limit the page never shows is still enforced).
>
> Round 0b called `declared_limits`/`screen_for` per workflow, which read the
> same tenant-wide field and form claims once per job and re-fetched
> gestures `job_facts` already had (Important #2 of the C2 review). This now
> reads the claims once (`kb_rows`, only when some job declares a parameter)
> and resolves each job's own screen from the gestures already loaded into
> `by_id` (`screen_of_loaded`, no second `gestures_for`), then joins per job
> with the pure `limits_from_rows` -- one tenant-wide knowledge read for
> however many jobs this call compiles, not one per job. Skipped entirely
> when no job in the call declares a parameter.
