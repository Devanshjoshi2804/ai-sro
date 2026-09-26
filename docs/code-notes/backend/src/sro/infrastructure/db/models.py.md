# Notes for `backend/src/sro/infrastructure/db/models.py`

Comments and docstrings moved out of [`backend/src/sro/infrastructure/db/models.py`](../../../../../../../backend/src/sro/infrastructure/db/models.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/infrastructure/db/models.py#L1): Docstring

> SQLAlchemy tables.
>
> Every table carries ``tenant_id`` and every index leads with it, so a query that
> forgets the tenant is also a query that misses its index.
>
> The exception is a table reached only through its parent. ``workflow_run_steps``
> and ``approvals`` are keyed on a run id and carry no tenant of their own: the
> run carries it, nothing reaches either table without going through the run, and
> a second copy of the tenant on a child row is one more thing that can disagree.

## module, [line 172](../../../../../../../backend/src/sro/infrastructure/db/models.py#L172): Note on the line above

Code: `EMBEDDING_DIMENSIONS = 768`

> Fixed by the column. Changing the embedding model means re-embedding the
> store, not mixing two geometries in one index.

## `SkillRow`, [line 88](../../../../../../../backend/src/sro/infrastructure/db/models.py#L88): Note on the line above

Code: `revision: Mapped[int] = mapped_column(Integer, nullable=False, default=0)`

> Bumped by every write to this row, and by nothing else.
>
> Every version of a skill lives in one JSONB document, so two writers that
> both read it, changed their own copy and saved overwrote each other -- a
> demonstration, a repair or a promotion gone, with a green log to show for
> it.
>
> `latest_version` used to be the counter, on the grounds that it already
> existed and already counted. It only moves when a version is *appended*,
> though, and that left everything else racing: two reviewers promoting two
> different versions of one skill both rewrite the whole list, so the second
> silently undoes the first. The comment here used to call that correct, on
> the grounds that a stage is one field -- but it is not one field that gets
> written, it is the document all the versions are in.

## `BrowserSessionRow`, [line 248](../../../../../../../backend/src/sro/infrastructure/db/models.py#L248): Docstring

> Which tenant a browser session belongs to, and, since S2, whether it is a
> lease.
>
> A row with `state IS NULL` is a capture session: the provider is the only
> truth about what is still live, and this row answers one question -- whose.
> The primary key on the provider's own id is the security property there. A
> second claim means one browser was handed to two callers, and that has to
> fail rather than transfer.
>
> A row with a `state` is an account's lease (§5.2): where it lives
> (`container_url`, `steel_session_id`, `context_id`), who holds it (`holder`,
> a run id or the keeper), and how long it has left (`heartbeat_at`,
> `expires_at`). One table and not two, because a stray sweeper closing every
> Steel session nobody claimed has to see both kinds without joining --
> `held_by` and `all_held` keep answering for capture sessions alone by
> filtering `state IS NULL`, so neither ever mistakes the other's row for its
> own.
>
> ponytail: a settled lease (`expired` or `broken`) is never deleted, so an
> account acquiring and losing its lease over and over grows this table
> forever. Left for S9, the sweeper, to delete the row once it has closed
> whatever the lease pointed at -- deleting it here, before anything has
> closed the Steel context it named, would be the same bug this table exists
> to prevent, one column over.

## `BrowserSessionRow.opened_by`, [line 253](../../../../../../../backend/src/sro/infrastructure/db/models.py#L253): Note

> Nullable since S2's fix round: a lease row leaves it unset. `holder`
> already says who a lease belongs to, and duplicating it into `opened_by`
> (`String(64)`, while `holder` is `String(128)`) meant a holder longer than
> 64 characters would fail the insert for a reason that had nothing to do
> with the lease itself. A capture session still always sets it -- `claim`
> is the only writer left that does.

## `BrowserSessionRow.__table_args__`, [line 268](../../../../../../../backend/src/sro/infrastructure/db/models.py#L268): Note

> `uq_browser_sessions_one_live_lease` is partial on `state IN ('signing_in',
> 'ready')` -- the two states `LIVE` (`domain/execution/account.py`) names --
> rather than unconditionally unique on `(tenant_id, account_key)`. An
> `expired` or `broken` lease is history for that account and must not block
> the next one from being claimed; a capture session's `state IS NULL` never
> matches the predicate at all, so it never collides with a lease that
> happens to share no columns with it in the first place.
>
> Keyed on `account_key` (`Account.key`, S1) and not on the raw `origin`
> and `username` columns those stay for display. `Account.of` only trims a
> username; the vault key and the advisory lock casefold and percent-encode
> it, so `Lena@example.com` and `lena@example.com` are one account there and
> would have been two here -- two live leases, two contexts, two sign-ins,
> both writing the same vault `…/state` key. An expression index on
> `lower(username)` would still be wrong: `casefold` is not `lower`
> (`ß` folds to `ss`; `lower` leaves it alone).

## `BrowserSessionRow.__table_args__`, [line 277](../../../../../../../backend/src/sro/infrastructure/db/models.py#L277): Note

Code: `CheckConstraint(`

> A lease row is whole or it is not a lease row: every column a live lease
> needs, non-null together, whenever `state` is set at all. Enforced here
> rather than left to `_lease_of`'s `or ""` -- a corrupt row used to read
> back as an account with an empty username and a container url of `""`,
> silently, and a bug like that is cheaper to make impossible in the schema
> than to keep catching in every place that reads a lease back.

## `AgentDeviceRow`, [line 289](../../../../../../../backend/src/sro/infrastructure/db/models.py#L289): Docstring
## `AgentDeviceRow`, [line 289](../../../../../../../backend/src/sro/infrastructure/db/models.py#L289): Docstring

> One installed extension in one browser profile.
>
> Unique on (tenant, principal, label) so a reinstall re-registers as the
> device it was. An administrator reading this table is answering "whose
> browsers are being observed", and one operator appearing four times is not
> an answer.

## `AgentDeviceRow`, [line 289](../../../../../../../backend/src/sro/infrastructure/db/models.py#L289): Note on the line above
## `AgentDeviceRow`, [line 308](../../../../../../../backend/src/sro/infrastructure/db/models.py#L308): Note on the line above

Code: `secret: Mapped[str | None] = mapped_column(String(64))`

> What this browser proves it is itself with. Nullable only for a device
> registered before it existed; that one is refused until its extension
> re-registers, which is idempotent on the label.

## `AgentDeviceRow`, [line 289](../../../../../../../backend/src/sro/infrastructure/db/models.py#L289): Note on the line above
## `AgentDeviceRow`, [line 310](../../../../../../../backend/src/sro/infrastructure/db/models.py#L310): Note on the line above

Code: `revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))`

> When this browser's authority was taken away. Nullable and never
> cleared: a column rather than a deleted row because a revoked device is
> still the answer to "whose browsers were being observed, and until when".

## `AgentDeviceRow`, [line 289](../../../../../../../backend/src/sro/infrastructure/db/models.py#L289): Note on the line above
## `AgentDeviceRow`, [line 312](../../../../../../../backend/src/sro/infrastructure/db/models.py#L312): Note on the line above

Code: `grants: Mapped[list[dict[str, Any]]] = mapped_column(`

> Hosts this operator said may be watched after all, each with an expiry.
> A list rather than a table: they are read only with the device, only ever
> all at once, and there are a handful at a time.

## `ObservationBatchRow`, [line 328](../../../../../../../backend/src/sro/infrastructure/db/models.py#L328): Docstring
## `ObservationBatchRow`, [line 328](../../../../../../../backend/src/sro/infrastructure/db/models.py#L328): Docstring

> One upload. The events are one object in the blob store, not a column.
>
> A day of passive capture is millions of events, none of them fetched by id.
> They are read whole, over a window, by a miner. In a column the row that
> says "this arrived" would cost as much to read as the evidence it points at.

## `ObservationPolicyRow`, [line 354](../../../../../../../backend/src/sro/infrastructure/db/models.py#L354): Docstring

> What one tenant agreed to have observed. Absent means nothing.

## `TriggerRow`, [line 362](../../../../../../../backend/src/sro/infrastructure/db/models.py#L362): Docstring

> What starts a run when nobody typed a sentence.

## `TriggerRow`, [line 362](../../../../../../../backend/src/sro/infrastructure/db/models.py#L362): Note on the line above
## `ObservationPolicyRow`, [line 354](../../../../../../../backend/src/sro/infrastructure/db/models.py#L354): Docstring

> What one tenant agreed to have observed. Absent means nothing.

## `TriggerRow`, [line 362](../../../../../../../backend/src/sro/infrastructure/db/models.py#L362): Docstring

> What starts a run when nobody typed a sentence.

## `TriggerRow`, [line 368](../../../../../../../backend/src/sro/infrastructure/db/models.py#L368): Note on the line above

Code: `workflow_id: Mapped[str | None] = mapped_column(String(64))`

> What this runs: a taught skill or a mined job, and exactly one of them.
> Both nullable in the column and neither optional in the domain -- `Trigger`
> refuses a row that names two or none, and a CHECK constraint here would be
> the same rule written twice in two languages.

## `TriggerRow`, [line 362](../../../../../../../backend/src/sro/infrastructure/db/models.py#L362): Note on the line above
## `TriggerRow`, [line 370](../../../../../../../backend/src/sro/infrastructure/db/models.py#L370): Note on the line above

Code: `asks: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)`

> Whether this watch asks a question rather than running anything. The
> third branch of the rule above -- a skill, a job, or a question and
> neither of them -- and the reason there is no CHECK constraint for it.

## `TaskCandidateRow`, [line 401](../../../../../../../backend/src/sro/infrastructure/db/models.py#L401): Docstring
## `TaskCandidateRow`, [line 401](../../../../../../../backend/src/sro/infrastructure/db/models.py#L401): Docstring

> A task somebody keeps doing, and how often.
>
> Episodes are one document: they are read whole, by the person deciding
> whether to teach it, and nothing queries a candidate by one of them.

## `ToolCallRow`, [line 439](../../../../../../../backend/src/sro/infrastructure/db/models.py#L439): Docstring
## `ToolCallRow`, [line 439](../../../../../../../backend/src/sro/infrastructure/db/models.py#L439): Docstring

> One key, claimed before a connector was called with it.
>
> A row rather than a JSONB list on something: two runs claiming the same key
> at once is exactly the race this exists to lose, and a primary key is the
> only thing that loses it reliably.

## `ConfirmationRow`, [line 449](../../../../../../../backend/src/sro/infrastructure/db/models.py#L449): Docstring

> A fire waiting for somebody to say yes, and what they said.

## `ConfirmationRow`, [line 449](../../../../../../../backend/src/sro/infrastructure/db/models.py#L449): Note on the line above
## `ConfirmationRow`, [line 449](../../../../../../../backend/src/sro/infrastructure/db/models.py#L449): Docstring

> A fire waiting for somebody to say yes, and what they said.

## `ConfirmationRow`, [line 456](../../../../../../../backend/src/sro/infrastructure/db/models.py#L456): Note on the line above

Code: `workflow_id: Mapped[str | None] = mapped_column(String(64))`

> What the card is asking about. Exactly one, as on `TriggerRow`.

## `GestureBatchRow`, [line 473](../../../../../../../backend/src/sro/infrastructure/db/models.py#L473): Docstring
## `GestureBatchRow`, [line 473](../../../../../../../backend/src/sro/infrastructure/db/models.py#L473): Docstring

> One upload from a browser, and what became of it.
>
> ``batch_id`` is minted by the extension and is the primary key, which is
> what makes ingest idempotent: an upload retried after its answer was lost
> is refused rather than stored twice. The second copy would double every
> gesture in it and be mined as a second doing of the same job.

## `GestureBatchRow`, [line 473](../../../../../../../backend/src/sro/infrastructure/db/models.py#L473): Note on the line above
## `GestureBatchRow`, [line 482](../../../../../../../backend/src/sro/infrastructure/db/models.py#L482): Note on the line above

Code: `ended_at: Mapped[str] = mapped_column(String(64), nullable=False, default="")`

> The device's own clock for the window this batch covers, against
> ``received_at``'s server clock, and kept exactly as it was sent. The
> protocol requires both and the rig discarded both -- the same silent loss
> as a dropped screenshot reference, except these two carry something
> nothing else does.

## `GestureBatchRow`, [line 473](../../../../../../../backend/src/sro/infrastructure/db/models.py#L473): Note on the line above
## `GestureBatchRow`, [line 484](../../../../../../../backend/src/sro/infrastructure/db/models.py#L484): Note on the line above

Code: `recording_id: Mapped[str | None] = mapped_column(String(64))`

> Which teaching recording this batch belongs to. ``mode`` says a batch
> was a demonstration; without this, nothing says WHICH, and the extension
> refuses to mix two recordings into one batch precisely so that this is
> answerable.

## `GestureRow`, [line 491](../../../../../../../backend/src/sro/infrastructure/db/models.py#L491): Docstring

> One thing an operator did, with the calls and page marks around it.

## `GestureRow`, [line 491](../../../../../../../backend/src/sro/infrastructure/db/models.py#L491): Note on the line above
## `GestureRow`, [line 491](../../../../../../../backend/src/sro/infrastructure/db/models.py#L491): Docstring

> One thing an operator did, with the calls and page marks around it.

## `GestureRow`, [line 495](../../../../../../../backend/src/sro/infrastructure/db/models.py#L495): Note on the line above

Code: `tenant_id: Mapped[str] = mapped_column(String(64), nullable=False)`

> Every reader filters on it: the mining pass, the pool, the reading loop
> and the routes.

## `GestureRow`, [line 491](../../../../../../../backend/src/sro/infrastructure/db/models.py#L491): Note on the line above
## `GestureRow`, [line 500](../../../../../../../backend/src/sro/infrastructure/db/models.py#L500): Note on the line above

Code: `at: Mapped[float] = mapped_column(Float, nullable=False)`

> Unix seconds as a float -- recorder.js's own format, and what every
> ordering in the rig is on. Not a timestamp: converting it would make two
> formats for one number and a reading loop that sorts differently from the
> browser that recorded it.

## `GestureRow`, [line 491](../../../../../../../backend/src/sro/infrastructure/db/models.py#L491): Note on the line above
## `GestureRow`, [line 507](../../../../../../../backend/src/sro/infrastructure/db/models.py#L507): Note on the line above

Code: `page_url: Mapped[str | None] = mapped_column(Text)`

> The TAB's url, which is not the frame's. A gesture inside a portal that
> hosts its screens in an iframe reports the frame's src in ``url``, and a
> run told to open that would load the frame's document outside the shell
> that gives it its session. This is the address an operator would type.

## `IntentRow`, [line 519](../../../../../../../backend/src/sro/infrastructure/db/models.py#L519): Docstring
## `IntentRow`, [line 519](../../../../../../../backend/src/sro/infrastructure/db/models.py#L519): Docstring

> What one model call read out of one gesture, and what it cost.
>
> One row per gesture, replaced rather than appended to: a second reading of
> the same evidence supersedes the first. A row with no usable ``act`` is
> still a row -- the model was asked, it answered, and it was billed, so the
> reading is visible rather than both billed and hidden.

## `IntentRow`, [line 519](../../../../../../../backend/src/sro/infrastructure/db/models.py#L519): Note on the line above
## `IntentRow`, [line 537](../../../../../../../backend/src/sro/infrastructure/db/models.py#L537): Note on the line above

Code: `thought_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)`

> Inside ``out_tokens``, not beside it: thinking is billed at the output
> rate and ``out_tokens`` is what the bill is computed from. Kept as its own
> column because on Flash it is ~84% of billed output, and a reader with one
> number cannot tell a long answer from a long silence.

## `IntentRow`, [line 519](../../../../../../../backend/src/sro/infrastructure/db/models.py#L519): Note on the line above
## `IntentRow`, [line 541](../../../../../../../backend/src/sro/infrastructure/db/models.py#L541): Note on the line above

Code: `unpriced: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)`

> A call that cost nothing and a call whose cost could not be established
> are the same row without this, and a bill summed over them is understated
> without saying so.

## `IntentRow`, [line 519](../../../../../../../backend/src/sro/infrastructure/db/models.py#L519): Note on the line above
## `IntentRow`, [line 545](../../../../../../../backend/src/sro/infrastructure/db/models.py#L545): Note on the line above

Code: `error: Mapped[str | None] = mapped_column(Text)`

> Why it read nothing, when it read nothing for a reason the API gave. An
> honest empty answer and a refused call are the same row without this.

## `OrphanRequestRow`, [line 550](../../../../../../../backend/src/sro/infrastructure/db/models.py#L550): Docstring
## `OrphanRequestRow`, [line 550](../../../../../../../backend/src/sro/infrastructure/db/models.py#L550): Docstring

> A recorded call no gesture claimed, kept against the batch it came in.
>
> Keyed on (batch, request) so a replayed batch re-offers its orphans without
> doubling them: the same call twice is not a second call.

## `OrphanPageRow`, [line 559](../../../../../../../backend/src/sro/infrastructure/db/models.py#L559): Docstring
## `OrphanPageRow`, [line 559](../../../../../../../backend/src/sro/infrastructure/db/models.py#L559): Docstring

> A page event no gesture claimed.
>
> A surrogate id rather than a natural key, deliberately: two distinct page
> events can share a batch, an instant and a payload, and keying on those
> would silently drop the second. ``gesture_batches.batch_id`` already makes
> re-ingesting a batch a no-op, so there is nothing here to deduplicate.

## `PoolRow`, [line 569](../../../../../../../backend/src/sro/infrastructure/db/models.py#L569): Docstring
## `PoolRow`, [line 569](../../../../../../../backend/src/sro/infrastructure/db/models.py#L569): Docstring

> Evidence a mining pass did not place, waiting to be shown again.
>
> Keyed by tenant rather than by stream. That is the whole mechanism by which
> one operator's Blue Yonder half meets another operator's SAP half.

## `PoolRow`, [line 569](../../../../../../../backend/src/sro/infrastructure/db/models.py#L569): Note on the line above
## `PoolRow`, [line 576](../../../../../../../backend/src/sro/infrastructure/db/models.py#L576): Note on the line above

Code: `waited: Mapped[int] = mapped_column(Integer, nullable=False, default=0)`

> Two clocks, because they measure opposite things and one counter cannot
> be both. ``age`` counts readings this entry was SHOWN and not cited, and
> runs out at ``K_POOL_AGE``. ``waited`` counts passes it was PASSED OVER,
> and drives priority so the day rotates. Using age for both made an entry
> that had been read six times outrank one never seen at all.

## `PoolRow`, [line 569](../../../../../../../backend/src/sro/infrastructure/db/models.py#L569): Note on the line above
## `PoolRow`, [line 580](../../../../../../../backend/src/sro/infrastructure/db/models.py#L580): Note on the line above

Code: `reason: Mapped[str] = mapped_column(Text, nullable=False, default="")`

> Why it retired, empty while it is still live. Evidence that leaves the
> prompt without a record is the failure this architecture exists to avoid.

## `WorkflowRunRow`, [line 585](../../../../../../../backend/src/sro/infrastructure/db/models.py#L585): Docstring
## `WorkflowRunRow`, [line 585](../../../../../../../backend/src/sro/infrastructure/db/models.py#L585): Docstring

> One run of a mined workflow: what it was performed with, and how it ended.
>
> ``workflow_runs`` rather than ``runs`` because ``runs`` is taken -- by the
> backend's own ``RunRow``, which is a different concept and predates this.
>
> Written whole after every step so the panel can poll it, and its steps are
> replaced rather than appended for the same reason.

## `WorkflowRunRow`, [line 585](../../../../../../../backend/src/sro/infrastructure/db/models.py#L585): Note on the line above
## `WorkflowRunRow`, [line 593](../../../../../../../backend/src/sro/infrastructure/db/models.py#L593): Note on the line above

Code: `values_: Mapped[Any] = mapped_column(`

> What this run is performed with. The press is the only source of them:
> nothing a chat door understood is carried across on its own.

## `WorkflowRunRow`, [line 585](../../../../../../../backend/src/sro/infrastructure/db/models.py#L585): Note on the line above
## `WorkflowRunRow`, [line 600](../../../../../../../backend/src/sro/infrastructure/db/models.py#L600): Note on the line above

Code: `items: Mapped[Any] = mapped_column(JSONB, nullable=False, default=list, server_default="[]")`

> What this run was asked to do the repeated block for: one set of values
> per thing on the list. Empty for every run of a job that does one thing
> once, which is most of them, and for every run made before repeats
> existed.

## `WorkflowRunRow`, [line 585](../../../../../../../backend/src/sro/infrastructure/db/models.py#L585): Note on the line above
## `WorkflowRunRow`, [line 607](../../../../../../../backend/src/sro/infrastructure/db/models.py#L607): Note on the line above

Code: `finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))`

> A real timestamp, where the rig kept text. The record still carries ISO
> strings, so this converts on the way in and out -- but a run whose clock is
> a string sorts a naive instant beside an offset-bearing one and neither is
> wrong, and ``started_at`` is what both indexes below order on.

## `WorkflowRunRow`, [line 585](../../../../../../../backend/src/sro/infrastructure/db/models.py#L585): Note on the line above
## `WorkflowRunRow`, [line 611](../../../../../../../backend/src/sro/infrastructure/db/models.py#L611): Note on the line above

Code: `from_step: Mapped[int] = mapped_column(Integer, nullable=False, default=0)`

> How many steps the operator did before the offer was made. Stored so a
> re-press of this run can be checked against what the first press asked
> for -- without it the row cannot say whether a second press is the same
> job or a different one.

## `WorkflowRunRow`, [line 585](../../../../../../../backend/src/sro/infrastructure/db/models.py#L585): Note on the line above
## `WorkflowRunRow`, [line 613](../../../../../../../backend/src/sro/infrastructure/db/models.py#L613): Note on the line above

Code: `withheld: Mapped[Any] = mapped_column(JSONB, nullable=False, default=list)`

> The writes a dry run produced and did not send, in full. This is what a
> person reads before pressing through to live.

## `WorkflowRunRow`, [line 585](../../../../../../../backend/src/sro/infrastructure/db/models.py#L585): Note on the line above
## `WorkflowRunRow`, [line 619](../../../../../../../backend/src/sro/infrastructure/db/models.py#L619): Note on the line above

Code: `unpriced: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)`

> A run that cost nothing and a run whose cost could not be established
> are the same row without this.

## `WorkflowRunRow`, [line 585](../../../../../../../backend/src/sro/infrastructure/db/models.py#L585): Note on the line above
## `WorkflowRunRow`, [line 626](../../../../../../../backend/src/sro/infrastructure/db/models.py#L626): Note on the line above

Code: `needs: Mapped[Any] = mapped_column(JSONB, nullable=False, default=list, server_default="[]")`

> Where each value came from, for values nobody typed. Empty for a run
> whose values came from a person.

## `WorkflowRunRow`, [line 585](../../../../../../../backend/src/sro/infrastructure/db/models.py#L585): Note on the line above
## `WorkflowRunRow`, [line 627](../../../../../../../backend/src/sro/infrastructure/db/models.py#L627): Note on the line above

Code: `unasked: Mapped[Any] = mapped_column(JSONB, nullable=False, default=list, server_default="[]")`

> Names the request asked for that this job declares no parameter for.
>
> Names and never values. A job's parameters are what two doings proved vary;
> the form has more fields than that, and a mail naming one of them is an
> ordinary request this job simply cannot take yet. Dropping it is right --
> nothing demonstrated that slot -- and dropping it silently is the fault
> this column exists to end.

## `WorkflowRunRow`, [line 585](../../../../../../../backend/src/sro/infrastructure/db/models.py#L585): Note on the line above
## `WorkflowRunRow`, [line 628](../../../../../../../backend/src/sro/infrastructure/db/models.py#L628): Note on the line above

Code: `undoes_run: Mapped[str | None] = mapped_column(String(64))`

> The run this one takes back. Null on every run that is not an undo.

## `WorkflowRunRow`, [line 585](../../../../../../../backend/src/sro/infrastructure/db/models.py#L585): Note on the line above
## `WorkflowRunRow`, [line 630](../../../../../../../backend/src/sro/infrastructure/db/models.py#L630): Note on the line above

Code: `asked_the_asker: Mapped[bool] = mapped_column(`

> Whether this run has already written to whoever sent the request. One
> mail per run: a worker that restarted between two stops would otherwise buy
> somebody a second mail about one request, and a mail cannot be unsent.

## `WorkflowRunRow`, [line 585](../../../../../../../backend/src/sro/infrastructure/db/models.py#L585): Note on the line above
## `WorkflowRunRow`, [line 634](../../../../../../../backend/src/sro/infrastructure/db/models.py#L634): Note on the line above

Code: `awaiting: Mapped[Any] = mapped_column(JSONB, nullable=True)`

> The outside conversation this run ended waiting to hear back on.
>
> `{"server": "gmail", "thread": "...", "until": "<iso>"}`, or null for every
> run nobody outside was asked about. The question itself stays in the
> operator's thread, which is where the state lives; this is the address a
> reply is matched against, and the instant after which there is nothing left
> to match. See `domain/execution/waiting.py`.

## `WorkflowRunRow`, [line 585](../../../../../../../backend/src/sro/infrastructure/db/models.py#L585): Note on the line above
## `WorkflowRunRow`, [line 636](../../../../../../../backend/src/sro/infrastructure/db/models.py#L636): Note on the line above

Code: `wrong_because: Mapped[str | None] = mapped_column(Text)`

> What the operator said was wrong with what this run made.
>
> Null on every run nobody has reported, which is almost all of them. The
> ladder cannot see a record created exactly as asked that was not the record
> the person wanted -- a job read out of a sentence can be the wrong job, and
> the warehouse answers 201 for it -- so this is the only place that failure
> is ever written down.

## `WorkflowRunStepRow`, [line 665](../../../../../../../backend/src/sro/infrastructure/db/models.py#L665): Docstring
## `WorkflowRunRow`, [line 661](../../../../../../../backend/src/sro/infrastructure/db/models.py#L661): Comment

Code: `CheckConstraint("executor IN ('extension', 'steel')", name="ck_workflow_runs_executor"),`

> Held to exactly two values at the one place that cannot be talked past: the
> unique index, the startup sweep and `in_flight` all narrow themselves to
> `executor = 'extension'`, and every one of those checks a string a caller
> could have misspelled. Without this, an extension run saved as
> `executor="Extension"` or `""` sits outside all three -- outside the index,
> so it never collides with a second press; outside the sweep, so an API
> restart never fails it; and outside `in_flight`, so it still reports its
> device as busy forever, with no way back in but a hand-edited row.

## `WorkflowRunStepRow`, [line 665](../../../../../../../backend/src/sro/infrastructure/db/models.py#L665): Docstring

> One step of a run: what was planned, what was sent, and what it earned.
>
> No tenant of its own and no foreign key, as in the rig: a step is reached
> only through its run, which carries the tenant, and the run's save deletes
> and reinserts this whole set every time.

## `WorkflowRunStepRow`, [line 665](../../../../../../../backend/src/sro/infrastructure/db/models.py#L665): Note on the line above
## `WorkflowRunStepRow`, [line 673](../../../../../../../backend/src/sro/infrastructure/db/models.py#L673): Note on the line above

Code: `made: Mapped[Any] = mapped_column(JSONB, nullable=False, default=dict, server_default="{}")`

> What the warehouse called the record this step created, where it made
> one. `{}` for every step that created nothing, which is most of them.

## `WorkflowRunStepRow`, [line 665](../../../../../../../backend/src/sro/infrastructure/db/models.py#L665): Note on the line above
## `WorkflowRunStepRow`, [line 675](../../../../../../../backend/src/sro/infrastructure/db/models.py#L675): Note on the line above

Code: `of_step: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")`

> Which step of the JOB this row is. `ord` is where in the RUN it happened,
> and the two are the same number until a job repeats its middle.

## `WorkflowRunStepRow`, [line 665](../../../../../../../backend/src/sro/infrastructure/db/models.py#L665): Note on the line above
## `WorkflowRunStepRow`, [line 677](../../../../../../../backend/src/sro/infrastructure/db/models.py#L677): Note on the line above

Code: `item: Mapped[int | None] = mapped_column(Integer, nullable=True)`

> Which thing on the list it was done for, or NULL for a step done once.

## `WorkflowRunStepRow`, [line 665](../../../../../../../backend/src/sro/infrastructure/db/models.py#L665): Note on the line above
## `WorkflowRunStepRow`, [line 680](../../../../../../../backend/src/sro/infrastructure/db/models.py#L680): Note on the line above

Code: `sent: Mapped[Any | None] = mapped_column(JSONB(none_as_null=True), nullable=True)`

> The command envelope's kind and payload, NULL for a step that sent
> nothing. ``none_as_null`` because JSONB otherwise stores ``None`` as the
> JSON scalar ``null``, which is not SQL NULL: ``sent IS NULL`` would be false
> and every reader that asks whether a step sent anything would be told yes.
> The rig wrote SQL NULL, and its readers test for it.

## `WorkflowRunStepRow`, [line 665](../../../../../../../backend/src/sro/infrastructure/db/models.py#L665): Note on the line above
## `WorkflowRunStepRow`, [line 682](../../../../../../../backend/src/sro/infrastructure/db/models.py#L682): Note on the line above

Code: `result: Mapped[Any | None] = mapped_column(JSONB(none_as_null=True), nullable=True)`

> What the extension answered, NULL when it never did -- the same reason.

## `WorkflowRunStepRow`, [line 665](../../../../../../../backend/src/sro/infrastructure/db/models.py#L665): Note on the line above
## `WorkflowRunStepRow`, [line 693](../../../../../../../backend/src/sro/infrastructure/db/models.py#L693): Note on the line above

Code: `notes: Mapped[Any] = mapped_column(JSONB, nullable=False, default=list, server_default="[]")`

> What is already known about the values this step writes, read off the
> knowledge base's field claims and shown beside the write a person is asked
> to approve. Empty for every step that writes nothing and for every one the
> dictionary has nothing to say about, which is most of them.

## `ApprovalRow`, [line 702](../../../../../../../backend/src/sro/infrastructure/db/models.py#L702): Docstring
## `ApprovalRow`, [line 702](../../../../../../../backend/src/sro/infrastructure/db/models.py#L702): Docstring

> An approval a person gave: which step of which run, when, and from where.
>
> The first tap wins; a second on the same step is not a second
> authorisation. That is the whole reason for the composite key -- a write
> rescued to the second rung parks at the same step and takes a second tap.
>
> Not deleted and rewritten with the run: the run record says a write went
> out, and this says a person let it.

## `ApprovalRow`, [line 702](../../../../../../../backend/src/sro/infrastructure/db/models.py#L702): Note on the line above
## `ApprovalRow`, [line 708](../../../../../../../backend/src/sro/infrastructure/db/models.py#L708): Note on the line above

Code: `device_id: Mapped[str | None] = mapped_column(String(64))`

> The browser whose panel the tap came from, when the panel named one. A
> bare POST is a tap, so this is nullable.

## `WorkflowRow`, [line 711](../../../../../../../backend/src/sro/infrastructure/db/models.py#L711): Docstring
## `WorkflowRow`, [line 711](../../../../../../../backend/src/sro/infrastructure/db/models.py#L711): Docstring

> A workflow a mining pass found: what it says, and the shape it is known by.
>
> No cost of its own. One pass makes exactly one model call and proposes
> every workflow in it, so a workflow names the pass that found it rather
> than carrying a copy of the bill -- three workflows out of one $0.04 call
> summed to $0.12 when they each carried it, an overstatement that grew with
> how well the pass did.

## `WorkflowRow`, [line 711](../../../../../../../backend/src/sro/infrastructure/db/models.py#L711): Note on the line above
## `WorkflowRow`, [line 717](../../../../../../../backend/src/sro/infrastructure/db/models.py#L717): Note on the line above

Code: `pass_id: Mapped[str] = mapped_column(Text, nullable=False, default="")`

> Empty for a workflow saved outside a pass, which today is only a test.

## `WorkflowRow`, [line 711](../../../../../../../backend/src/sro/infrastructure/db/models.py#L711): Note on the line above
## `WorkflowRow`, [line 724](../../../../../../../backend/src/sro/infrastructure/db/models.py#L724): Note on the line above

Code: `shape_key: Mapped[Any] = mapped_column(JSONB, nullable=False, default=list)`

> What identity resolution compares a new proposal against. Rewritten in
> place by ``rekey`` when the rule that makes a key changes, because keys
> mined before the change no longer match keys mined after and a job already
> held could then be proposed again as a new one.

## `WorkflowRow`, [line 711](../../../../../../../backend/src/sro/infrastructure/db/models.py#L711): Note on the line above
## `WorkflowRow`, [line 726](../../../../../../../backend/src/sro/infrastructure/db/models.py#L726): Note on the line above

Code: `repeat: Mapped[Any] = mapped_column(JSONB, nullable=True)`

> The steps this job does once per thing on a list, as `{first_step,
> last_step}`, or NULL for a job that does one thing once -- which is most of
> them and every job mined before repeats existed. JSONB rather than two
> integer columns because the pair is one fact and a row with one of them set
> is a row that means nothing.

## `WorkflowRow`, [line 711](../../../../../../../backend/src/sro/infrastructure/db/models.py#L711): Note on the line above
## `WorkflowRow`, [line 730](../../../../../../../backend/src/sro/infrastructure/db/models.py#L730): Note on the line above

Code: `same_as: Mapped[str | None] = mapped_column(String(64))`

> The model's opinion about whether this is one it has proposed before. It
> is recorded and it decides nothing: a model re-judging its own earlier
> verdict disagrees with itself at roughly 90%.
>
> No longer asked for (2026-09-23): the mining schema dropped the field, and
> the column stays because no column is dropped in that wave. Old rows keep
> what they had; new rows are NULL.

## `WorkflowRow`, [line 711](../../../../../../../backend/src/sro/infrastructure/db/models.py#L711): Note on the line above
## `WorkflowRow`, [line 734](../../../../../../../backend/src/sro/infrastructure/db/models.py#L734): Note on the line above

Code: `retired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))`

> When an operator retired this job, or NULL for a live one. The row is kept
> rather than deleted so its citations stay placed: the mining pass never
> reads a retired job's gestures into a fresh copy of it. `known` and `get`
> do not return it, and `save` never writes this column.

## `WorkflowPlacementRow`, [line 739](../../../../../../../backend/src/sro/infrastructure/db/models.py#L739): Docstring
## `WorkflowPlacementRow`, [line 739](../../../../../../../backend/src/sro/infrastructure/db/models.py#L739): Docstring

> A gesture a job has explained without a step citing it: a doing the mining
> pass recognised as that job, or one a growth replaced. Keyed by tenant and
> gesture, because what the mining pass asks is "has anything placed this",
> once per gesture; the job is kept for whoever asks which.

## `WorkflowStepRow`, [line 747](../../../../../../../backend/src/sro/infrastructure/db/models.py#L747): Docstring
## `WorkflowStepRow`, [line 747](../../../../../../../backend/src/sro/infrastructure/db/models.py#L747): Docstring

> One step of a workflow, and the gestures that prove it.
>
> No tenant of its own and no foreign key, as in the rig: a step is reached
> only through its workflow, which carries the tenant, and the workflow's
> save deletes and reinserts this whole set every time.
>
> ``cites`` is the reason the mining prompt selects rather than generates:
> free-generated workflow JSON hallucinated up to 21% of steps, and forced to
> select from real evidence that fell below 7.5%. An uncited step is rejected.

## `WorkflowStepRow`, [line 747](../../../../../../../backend/src/sro/infrastructure/db/models.py#L747): Note on the line above
## `WorkflowStepRow`, [line 757](../../../../../../../backend/src/sro/infrastructure/db/models.py#L757): Note on the line above

Code: `uses: Mapped[Any] = mapped_column(JSONB, nullable=False, default=list)`

> The earlier steps whose output this one consumes, by `ord`.
>
> Empty on every job mined so far and honestly so: nothing emits the edge
> yet. See `Step.uses`, which carries the argument and the measurement.

## `WorkflowStaleRow`, [line 760](../../../../../../../backend/src/sro/infrastructure/db/models.py#L760): Docstring
## `WorkflowStaleRow`, [line 760](../../../../../../../backend/src/sro/infrastructure/db/models.py#L760): Docstring

> A step whose control was only found by the weakest rung of the locator
> ladder. The run succeeded; the step is about to break.
>
> One row per step, so a workflow run daily reports the same weak step once
> rather than daily. Kept apart from the workflow itself because that is what
> a mining pass writes and this is what a run learned -- rewriting the
> workflow from here would race a re-mine and lose one of the two.

## `WorkflowLearnedRow`, [line 769](../../../../../../../backend/src/sro/infrastructure/db/models.py#L769): Docstring
## `WorkflowLearnedRow`, [line 769](../../../../../../../backend/src/sro/infrastructure/db/models.py#L769): Docstring

> The locator that last worked for a step whose recorded identity did not.
>
> `WorkflowStaleRow` above is the negative twin: it records that a step is
> about to break. This records what the run FOUND when it did, so the next
> run tries that first instead of climbing the same ladder and paying for the
> same model call to reach the same control.
>
> One row per step, the last answer winning, and kept apart from the workflow
> for the stale row's reason: the workflow is what a mining pass writes and
> this is what a run observed, and one rewriting the other would race a
> re-mine.

## `WorkflowLearnedRow`, [line 769](../../../../../../../backend/src/sro/infrastructure/db/models.py#L769): Note on the line above
## `WorkflowLearnedRow`, [line 777](../../../../../../../backend/src/sro/infrastructure/db/models.py#L777): Note on the line above

Code: `holds: Mapped[int | None] = mapped_column(Integer)`

> How many characters this step's box will take, where a run has found
> out. Null until one has, and on every step that is not a typing step.

## `WorkflowLearnedHistoryRow`, [line 795](../../../../../../../backend/src/sro/infrastructure/db/models.py#L795): Docstring
## `WorkflowLearnedHistoryRow`, [line 795](../../../../../../../backend/src/sro/infrastructure/db/models.py#L795): Docstring

> What a job taught itself, kept rather than overwritten.
>
> `WorkflowLearnedRow` above is one row per step and the last answer wins.
> That is right for the question it answers -- what should the next run try
> first -- and it means a job rewrites its own behaviour with nothing left
> behind. A locator learned from a screenshot that quietly replaced one
> learned from a component is a job that drifted, and the only record of it
> was the difference between two runs nobody compared.
>
> Append-only and never updated: a history that can be edited is a history
> nobody can rely on. Read by nobody in the hot path, so a job that has
> learned four hundred times costs a run nothing.

## `WorkflowLearnedHistoryRow`, [line 795](../../../../../../../backend/src/sro/infrastructure/db/models.py#L795): Note on the line above
## `WorkflowLearnedHistoryRow`, [line 802](../../../../../../../backend/src/sro/infrastructure/db/models.py#L802): Note on the line above

Code: `about: Mapped[str] = mapped_column(Text, nullable=False)`

> `locator` or `holds`. One table rather than two: they are the same event
> -- a job changed its mind about a step -- and a reader wants them in one
> order.

## `WorkflowLearnedHistoryRow`, [line 795](../../../../../../../backend/src/sro/infrastructure/db/models.py#L795): Note on the line above
## `WorkflowLearnedHistoryRow`, [line 805](../../../../../../../backend/src/sro/infrastructure/db/models.py#L805): Note on the line above

Code: `now: Mapped[str] = mapped_column(Text, nullable=False, default="")`

> What it was and what it became, both as text including the limit: the
> reader is a person, and `4` beside `60` says what a nullable integer column
> would say less clearly.

## `WorkflowLearnedHistoryRow`, [line 795](../../../../../../../backend/src/sro/infrastructure/db/models.py#L795): Note on the line above
## `WorkflowLearnedHistoryRow`, [line 808](../../../../../../../backend/src/sro/infrastructure/db/models.py#L808): Note on the line above

Code: `found_by: Mapped[str] = mapped_column(Text, nullable=False, default="")`

> Which run taught it and which rung produced it, so somebody reading a
> surprising locator can go and look at the run that found it.

## `LearnedWriteRow`, [line 813](../../../../../../../backend/src/sro/infrastructure/db/models.py#L813): Docstring
## `LearnedWriteRow`, [line 813](../../../../../../../backend/src/sro/infrastructure/db/models.py#L813): Docstring

> A write this deployment has watched succeed, and may now replay.
>
> `knowledge-base/index/write-endpoints.json` is the other ledger, and it is
> a research project's hand-kept file: a deployment could not add to it, so
> a job whose write it had confirmed eight times still clicked Save the
> ninth. This is what the deployment learnt for itself, under the same bar
> the file claims -- the call went out live, the step held, and the verdict
> came from a state belt rather than from a model reading a picture.
>
> Keyed by tenant, because a write verified against one customer's system is
> not verified against another's. `origin` is kept beside the pattern rather
> than in the key: the ledger's match is on `(method, path)` and a second
> system serving the same path is the case a tenant scope already answers.

## `LearnedWriteRow`, [line 813](../../../../../../../backend/src/sro/infrastructure/db/models.py#L813): Note on the line above
## `LearnedWriteRow`, [line 823](../../../../../../../backend/src/sro/infrastructure/db/models.py#L823): Note on the line above

Code: `verified_by: Mapped[str] = mapped_column(String(16), nullable=False)`

> `status` or `read` -- which state belt saw it. A picture is not an
> effect and never reaches here; see `state_verified`.

## `WorkflowEffectRow`, [line 828](../../../../../../../backend/src/sro/infrastructure/db/models.py#L828): Docstring
## `WorkflowEffectRow`, [line 828](../../../../../../../backend/src/sro/infrastructure/db/models.py#L828): Docstring

> One write a live run made and the verifier then saw hold by STATE -- a
> status the server answered, or a read that showed the record.
>
> Never by a picture: a model reading a screenshot is not evidence anything
> was written. Three runs whose every write is in here is what buys a job the
> right to write unasked, and one failed write empties it for that workflow.

## `MiningPassRow`, [line 838](../../../../../../../backend/src/sro/infrastructure/db/models.py#L838): Docstring
## `MiningPassRow`, [line 838](../../../../../../../backend/src/sro/infrastructure/db/models.py#L838): Docstring

> One reading of one tenant's day, and what it cost.
>
> ``mining_passes`` rather than the rig's ``passes``: the shorter word says
> nothing about what kind of pass it is in a schema this size.
>
> Written whether the pass found anything or not -- including when it was
> refused, which is the only record left of a call that cost money and
> returned nothing.

## `MiningPassRow`, [line 838](../../../../../../../backend/src/sro/infrastructure/db/models.py#L838): Note on the line above
## `MiningPassRow`, [line 847](../../../../../../../backend/src/sro/infrastructure/db/models.py#L847): Note on the line above

Code: `thought_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)`

> Inside out_tokens, not beside them.

## `MiningPassRow`, [line 838](../../../../../../../backend/src/sro/infrastructure/db/models.py#L838): Note on the line above
## `MiningPassRow`, [line 855](../../../../../../../backend/src/sro/infrastructure/db/models.py#L855): Note on the line above

Code: `learned_parameters: Mapped[int] = mapped_column(Integer, nullable=False, default=0)`

> What the pass LEARNT, beside what it kept. See `MiningPass`.

## `MiningPassRow`, [line 838](../../../../../../../backend/src/sro/infrastructure/db/models.py#L838): Note on the line above
## `MiningPassRow`, [line 862](../../../../../../../backend/src/sro/infrastructure/db/models.py#L862): Note on the line above

Code: `unplaced: Mapped[int] = mapped_column(Integer, nullable=False, default=0)`

> How much evidence this pass was shown, and how much the budget dropped.
> What the scheduled sweep reads to tell a tenant with more to say from one
> whose window already held everything. See `MiningPass`.

## `MiningPassRow`, [line 838](../../../../../../../backend/src/sro/infrastructure/db/models.py#L838): Note on the line above
## `MiningPassRow`, [line 864](../../../../../../../backend/src/sro/infrastructure/db/models.py#L864): Note on the line above

Code: `error: Mapped[str | None] = mapped_column(Text)`

> Why it found nothing, when it found nothing for a reason the API gave.
> An honest zero and a refused call are the same row without this.

## `AttemptRow`, [line 869](../../../../../../../backend/src/sro/infrastructure/db/models.py#L869): Docstring
## `AttemptRow`, [line 869](../../../../../../../backend/src/sro/infrastructure/db/models.py#L869): Docstring

> Something a person asked this system for, and what came of it.
>
> Append-only, and nothing in this system's behaviour reads it: that is what
> makes it safe to write from a door that is in the middle of refusing
> something. See `sro.domain.observation.attempts` for what belongs here and
> what does not.

## `OfferRow`, [line 884](../../../../../../../backend/src/sro/infrastructure/db/models.py#L884): Docstring
## `OfferRow`, [line 884](../../../../../../../backend/src/sro/infrastructure/db/models.py#L884): Docstring

> One offer the extension made from a recognised prefix, and its fate.
>
> The labelled record of whether recognition was right: the share of
> ``diverged`` in a job's newest offers is what moves its threshold, and a run
> of refusals from one browser is what rests it there.
>
> ``seq`` is the rig's ``rowid`` tiebreak made explicit. The extension sends
> the browser's own clock, several offers can carry the same second, and the
> newest three of them decide whether a job is rested -- so "newest" has to
> mean arrival order once ``at`` ties, and Postgres promises no order at all
> without a column to say so.

## `OfferRow`, [line 884](../../../../../../../backend/src/sro/infrastructure/db/models.py#L884): Note on the line above
## `OfferRow`, [line 893](../../../../../../../backend/src/sro/infrastructure/db/models.py#L893): Note on the line above

Code: `k: Mapped[int] = mapped_column(Integer, nullable=False)`

> How many gestures of the tail matched when it was offered. Zero is an
> arrival nudge -- "you have been here before", nothing typed -- which is
> neither kind of evidence and is filtered out of the counsel window.

## `ChatRow`, [line 920](../../../../../../../backend/src/sro/infrastructure/db/models.py#L920): Docstring
## `ChatRow`, [line 920](../../../../../../../backend/src/sro/infrastructure/db/models.py#L920): Docstring

> One sentence the chat door read, and what the reading cost.
>
> The sentence is not here and there is no column for it: it is an operator's
> words about their warehouse, and the row exists for the cap and the spend
> line, neither of which needs them.

## `ChatRow`, [line 920](../../../../../../../backend/src/sro/infrastructure/db/models.py#L920): Note on the line above
## `ChatRow`, [line 925](../../../../../../../backend/src/sro/infrastructure/db/models.py#L925): Note on the line above

Code: `workflow_id: Mapped[str | None] = mapped_column(String(64))`

> The job the sentence turned out to be about, when it was about one.

## `ChatRow`, [line 920](../../../../../../../backend/src/sro/infrastructure/db/models.py#L920): Note on the line above
## `ChatRow`, [line 929](../../../../../../../backend/src/sro/infrastructure/db/models.py#L929): Note on the line above

Code: `thought_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)`

> Inside out_tokens, not beside them.

## `ChatRow`, [line 920](../../../../../../../backend/src/sro/infrastructure/db/models.py#L920): Note on the line above
## `ChatRow`, [line 932](../../../../../../../backend/src/sro/infrastructure/db/models.py#L932): Note on the line above

Code: `unpriced: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)`

> A reading that cost nothing and a reading nobody could price are the
> same row without this, and the day's bill is understated silently.

## `RecordingRow`, [line 35](../../../../../../../backend/src/sro/infrastructure/db/models.py#L35): Comment

Code: `objective_type: Mapped[str | None] = mapped_column(String(64))`

> Nullable while capturing: the evidence names the task at seal.

## `RecordingRow`, [line 45](../../../../../../../backend/src/sro/infrastructure/db/models.py#L45): Comment

Code: `device_id: Mapped[str | None] = mapped_column(String(64))`

> The operator's own browser, when the demonstration happened there. A
> recording has one or the other, never both.

## `SkillRow`, [line 91](../../../../../../../backend/src/sro/infrastructure/db/models.py#L91): Comment

Code: `"version_id_col": revision,`

> The UPDATE carries `WHERE revision = <what was read>`, so a write
> onto a skill somebody else has touched fails instead of landing, and
> `UnitOfWork.commit` turns that into a `Conflict` for the caller to
> answer.

## `SkillRow`, [line 95](../../../../../../../backend/src/sro/infrastructure/db/models.py#L95): Comment

Code: `Index(`

> One skill per objective per tenant: induction adds a version rather
> than a second skill, which is what makes provenance a chain.

## `ConnectionRow`, [line 125](../../../../../../../backend/src/sro/infrastructure/db/models.py#L125): Comment

Code: `Index("uq_connections_tenant_system", "tenant_id", "target_system", unique=True),`

> One connection per system per tenant: a second would mean two sessions
> racing each other into the same WMS.

## `RunRow`, [line 138](../../../../../../../backend/src/sro/infrastructure/db/models.py#L138): Comment

Code: `device_id: Mapped[str | None] = mapped_column(String(64))`

> Nullable: almost every run is performed in a browser the deployment owns,
> and this names the operator's own when it is not.

## `RunRow`, [line 139](../../../../../../../backend/src/sro/infrastructure/db/models.py#L139): Comment

Code: `may_take_focus: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)`

> False for every run that already exists, which is what they were: nothing
> could take an operator's screen before there was a browser to take it in.

## `RunRow`, [line 141](../../../../../../../backend/src/sro/infrastructure/db/models.py#L141): Comment

Code: `systems: Mapped[Any] = mapped_column(JSONB, nullable=False, default=list)`

> Every system the run touched, for the breaker of a system it wrote into
> without being keyed by. Empty for the ordinary single-system run, which is
> every run there has ever been.

## `RunRow`, [line 142](../../../../../../../backend/src/sro/infrastructure/db/models.py#L142): Comment

Code: `iterations: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)`

> What each loop's body is being run with, one entry per thing in the list
> the system returned. Empty for a skill without loops, which is most.

## `RunRow`, [line 155](../../../../../../../backend/src/sro/infrastructure/db/models.py#L155): Comment

Code: `wrong_because: Mapped[str | None] = mapped_column(Text)`

> Null means nobody said anything, which is the ordinary case and is not a
> verdict. Set only by the one person who saw what this run made.

## `RunRow`, [line 156](../../../../../../../backend/src/sro/infrastructure/db/models.py#L156): Comment

Code: `intent: Mapped[str] = mapped_column(Text, nullable=False, default="")`

> Empty for a console run, a batch, a trigger -- everything that did not
> begin with somebody typing a sentence. The one store for it; see
> ``Run.intent``.

## `RunRow`, [line 157](../../../../../../../backend/src/sro/infrastructure/db/models.py#L157): Comment

Code: `revisions: Mapped[Any] = mapped_column(JSONB, nullable=False, default=list)`

> Values the operator changed while this was running: [name, value, when],
> in the order they changed them. A document because nothing queries one --
> they are read beside the run, by somebody asking who decided what it used.

## `RunRow`, [line 161](../../../../../../../backend/src/sro/infrastructure/db/models.py#L161): Comment

Code: `Index("ix_runs_system_ended", "tenant_id", "target_system", "ended_at"),`

> The breaker's question: how has this system behaved lately.

## `RunRow`, [line 162](../../../../../../../backend/src/sro/infrastructure/db/models.py#L162): Comment

Code: `Index(`

> One unfinished run per browser, the same rule
> `uq_workflow_runs_one_running_per_device` keeps for the rig -- and
> the skill path had none of any kind. Two triggers firing two skills
> at one device in the same minute interleaved their clicks into one
> window, which is exactly the corrupted form against a live warehouse
> that migration 0043 was written about.
>
> `ended_at IS NULL` is this table's word for running. And a run with
> no `device_id` is a Steel run in a browser of its own: Postgres does
> not collide NULLs in a unique index, which is the answer wanted here
> rather than an exception to write down.

## `KnowledgeRow`, [line 189](../../../../../../../backend/src/sro/infrastructure/db/models.py#L189): Comment

Code: `superseded_by: Mapped[str | None] = mapped_column(String(64))`

> Superseded rows are kept: "we used to believe this" is the only way to
> explain an incident afterwards.

## `KnowledgeRow`, [line 194](../../../../../../../backend/src/sro/infrastructure/db/models.py#L194): Comment

Code: `Index(`

> Retrieval filters on all four before it ever measures a distance.

## `KnowledgeRow`, [line 203](../../../../../../../backend/src/sro/infrastructure/db/models.py#L203): Comment

Code: `Index(`

> The only vector index in the schema, and for a long time there was
> none: every semantic lookup read every one of the tenant's rows and
> computed an exact 768-dimension distance on each. Measured on this
> store, one tenant, 3,485 rows: 139 ms without it and 4.9 ms with,
> 20 of 20 recall against the exact answer. Migration 0050 carries the
> reasoning for HNSW over IVFFlat and for the partial predicate.

## `ThreadRow`, [line 243](../../../../../../../backend/src/sro/infrastructure/db/models.py#L243): Comment

Code: `messages: Mapped[Any] = mapped_column(JSONB, nullable=False, default=list)`

> One document: a thread is read whole and never queried by message.

## `ObservationBatchRow`, [line 328](../../../../../../../backend/src/sro/infrastructure/db/models.py#L328): Comment
## `ObservationBatchRow`, [line 336](../../../../../../../backend/src/sro/infrastructure/db/models.py#L336): Comment

Code: `recording_id: Mapped[str | None] = mapped_column(String(64), index=True)`

> Null for passive capture, which is all of it until somebody is asked to
> demonstrate something.

## `ObservationBatchRow`, [line 328](../../../../../../../backend/src/sro/infrastructure/db/models.py#L328): Comment
## `ObservationBatchRow`, [line 346](../../../../../../../backend/src/sro/infrastructure/db/models.py#L346): Comment

Code: `rejected: Mapped[Any] = mapped_column(JSONB, nullable=False, default=list)`

> Kept with the batch rather than logged: a rejection is a bug in a specific
> version of the extension, and it has to be findable next to the upload it
> came from.

## `TriggerRow`, [line 362](../../../../../../../backend/src/sro/infrastructure/db/models.py#L362): Comment
## `TriggerRow`, [line 375](../../../../../../../backend/src/sro/infrastructure/db/models.py#L375): Comment

Code: `from_message: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)`

> Which of those values whatever fires this may supply instead. A column
> rather than a key inside `parameters`, because these two are read in
> opposite directions: one is what the trigger knows, the other is what it
> is allowed to be told.

## `TriggerRow`, [line 362](../../../../../../../backend/src/sro/infrastructure/db/models.py#L362): Comment
## `TriggerRow`, [line 376](../../../../../../../backend/src/sro/infrastructure/db/models.py#L376): Comment

Code: `watch: Mapped[dict[str, Any] | None] = mapped_column(JSONB)`

> What makes a mail one of these, for a trigger the operator's browser
> evaluates. Terms and locators only: a term names a header and carries the
> operator's own phrase, a value carries a place to read and no text, so
> there is no field here a mail body would fit in.

## `TriggerRow`, [line 362](../../../../../../../backend/src/sro/infrastructure/db/models.py#L362): Comment
## `TriggerRow`, [line 377](../../../../../../../backend/src/sro/infrastructure/db/models.py#L377): Comment

Code: `arrival: Mapped[dict[str, Any] | None] = mapped_column(JSONB)`

> And the other rule a browser holds: the page whose arrival starts this.
> Beside the watch rather than inside it -- a watch carries terms about a
> mail, an arrival carries one page, and there is nowhere in either for
> the other's content.

## `TriggerRow`, [line 362](../../../../../../../backend/src/sro/infrastructure/db/models.py#L362): Comment
## `TriggerRow`, [line 384](../../../../../../../backend/src/sro/infrastructure/db/models.py#L384): Comment

Code: `authorized_by: Mapped[str | None] = mapped_column(String(64))`

> Not nullable by accident: a trigger for a skill that writes cannot exist
> without one, and the entity refuses to be built otherwise.

## `TaskCandidateRow`, [line 401](../../../../../../../backend/src/sro/infrastructure/db/models.py#L401): Comment
## `TaskCandidateRow`, [line 408](../../../../../../../backend/src/sro/infrastructure/db/models.py#L408): Comment

Code: `signature: Mapped[str] = mapped_column(Text, nullable=False)`

> The clustering key, and the reason the table has a unique index rather
> than a primary key that means anything: mining runs again over evidence
> it has read, and the same task must find its own row.

## `TaskCandidateRow`, [line 401](../../../../../../../backend/src/sro/infrastructure/db/models.py#L401): Comment
## `TaskCandidateRow`, [line 410](../../../../../../../backend/src/sro/infrastructure/db/models.py#L410): Comment

Code: `starts_on: Mapped[str] = mapped_column(Text, nullable=False, default="")`

> The page the first doing began on, host and path, no query. What a panel
> recognises when somebody lands there. Empty where no gesture carried a
> URL, which is every candidate mined before this column existed.

## `TaskCandidateRow`, [line 401](../../../../../../../backend/src/sro/infrastructure/db/models.py#L401): Comment
## `TaskCandidateRow`, [line 413](../../../../../../../backend/src/sro/infrastructure/db/models.py#L413): Comment

Code: `learned_from: Mapped[int] = mapped_column(Integer, nullable=False, default=0)`

> How many doings had been seen when learning was last tried on this, so an
> unattended sweep does not retry the same evidence every quarter hour.

## `TaskCandidateRow`, [line 401](../../../../../../../backend/src/sro/infrastructure/db/models.py#L401): Comment
## `TaskCandidateRow`, [line 414](../../../../../../../backend/src/sro/infrastructure/db/models.py#L414): Comment

Code: `learned_under: Mapped[int] = mapped_column(Integer, nullable=False, default=0)`

> And which induction rules made that attempt, so a candidate refused under
> rules that have since been fixed comes back without waiting for a doing.

## `TaskCandidateRow`, [line 401](../../../../../../../backend/src/sro/infrastructure/db/models.py#L401): Comment
## `TaskCandidateRow`, [line 419](../../../../../../../backend/src/sro/infrastructure/db/models.py#L419): Comment

Code: `offered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))`

> When this was offered to the operator, so a quarter-hourly sweep does not
> say the same sentence into their thread again.

## `TaskCandidateRow`, [line 401](../../../../../../../backend/src/sro/infrastructure/db/models.py#L401): Comment
## `TaskCandidateRow`, [line 422](../../../../../../../backend/src/sro/infrastructure/db/models.py#L422): Comment

Code: `joins: Mapped[Any] = mapped_column(JSONB, nullable=False, default=list)`

> Suggestions about this candidate -- read whole beside it, never queried,
> and never acted on by anything but a person.

## `ConfirmationRow`, [line 449](../../../../../../../backend/src/sro/infrastructure/db/models.py#L449): Comment
## `ConfirmationRow`, [line 470](../../../../../../../backend/src/sro/infrastructure/db/models.py#L470): Comment

Code: `__table_args__ = (Index("ix_confirmations_tenant_answer", "tenant_id", "answer", "asked_at"),)`

> What the console asks for: this tenant's, oldest first, waiting ones.

## `GestureRow`, [line 491](../../../../../../../backend/src/sro/infrastructure/db/models.py#L491): Inline
## `GestureRow`, [line 503](../../../../../../../backend/src/sro/infrastructure/db/models.py#L503): Inline

Code: `system: Mapped[str | None] = mapped_column(Text)`

> scheme+host, derived at ingest

## `IntentRow`, [line 519](../../../../../../../backend/src/sro/infrastructure/db/models.py#L519): Comment
## `IntentRow`, [line 547](../../../../../../../backend/src/sro/infrastructure/db/models.py#L547): Comment

Code: `__table_args__ = (Index("ix_intents_tenant_created", "tenant_id", "created_at"),)`

> The spend sum reads it: everything this tenant was billed for over a
> window, and a cap that cannot ask that question is not a cap.

## `WorkflowRunRow`, [line 585](../../../../../../../backend/src/sro/infrastructure/db/models.py#L585): Comment
## `WorkflowRunRow`, [line 594](../../../../../../../backend/src/sro/infrastructure/db/models.py#L594): Comment

Code: `quoted_name("values", True),`

> Quoted by hand: SQLAlchemy does not hold `values` to be reserved and
> would emit it bare, which Postgres happens to accept in a column
> definition and does not in every position a query can put it.

## `WorkflowRunRow`, [line 585](../../../../../../../backend/src/sro/infrastructure/db/models.py#L585): Comment
## `WorkflowRunRow`, [line 645](../../../../../../../backend/src/sro/infrastructure/db/models.py#L645): Comment

Code: `Index("ix_workflow_runs_undoes", "undoes_run"),`

> The one question `undoes_run` is asked: has this run been taken back
> already. Without it, answering it reads every run of the tenant.

## `WorkflowRunRow`, [line 585](../../../../../../../backend/src/sro/infrastructure/db/models.py#L585): Comment
## `WorkflowRunRow`, [line 646](../../../../../../../backend/src/sro/infrastructure/db/models.py#L646): Comment

Code: `Index("ix_workflow_runs_tenant_device", "tenant_id", "device_id", "outcome"),`

> The busy check: whether this browser already has a run in flight.
> One browser, one hand -- two runs driving the same window interleave
> their clicks into a form neither of them can then read back.

## `WorkflowRunRow`, [line 647](../../../../../../../backend/src/sro/infrastructure/db/models.py#L647): Comment

Code: `Index(`

> And the rule the index above can only report on. Reading "is this
> browser busy" and then claiming it is two statements with awaits
> between them, so two presses on one event loop both read free and
> both claim -- demonstrated against real Postgres, two rows and one
> browser. Migration 0039 named this index as what a second worker
> would need; it turns out one worker needs it too, because async does
> not give one request at a time.

## `WorkflowRunRow`, [line 654](../../../../../../../backend/src/sro/infrastructure/db/models.py#L654): Comment

Code: `Index(`

> "Is any run of this tenant waiting to hear back on this thread", and
> that is the only question asked of it -- once per arriving mail, on
> every beat. Partial because almost no run names a conversation, and
> on the expressions rather than the column because a match is on two
> fields inside one document.
>
> Declared here as well as in migration 0062 for the reason the index
> above it is: the rest of the suite builds its schema from
> `Base.metadata`, so an index that lived only in the migration would
> keep every test green while the thing a deployment runs built
> something else. `test_the_migrations_run` compares the two.

## `WorkflowLearnedHistoryRow`, [line 795](../../../../../../../backend/src/sro/infrastructure/db/models.py#L795): Comment
## `WorkflowLearnedHistoryRow`, [line 797](../../../../../../../backend/src/sro/infrastructure/db/models.py#L797): Comment

Code: `__table_args__ = (Index("ix_workflow_learned_history_job", "workflow_id", "at"),)`

> The one query this table is for: what has this job taught itself, newest
> first. Declared here as well as in the migration, because the schema the
> code describes and the schema the migrations build are held equal by a
> test -- and an index in one and not the other is a query that is fast in
> development and a sequential scan in production.

## `AttemptRow`, [line 869](../../../../../../../backend/src/sro/infrastructure/db/models.py#L869): Comment
## `AttemptRow`, [line 871](../../../../../../../backend/src/sro/infrastructure/db/models.py#L871): Comment

Code: `__table_args__ = (Index("ix_attempts_tenant_at", "tenant_id", "at"),)`

> The only question this table is asked: what happened to this tenant,
> since when. A plain index on the tenant would make Postgres sort a
> tenant's whole history to answer it.

## `AttemptRow`, [line 869](../../../../../../../backend/src/sro/infrastructure/db/models.py#L869): Comment
## `AttemptRow`, [line 874](../../../../../../../backend/src/sro/infrastructure/db/models.py#L874): Comment

Code: `seq: Mapped[int] = mapped_column(BigInteger, Identity(), nullable=False)`

> `offers`' tiebreak, for its reason: several attempts share a second and
> "newest" has to mean arrival order once `at` ties.
