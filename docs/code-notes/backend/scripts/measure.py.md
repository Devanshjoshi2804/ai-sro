# Notes for `backend/scripts/measure.py`

Comments and docstrings moved out of [`backend/scripts/measure.py`](../../../../backend/scripts/measure.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../backend/scripts/measure.py#L1): Docstring

> What this system has actually done, with what every number stands on.
>
>     uv run python scripts/measure.py                 # every tenant
>     uv run python scripts/measure.py --tenant acme
>     uv run python scripts/measure.py --json out.json # for the review to read
>     ... --questions questions.txt                    # also plan those lookups
>
> Written for one purpose: a later review that decides whether this direction is
> worth continuing needs numbers nobody can argue with, and the argument is never
> about arithmetic. It is about what the number was measured ON. A 74% that came
> off recorded evidence and a 74% that came off a warehouse are the same digits
> and different facts, and the first has been mistaken for the second in this
> repository before -- `findings.md` carries two corrections of exactly that
> shape, one of them mine, both landed within the hour.
>
> So every line printed here carries a STANDING: what the number rests on.
>
>     warehouse   a real Blue Yonder host answered
>     mail        a real mailbox
>     local       a page this repository serves to itself
>     recorded    replayed from stored evidence; no system was touched
>     none        nothing has ever run this; the absence IS the measurement
>
> A section with nothing in it prints `none` and stays in the report. An empty
> section deleted for tidiness is how a gap becomes invisible, and the gaps are
> the point: `verdict_by='screen'` having zero rows is the single most useful
> number on this page, because it says the third rung of verification has never
> executed against anything.
>
> **Reads, and nothing else.** Raw SQL against the store rather than the domain
> ports, deliberately: the ports answer the questions the product asks, and this
> asks questions the product never does -- how many steps were verified by which
> belt, how much of the evidence came from which host. A repository method added
> for a measurement is a repository method the product then has to carry.

## module, [line 24](../../../../backend/scripts/measure.py#L24): Note on the line above

Code: `WAREHOUSE = "jdadelivers.com"`

> The real Blue Yonder host this deployment has been signed into. Named here
> rather than inferred: "the host with the most gestures" would silently promote
> localhost to a warehouse on a laptop that spent a week on fixtures.

## module, [line 82](../../../../backend/scripts/measure.py#L82): Note on the line above

Code: `MINE = "(cast(:tenant as text) is null or tenant_id = cast(:tenant as text))"`

> Every query's tenant filter, as a bound parameter rather than a spliced clause.
>
> Splicing `where tenant_id = 'acme'` into an f-string works and reads fine until
> the day a tenant id comes from somewhere that is not a flag. One static string
> with one bound parameter has no such day, and `:tenant is null` is what lets the
> same query serve "every tenant" without a second spelling of it.
>
> The cast is not decoration: asyncpg prepares every statement and refuses one
> whose parameter type it cannot infer -- `$1 is null` alone is ambiguous, and the
> error it raises ("could not determine data type of parameter $1") names nothing
> about tenants.

## `Line`, [line 31](../../../../backend/scripts/measure.py#L31): Docstring

> One measured thing, and what it rests on.

## `unmeasured`, [line 408](../../../../backend/scripts/measure.py#L408): Docstring

> The list this whole script exists to print.
>
> Every line here is something the product does that no number above covers.
> Written by hand and kept in the report on purpose: a gap that is only
> visible as a missing section is a gap the next reader will not see.

## `running`, [line 290](../../../../backend/scripts/measure.py#L290): Comment

Code: `for belt in ("status", "read", "screen"):`

> The ladder, named explicitly. `verdict_by` also carries `performed` (the
> driver said the gesture landed), `dry` and `none`, and those appear in the
> breakdown above -- but the three rungs are the claim the product makes
> about reality, so each one is asked about by name even when the answer is
> zero. A rung that has never run is the most useful line on this page.

## `main`, [line 516](../../../../backend/scripts/measure.py#L516): Comment

Code: `asked = (`

> The report is written HERE rather than inside the measuring, so the file
> write is not an async function doing blocking IO -- and so a failure to
> write it cannot lose the report that was already printed.
> Read here rather than in the measuring, which is async: a blocking file
> read inside an async function is the kind of thing that works until the
> day it is called from a server.
