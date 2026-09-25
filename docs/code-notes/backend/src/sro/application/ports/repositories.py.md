# Notes for `backend/src/sro/application/ports/repositories.py`

Comments and docstrings moved out of [`backend/src/sro/application/ports/repositories.py`](../../../../../../../backend/src/sro/application/ports/repositories.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/ports/repositories.py#L1): Docstring

> Persistence ports.
>
> ``tenant_id`` is the first parameter everywhere and never defaulted, so scoping
> is checked by mypy rather than by review. Missing entities raise ``NotFound``
> instead of returning ``None``.

## `BrowserSessionRepository`, [line 179](../../../../../../../backend/src/sro/application/ports/repositories.py#L179): Docstring

> Who a browser belongs to.
>
> The only durable answer to that question. The API and the Temporal worker
> each open and close browsers in their own process, so an in-memory map is
> one process's opinion about a resource both of them touch.

## `ToolCallRepository`, [line 321](../../../../../../../backend/src/sro/application/ports/repositories.py#L321): Docstring

> What has already been sent through a connector, so it is not sent twice.
>
> A network step is protected within its run: an answered write is never
> retried, because a status code means the application saw it. Nothing
> protected a tool call *across* runs -- the same trigger firing twice, a
> durable workflow replayed after a crash, an operator pressing the button
> again because the first press seemed to hang. For a mail that is one
> message becoming two, and there is no taking it back.

## `GestureRepository`, [line 335](../../../../../../../backend/src/sro/application/ports/repositories.py#L335): Docstring

> The evidence plane: what a browser sent, what was read out of it.

## `PoolRepository`, [line 385](../../../../../../../backend/src/sro/application/ports/repositories.py#L385): Docstring

> Evidence a pass did not place, waiting to be shown again.
>
> A retired entry is not a deleted one: it stops being offered ahead of fresh
> evidence and goes on being packed on its own merits. So the live entries
> and the retired ones are two reads, and an entry is retired exactly when it
> has a ``reason``.

## `WorkflowRunRepository`, [line 399](../../../../../../../backend/src/sro/application/ports/repositories.py#L399): Docstring

> What a run of a mined workflow left behind, and the approvals on it.
>
> Not every read here takes a tenant. ``approve`` and ``fail_orphans`` are
> deliberately tenant-blind and say why below; ``approvals`` does not, and
> nor do the five workflow-scoped methods on ``WorkflowRepository``
> (``mark_stale``, ``clear_stale``, ``stale_count``, ``record_effect``,
> ``forget_effects``). Those six are safe only because a run or workflow id
> is unguessable and the route has already checked who is asking -- plan 3
> scopes them by workflow ownership, which is where the reason will be
> written down.

## `WorkflowRepository`, [line 450](../../../../../../../backend/src/sro/application/ports/repositories.py#L450): Docstring

> What a mining pass found, and what running it has since earned.
>
> Four things behind one port because they are one lifecycle: a pass proposes
> a workflow, its steps cite the evidence, a run notices a step going weak,
> and a verified write is registered against the job it was a step of.

## `AttemptRepository`, [line 521](../../../../../../../backend/src/sro/application/ports/repositories.py#L521): Docstring

> Something a person asked for, and what came of it.
>
> One write and one read, and the write never raises: see `record`.

## `OfferRepository`, [line 529](../../../../../../../backend/src/sro/application/ports/repositories.py#L529): Docstring

> What the extension offered, and what became of it.
>
> Three reads and one write, because the two windows are one query with one
> predicate between them and the tally is a different question entirely.

## `ChatRepository`, [line 545](../../../../../../../backend/src/sro/application/ports/repositories.py#L545): Docstring

> What the chat door read, and what the reading cost.
>
> Never the sentence. There is no column for it and no method that would
> write one: the row exists for the cap and the spend line, and neither needs
> an operator's words about their own warehouse.

## `SpendRepository`, [line 551](../../../../../../../backend/src/sro/application/ports/repositories.py#L551): Docstring

> What today has cost, across every table that can bill it.

## `UnitOfWork`, [line 557](../../../../../../../backend/src/sro/application/ports/repositories.py#L557): Docstring

> Transaction boundary. Leaving the block without ``commit`` rolls back.

## `RecordingRepository.list_for_tenant`, [line 57](../../../../../../../backend/src/sro/application/ports/repositories.py#L57): Docstring

> Newest first. Filtering by objective is how the UI offers run pairing.

## `RecordingRepository.list_capturing`, [line 66](../../../../../../../backend/src/sro/application/ports/repositories.py#L66): Docstring

> Recordings open right now, across tenants.
>
> Crosses the tenant boundary for one reason: the browser reaper has to
> know which sessions somebody is demonstrating in before it releases
> any, and nobody is making that request. It returns recordings, never
> their contents.

## `SkillRepository.find_by_objective`, [line 76](../../../../../../../backend/src/sro/application/ports/repositories.py#L76): Docstring

> ``None`` is meaningful here: the caller creates the skill instead.

## `ConnectionRepository.find_by_system`, [line 92](../../../../../../../backend/src/sro/application/ports/repositories.py#L92): Docstring

> ``None`` is meaningful: the caller offers to connect one instead.

## `ConnectionRepository.list_connected`, [line 98](../../../../../../../backend/src/sro/application/ports/repositories.py#L98): Docstring

> Every connected system, across tenants.
>
> The one query in this codebase that deliberately crosses the tenant
> boundary, and the only caller is the keeper that signs sessions back in
> before they expire: nobody is making the request, so there is no tenant
> to scope it to. It returns connections, never anybody's data.

## `RunRepository.in_flight`, [line 106](../../../../../../../backend/src/sro/application/ports/repositories.py#L106): Docstring

> The skill run already driving this browser, if one is.
>
> The same question `WorkflowRunRepository.in_flight` answers for the rig,
> and the skill path had neither this nor the index behind it: two
> triggers firing at one device in the same minute both started, and
> their clicks interleaved in one window.
>
> The read names the run so a person can be told which one has the
> browser. `uq_runs_one_running_per_device` is what actually refuses the
> second claim -- there are awaits between this and the commit.

## `RunRepository.save`, [line 108](../../../../../../../backend/src/sro/application/ports/repositories.py#L108): Docstring

> Overwrite the record of a run in progress.
>
> A run is append-only in the domain, so this only ever grows the step
> log; the repository rewrites the row because a run is one document.

## `RunRepository.list_for_tenant`, [line 110](../../../../../../../backend/src/sro/application/ports/repositories.py#L110): Docstring

> Newest first.

## `RunRepository.finished_since`, [line 119](../../../../../../../backend/src/sro/application/ports/repositories.py#L119): Docstring

> Runs against one system that have ended. What the breaker reads.

## `RunRepository.since`, [line 123](../../../../../../../backend/src/sro/application/ports/repositories.py#L123): Docstring (debt)

> Every run in a window, whatever it was for. What a summary counts.
>
> ponytail: whole rows, and the caller judges each one with the same
> function that judged it at finish -- so the numbers on a screen agree
> with the ladder rather than being a second opinion about it. Becomes a
> GROUP BY when a tenant does thousands of runs a day.

## `KnowledgeRepository.current`, [line 129](../../../../../../../backend/src/sro/application/ports/repositories.py#L129): Docstring

> The claim believed right now for this key, if there is one.

## `KnowledgeRepository.history`, [line 135](../../../../../../../backend/src/sro/application/ports/repositories.py#L135): Docstring

> Every claim ever made about one key, newest first, superseded ones
> included.
>
> ``current`` is what the system believes; this is how it came to believe
> it. Nothing here is ever overwritten, so how many separate runs have
> said the same thing is already recorded and needs no counter of its own
> -- which is what a rule that must not act on a single observation reads.

## `KnowledgeRepository.without_embedding`, [line 139](../../../../../../../backend/src/sro/application/ports/repositories.py#L139): Docstring

> Current entries with no vector, for a deployment that turned
> embeddings on after it had already stored things.

## `KnowledgeRepository.search`, [line 143](../../../../../../../backend/src/sro/application/ports/repositories.py#L143): Docstring

> Superseded entries are never returned: they are history, not belief.
>
> Structured filters narrow first and similarity only orders what is left
> -- ``docs/09-agentic-standards.md``, because a nearest neighbour across
> the whole store answers confidently with the wrong system's endpoint.

## `ThreadRepository.list_for_tenant`, [line 163](../../../../../../../backend/src/sro/application/ports/repositories.py#L163): Docstring

> Most recently opened first.
>
> `opened_by` is one operator's own conversations, and it is a clause
> rather than a filter the caller applies afterwards: the console starts
> a thread on every first ask, so a page of the tenant's newest is a
> window somebody else's threads can push an operator's out of -- which
> would quietly begin them a second conversation.

## `ModelCallRepository.list_for_run`, [line 176](../../../../../../../backend/src/sro/application/ports/repositories.py#L176): Docstring

> Every call a run made, oldest first. The run's egress record.

## `BrowserSessionRepository.claim`, [line 180](../../../../../../../backend/src/sro/application/ports/repositories.py#L180): Docstring

> Record the owner.
>
> Raises ``Conflict`` when somebody already holds this id, which means the
> provider handed one browser to two callers. Serving it to the second is
> the bug this record exists to prevent, so it fails rather than transfers.

## `BrowserSessionRepository.held_by`, [line 188](../../../../../../../backend/src/sro/application/ports/repositories.py#L188): Docstring

> Every session this tenant has claimed, live or not.
>
> Liveness belongs to the provider; the caller intersects the two.

## `BrowserSessionRepository.all_held`, [line 190](../../../../../../../backend/src/sro/application/ports/repositories.py#L190): Docstring

> Every claim in the deployment, and when it was made.
>
> Crosses the tenant boundary for the same reason ``list_capturing`` does:
> the browser sweep has to know which sessions are spoken for, and nobody
> is making that request. Ids and timestamps, never a tenant.

## `BrowserSessionRepository.release`, [line 192](../../../../../../../backend/src/sro/application/ports/repositories.py#L192): Docstring

> Forget the claim. Idempotent, and deliberately not tenant-scoped:
> crash recovery and the sweep are not anybody's request.

## `BrowserSessionRepository.lease`, [line 194](../../../../../../../backend/src/sro/application/ports/repositories.py#L194): Docstring

> Claim the account's lease, or attach to whichever one already exists.
>
> Not `Conflict` for the ordinary case: two runs racing to acquire the same
> account are not an error, they are §5.4's ordinary case, and the second
> one wants the first one's lease, not a refusal. The unique partial index
> on `(tenant_id, account_key)` decides which lease wins when both insert at
> once; this always answers with the one that did -- except in the one
> window where the winner is settled between the insert and the re-read, so
> narrow that only a `Conflict` (this door's ordinary shape for "somebody
> else was here first") answers it rather than a made-up account.

## `BrowserSessionRepository.current_lease`, [line 196](../../../../../../../backend/src/sro/application/ports/repositories.py#L196): Docstring

> The account's lease, if one is `signing_in` or `ready` -- whatever its
> `expires_at`. Liveness by state and not by time: the sweeper alone decides
> when a silent lease is gone (`expired`), so a lease that simply has not
> been swept yet is still the one every acquire attaches to.

## `BrowserSessionRepository.get_lease`, [line 198](../../../../../../../backend/src/sro/application/ports/repositories.py#L198): Docstring

> One lease by id, tenant-checked, whatever its state -- unlike
> `current_lease`, a settled lease still answers here. A run re-attaching
> after a worker restart has the lease id from its own progress, not the
> account, and needs to see it even mid-expiry to know what happened to it.

## `BrowserSessionRepository.settle`, [line 200](../../../../../../../backend/src/sro/application/ports/repositories.py#L200): Docstring

> The holder's own transition: `signing_in` to `ready` on a successful
> sign-in, or to `broken` on a failed one. Real callers (S7's `_ready`, S8)
> do exactly this, under S3's account lock, which is what makes an update
> unconditional on the holder safe -- the lock already serialises whoever
> calls it, and `holder` itself is not a reliable check on its own, since
> D8 lets several runs share one lease as separate tabs.
>
> What IS enforced, in the `WHERE`, is that the row is still in a live
> state when this runs: `settle` can move a lease neither to `expired` (it
> raises rather than try -- `expire`'s compare-and-set owns that
> transition, precisely because an unconditional write from outside the
> lock could race it) nor, by the same `WHERE`, FROM `expired` -- a lease
> the sweeper already killed cannot be revived back to `ready` by a slow
> holder finishing sign-in after the fact. Returns `False`, silently, on
> an id that lost that race, is not this tenant's, or is not live for any
> other reason: nothing here is anybody's request to fail loudly at.

## `BrowserSessionRepository.expire`, [line 202](../../../../../../../backend/src/sro/application/ports/repositories.py#L202): Docstring

> The sweeper's transition, and the only door it uses to make one. A
> compare-and-set: it moves a lease to `expired` only if it is still live
> AND its `expires_at` is still `<= now` at the moment of the write, not
> only at the moment the sweeper's earlier `expired(now=...)` read it. A
> heartbeat landing in between makes this a no-op, `False`, and the lease
> survives -- the sweeper reading a stale list is not the same as the
> sweeper acting on one.

## `BrowserSessionRepository.beat`, [line 204](../../../../../../../backend/src/sro/application/ports/repositories.py#L204): Docstring

> `heartbeat_at = now`, `expires_at = now + K_LEASE_TTL`. Only a live lease
> moves: a heartbeat that arrived after the sweeper already called this one
> expired must not resurrect it out from under whoever claims it next --
> and answers `False` rather than silently doing nothing, so the caller
> that just lost a race with the sweeper's `expire` learns it, rather than
> going on driving a context nobody else thinks is theirs any more.
> `holder` moves too when a run takes over an already-`ready` lease -- given,
> not always, since an ordinary heartbeat from the same holder has nothing
> new to say.

## `BrowserSessionRepository.expired`, [line 213](../../../../../../../backend/src/sro/application/ports/repositories.py#L213): Docstring

> Every live-state lease whose `expires_at` has passed, every tenant. The
> sweeper's whole read: it used to run a 15-minute grace timer against an
> in-memory session list, which forgot everything on a worker restart. This
> forgets nothing, because it is the same row a restart re-attaches by.

## `BrowserSessionRepository.busy_containers`, [line 217](../../../../../../../backend/src/sro/application/ports/repositories.py#L217): Docstring

> One `container_url` per live, unexpired lease, every tenant: one entry
> per browser context a container holds. This is the only count of a
> container's capacity (S7 round 1, C1): the Steel client keeps none, so a
> restarted process or the API beside the worker counts the same contexts.
> Not tenant-scoped (S7 round 1, M1): every tenant missing from
> `steel_urls` shares the fallback container, and a per-tenant count
> undercounted its load.

## `BrowserSessionRepository.leased_sessions`, [line 223](../../../../../../../backend/src/sro/application/ports/repositories.py#L223): Docstring

> Every Steel session id a live lease still answers for, every tenant. The
> stray sweeper's guardrail: a Steel session with no row here at all is an
> orphan and safe to close, but one this set names is somebody's lease and
> must survive the sweep even though closing by `context_id` never touches
> it directly. It holds the real Steel session id: `Lease.steel_session_id`
> is the session the pool opened the context in, never the context id.

## `BrowserSessionRepository.retired_contexts`, [line 219](../../../../../../../backend/src/sro/application/ports/repositories.py#L219): Docstring

> Of the given context ids on one container, those whose lease row has
> ended (EXPIRED or BROKEN). The broker disposes them: a close that timed
> out, or a process that died before closing, leaves them in Chrome.
> A context with no row at all is never named: another process may have
> just created it and not yet committed its lease (S7 review, C1 ruling),
> so only a known, ended owner makes a context safe to reclaim.

## `DeviceRepository.registered_as`, [line 233](../../../../../../../backend/src/sro/application/ports/repositories.py#L233): Docstring

> The device this operator already registered under this label.
>
> Registration is idempotent on it: an extension that lost its stored id
> -- a reinstall, a cleared profile -- must not accumulate a device per
> attempt, because the device list is how an administrator sees who is
> being observed.

## `DeviceRepository.list_for_tenant`, [line 237](../../../../../../../backend/src/sro/application/ports/repositories.py#L237): Docstring

> Most recently seen first.

## `DeviceRepository.revoke`, [line 239](../../../../../../../backend/src/sro/application/ports/repositories.py#L239): Docstring

> Whether there was a live browser to revoke.
>
> The secret is left alone rather than blanked: a device with no secret
> cannot be told from one registered before secrets existed, and this has
> to say *when* the authority ended as well as that it did. ``False`` for
> a browser already revoked, so a second press does not move that instant;
> ``NotFound`` for one this tenant does not have, which is a different
> answer and a different status code.

## `DeviceRepository.restore`, [line 241](../../../../../../../backend/src/sro/application/ports/repositories.py#L241): Docstring

> Give a revoked browser its authority back. ``True`` when one had
> been taken away, ``False`` when it was never revoked.
>
> Exists because revocation started enforcing. While ``revoked_at``
> changed no answer, a wrong press was cosmetic; now `refuse_unless_itself`
> refuses the browser on every device-scoped path, and registration is
> deliberately idempotent and hands back the same secret -- so
> re-registering does NOT undo it, and without this the only way back is
> a hand-edited row. ``NotFound`` for a browser this tenant does not
> have, as `revoke` gives.
>
> The secret is untouched: the browser still holds a working one, which
> is the whole reason it needs no reinstall.

## `DeviceRepository.since`, [line 243](../../../../../../../backend/src/sro/application/ports/repositories.py#L243): Docstring

> Every browser registered or revoked at or after this ISO instant,
> newest registration first.
>
> The audit's only answer to "who could act, and from when to when":
> ``revoked_at`` is the fact the runs and the offers cannot carry, so a
> browser registered last month and revoked this morning belongs in this
> morning's audit as much as one registered in it.

## `ObservationRepository.add`, [line 247](../../../../../../../backend/src/sro/application/ports/repositories.py#L247): Docstring

> Raises ``Conflict`` when this batch id is already stored. The id is
> the extension's, so a retry of an upload that did land must be
> recognised rather than stored twice.

## `ObservationRepository.get`, [line 249](../../../../../../../backend/src/sro/application/ports/repositories.py#L249): Docstring

> ``None`` rather than ``NotFound``: the caller is asking whether a
> retry is a retry, and absence is the ordinary answer.

## `ObservationRepository.between`, [line 251](../../../../../../../backend/src/sro/application/ports/repositories.py#L251): Docstring

> Batches overlapping a window, oldest first. What the miner reads, and
> what a purge counts.

## `ObservationRepository.received_before`, [line 260](../../../../../../../backend/src/sro/application/ports/repositories.py#L260): Docstring

> Batches this deployment RECEIVED before an instant, oldest first.
>
> What retention is counted on, and the reason it is not `between`: the
> window a tenant declares is "how long we keep what you send us", and
> the only clock that can answer it is the one that took delivery.
> `started_at` is the browser's, and on this store it runs up to 23 hours
> from `received_at` -- an offline extension flushing a queue, or simply
> a machine whose clock is wrong. Counted on that, a batch that arrived
> this morning can be a day old on arrival and be swept the same day.

## `ObservationRepository.tenants_since`, [line 264](../../../../../../../backend/src/sro/application/ports/repositories.py#L264): Docstring

> Every tenant with evidence in the window.
>
> Tenant-blind, like the browser sweep and for the same reason: the
> scheduled miner has no request behind it and nobody to take a tenant
> from. Ids only, never a row.

## `ObservationRepository.forget`, [line 266](../../../../../../../backend/src/sro/application/ports/repositories.py#L266): Docstring

> Delete the rows. The blobs they point at are the caller's to remove;
> a repository does not reach into object storage.

## `CandidateRepository.list_for_tenant`, [line 276](../../../../../../../backend/src/sro/application/ports/repositories.py#L276): Docstring

> Most often seen first. The miner reads them all, including dismissed
> ones -- a task somebody said no to must not be offered again next week
> as if it were new.
>
> `host` is one system, which is what the extension's panel asks: "tasks
> you keep doing *here*" is a different question from "tasks you keep
> doing", and filtering after a limit would let twenty from elsewhere push
> the answer off the list.

## `ObservationPolicyRepository.get`, [line 288](../../../../../../../backend/src/sro/application/ports/repositories.py#L288): Docstring

> ``None`` when this tenant has never been given one. The caller
> supplies the refusing default -- absence must never read as consent.

## `TriggerRepository.list_for_tenant`, [line 302](../../../../../../../backend/src/sro/application/ports/repositories.py#L302): Docstring

> Newest first.

## `TriggerRepository.find`, [line 306](../../../../../../../backend/src/sro/application/ports/repositories.py#L306): Docstring

> Deliberately tenant-blind, and the only method here that is.
>
> A schedule fires with an id and nothing else -- there is no request and
> no caller to take a tenant from. What comes back carries its own, and
> everything after this point is scoped by that.

## `ConfirmationRepository.waiting`, [line 316](../../../../../../../backend/src/sro/application/ports/repositories.py#L316): Docstring

> Everything this tenant has not answered, oldest first.
>
> Including the ones that have run out: a card that vanished from a
> screen is not the same as one somebody can see was never answered, and
> the second is what tells a team its queue is not being read.

## `ToolCallRepository.remember`, [line 322](../../../../../../../backend/src/sro/application/ports/repositories.py#L322): Docstring

> Claim this key. ``False`` when somebody already claimed it.
>
> Written *before* the call, and kept whatever the call answers. A key
> released on failure would let a timeout -- the one case where the send
> may well have landed -- be retried into a second send, which is the
> exact thing this exists to prevent. So a retry is refused and somebody
> is told the call may already have happened, which is the truth.
>
> `stale_after` is for a key that is not unique to one attempt. A
> connector call is keyed by run and step and is claimed forever; a rig
> step's write is keyed by the JOB, the step and the values, so that two
> runs of one job started three minutes apart cannot both create the
> record -- and a key like that must expire, or a job could never be done
> twice with the same values for the rest of the tenant's life. A claim
> older than `stale_after` is taken over rather than refused.

## `ToolCallRepository.forget`, [line 332](../../../../../../../backend/src/sro/application/ports/repositories.py#L332): Docstring

> Give a claim back, for the one case where nothing was sent.
>
> The rule above is that a claim is KEPT whatever the call answers, and
> it names the reason: a timeout may well have landed, and releasing it
> would retry a write into a second one. That reasoning is about the
> wire. It does not cover a browser that never reached the wire -- a
> command the extension refused because no tab was open on the system,
> or because the run was aborted, never touched the warehouse, and
> holding its key for half an hour blocks a retry that is entirely safe.
>
> Found on the live deployment 2026-09-16: a run failed
> `no_tab_for_system` because the operator's Blue Yonder session had
> expired, and every later run of the same job with the same values was
> refused for half an hour on the grounds that the first `may have
> landed`. It could not have.
>
> Narrow on purpose, and the caller decides: only the kinds that mean the
> extension refused BEFORE acting, never `timeout` and never a failure
> the page itself answered. Idempotent -- a key nobody claimed is a
> no-op, not an error.

## `GestureRepository.add_batch`, [line 336](../../../../../../../backend/src/sro/application/ports/repositories.py#L336): Docstring

> Raises ``Conflict`` if that batch id was already written.
>
> An upload retried after its answer was lost must not be stored twice:
> the second copy would double every gesture in it and be mined as a
> second doing of the same job.

## `GestureRepository.gestures_for`, [line 340](../../../../../../../backend/src/sro/application/ports/repositories.py#L340): Docstring

> Ordered by ``at``. ``ids`` narrows to a citation set.
>
> ``after`` and ``before`` narrow to a window of the browser's own clock,
> exclusive and inclusive -- what happened in the minutes after something
> else, which is how a run asks what the operator did once it had
> stopped.

## `GestureRepository.uploads_for`, [line 349](../../../../../../../backend/src/sro/application/ports/repositories.py#L349): Docstring

> What each of these uploads said about the clock it was recorded on.
>
> The device's window and the moment we received it, which is the only
> thing that makes a browser's timestamps comparable with this server's.
> See `domain/observation/driving.py`.

## `GestureRepository.unread`, [line 353](../../../../../../../backend/src/sro/application/ports/repositories.py#L353): Docstring

> Gestures with no intent row yet, oldest first.

## `GestureRepository.newest_arrival`, [line 355](../../../../../../../backend/src/sro/application/ports/repositories.py#L355): Docstring

> When this tenant's evidence last arrived, or nothing if it never has.
>
> The server's clock, off the same `received_at` and the same "carried
> something" rule `tenants_since` uses, so the two agree about what an
> arrival is. `MineLately` reads it to ask how many passes have run since
> anybody added to the store.

## `GestureRepository.tenants_since`, [line 357](../../../../../../../backend/src/sro/application/ports/repositories.py#L357): Docstring

> Every tenant whose browsers uploaded in the window.
>
> Tenant-blind, like `ObservationRepository.tenants_since` and for the
> same reason: the scheduled miner has no request behind it and nobody to
> take a tenant from. Ids only, never a row.
>
> The rig's own, rather than reusing the observation table's. The two
> answer the same today because one upload writes both, and building the
> rig's autonomy on the table it migrated away from is a trap that only
> springs the day the legacy write stops.
>
> Measured against the server's clock and not the browser's: a device
> whose clock is wrong would otherwise take its tenant out of every sweep
> or put it in every one.

## `GestureRepository.save_intent`, [line 359](../../../../../../../backend/src/sro/application/ports/repositories.py#L359): Docstring

> Replaces any earlier reading of that gesture.

## `GestureRepository.intents_since`, [line 363](../../../../../../../backend/src/sro/application/ports/repositories.py#L363): Docstring

> Every reading stored at or after this ISO instant, newest first.
>
> ``intents_since`` rather than a bare ``since``: this port holds two
> kinds of record and names every read after the one it returns. The
> clock is the row's ``created_at``, which is when the reading was
> stored rather than when the gesture happened -- the same column the
> day's spend is summed over, because it is the reading that was billed.

## `GestureRepository.add_orphan_request`, [line 365](../../../../../../../backend/src/sro/application/ports/repositories.py#L365): Docstring

> The same orphan twice is one row.

## `GestureRepository.batch_owner`, [line 378](../../../../../../../backend/src/sro/application/ports/repositories.py#L378): Docstring

> Which device uploaded that batch. ``None`` when nothing did.
>
> Tenant-blind on purpose, like ``TriggerRepository.find``: the question
> is asked of a device presenting its own token, before there is a tenant
> to scope by, so that one browser cannot mirror a screenshot onto
> another browser's batch.

## `GestureRepository.streams`, [line 382](../../../../../../../backend/src/sro/application/ports/repositories.py#L382): Docstring

> (stream id, the last gesture's ``at``, how many), newest first.

## `PoolRepository.add_unclaimed`, [line 386](../../../../../../../backend/src/sro/application/ports/repositories.py#L386): Docstring

> Anything the pass did not cite enters at age 0; anything it did leaves.
>
> ``claimed`` is cleared in full rather than only where it intersects the
> window: a pooled gesture is packed beside the fresh ones, so a pass can
> cite evidence that is only in the pool. Returns how many entered, and
> re-entering does not reset an entry's clock.

## `PoolRepository.age`, [line 390](../../../../../../../backend/src/sro/application/ports/repositories.py#L390): Docstring

> One reading older, and only for evidence a reading actually saw.
>
> ``shown`` is what was in the window; ``None`` means every entry ages,
> which is what a caller with no window wants, and an empty tuple means a
> pass that packed nothing -- every entry waited one more. Returns how
> many retired, by either cap.

## `PoolRepository.waiting`, [line 392](../../../../../../../backend/src/sro/application/ports/repositories.py#L392): Docstring

> Live entries, oldest first.

## `PoolRepository.ids`, [line 394](../../../../../../../backend/src/sro/application/ports/repositories.py#L394): Docstring

> Just the ids of the live entries, in the same order.

## `PoolRepository.retired`, [line 396](../../../../../../../backend/src/sro/application/ports/repositories.py#L396): Docstring

> What the pool stopped offering, and why.

## `WorkflowRunRepository.save`, [line 400](../../../../../../../backend/src/sro/application/ports/repositories.py#L400): Docstring

> Whole run, every time: called after every step so the panel can
> poll, with steps replaced rather than appended.

## `WorkflowRunRepository.get`, [line 406](../../../../../../../backend/src/sro/application/ports/repositories.py#L406): Docstring

> ``None``, not ``NotFound``: every caller answers 404 itself.

## `WorkflowRunRepository.for_workflow`, [line 408](../../../../../../../backend/src/sro/application/ports/repositories.py#L408): Docstring

> Every run of one job, oldest first -- which is NOT how the rig
> listed them.
>
> The rig's ``GET /v1/runs`` was ``ORDER BY started_at DESC LIMIT ?``:
> the most recent runs, newest first. That is a list for a person to
> pick from, and it is ``recent`` below.
>
> This is the evidence order. What reads it is ``proofs`` -- the store's
> own query orders ``(started_at, id)`` ascending and the fake reaches
> this method to get the same -- and a job's writes are read forward,
> because the question is how this job has settled over time and the
> answer to it runs in the direction time does. Unbounded for the same
> reason: proof is not a page.
>
> Total, and the id is what makes it so: two runs of one workflow
> routinely start in the same instant -- one form submits them -- and an
> order that is not total is an order that changes between reads.

## `WorkflowRunRepository.recent`, [line 412](../../../../../../../backend/src/sro/application/ports/repositories.py#L412): Docstring

> The most recent runs, newest first, capped: the rig's own list
> query (``api.py:1152``), filters and all.
>
> ``workflow_id`` narrows to one job and ``ids`` to a named set --
> which is how ``awaiting=true`` is served, because the parked runs are
> a set of ids that comes from ``awaiting`` below. An empty ``ids`` is
> not the same as ``None``: it means nothing can match, said here so no
> caller has to branch on it -- the rig had to, because ``id IN ()`` with
> no ids to interpolate was a syntax error where it ran.
>
> The cap is in the query and not in the caller. Filtering or slicing a
> tenant's whole run history in Python is the defect ``tallies`` exists
> to have removed once already: it is linear in rows nobody asked for,
> and it degrades exactly as a customer succeeds.
>
> It caps the ROWS, though, and not ``ids``. A caller passing a set
> interpolates all of it, and the honest bound on that set is whatever
> the caller's own read returns -- see ``ListWorkflowRuns``, which says
> what bounds its one.
>
> Total, reversed, and for ``for_workflow``'s reason -- ``(started_at,
> id)`` descending, so a page boundary falls in the same place twice.

## `WorkflowRunRepository.taken_back_by`, [line 421](../../../../../../../backend/src/sro/application/ports/repositories.py#L421): Docstring

> The run that took this one back, where one already has.
>
> An undo pressed twice is a second delete addressed to a record the
> first one removed, and what a warehouse answers to that is nobody's
> idea of a good surprise. Asked of the store rather than remembered on
> the card, because the card is one browser's copy and a second window
> holds another.
>
> Only a run that HELD counts as having taken it back. One that failed
> left the record where it was, and refusing a second attempt because the
> first did not work is refusing the one attempt that might.

## `WorkflowRunRepository.failures`, [line 423](../../../../../../../backend/src/sro/application/ports/repositories.py#L423): Docstring

> How many runs of each job ended in the job's OWN failure.
>
> `failed` and `refused` only. A run that stopped to ask a person did not
> fail -- it asked -- and one a person aborted is a person changing their
> mind. Counting either as a failure silenced every job this deployment
> has: twelve runs of the sign-in job, eleven of them stopped on a
> password it was waiting for, and the job vanished from the browser that
> was trying to finish it.

## `WorkflowRunRepository.tallies`, [line 425](../../../../../../../backend/src/sro/application/ports/repositories.py#L425): Docstring

> ``(runs, held)`` for every workflow of this tenant that has been
> run, in one ``GROUP BY``.
>
> What ``shapes_for`` gates on, and the only reason it is a batch: the
> gate needs two integers per workflow, and asking ``for_workflow`` per
> proven workflow loads every run ever recorded with all of its steps to
> compute them. Counted against real Postgres, three workflows of four
> runs: ``shapes_for`` issued 14 statements, 6 against the runs tables;
> with this it issues 9 and 1. The 6 were linear in total run rows, on
> the read every browser makes on every gesture cache miss. The rig read
> the same two numbers off the runs index and this is that, batched
> across the tenant instead of asked per workflow.
>
> A workflow with no runs is ABSENT, not a zero pair. That is the runs
> index answering about itself -- it has no row to count and does not
> know what workflows exist -- and the caller defaults it, which is what
> keeps a job that has never been run servable.

## `WorkflowRunRepository.since`, [line 427](../../../../../../../backend/src/sro/application/ports/repositories.py#L427): Docstring

> Every run started at or after this ISO instant, newest first, with
> its steps. The spine of the audit: the approvals on each are read
> beside it, through ``approvals``.

## `WorkflowRunRepository.driving_windows`, [line 433](../../../../../../../backend/src/sro/application/ports/repositories.py#L433): Docstring

> When each of this tenant's runs held a browser, on this clock.
>
> What a second check against mining our own replays needs, and nothing
> else: which device, from when, until when. See
> `domain/observation/driving.py`.

## `WorkflowRunRepository.in_flight`, [line 435](../../../../../../../backend/src/sro/application/ports/repositories.py#L435): Docstring

> The run this browser is already driving, if any.
>
> One browser, one hand: two runs driving the same window interleave
> their clicks into a form neither of them can then read back.

## `WorkflowRunRepository.awaiting`, [line 437](../../../../../../../backend/src/sro/application/ports/repositories.py#L437): Docstring

> (run id, step ord, what the step says) for every step waiting on a
> person, across browsers: anyone may answer a parked run.
>
> A stated divergence from the rig, not an accident: the rig reported the
> deepest parked step of each run and this returns every one of them,
> ``ord`` ascending. Plan 4b decided it that way and kept it -- anyone
> may answer a parked run, and a queue that hides all but the deepest
> step hides work from the person who could clear it. ``GET
> /v1/workflow-runs`` serves the same rule from the other end: it
> answers with whole rows, so every parked step is on the wire and no
> reader has to ask a second time which of them are waiting.

## `WorkflowRunRepository.waiting_on`, [line 439](../../../../../../../backend/src/sro/application/ports/repositories.py#L439): Docstring

> The run that ended waiting to hear back on this outside conversation.
>
> Newest first, because a thread somebody asks about twice has two runs
> against it and the live question is the last one asked. Whether the
> wait is still open is the caller's to decide -- `still_waiting` reads
> the deadline -- because "nobody is holding this open any more" is a
> different sentence from "nobody ever asked about this", and a caller
> told `None` for both cannot say either.

## `WorkflowRunRepository.approve`, [line 443](../../../../../../../backend/src/sro/application/ports/repositories.py#L443): Docstring

> Whether this tap was the one that authorised the step.
>
> The first tap wins: a write rescued to the second rung parks at the
> same step and takes a second tap, and the first authorisation stands.
> Tenant-blind because the run id is the only thing the panel has, and
> the route has already checked the browser is driving this run.

## `WorkflowRunRepository.approvals`, [line 445](../../../../../../../backend/src/sro/application/ports/repositories.py#L445): Docstring

> (step ord, when, which browser) for each write a person let out.

## `WorkflowRunRepository.fail_orphans`, [line 447](../../../../../../../backend/src/sro/application/ports/repositories.py#L447): Docstring

> Every run still ``running`` is marked failed, and how many there were.
>
> Called once at startup, across tenants -- nobody is making the request.
> One worker owns every run, so a row that says ``running`` when the
> process starts is a run nobody is driving. The reason lands on the
> last step, or on a new step when the run never reached one.

## `WorkflowRepository.save`, [line 451](../../../../../../../backend/src/sro/application/ports/repositories.py#L451): Docstring

> Whole workflow, steps replaced rather than appended.
>
> Identity resolution re-saves a workflow it merged evidence into, so a
> step the merge dropped has to leave the store with it.

## `WorkflowRepository.known`, [line 453](../../../../../../../backend/src/sro/application/ports/repositories.py#L453): Docstring

> Oldest first, which is the order the miner resolves against.

## `WorkflowRepository.rekey`, [line 469](../../../../../../../backend/src/sro/application/ports/repositories.py#L469): Docstring

> Replace the shape identity resolution compares proposals against.
>
> Run once at startup, when the rule that makes a key has changed: keys
> mined before the change no longer match keys mined after, and a job
> already held could be proposed again as a new one.

## `WorkflowRepository.add_pass`, [line 471](../../../../../../../backend/src/sro/application/ports/repositories.py#L471): Docstring

> One row per reading of a tenant's day, found anything or not.
>
> A refused call is the case that matters: it is then the only record
> left of a call that cost money and returned nothing.
>
> Raises ``Conflict`` when that pass id is already stored. An id is
> minted per reading, so a second row under one id is one model call
> billed twice.

## `WorkflowRepository.passes`, [line 473](../../../../../../../backend/src/sro/application/ports/repositories.py#L473): Docstring

> Every pass this tenant has been billed for, oldest first.

## `WorkflowRepository.mark_stale`, [line 475](../../../../../../../backend/src/sro/application/ports/repositories.py#L475): Docstring

> A step only the weakest rung of the locator ladder found.
>
> One row per step, so a job run every morning reports the same weak step
> once rather than daily. Not written onto the workflow itself: that is
> what a mining pass writes and this is what a run learned, and one
> rewriting the other would race a re-mine.

## `WorkflowRepository.remember_locator`, [line 479](../../../../../../../backend/src/sro/application/ports/repositories.py#L479): Docstring

> What a run found when the job's own identity for a control did not.
>
> `mark_stale` above says a step is about to break; this says what the
> run FOUND, so the next one tries it first rather than climbing the same
> ladder and paying for the same model call. One row per step, the last
> answer winning.

## `WorkflowRepository.learned_for`, [line 483](../../../../../../../backend/src/sro/application/ports/repositories.py#L483): Docstring

> Every step of this job that a run has found a working locator for.

## `WorkflowRepository.taught_itself`, [line 485](../../../../../../../backend/src/sro/application/ports/repositories.py#L485): Docstring

> What this job has changed its mind about, newest first.
>
> The reviewable half of learning. `remember_locator` and
> `remember_limit` store the CURRENT answer and overwrite what was there,
> which is right for the run asking what to try first and leaves a job
> rewriting its own behaviour with nothing behind it.
>
> Bounded, and small: a history nobody can read in one page is a log.

## `WorkflowRepository.remember_limit`, [line 487](../../../../../../../backend/src/sro/application/ports/repositories.py#L487): Docstring

> How many characters this step's box turned out to take.
>
> Learnt on a step whose locator matched perfectly well, which is why it
> is not part of `remember_locator`: writing the two together would have
> a truncation erase a locator, or a locator erase a limit.

## `WorkflowRepository.clear_stale`, [line 491](../../../../../../../backend/src/sro/application/ports/repositories.py#L491): Docstring

> The step matched properly again. A warning that never clears is a
> warning nobody reads. Idempotent: clearing a step that was never weak
> is not an error.

## `WorkflowRepository.stale_count`, [line 493](../../../../../../../backend/src/sro/application/ports/repositories.py#L493): Docstring

> How many of this job's steps are about to break.

## `WorkflowRepository.grew`, [line 495](../../../../../../../backend/src/sro/application/ports/repositories.py#L495): Docstring

> Save a job whose steps have grown, taking its learning with them.
>
> `save` already replaces a workflow's steps. What it cannot do is move
> what is keyed to their numbers: the locator a run last found, the mark
> that a step is about to break, and what the job taught itself. See
> `skill.shape.where_steps_moved`, which computes `moved` and says why a
> past run's own record is deliberately left where it is.

## `WorkflowRepository.remember_write`, [line 497](../../../../../../../backend/src/sro/application/ports/repositories.py#L497): Docstring

> This deployment watched this write succeed; it may now be replayed.
>
> The same bar `record_effect` keeps, because it is called from the same
> moment: live, held, wrote, and verified by a state belt. Idempotent --
> a job that proves the same endpoint every week is one ledger entry.

## `WorkflowRepository.learned_writes`, [line 510](../../../../../../../backend/src/sro/application/ports/repositories.py#L510): Docstring

> What this tenant has watched succeed, for the gate that decides
> whether a step is replayed as a call or clicked.

## `WorkflowRepository.record_effect`, [line 512](../../../../../../../backend/src/sro/application/ports/repositories.py#L512): Docstring

> Register a write the verifier saw hold by state.
>
> A verdict that is not a state belt is dropped rather than stored: a
> model reading a screenshot is not evidence anything was written. One
> write of one run is one row however many times it is verified.

## `WorkflowRepository.forget_effects`, [line 516](../../../../../../../backend/src/sro/application/ports/repositories.py#L516): Docstring

> How many were forgotten. One failed write empties the register.

## `WorkflowRepository.proofs`, [line 518](../../../../../../../backend/src/sro/application/ports/repositories.py#L518): Docstring

> One per live run of this workflow that held, for ``earned_from``.
>
> The steps that wrote come off each step's own ``wrote`` marker, which
> the runner set at send time: SQL cannot ask ``writes()``, and the
> evidence a later reader would have to ask it about may have been
> re-mined by then.

## `AttemptRepository.record`, [line 522](../../../../../../../backend/src/sro/application/ports/repositories.py#L522): Docstring

> One attempt, one row -- and nothing this raises reaches the caller.
>
> The callers are doors in the middle of answering somebody, most of them
> in the middle of REFUSING somebody, and a refusal that turns into a 500
> because the recording of it failed is strictly worse than the silence
> this replaces. An implementation that cannot write says so in the log
> and returns.

## `AttemptRepository.since`, [line 524](../../../../../../../backend/src/sro/application/ports/repositories.py#L524): Docstring

> This tenant's attempts, newest first, capped.
>
> Newest first because a day is read from the end: the question is what
> just happened, and an audit that starts at breakfast makes somebody
> scroll to reach it.

## `OfferRepository.record`, [line 530](../../../../../../../backend/src/sro/application/ports/repositories.py#L530): Docstring

> One offer, one row. The id is minted where the offer is made.

## `OfferRepository.newest`, [line 532](../../../../../../../backend/src/sro/application/ports/repositories.py#L532): Docstring

> Newest first, ``at`` then arrival -- the window ``counsel_over``
> reads. Nudges (``k = 0``) are excluded: an arrival is not evidence
> either way. Every browser's offers count, because recognition is a
> property of the job rather than of who was asked.

## `OfferRepository.newest_for_device`, [line 536](../../../../../../../backend/src/sro/application/ports/repositories.py#L536): Docstring

> The same window, one browser's. Resting is per browser: one
> operator's no is not the next operator's.

## `OfferRepository.fates`, [line 540](../../../../../../../backend/src/sro/application/ports/repositories.py#L540): Docstring

> How many of this job's offers ended each way, nudges included.
>
> The panel's tally rather than the counsel's window, so neither the
> ``k > 0`` filter nor the limit applies: an arrival nudge is still an
> offer that was made.

## `OfferRepository.since`, [line 542](../../../../../../../backend/src/sro/application/ports/repositories.py#L542): Docstring

> Every offer made at or after this ISO instant, newest first, whole.
>
> The audit's question, not the counsel's: no ``k > 0`` and no limit,
> because an arrival nudge is still something this tenant's browsers were
> shown. Ties on ``at`` break on arrival, as everywhere else here.

## `ChatRepository.since`, [line 548](../../../../../../../backend/src/sro/application/ports/repositories.py#L548): Docstring

> Every reading at or after this ISO instant, newest first. The day's
> spend is the sum over it, which is why the index leads with the
> tenant.

## `SpendRepository.today`, [line 554](../../../../../../../backend/src/sro/application/ports/repositories.py#L554): Docstring

> Everything this tenant has been billed for since midnight UTC.
>
> Four tables, one predicate each: a reading, a mining pass, a run and
> a chat are the only things that cost money, and a cap that reads
> three of them is a cap.
>
> ``now`` is passed rather than read here so the caller's clock is the
> one the day is measured from; midnight is UTC's either way, and a
> ``now`` with no zone is read as UTC rather than as the server's local
> time.
