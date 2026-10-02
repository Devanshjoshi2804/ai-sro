# Notes for `backend/src/sro/domain/execution/belts.py`

Comments and docstrings moved out of [`backend/src/sro/domain/execution/belts.py`](../../../../../../../backend/src/sro/domain/execution/belts.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/domain/execution/belts.py#L1): Docstring

> A14: verify against state, and only then against a picture -- and D2: when a
> job has earned the right to write without being asked.
>
> Measured over the 643 tasks of the WebVoyager benchmark, a validator reading
> the run's own text -- what the calls returned -- scored 84.24% against 70.04%
> for one reading screenshots, with over 84% agreement with human annotators; a
> screenshot read beside the agent's final answer still only reached 83.00%. So: the response the
> command itself returned first, a confirming read the cited evidence shows the
> page performs second, and the screenshot last and least. A green toast is the
> weakest of the three and the easiest to be wrong about.
>
> arXiv:2410.00689, Tables 1 and 2. Corrected twice: the figures that stood here
> first (86.9/78.8, 94%, "192 of 321") are in no version of that paper, and the
> first correction then misattributed the denominator -- 322 is the subset used
> for the self-validation experiment, not for these tables. `verify.py` carries
> the whole account.
>
> The earning rule reads the same order from the other end. Autonomy is earned by
> verified effect, not by counting runs: a write counts only when the verifier
> decided `held` by state -- a status the server answered, or a read that showed
> the record -- and never by a picture. A failed write un-earns the job, and the
> next runs ask again.
>
> Pure: the belts decide, and the sending, the asking and the counting of rows
> live outside. `verify` itself -- the probe on the wire and the model that reads
> the picture -- is the application's, and asks these questions.

## module, [line 12](../../../../../../../backend/src/sro/domain/execution/belts.py#L12): Note on the line above

Code: `K_WEAK_LOCATORS = frozenset({"css_path", None})`

> A step that only ever matches on the last fallback is a step about to break.
> The run succeeds and the step is flagged stale.

## module, [line 14](../../../../../../../backend/src/sro/domain/execution/belts.py#L14): Note on the line above

Code: `K_EARNED_RUNS = 3`

> Live runs whose every write verified by state before the tap goes away.
> Three is a job that worked on three different days' values, not a job that
> worked once.

## module, [line 16](../../../../../../../backend/src/sro/domain/execution/belts.py#L16): Note on the line above

Code: `STATE_BELTS = ("status", "read")`

> The two verdicts that saw the state itself. `screen` is a model reading a
> picture, and a picture is not an effect.

## `StepVerdict`, [line 20](../../../../../../../backend/src/sro/domain/execution/belts.py#L20): Docstring

> One step's verify, and which belt decided it. Named for the step because
> `sro.domain.skill.track_record.Verdict` is the other one -- a whole run's
> standing, counted over many of these.

## `StepVerdict`, [line 28](../../../../../../../backend/src/sro/domain/execution/belts.py#L28): Note on the line above

Code: `refuted: bool = False`

> Whether a read went and looked, and the write is NOT in the warehouse.
>
> Not the same as a write that failed. Most ways a write fails leave the
> state unknown -- the browser went away, a 5xx came back, a screen said
> something nobody could parse -- and "unknown after a write" is what stops a
> job being offered a second press, because a second press after a write that
> might be in the warehouse is how somebody gets two of something.
>
> This is the one case that is not unknown. `verify` read the record back,
> the read ANSWERED, and what came back does not carry what this run sent. A
> write that is provably not there can be tried again, and the operator is
> owed the button.
>
> Only from a read that succeeded. A read-back that could not be performed
> leaves this false, which is the safe direction.

## `StepVerdict`, [line 30](../../../../../../../backend/src/sro/domain/execution/belts.py#L30): Note on the line above

Code: `called: Mapping[str, str] = field(default_factory=dict)`

> The `{method, url}` this belt WATCHED go out, where it watched one.
>
> `made` is what the record was called; this is what was called to make it,
> and only the status belt can ever fill it -- it is the one that reads the
> page's own traffic. It is how a CLICK teaches the write ledger: the send
> was a click and carries no url, so without this only a step that already
> replayed as a call could ever prove an endpoint, which is a bootstrap that
> never starts. See `effects._remember_the_write`.

## `StepVerdict`, [line 19](../../../../../../../backend/src/sro/domain/execution/belts.py#L19): Note on the line above

Code: `@dataclass(frozen=True, slots=True)`

> What the warehouse called the record this step created, where it made
> one and said so. Empty for every step that created nothing, which is most
> of them -- and for a create whose answer named nothing this can read.
>
> A run that made three records has to be able to say which three, or nobody
> can go and look at them.

## `expected_statuses`, [line 33](../../../../../../../backend/src/sro/domain/execution/belts.py#L33): Docstring

> Every status the call this step replays actually came back with.
>
> The call this step replays is `recorded_call`'s, so that endpoint is the
> only one whose statuses mean anything here. An earlier version took every
> mutating call on every cited gesture, which let a page's own background
> traffic into the set a run is verified against: on four steps across both
> real tenants -- `new`'s `Create a Customer Type` step 5, acme's steps 1 and
> 6 of the same job, and acme's `Create an Activity Code` step 7 -- the
> evidence fires a 201 create AND a 200 keep-alive or telemetry batch, and
> the set came out `{200, 201}`. A replayed create that came back 200 instead
> of 201 would then be held by rung 1 of `verify` on the strength of a
> performance beacon's status code, with the read-back and the screenshot
> never asked. Narrowed to the replayed endpoint, those four steps give
> `{201}` and a 200 falls through to the rest of the ladder.
>
> Only a mutation names a status here. If this step's evidence made no write
> the set is empty, and `verify` falls back to plain 2xx -- a GET's 204
> counted here would teach it that 204 is what a write looks like.
>
> A request with a `failure_reason` never completed, so whatever status it
> carries is not a status the warehouse returned -- see `origin_of`, which
> learned the same thing about picking a host off a dead call.

## `confirming_read`, [line 51](../../../../../../../backend/src/sro/domain/execution/belts.py#L51): Docstring (debt)

> A GET a cited gesture made after its write, and that came back: the read
> the page performs to show the result, which is the hidden state a run can
> ask for again.
>
> Same completion guard as `expected_statuses`, for the reason `origin_of`
> already learned -- the real capture has a GET to a dead host arriving one
> millisecond after the write, and a probe aimed there proves nothing.
>
> A call with no `started_at` is a call at an unknown time. It cannot be shown
> to have come after the write, and "after the write" is the whole claim, so
> it is not the read -- the same strictness that makes the same instant not
> after.
>
> ponytail: "first completed GET after the write" still admits a stream, a
> beacon or a health poll; pick by response shape if that starts costing.

## `status_of`, [line 70](../../../../../../../backend/src/sro/domain/execution/belts.py#L70): Docstring

> The status out of the browser's reply, when it gave one.

## `mentions`, [line 86](../../../../../../../backend/src/sro/domain/execution/belts.py#L86): Docstring

> Whether the read came back carrying a value this run supplied.
>
> Leaf equality, not substring: the capture's own order list answers
> `{"orders": [{"id": "ORD-1"}]}`, and a run value of "1" is inside that
> string without being in it. A length floor cannot save the substring test
> either -- this tenant's real work-area codes are two characters. Substring
> is kept only for a body that is not JSON, where there are no leaves to
> compare.
>
> ANY value, because this is asked AFTER the write: the read is being shown
> the record that was just made, and one value of it coming back is the
> record coming back. `carries_every` is the same question asked before the
> write, where any is the wrong quantifier and the difference is a write
> that never happens.

## `carries_every`, [line 90](../../../../../../../backend/src/sro/domain/execution/belts.py#L90): Docstring

> Whether the read shows ALL of what this run would write.
>
> The precondition's rule, and it has to be every one of them. A job carries
> values that change from run to run and values that do not -- an order's
> reference, a facility, a site -- and `any` reads a record whose UNCHANGED
> half matches as the record this run was going to create.
>
> Measured end to end, live, on 2026-09-15: four runs of a three-step job
> that types a new client code and the same reference each time. The
> confirming read answered the PREVIOUS record, its `reference` matched, and
> every one of the four skipped its write and reported `held` -- 0 writes
> reached the page across four runs that each said they had done the job.
> Nothing in 3000 unit tests saw it, because nothing asked what happens when
> one of the values is the same as last time.

## `carries_in_slot`, [line 94](../../../../../../../backend/src/sro/domain/execution/belts.py#L94): Docstring

> Whether the read shows each value in the KEY the plan put it in.
>
> What `carries_every` above cannot ask. It searches the whole record for the
> value, so a job that fills two fields is confirmed by a record that carries
> the right code in the wrong place -- and it is confirmed just as happily by
> a record that carries the code somewhere the plan never wrote.
>
> Measured over the 94 recorded creates whose request and response are both
> JSON objects: **16 send a value that appears nowhere in the answer**, every
> one of them a `…Description` key where the form posts the code and the
> server stores the resolved label. `carries_every` fails those records, and
> they are correct records -- a failed write stops the run and empties the
> job's register of verified effects. `wanted` is `WritePlan.confirm`, which
> is already narrowed to the slots the demonstration's own answer echoed
> back unchanged, so a slot the server rewrites is never asked about.
>
> Empty `wanted` is False: nothing was checked, so nothing was shown. The
> caller decides what to do with a belt that could not run -- `verify` does
> not reach here at all for an empty one, and holds on the status instead.

## `record_carrying`, [line 100](../../../../../../../backend/src/sro/domain/execution/belts.py#L100): Docstring

> The record in this answer that carries every one of these values, or None.
>
> What `carries_in_slot` asks, and what the result card reads. A run that
> made a record has to be able to say WHICH record, and on this endpoint
> `made_by`'s suffix rule cannot: the identifier is `customerType`, which
> ends in none of `id`/`code`/`name`/`number`/`key`. The plan already knows
> which keys this job varies, so the row those keys found is the row to show.

## `_records`, [line 124](../../../../../../../backend/src/sro/domain/execution/belts.py#L124): Docstring

> The records an answer holds, whether it is one or a page of them.
>
> A confirming read is whatever GET the page made after its write, and on the
> system this was built for that is the COLLECTION, not the created row:
> measured live 2026-09-16, the read after `POST /wm/customerTypes` is
> `GET /wm/customerTypes?siteId=SG&…`, a list of every customer type. A rule
> that could only read a single record called a 201'd create failed because
> it was looking for `customerType` on the envelope of a list.
>
> So: the document itself, what is inside its `data` envelope -- the shape
> 112 of the 114 recorded successful writes carry -- and, where that is a
> list, each row of it.
>
> `any` over records and `all` over slots, and the pairing is the point. A
> record that carries EVERY slot this run filled is the record this run
> created; a list in which one row matches the code and another matches the
> description shows neither. The whole-body search this replaced could not
> tell those apart -- it flattened the page to a set of leaves, so a
> collection confirmed a write as long as the values existed anywhere in it,
> including in two different rows and including in the row the demonstration
> made.

## `unreturned`, [line 149](../../../../../../../backend/src/sro/domain/execution/belts.py#L149): Docstring

> The names this run supplied that the read did not come back carrying.
>
> `mentions` asks whether ANY of them came back, and holds on one -- which is
> right, and is why this exists beside it rather than instead of it. A record
> read after a write is being asked "are you there", and one value answering
> is the record answering. Requiring ALL of them was tried and measured
> wrong: of 94 recorded creates, 16 send a value that appears nowhere in the
> answer -- every one a `...Description` key holding the label its code
> resolved to -- so `carries_every` failed roughly one correct create in six
> and un-earned a job for being right.
>
> But a warehouse that silently shortens a field answers the same way. Send a
> code and a sixty-character description, have the description truncated on
> save, and the code comes back, `mentions` is satisfied, and the step holds
> by `read`. Every belt in the chain then agrees, because every one of them
> compares the record to ITSELF: the status is the server's, the read-back is
> the record as stored, and a picture of the grid row looks right to a model
> with no idea what was asked for.
>
> So the step still holds -- one value back is the record back -- and what
> did NOT come back is named. A truncation stops being invisible without a
> correct write being failed for it.
>
> Names, never values: this is read by a panel and a log.

## `RunProof`, [line 161](../../../../../../../backend/src/sro/domain/execution/belts.py#L161): Docstring

> One live run that held, reduced to the two sets the rule compares:
> the steps that wrote, and the steps a state belt verified.

## `proven_runs`, [line 171](../../../../../../../backend/src/sro/domain/execution/belts.py#L171): Docstring

> How many live held runs had every write verified by state -- the count
> `earned_from` compares, served so a surface can say "2 of 3" and not only
> yes or no.

## `earned_from`, [line 175](../../../../../../../backend/src/sro/domain/execution/belts.py#L175): Docstring

> Whether a job may write unasked: `K_EARNED_RUNS` live held runs, each
> with every write verified by state (`STATE_BELTS`). Effects decided by
> screen are never recorded, so `verified` here is state by construction.

## `state_verified`, [line 179](../../../../../../../backend/src/sro/domain/execution/belts.py#L179): Docstring

> The gate `record_effect` keeps: only a state belt's verdict is an effect.

## `RunProof.proves`, [line 167](../../../../../../../backend/src/sro/domain/execution/belts.py#L167): Docstring

> A run with no write proves nothing about writing. One with a write
> a state belt did not see proves the opposite.

## `StepVerdict`, [line 21](../../../../../../../backend/src/sro/domain/execution/belts.py#L21): Inline

Code: `state: str`

> held | failed | unclear

## `StepVerdict`, [line 22](../../../../../../../backend/src/sro/domain/execution/belts.py#L22): Inline

Code: `by: str`

> status | read | screen | none
