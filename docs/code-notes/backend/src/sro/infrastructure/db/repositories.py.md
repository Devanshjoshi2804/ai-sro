# Notes for `backend/src/sro/infrastructure/db/repositories.py`

Comments and docstrings moved out of [`backend/src/sro/infrastructure/db/repositories.py`](../../../../../../../backend/src/sro/infrastructure/db/repositories.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/infrastructure/db/repositories.py#L1): Docstring

> Postgres-backed repositories and the unit of work.
>
> Reads are always filtered by ``tenant_id`` as well as by id. A row belonging to
> another tenant is reported as ``NotFound``, which is the same answer as a row
> that does not exist -- the difference is not something a caller may learn.

## `SqlSkillRepository`, [line 183](../../../../../../../backend/src/sro/infrastructure/db/repositories.py#L183): Docstring

> Holds on to the rows it read, for as long as the unit of work lasts.
>
> SQLAlchemy's identity map is weak, and a repository that loads a row, builds
> an aggregate out of it and drops the row leaves nothing referring to it --
> so the row is collected and the next `save` re-reads it. That re-read is
> what defeated the version check on `skills`: it fetched, and believed, a
> `latest_version` somebody else had committed in between, and then wrote over
> them. Keeping the row is what makes "the version I read" mean anything.

## `_terms`, [line 360](../../../../../../../backend/src/sro/infrastructure/db/repositories.py#L360): Docstring

> Words worth matching. Two characters or fewer match everything.

## `SqlKnowledgeRepository`, [line 368](../../../../../../../backend/src/sro/infrastructure/db/repositories.py#L368): Docstring

> Structured filters narrow, similarity only orders.
>
> A nearest-neighbour search across the whole store answers confidently with
> another system's endpoint, so system and kind are `WHERE` clauses and the
> vector is an `ORDER BY`. Superseded rows never come back: they are history,
> not belief.

## `SqlModelCallRepository`, [line 519](../../../../../../../backend/src/sro/infrastructure/db/repositories.py#L519): Docstring

> Append-only. A model call is a fact about what left the deployment.

## `_lease_of`, [line 539](../../../../../../../backend/src/sro/infrastructure/db/repositories.py#L539): Note

> Every reader (``current_lease``, ``get_lease``, ``expired``) already filters
> to rows with a real ``state`` before it reaches here -- ``get_lease`` by an
> explicit check, the other two by ``state.in_(_LIVE_STATES)`` -- so the guard
> is unreachable in practice, in the same way `ck_browser_sessions_lease_is_whole`
> (`models.py`) makes the None-checks on the other eight fields unreachable
> too: the database already refuses a row that is live and incomplete.
> Both stay for the same reason -- a function that turns a row into a
> `Lease` should refuse to fabricate one from a corrupt row rather than mask
> it with `or ""` and hand back an account with an empty username, which
> the previous version of this function did.

## `SqlBrowserSessionRepository.expire`, [line 666](../../../../../../../backend/src/sro/infrastructure/db/repositories.py#L666): Note

> `expires_at <= now` is in the `WHERE`, not just in the sweeper's earlier
> `expired(now=...)` read -- a compare-and-set, so a `beat` that lands
> between the sweeper's read and this write leaves the row's `expires_at`
> in the future and this `UPDATE` matches zero rows.
>
> ponytail: `now` is whichever clock called `expire` or `beat` -- the
> sweeper's process for one, the holder's for the other, not necessarily the
> same box. `K_LEASE_TTL` is two minutes, and ordinary clock skew is noise
> against that; the native rung, if it ever is not, is `now()` inside the
> database for both, so both writers use the one clock. The tests inject
> `now` on purpose and would need to change first.

## `SqlBrowserSessionRepository`, [line 565](../../../../../../../backend/src/sro/infrastructure/db/repositories.py#L565): Docstring

> Ownership of a browser, and, since S2, an account's lease -- one table,
> because the stray sweeper has to see both kinds without a join.
>
> ``held_by`` and ``all_held`` add ``state.is_(None)`` so a lease row never
> answers for a capture session's claim. ``get_lease`` is the one place that
> DOES fetch a row by id -- a run re-attaching after a restart has the lease
> id from its own progress, not the account -- but it is tenant-checked
> in Python after the fetch rather than in the `WHERE`, the same shape
> ``_row`` would have, because a lease found under the wrong tenant is worth
> a clear "not yours" rather than a silent "not found".

## `SqlBrowserSessionRepository.lease`, [line 612](../../../../../../../backend/src/sro/infrastructure/db/repositories.py#L612): Note

> `on_conflict_do_nothing` against the partial unique index, then a plain
> read -- never `RETURNING`, because the row `RETURNING` would answer with is
> empty on the losing side of a race, and the caller does not want "empty",
> it wants whichever lease won. Two inserts racing at once always agree
>
> A `None` read here means the winner was settled (by the sweeper's
> `expire`, or the holder's own `settle`) in the gap between this insert and
> this re-read -- a real but narrow race, not a corrupt account. `Conflict`
> says so; it used to be `InvariantViolation`, which reads as a caller's own
> mistake and answers 422, when the honest answer is "try again", 409.
> afterward on the same read.

## `SqlToolCallRepository`, [line 994](../../../../../../../backend/src/sro/infrastructure/db/repositories.py#L994): Docstring

> The claim is the insert. Two writers racing for one key both try it, the
> primary key refuses one of them, and that refusal is the answer.

## `SqlUnitOfWork`, [line 1087](../../../../../../../backend/src/sro/infrastructure/db/repositories.py#L1087): Docstring

> One session per block. The session opens on entry, not on construction,
> so a unit of work can be built once and used per request.
>
> **Re-entrant, by depth count.** A use case handed this object may open a
> block inside another block on the same instance -- `run_workflow`'s write
> claim sits inside `StartWorkflowRun`'s block, and `InduceSkill` runs
> `AskAbout`'s whole block inside its own. Opening a second session there is
> what the obvious implementation does, and it is a crash and a leak: the
> inner `__aexit__` closes the new session and sets `_session` to None, so
> the outer block's next `commit()` raises "must be used as an async context
> manager" -- which the panel renders as the run's failure reason -- while
> the outer session's connection is never returned to the pool. Fifteen of
> those wedge the API on checkout (`pool_size=5, max_overflow=10`).
>
> So the inner block reuses the session and the outermost exit closes it.
> One request is one transaction, which is what the surrounding code already
> assumed and what `tests.unit.fakes.FakeUnitOfWork` has always modelled --
> its `_entered` is sticky for this exact reason, which is why 3000 green
> unit tests never saw the real one's behaviour. An inner `commit()` still
> commits, as it did before; an exception inside a nested block rolls the
> whole thing back at the outermost exit rather than half of it.

## `SqlToolCallRepository.forget`, [line 1026](../../../../../../../backend/src/sro/infrastructure/db/repositories.py#L1026): Docstring

> Delete the claim. Tenant-scoped, unlike the session sweep next door:
> this is somebody's run giving back its own key, not crash recovery.

## `SqlRunRepository.in_flight`, [line 289](../../../../../../../backend/src/sro/infrastructure/db/repositories.py#L289): Comment

Code: `busy: str | None = await self._session.scalar(`

> `ended_at IS NULL` is this table's word for running, and the same
> predicate `uq_runs_one_running_per_device` is built on: a read that
> disagreed with the index would refuse runs the index allows, or
> promise ones it will not.

## `SqlRunRepository.finished_since`, [line 339](../../../../../../../backend/src/sro/infrastructure/db/repositories.py#L339): Comment

Code: `or_(`

> Keyed by it, or one of the systems it touched on the way. A
> workflow that fails in its second system is stored under the
> first, and a breaker that could not see that would be protecting
> nothing while appearing to.

## `SqlKnowledgeRepository.search`, [line 447](../../../../../../../backend/src/sro/infrastructure/db/repositories.py#L447): Comment

Code: `query = query.where(`

> In the query, not after it: filtering the page would hide strong
> claims behind weak ones that happened to sort first.

## `SqlKnowledgeRepository.search`, [line 454](../../../../../../../backend/src/sro/infrastructure/db/repositories.py#L454): Comment

Code: `hits = [`

> Any word, not the whole phrase. "add a carrier" ILIKE'd whole
> matches nothing, and a sentence is how the question arrives.

## `SqlKnowledgeRepository.search`, [line 462](../../../../../../../backend/src/sro/infrastructure/db/repositories.py#L462): Comment

Code: `matched = sum(`

> HOW MANY of them, kept for the ordering below.
>
> `or_` lets a row through on one word and the vector then decided
> everything, which on a store of near-synonyms is the wrong
> decision. Measured on the deployment 2026-09-20: asked "is there
> a customer type called KKYT", the forty entries shown to the
> lookup planner held eleven `...types////` SCREENS and twenty
> `rpux/filter/columns/WM*Types` endpoints -- every one of them
> matching on the single word `type` -- and NOT
> `/data/WM/wm/customerTypes`, which is the endpoint that answers
> the question and which this deployment has watched answer 200
> many times. The planner is told to prefer a call over a screen
> and it did what it was told: no endpoint it was shown could
> answer, so it planned a screen, and the screen was refused for
> wanting the operator's tab.
>
> An entry matching `customer` AND `type` is about customer types.
> One matching `type` alone is about types. That is a difference
> the query already knows and was throwing away.

## `SqlKnowledgeRepository.search`, [line 467](../../../../../../../backend/src/sro/infrastructure/db/repositories.py#L467): Comment

Code: `await self._session.execute(text("SET LOCAL hnsw.iterative_scan = relaxed_order"))`

> The index is over the vector column and nothing else -- pgvector
> indexes one column -- so every other clause here is applied to
> what the scan returns. An HNSW scan stops after `ef_search`
> candidates, and a tenant with a small share of the table can have
> all of its rows filtered out of that set and be answered nothing
> at all. `iterative_scan` is pgvector 0.8's answer: the scan keeps
> pulling until the filters have let enough rows through.
>
> `relaxed_order` rather than `strict_order`: strict re-sorts every
> batch to guarantee exact distance ordering, and this result is
> read by a model choosing which claims to quote, not by anything
> that cares whether the fourth and fifth swapped places.

## `SqlKnowledgeRepository.search`, [line 468](../../../../../../../backend/src/sro/infrastructure/db/repositories.py#L468): Comment

Code: `query = query.where(KnowledgeRow.embedding.is_not(None)).order_by(`

> Words first, then distance. Similarity is an ordering over things
> that already survived the filters, and it cannot tell
> `customerTypes` from `WMCountTypes` -- they are the same word
> twice over in embedding space. How much of the question an entry
> actually says is the cheaper and stronger signal, and distance
> settles the rest.

## `SqlKnowledgeRepository.search`, [line 473](../../../../../../../backend/src/sro/infrastructure/db/repositories.py#L473): Comment

Code: `query = query.order_by(`

> Best evidence first when there is no distance to sort by: a
> reproduced claim outranks a scraped one for the same question.

## `SqlBrowserSessionRepository.claim`, [line 585](../../../../../../../backend/src/sro/infrastructure/db/repositories.py#L585): Comment

Code: `await self._session.flush()`

> Flushed here rather than at commit: the caller is about to hand a
> browser to somebody, and "who owns this" has to be settled before
> they get it, not after the request has already done its work.

## `SqlDeviceRepository.add`, [line 730](../../../../../../../backend/src/sro/infrastructure/db/repositories.py#L730): Comment

Code: `await self._session.flush()`

> Flushed here, like the observation batch: two registrations for
> the same (tenant, principal, label) racing each other must not
> let the second one 500 instead of finding the first via
> `registered_as` the way RegisterDevice's own idempotency assumes.

## `SqlDeviceRepository.since`, [line 762](../../../../../../../backend/src/sro/infrastructure/db/repositories.py#L762): Comment

Code: `at = when(since)`

> Registered since, or revoked since: the audit is asking who could
> act and until when, and a browser registered last month and revoked
> this morning is part of this morning's answer.
>
> Tenant-scoped, where the rig's audit select was not: its device query
> had no `tenant = ?` at all, so one tenant's audit listed every
> tenant's browsers by id. That is a leak rather than a rule, and it
> does not travel.

## `SqlDeviceRepository.since`, [line 769](../../../../../../../backend/src/sro/infrastructure/db/repositories.py#L769): Comment

Code: `.order_by(AgentDeviceRow.registered_at.desc(), AgentDeviceRow.id.desc())`

> On the id as well, as the audit's other three reads all are:
> `workflow_runs.since` and `chats.since` on `id DESC`,
> `offers.since` on `seq DESC`. Two browsers registered in the same
> instant -- one operator installing on two profiles, a fixture
> planting a morning -- have no order at all under
> `registered_at` alone, so the same audit read twice could report
> them two ways and a reader diffing the two saw a change nobody
> made.

## `SqlDeviceRepository.revoke`, [line 775](../../../../../../../backend/src/sro/infrastructure/db/repositories.py#L775): Comment

Code: `row = await self._row(tenant_id, device_id, lock=True)`

> Read then set, rather than a conditional UPDATE: the row is the one
> `get` in this session already holds, so nothing here can leave a
> caller reading a browser it has just revoked as still live. `_row`
> raises `NotFound` for a device this tenant does not have, which is a
> different answer from "there was nothing live to revoke".
>
> Locked, because the read and the set are what the rig did atomically
> in one `UPDATE ... WHERE revoked_at IS NULL`: without the lock two
> concurrent revocations both read a live browser, both answer True,
> and the second overwrites the instant the first recorded -- which is
> precisely what this promises cannot happen.

## `SqlDeviceRepository.revoke`, [line 777](../../../../../../../backend/src/sro/infrastructure/db/repositories.py#L777): Comment

Code: `return False`

> The first revocation stands. A second press must not move the
> instant the authority ended -- that instant is what an audit of
> what this browser was allowed to do is read against.

## `SqlDeviceRepository.revoke`, [line 778](../../../../../../../backend/src/sro/infrastructure/db/repositories.py#L778): Comment

Code: `row.revoked_at = when(at)`

> UTC when it said nothing: this is the server's own clock, and a naive
> local instant beside the aware ones reads as a revocation hours before
> the browser registered.

## `SqlDeviceRepository.restore`, [line 782](../../../../../../../backend/src/sro/infrastructure/db/repositories.py#L782): Comment

Code: `row = await self._row(tenant_id, device_id, lock=True)`

> Read then set under the same lock as `revoke`, and for the same two
> reasons: the row is the one this session already holds, so nothing
> can read a browser it has just restored as still revoked; and two
> concurrent presses must not both answer True, because the boolean is
> what the route reports as "this press is what moved it".
>
> `revoked_at = NULL` and nothing else. The secret is not reissued --
> revoking never blanked it, and the extension is still holding the one
> it was minted with.

## `SqlDeviceRepository._row`, [line 796](../../../../../../../backend/src/sro/infrastructure/db/repositories.py#L796): Comment

Code: `query = query.with_for_update()`

> FOR UPDATE, and only where a caller is about to write what it
> read. Every other read here is a read.

## `SqlObservationRepository.add`, [line 810](../../../../../../../backend/src/sro/infrastructure/db/repositories.py#L810): Comment

Code: `await self._session.flush()`

> Flushed here rather than at commit: the id is the extension's, and
> whether this upload is a retry has to be settled before the
> response says how many events were kept.

## `SqlObservationRepository.between`, [line 831](../../../../../../../backend/src/sro/infrastructure/db/repositories.py#L831): Comment

Code: `query = select(ObservationBatchRow).where(`

> Overlap, not containment: a batch that began before the window and
> ended inside it holds events the window asked for.

## `SqlCandidateRepository.add`, [line 883](../../../../../../../backend/src/sro/infrastructure/db/repositories.py#L883): Comment

Code: `await self._session.flush()`

> A manual mine-now request can race the scheduled sweep onto the
> same new (tenant, principal, signature). Flushed here so that
> collision fails on its own row rather than rolling back every
> candidate the rest of that mining pass already found.

## `SqlCandidateRepository.list_for_tenant`, [line 911](../../../../../../../backend/src/sro/infrastructure/db/repositories.py#L911): Comment

Code: `query = query.where(TaskCandidateRow.host == host.lower())`

> Stored lowercased by the segmenter, so the caller's spelling of a
> hostname does not decide whether their own tasks come back.

## `SqlToolCallRepository.remember`, [line 1007](../../../../../../../backend/src/sro/infrastructure/db/repositories.py#L1007): Comment

Code: `insert = pg_insert(ToolCallRow).values(`

> `ON CONFLICT DO NOTHING` rather than a read followed by a write:
> between the two of those, the other run inserts.
>
> With `stale_after` it is DO UPDATE under a WHERE instead, which is
> the same statement doing the same job for a key that expires: the
> row is taken over only when the claim on it is older than the
> window, and the taking-over is what returns the key. Still one
> statement, because a read-then-decide here is the race this class
> exists to lose.

## `SqlToolCallRepository.remember`, [line 1022](../../../../../../../backend/src/sro/infrastructure/db/repositories.py#L1022): Comment

Code: `).returning(ToolCallRow.idempotency_key)`

> What came back rather than how many rows: `rowcount` is the
> driver's, and asking the statement to return the key it wrote
> answers the same question in one shape everywhere.

## `SqlUnitOfWork.__aexit__`, [line 1127](../../../../../../../backend/src/sro/infrastructure/db/repositories.py#L1127): Comment

Code: `await session.rollback()`

> At every depth: an inner block that raised must not leave its
> half-written rows for the outer block to commit.

## `SqlUnitOfWork.commit`, [line 1139](../../../../../../../backend/src/sro/infrastructure/db/repositories.py#L1139): Comment

Code: `await self._require_session().rollback()`

> Somebody wrote the row between this block reading it and
> committing, and the write that was about to land was computed
> from what it read. Reported as a conflict rather than a crash
> because it is one: the caller decides whether to redo the work
> against what is there now or to leave it to whoever comes next.

## `_job_live`, [line 1079](../../../../../../../backend/src/sro/infrastructure/db/repositories.py#L1079): Note

> A trigger on a retired job is never chosen: `find` (how a schedule fires)
> and `list_for_tenant` (how watches and arrivals are picked) both leave it
> out. `FireTrigger` then finds no trigger and takes the schedule down,
> instead of firing into `NotFound` every period with nobody told (final
> review M-4, 2026-09-24). `get` still returns it by id, so switching it
> off or deleting it still works.
