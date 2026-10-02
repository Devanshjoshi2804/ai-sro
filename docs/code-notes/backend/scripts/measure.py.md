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

## module, [line 181](../../../../backend/scripts/measure.py#L181): Note on the line above

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

## `Line`, [line 130](../../../../backend/scripts/measure.py#L130): Docstring

> One measured thing, and what it rests on.

## `unmeasured`, [line 543](../../../../backend/scripts/measure.py#L543): Docstring

> The list this whole script exists to print.
>
> Every line here is something the product does that no number above covers.
> Written by hand and kept in the report on purpose: a gap that is only
> visible as a missing section is a gap the next reader will not see.

## `running`, [line 425](../../../../backend/scripts/measure.py#L425): Comment

Code: `for belt in ("status", "read", "screen"):`

> The ladder, named explicitly. `verdict_by` also carries `performed` (the
> driver said the gesture landed), `dry` and `none`, and those appear in the
> breakdown above -- but the three rungs are the claim the product makes
> about reality, so each one is asked about by name even when the answer is
> zero. A rung that has never run is the most useful line on this page.

## `main`, [line 652](../../../../backend/scripts/measure.py#L652): Comment

Code: `asked = (`

> The report is written HERE rather than inside the measuring, so the file
> write is not an async function doing blocking IO -- and so a failure to
> write it cannot lose the report that was already printed.
> Read here rather than in the measuring, which is async: a blocking file
> read inside an async function is the kind of thing that works until the
> day it is called from a server.

## `class_of`, [line 119](../../../../backend/scripts/measure.py#L119): Note on the function

> The first matching class wins, in `_CLASS_WORDS` order, and each rule's words
> are the reason shapes seen on QA (2026-10-03, 151 failing steps), not generic
> words: a loose word such as "did not answer" or "is null" also matches the
> screen reader's free text and the model's own failures. Order is the
> precedence, tested per adjacent pair: `wrong_resume` before `sign_in` (a
> resumed step names the earlier attempt, which may mention a sign-in);
> `missing_value` before `sign_in` ("nobody gave a value for Password" is a
> missing value); `not_found` and `timing` before `wrong_page` (a reason that
> names the page it is on and also the real cause is that cause). "other" is
> reviewed by a person, never re-bucketed silently, and stays the canary for a
> new cause. `screen_disagrees` is the one rule by who judged: only a `failed`
> verdict by the screen reader whose free text carries `_SCREEN_WORDS`; an
> `unclear` step, or screen text with none of those words, is "other".
> `known_broken` carries only digests, so it is counted per lane, not classed.
> Classes beyond the spec's six (`no_browser`, `wrong_page`, `no_approval`,
> `missing_value`, `no_model`, `screen_disagrees`) exist because the first QA
> baseline left 80% in "other".
