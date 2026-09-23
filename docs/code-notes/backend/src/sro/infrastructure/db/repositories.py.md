# Notes for `backend/src/sro/infrastructure/db/repositories.py`

Comments and docstrings moved out of [`backend/src/sro/infrastructure/db/repositories.py`](../../../../../../../backend/src/sro/infrastructure/db/repositories.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/infrastructure/db/repositories.py#L1): Docstring

> Postgres-backed repositories and the unit of work.
>
> Reads are always filtered by ``tenant_id`` as well as by id. A row belonging to
> another tenant is reported as ``NotFound``, which is the same answer as a row
> that does not exist -- the difference is not something a caller may learn.

## `SqlSkillRepository`, [line 170](../../../../../../../backend/src/sro/infrastructure/db/repositories.py#L170): Docstring

> Holds on to the rows it read, for as long as the unit of work lasts.
>
> SQLAlchemy's identity map is weak, and a repository that loads a row, builds
> an aggregate out of it and drops the row leaves nothing referring to it --
> so the row is collected and the next `save` re-reads it. That re-read is
> what defeated the version check on `skills`: it fetched, and believed, a
> `latest_version` somebody else had committed in between, and then wrote over
> them. Keeping the row is what makes "the version I read" mean anything.

## `_terms`, [line 347](../../../../../../../backend/src/sro/infrastructure/db/repositories.py#L347): Docstring

> Words worth matching. Two characters or fewer match everything.

## `SqlKnowledgeRepository`, [line 355](../../../../../../../backend/src/sro/infrastructure/db/repositories.py#L355): Docstring

> Structured filters narrow, similarity only orders.
>
> A nearest-neighbour search across the whole store answers confidently with
> another system's endpoint, so system and kind are `WHERE` clauses and the
> vector is an `ORDER BY`. Superseded rows never come back: they are history,
> not belief.

## `SqlModelCallRepository`, [line 506](../../../../../../../backend/src/sro/infrastructure/db/repositories.py#L506): Docstring

> Append-only. A model call is a fact about what left the deployment.

## `SqlBrowserSessionRepository`, [line 523](../../../../../../../backend/src/sro/infrastructure/db/repositories.py#L523): Docstring

> Ownership of a browser, and nothing else about it.
>
> No ``_row(tenant_id, id)`` helper here because nothing fetches one row by
> id: the two-predicate check is ``held_by``, and ``release`` is untenanted on
> purpose -- the sweep and crash recovery are not anybody's request.

## `SqlToolCallRepository`, [line 845](../../../../../../../backend/src/sro/infrastructure/db/repositories.py#L845): Docstring

> The claim is the insert. Two writers racing for one key both try it, the
> primary key refuses one of them, and that refusal is the answer.

## `SqlUnitOfWork`, [line 929](../../../../../../../backend/src/sro/infrastructure/db/repositories.py#L929): Docstring

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

## `SqlToolCallRepository.forget`, [line 877](../../../../../../../backend/src/sro/infrastructure/db/repositories.py#L877): Docstring

> Delete the claim. Tenant-scoped, unlike the session sweep next door:
> this is somebody's run giving back its own key, not crash recovery.

## `SqlRunRepository.in_flight`, [line 276](../../../../../../../backend/src/sro/infrastructure/db/repositories.py#L276): Comment

Code: `busy: str | None = await self._session.scalar(`

> `ended_at IS NULL` is this table's word for running, and the same
> predicate `uq_runs_one_running_per_device` is built on: a read that
> disagreed with the index would refuse runs the index allows, or
> promise ones it will not.

## `SqlRunRepository.finished_since`, [line 326](../../../../../../../backend/src/sro/infrastructure/db/repositories.py#L326): Comment

Code: `or_(`

> Keyed by it, or one of the systems it touched on the way. A
> workflow that fails in its second system is stored under the
> first, and a breaker that could not see that would be protecting
> nothing while appearing to.

## `SqlKnowledgeRepository.search`, [line 434](../../../../../../../backend/src/sro/infrastructure/db/repositories.py#L434): Comment

Code: `query = query.where(`

> In the query, not after it: filtering the page would hide strong
> claims behind weak ones that happened to sort first.

## `SqlKnowledgeRepository.search`, [line 441](../../../../../../../backend/src/sro/infrastructure/db/repositories.py#L441): Comment

Code: `hits = [`

> Any word, not the whole phrase. "add a carrier" ILIKE'd whole
> matches nothing, and a sentence is how the question arrives.

## `SqlKnowledgeRepository.search`, [line 449](../../../../../../../backend/src/sro/infrastructure/db/repositories.py#L449): Comment

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

## `SqlKnowledgeRepository.search`, [line 454](../../../../../../../backend/src/sro/infrastructure/db/repositories.py#L454): Comment

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

## `SqlKnowledgeRepository.search`, [line 455](../../../../../../../backend/src/sro/infrastructure/db/repositories.py#L455): Comment

Code: `query = query.where(KnowledgeRow.embedding.is_not(None)).order_by(`

> Words first, then distance. Similarity is an ordering over things
> that already survived the filters, and it cannot tell
> `customerTypes` from `WMCountTypes` -- they are the same word
> twice over in embedding space. How much of the question an entry
> actually says is the cheaper and stronger signal, and distance
> settles the rest.

## `SqlKnowledgeRepository.search`, [line 460](../../../../../../../backend/src/sro/infrastructure/db/repositories.py#L460): Comment

Code: `query = query.order_by(`

> Best evidence first when there is no distance to sort by: a
> reproduced claim outranks a scraped one for the same question.

## `SqlBrowserSessionRepository.claim`, [line 543](../../../../../../../backend/src/sro/infrastructure/db/repositories.py#L543): Comment

Code: `await self._session.flush()`

> Flushed here rather than at commit: the caller is about to hand a
> browser to somebody, and "who owns this" has to be settled before
> they get it, not after the request has already done its work.

## `SqlDeviceRepository.add`, [line 575](../../../../../../../backend/src/sro/infrastructure/db/repositories.py#L575): Comment

Code: `await self._session.flush()`

> Flushed here, like the observation batch: two registrations for
> the same (tenant, principal, label) racing each other must not
> let the second one 500 instead of finding the first via
> `registered_as` the way RegisterDevice's own idempotency assumes.

## `SqlDeviceRepository.since`, [line 607](../../../../../../../backend/src/sro/infrastructure/db/repositories.py#L607): Comment

Code: `at = when(since)`

> Registered since, or revoked since: the audit is asking who could
> act and until when, and a browser registered last month and revoked
> this morning is part of this morning's answer.
>
> Tenant-scoped, where the rig's audit select was not: its device query
> had no `tenant = ?` at all, so one tenant's audit listed every
> tenant's browsers by id. That is a leak rather than a rule, and it
> does not travel.

## `SqlDeviceRepository.since`, [line 614](../../../../../../../backend/src/sro/infrastructure/db/repositories.py#L614): Comment

Code: `.order_by(AgentDeviceRow.registered_at.desc(), AgentDeviceRow.id.desc())`

> On the id as well, as the audit's other three reads all are:
> `workflow_runs.since` and `chats.since` on `id DESC`,
> `offers.since` on `seq DESC`. Two browsers registered in the same
> instant -- one operator installing on two profiles, a fixture
> planting a morning -- have no order at all under
> `registered_at` alone, so the same audit read twice could report
> them two ways and a reader diffing the two saw a change nobody
> made.

## `SqlDeviceRepository.revoke`, [line 620](../../../../../../../backend/src/sro/infrastructure/db/repositories.py#L620): Comment

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

## `SqlDeviceRepository.revoke`, [line 622](../../../../../../../backend/src/sro/infrastructure/db/repositories.py#L622): Comment

Code: `return False`

> The first revocation stands. A second press must not move the
> instant the authority ended -- that instant is what an audit of
> what this browser was allowed to do is read against.

## `SqlDeviceRepository.revoke`, [line 623](../../../../../../../backend/src/sro/infrastructure/db/repositories.py#L623): Comment

Code: `row.revoked_at = when(at)`

> UTC when it said nothing: this is the server's own clock, and a naive
> local instant beside the aware ones reads as a revocation hours before
> the browser registered.

## `SqlDeviceRepository.restore`, [line 627](../../../../../../../backend/src/sro/infrastructure/db/repositories.py#L627): Comment

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

## `SqlDeviceRepository._row`, [line 641](../../../../../../../backend/src/sro/infrastructure/db/repositories.py#L641): Comment

Code: `query = query.with_for_update()`

> FOR UPDATE, and only where a caller is about to write what it
> read. Every other read here is a read.

## `SqlObservationRepository.add`, [line 655](../../../../../../../backend/src/sro/infrastructure/db/repositories.py#L655): Comment

Code: `await self._session.flush()`

> Flushed here rather than at commit: the id is the extension's, and
> whether this upload is a retry has to be settled before the
> response says how many events were kept.

## `SqlObservationRepository.between`, [line 676](../../../../../../../backend/src/sro/infrastructure/db/repositories.py#L676): Comment

Code: `query = select(ObservationBatchRow).where(`

> Overlap, not containment: a batch that began before the window and
> ended inside it holds events the window asked for.

## `SqlCandidateRepository.add`, [line 742](../../../../../../../backend/src/sro/infrastructure/db/repositories.py#L742): Comment

Code: `await self._session.flush()`

> A manual mine-now request can race the scheduled sweep onto the
> same new (tenant, principal, signature). Flushed here so that
> collision fails on its own row rather than rolling back every
> candidate the rest of that mining pass already found.

## `SqlCandidateRepository.list_for_tenant`, [line 770](../../../../../../../backend/src/sro/infrastructure/db/repositories.py#L770): Comment

Code: `query = query.where(TaskCandidateRow.host == host.lower())`

> Stored lowercased by the segmenter, so the caller's spelling of a
> hostname does not decide whether their own tasks come back.

## `SqlToolCallRepository.remember`, [line 858](../../../../../../../backend/src/sro/infrastructure/db/repositories.py#L858): Comment

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

## `SqlToolCallRepository.remember`, [line 873](../../../../../../../backend/src/sro/infrastructure/db/repositories.py#L873): Comment

Code: `).returning(ToolCallRow.idempotency_key)`

> What came back rather than how many rows: `rowcount` is the
> driver's, and asking the statement to return the key it wrote
> answers the same question in one shape everywhere.

## `SqlUnitOfWork.__aexit__`, [line 969](../../../../../../../backend/src/sro/infrastructure/db/repositories.py#L969): Comment

Code: `await session.rollback()`

> At every depth: an inner block that raised must not leave its
> half-written rows for the outer block to commit.

## `SqlUnitOfWork.commit`, [line 981](../../../../../../../backend/src/sro/infrastructure/db/repositories.py#L981): Comment

Code: `await self._require_session().rollback()`

> Somebody wrote the row between this block reading it and
> committing, and the write that was about to land was computed
> from what it read. Reported as a conflict rather than a crash
> because it is one: the caller decides whether to redo the work
> against what is there now or to leave it to whoever comes next.
