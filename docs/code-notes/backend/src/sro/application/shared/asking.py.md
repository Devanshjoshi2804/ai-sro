# Notes for `backend/src/sro/application/shared/asking.py`

Comments and docstrings moved out of [`backend/src/sro/application/shared/asking.py`](../../../../../../../backend/src/sro/application/shared/asking.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## `ask`, [line 17](../../../../../../../backend/src/sro/application/shared/asking.py#L17): Docstring

> The one way a prompt record is sent. The record decides the model, the
> thinking, the instructions and the schema; the caller decides only what the
> model is shown, split into `trusted` (JSON the system built) and
> `untrusted` (text somebody outside the system wrote, each fenced).
>
> The model comes from the record, not from a setting: a model change is a
> prompt change, and a prompt change bumps the record's version and goes
> through the eval gate (Global Constraint 9). A setting could move it
> silently. The record's `fallback_model` is not a model change: see the
> note on `Prompt.fallback_model` for why, and for the ruling it waits on.
>
> `image`, `images` and `audio` are what the model is shown besides text.
> `audio` is `(bytes, mime type)`: the narration `TRANSCRIBE` hears. It is
> here so the transcriber asks through this one path, with its fallback and
> its schema check, instead of calling the client itself.
>
> First the record's `unit` drops the items that break the schema
> (`Prompt.kept`). An answer that still does not match comes back with no
> data and an error naming the record and its version, and keeps what it
> cost: the call was made and billed, and a caller reads "no data" as
> unsure, never as an answer (Global Constraint 10). An error the asker
> already set is kept rather than overwritten: it is the truer cause.
>
> What was dropped is counted on the answer (`Answer.dropped`) and logged
> as the record's name, version and the count -- never the items, which are
> a model's reading of somebody's mail and pages.

## `ask`, [line 29](../../../../../../../backend/src/sro/application/shared/asking.py#L29): Note on the line above

Code: `if prompt.fallback_model is None or not _failed(first, prompt.unit):`

> The one place a record falls back (`Prompt.fallback_model`), so no caller
> can do it differently. Asked once, with the same record, the same evidence
> and the same schema. The fallback's answer is used when it is usable;
> otherwise the first failure comes back as it was, so a caller reads the
> same error it read before there was a fallback.
>
> Both calls were made and both are billed: the meter writes a spend row per
> call under the model actually called, and the day's cap is asked before
> each. The answer carries the tokens and cost of both, so a run's total and
> an eval's cost per case count the second call too, and `fell_back` says it
> was made.
>
> Safe to ask twice: a model call has no side effects. Nothing is written,
> sent or clicked by asking, so a retry can never double a write.
>
> The log line names the record, both models and the reason -- the asker's
> error, built from an exception's type or a parser's message, never from
> what was sent -- and never the prompt or the answer. When the fallback
> fails too, a second line says so with its own reason, so a fallback that is
> itself broken (a quota, a retired model) is visible and not hidden behind
> the first model's error.
>
> The thinking level is the record's, sent to both models as it is. No
> record asks 3.7-flash for a level it does not take today; the asker's note
> on `LESS_THINKING` holds the case where one would.
>
> The day's cap is asked before the fallback's call too. When the first call
> fills it, `OverCap` is raised before 3.7-flash is asked, and nothing is
> spent past the cap. Ceiling: the exception carries no `Answer`, so the
> first call's cost reaches the spend table (the cap and the bill are right)
> but not the caller's run or step total, which under-reports by that one
> call. The same holds when a caller's timeout cancels mid-fallback. Carry
> the spent answer on `OverCap` if run totals must match the bill exactly.

## `_failed`, [line 62](../../../../../../../backend/src/sro/application/shared/asking.py#L62): Docstring

> No data, or data whose every item broke the schema. An answer with no
> items that dropped none is an answer: the model found nothing.
