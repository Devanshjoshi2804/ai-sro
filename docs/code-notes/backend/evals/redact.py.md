# Notes for `backend/evals/redact.py`

How a real case becomes one that may be committed: every string is redacted by its role, and schema keys are never touched.

## `_VALUE_KEYS`, [line 14](../../../../backend/evals/redact.py#L14): Constant

> Strings under these keys are values: typed and seen values, hosts, the
> tenant, a search query, a job's shape key, and every value of a recorded
> call's body. A value is shaped whole, whatever its case: `testsro` is
> `aaaaaaa`. `_URL_KEYS` hold URLs and paths, whose host and every path
> segment are shaped. The rest is prose.

## `_key`, [line 39](../../../../backend/evals/redact.py#L39): Design

> A key is schema and is kept (`shape_key`, `seen_values` and `pass_id`
> must still load into `Workflow` and still be read by the scoring). Only
> two maps are keyed by data: `crossings` (keyed by a typed value, shaped
> as a value) and a reader case's `expected.values` (keyed by a field
> label, shaped as prose).

## `_Shapes.learn`, [line 73](../../../../backend/evals/redact.py#L73): Design

> The first pass collects every word of every value, URL and the tenant. In
> the second pass prose keeps its lowercase words except those, so an
> account typed into a login and named again in the mail is shaped in both.
> Other lowercase prose (says, narrative, a mail body) is kept; a lowercase
> customer word that is never a value survives, which is why a person reads
> every candidate.

## `shape`, [line 24](../../../../backend/evals/redact.py#L24): Function

> Upper case to `A`, other letters to `a`, digits to `9`, anything else kept:
> `GT-0042` is `AA-9999`. A shape keeps what a prompt reasons with (a code, a
> date, a quantity) and drops what the value was.

## `redacted`, [line 120](../../../../backend/evals/redact.py#L120): Design

> One shape map per case, shared by the input, the expected and the recorded
> answer: the same value becomes the same shape everywhere, so an expected
> value still matches the answer and a cite still names its gesture (this
> system's ids are kept). Two values with one shape get `~2`, `~3`. A
> redacted case loads and scores exactly as the raw one (the probe test).
