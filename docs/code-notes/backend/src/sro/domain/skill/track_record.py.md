# Notes for `backend/src/sro/domain/skill/track_record.py`

Comments and docstrings moved out of [`backend/src/sro/domain/skill/track_record.py`](../../../../../../../backend/src/sro/domain/skill/track_record.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/domain/skill/track_record.py#L1): Docstring

> What a skill version has actually done, and whether that earns autonomy.
>
> Promotion to autonomous is the one rung nobody watches, so it is the one rung
> that has to be earned by evidence rather than granted by a click. Two things
> count, and both are refusals more often than permissions.

## module, [line 22](../../../../../../../backend/src/sro/domain/skill/track_record.py#L22): Note on the line above

Code: `REQUIRED_CLEAN_RUNS = 10`

> Consecutive clean runs before autonomy is available.
>
> Consecutive, not cumulative: a skill that works nine times in ten is a skill
> that will quietly do the wrong thing on a Tuesday, and a total would hide that
> behind a good average.

## module, [line 24](../../../../../../../backend/src/sro/domain/skill/track_record.py#L24): Note on the line above

Code: `DEMOTE_AFTER_FAILURES = 3`

> Consecutive failures that pull an autonomous skill back to assisted.
>
> Low on purpose. The cost of demoting a healthy skill is that a human confirms
> the next few runs; the cost of not demoting a broken one is that it keeps
> writing.

## `Verdict`, [line 10](../../../../../../../backend/src/sro/domain/skill/track_record.py#L10): Docstring

> What a finished run says about the skill that produced it.
>
> Defined here rather than with execution because it is a fact about a
> *record*: a run either advances a version's case for autonomy, resets it, or
> says nothing. Execution decides which one a given run was.

## `Verdict`, [line 11](../../../../../../../backend/src/sro/domain/skill/track_record.py#L11): Note on the line above

Code: `CLEAN = "clean"`

> Every step performed at L1, every assertion passed. The only kind of run
> that counts towards autonomy.

## `Verdict`, [line 13](../../../../../../../backend/src/sro/domain/skill/track_record.py#L13): Note on the line above

Code: `DEGRADED = "degraded"`

> It worked, but a slower rung had to finish it. Evidence the skill is
> drifting: it resets the counter rather than advancing it.

## `Verdict`, [line 17](../../../../../../../backend/src/sro/domain/skill/track_record.py#L17): Note on the line above

Code: `WITHHELD = "withheld"`

> A shadow run. It proves the request was buildable and nothing more, so it
> neither advances nor resets anything.

## `Verdict`, [line 19](../../../../../../../backend/src/sro/domain/skill/track_record.py#L19): Note on the line above

Code: `UNREACHABLE = "unreachable"`

> It never reached the system it was aiming at, so it says nothing about the
> skill either way.
>
> A closed laptop, no tab open on the system, a connection that died before a
> response. The trigger already treats this as ordinary -- a browser that
> cannot be reached does not stop a trigger, because it will be open again
> before the next one -- and a run has no better claim to be evidence than the
> trigger that started it. Counted, so the record says the attempt happened;
> counted separately, so nobody reads it as either a success or a fault.

## `TrackRecord`, [line 34](../../../../../../../backend/src/sro/domain/skill/track_record.py#L34): Note on the line above

Code: `unreachable_runs: int = 0`

> Attempts that never reached the system. Kept in its own column rather
> than folded into the failures or left out: a reviewer asking why a skill has
> four runs and two clean ones deserves the third number instead of having to
> infer that something is missing.

## `TrackRecord`, [line 38](../../../../../../../backend/src/sro/domain/skill/track_record.py#L38): Note on the line above

Code: `failures_before_the_last_run: int = 0`

> What `consecutive_failures` held before the most recent counted run.
>
> Kept for exactly one reader, `instead_of` below. `consecutive_failures` is
> collapsed to zero by any clean run, so a verdict that is later replaced --
> a run that ended clean and that the operator then said made the wrong
> record -- had already destroyed the number the replacement needs to count
> up from. One integer is the whole of what it takes to put that back, and
> the alternative is a version that made the wrong record every single time
> never reaching three failures in a row because each of its own runs reset
> the count on the way past.
>
> Not a second track record and not history: it describes the one run that
> can still be revised, which is the run the panel offers "it's wrong" for.

## `why_not_autonomous`, [line 109](../../../../../../../backend/src/sro/domain/skill/track_record.py#L109): Docstring

> The reason autonomy is refused, or ``None`` when it is earned.
>
> A reason rather than a boolean because this is shown to whoever asked, and
> "no" without "because" is how a governance gate becomes a thing people work
> around.

## `TrackRecord.after`, [line 44](../../../../../../../backend/src/sro/domain/skill/track_record.py#L44): Docstring

> The record this run leaves behind.

## `TrackRecord.instead_of`, [line 88](../../../../../../../backend/src/sro/domain/skill/track_record.py#L88): Docstring (debt)

> The record after a verdict already counted is replaced by another.
>
> One run is one run. `CallRunWrong` judges a run `FinishRun` has already
> judged, so counting both left a single attempt with two entries --
> `total_runs` and `clean_runs` overstating permanently, and `earn`
> reading a clean run that, on the operator's own account, never
> happened.
>
> Three things are put back, and the third is the one that matters.
>
> The count column of the replaced verdict is decremented before the new
> one is applied, which is exact.
>
> `consecutive_failures` is rewound to what it held before the replaced
> verdict touched it, from `failures_before_the_last_run`, and only then
> is the new verdict applied on top. Restoring what the replaced verdict
> cleared is precisely this method's job: without it, the sequence that
> actually happens -- a run ends clean, the operator looks at what it
> made and says it is wrong, repeat -- oscillates between zero and one
> forever, because every run's own clean verdict resets the count before
> the operator's answer can raise it. `DEMOTE_AFTER_FAILURES` then never
> fires, and a version that makes the wrong record every single time runs
> assisted indefinitely. That is the backstop ADR 014 rests its whole
> residual-risk argument on, so it has to hold through the ordinary
> sequence and not only through three outright crashes.
>
> `clean_streak` is not rewound and does not need to be: every revision
> this codebase can make lands on FAILED -- `judge` reads
> `wrong_because` before anything else and `CallRunWrong` is the only
> caller with a verdict to replace -- and FAILED sets the streak to zero
> outright rather than relative to what was there. A revision *to* CLEAN
> would need the same treatment as the failures above; nothing can make
> one, and a second remembered integer for a case that cannot arise is
> a field to keep correct forever in exchange for nothing.
>
> ponytail: the remembered number describes the most recently counted
> run. Calling a run wrong that is not that one -- two devices running
> the same version, and the older result queried last -- rewinds to the
> wrong base. The panel only ever offers "it's wrong" for the run it just
> watched finish, so nothing reaches that today; the fix if it ever does
> is to remember the number on the `Run` rather than on the record.

## `TrackRecord.after`, [line 47](../../../../../../../backend/src/sro/domain/skill/track_record.py#L47): Comment

Code: `return self`

> WITHHELD: a shadow run counts nothing, so there is nothing to
> revise later and nothing to remember about what came before it.

## `TrackRecord._counted`, [line 56](../../../../../../../backend/src/sro/domain/skill/track_record.py#L56): Comment

Code: `return replace(`

> Not a failure, and not progress. A run that needed the browser
> or a model is evidence the recipe no longer fits the system.

## `TrackRecord._counted`, [line 64](../../../../../../../backend/src/sro/domain/skill/track_record.py#L64): Comment

Code: `return replace(`

> Neither a step forward nor a step back. The streak survives it
> because a browser that was closed is not the skill drifting,
> and the failure count survives it because three closed laptops
> in a row would otherwise demote a skill that has never once
> done anything wrong.

## `TrackRecord.instead_of`, [line 96](../../../../../../../backend/src/sro/domain/skill/track_record.py#L96): Comment

Code: `return self.after(verdict, at)`

> WITHHELD counted nothing, so there is nothing to take back.

## `TrackRecord.instead_of`, [line 97](../../../../../../../backend/src/sro/domain/skill/track_record.py#L97): Comment

Code: `counted = max(getattr(self, undone) - 1, 0)`

> Clamped rather than refused. A run whose first verdict never reached
> this version -- one finished before the record existed, or against a
> version since replaced -- is a plausible thing to be handed, and the
> operator pressing "it's wrong" must not be the person who finds out.
> Taking nothing back where there is nothing to take back leaves the
> counts honest either way; raising would only turn a stale row into a
> dead button.

## `why_not_autonomous`, [line 117](../../../../../../../backend/src/sro/domain/skill/track_record.py#L117): Comment

Code: `return (`

> Not "not yet" -- not ever. A step with no call behind it is performed
> as a gesture, `judge` calls any run that performs one degraded, and a
> degraded run resets the streak. So this version cannot accumulate the
> ten it would need, and reporting only the count would leave somebody
> waiting for a number that is never going to move.
