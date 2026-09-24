# Notes for `backend/src/sro/container.py`

Comments and docstrings moved out of [`backend/src/sro/container.py`](../../../../../backend/src/sro/container.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../backend/src/sro/container.py#L1): Docstring

> Composition root. The only module allowed to import ``sro.infrastructure``.
>
> Everything above this line depends on protocols; the choice of Postgres, MinIO
> or Steel is made here and nowhere else. Swapping an adapter is an edit to this
> file, which is the whole point of the dependency rule.

## module, [line 184](../../../../../backend/src/sro/container.py#L184): Note on the line above

Code: `RUNS_LOCK = 5721966`

> The advisory lock one API process holds while it owns the runs.
>
> Any constant would do; this one is arbitrary and only has to differ from
> whatever else ever takes an advisory lock on this database.

## `Container`, [line 188](../../../../../backend/src/sro/container.py#L188): Docstring

> Long-lived adapters, built once per process.
>
> Use cases are cheap objects built per call: they hold a unit of work, which
> must not be shared between concurrent requests.

## `Container`, [line 189](../../../../../backend/src/sro/container.py#L189): Note on the line above

Code: `_schema_announced: bool = field(default=False, init=False, repr=False)`

> Whether the schema line has been written this process. See
> `_announce_once`: the fact is worth saying, and worth saying once.

## `Container`, [line 191](../../../../../backend/src/sro/container.py#L191): Note on the line above

Code: `_mining_asker: Asker | None = field(default=None, init=False, repr=False)`

> The mining pass's own client, built on the first pass that needs one.
> See `_patient_asker`: same model, its own patience.

## `Container`, [line 193](../../../../../backend/src/sro/container.py#L193): Note on the line above

Code: `_mining_asker_from: Asker | None = field(default=None, init=False, repr=False)`

> Which `asker` the one above was built from, so replacing the asker
> replaces it too. A cache keyed on nothing is a cache that answers with the
> thing it was built from after somebody changed it.

## `Container`, [line 204](../../../../../backend/src/sro/container.py#L204): Note on the line above

Code: `asker: Asker | None`

> The model the rig's own passes ask, or ``None`` where none is configured.
>
> Separate from ``interpreter`` and ``intent_parser``, which each answer one
> narrow question with their own model name. This is the general one: the
> miner and the runner hand it a schema and an instruction and read structured
> JSON back, and both need to bill what they spent, which is why the port
> carries ``Answer`` rather than a string.
>
> ``None`` rather than a no-op double, deliberately. A miner with nothing to
> ask must not run and quietly find nothing -- that reads exactly like a day
> with no work in it. The caller that checks and refuses now exists: it is
> `asker_or_refuse` in `application/ports/model.py`, and every door that needs
> a model reaches it through that one function.
>
> Which doors those are is NOT written down here any more. This paragraph
> used to name them and count them, with a note saying the count went up
> "when task 5 lands and not before" -- and task 5 landed, and the sentence
> stayed at two for a week, on the same attribute that carried a "nothing
> reads this" defect the week before. It wrote its own trip-wire and nobody
> tripped it, which is what a prose trip-wire is worth. The count now lives
> in `test_every_door_that_needs_a_model_refuses_through_the_one_guard`,
> which fails on the commit that adds or removes a caller instead of on the
> commit that reads the comment.
>
> The check is deliberately not on this attribute and not a method here. Each
> caller takes `Asker | None` and refuses at the top of its own `execute`, so
> a deployment with no model still builds every factory and fails at use
> rather than at construction.

## `Container`, [line 221](../../../../../backend/src/sro/container.py#L221): Note on the line above

Code: `engine: AsyncEngine | None = None`

> The pool behind `session_factory`, so a process that built one can close
> it. `None` for a container built in a test, which brings its own store.
>
> Held because nothing could close it: every app start made an engine and
> left it open, and a process that starts many apps -- a reloading dev
> server, a suite that drives the ASGI app per request -- ran the database
> out of connections. That went unnoticed while nothing connected at startup;
> the orphan sweep connects, and it surfaced as `TooManyConnectionsError`
> inside a contract test that had nothing to do with it.

## `Container`, [line 225](../../../../../backend/src/sro/container.py#L225): Note on the line above

Code: `agent_sockets: DeviceSockets = field(default_factory=DeviceSockets)`

> Channels to operators' browsers, open right now, in this process.
>
> In memory for the same reason as the pursuits below: a socket does not
> survive a restart, so a durable record of which browser was connected would
> only ever be a record of which browser used to be.

## `Container`, [line 227](../../../../../backend/src/sro/container.py#L227): Note on the line above

Code: `stops: Stops = field(default_factory=Stops)`

> Runs somebody has asked to stop. In memory beside the pursuits and the
> sockets, and for the same reason: the task that would honour it is in this
> process, so an intention that outlived the process would outlive the only
> thing able to act on it.

## `Container`, [line 231](../../../../../backend/src/sro/container.py#L231): Note on the line above

Code: `approvals: Approvals = field(default_factory=Approvals)`

> Runs parked in front of a person, and the event each one waits on. In
> memory for `Stops`' reason and one more of its own: the wait is an
> `asyncio.Event` in the task driving the run, so a tap that landed in another
> process would set an event nothing is waiting on. That is the same
> one-worker assumption the sockets above already make, and
> `application/execution/approvals.py` is where its end is written down.

## `Container`, [line 233](../../../../../backend/src/sro/container.py#L233): Note on the line above

Code: `pursuits: Pursuits = field(default_factory=Pursuits)`

> Pursuits this process is driving. In memory on purpose: the browser one
> was driving does not survive a restart either, and a half-finished pursuit
> resumed against a screen nobody can see is worse than one that stopped.

## `Container`, [line 235](../../../../../backend/src/sro/container.py#L235): Note on the line above

Code: `capture: CaptureController = field(init=False)`

> Set by ``build_container``: the supervisor is built from the container's
> own use-case factories, so it cannot be a constructor argument.

## `Container`, [line 237](../../../../../backend/src/sro/container.py#L237): Note on the line above

Code: `driving_runs: AsyncConnection | None = None`

> The connection holding the lock that says this process owns the runs.
>
> Set by `claim_the_runs`, held open for the life of the process, and
> released when `lifespan` disposes the engine. One connection out of the
> pool, permanently, which is the price of the guarantee.

## `_build_transcriber`, [line 817](../../../../../backend/src/sro/container.py#L817): Docstring

> Narration leaves the deployment, so it takes two switches, not one.
>
> A key on its own is not consent to send a customer's operators' voices to a
> hosted model; `transcription_enabled` is that decision, made per deployment.

## `_build_intent_parser`, [line 826](../../../../../backend/src/sro/container.py#L826): Docstring

> Reading values out of an operator's sentence. Same switch as the rest:
> the words they type are theirs, and sending them is a decision.

## `_build_interpreter`, [line 835](../../../../../backend/src/sro/container.py#L835): Docstring

> Reading a demonstration sends its calls and bodies to a hosted model.
>
> Through the metered client like every other adapter, so its calls are
> capped and billed: a pursue still reaches it (`pursue_goal` ->
> `understand_recording`), on a pro model. The earlier ruling that skipped it
> assumed Task 6 deleted its callers; it did not (final review I-1,
> 2026-09-24).

## `_patient_asker_for`, [line 844](../../../../../backend/src/sro/container.py#L844): Docstring

> The same asker, given the mining call's own patience.
>
> A second instance rather than a per-call argument: the timeout belongs to
> the SDK client, the port's `ask` says nothing about time, and widening it
> to carry one would put a transport detail in every caller's signature to
> serve one of them.
>
> `isinstance` in the composition root, which is the one place that is
> allowed to know a concrete adapter. Anything else -- a fake in a test, an
> asker a future deployment injects -- is handed back untouched, because
> only this one has a timeout to set.

## `_build_asker`, [line 854](../../../../../backend/src/sro/container.py#L854): Docstring

> The same two switches as its neighbours: a key is not consent to send.
>
> ``interpretation_enabled`` is the switch, because what this sends is what
> that switch is about -- a tenant's captured gestures and the bodies of
> their calls, read by a hosted model.

## `_build_vision`, [line 860](../../../../../backend/src/sro/container.py#L860): Docstring

> Two switches again, and the more consequential pair: this one sends a
> picture of a customer's live warehouse system.

## `_build_embedder`, [line 869](../../../../../backend/src/sro/container.py#L869): Docstring

> Same two-switch rule as transcription: a key is not consent to send.

## `_build_vault`, [line 878](../../../../../backend/src/sro/container.py#L878): Docstring

> A vault that refuses to start beats one that writes plaintext.
>
> The failure is deferred to first use rather than to boot: reading recordings
> and reviewing skills need no secrets, and an API that will not start because
> nobody has generated a key yet is worse than one that says so when a
> connection is attempted.

## `instrument`, [line 901](../../../../../backend/src/sro/container.py#L901): Docstring

> Make the API's requests produce spans.
>
> Here rather than in `interface`, which may not reach an adapter: the
> dependency rule is the one gate that fails on architecture rather than on
> code, and `interface -> infrastructure` is exactly what it exists to
> refuse. This module is the composition root and is allowed to bind one.
>
> Guarded on the endpoint by the caller, so a deployment that has not asked
> for telemetry installs nothing.

## `_servers`, [line 1008](../../../../../backend/src/sro/container.py#L1008): Docstring

> `name=url, name=url` into connectors.
>
> A malformed entry is skipped rather than raising: one typo in a
> comma-separated setting must not stop a deployment whose other connectors
> are fine, and a connector that is absent is already an answer this system
> knows how to give.
>
> **No `#token` any more.** The form used to be `name=url#token`, and that
> token was one bearer for the whole deployment: every tenant's step went out
> holding it, so a run for any tenant reached the same connector and the same
> person's grant. Credentials are per tenant, in the vault, under
> `tenant/server/mcp_token`. Anything after a `#` is dropped rather than
> honoured -- a setting that silently kept working would be a shared
> credential nobody meant to still have.

## `Container.claim_the_runs`, [line 242](../../../../../backend/src/sro/container.py#L242): Docstring

> Whether this process is the one that owns every run.
>
> Everything about runs in this codebase is true only because there is
> exactly one API process: the approval register is an `asyncio.Event`,
> the device sockets are a dict, and the startup sweep marks EVERY
> tenant's `running` rows failed on the reasoning that a row still
> running belongs to a process that died. `Dockerfile` pins
> `--workers 1` and nothing else enforced it, so a rolling deploy, a
> `--scale backend=2` or a restarted pod had a second process sweep the
> first one's live, in-flight runs to `failed` -- which also clears the
> partial unique index on running runs and frees the browser for a
> second run to claim while the first is still driving it.
>
> A Postgres session advisory lock, because it is the one piece of
> shared state both processes already have and it is released by the
> connection dying -- a process that is SIGKILLed releases it, which a
> row in a table would not.
>
> `True` for a container with no engine of its own: a test brings its
> own store and is alone in it.

## `Container.readiness`, [line 260](../../../../../backend/src/sro/container.py#L260): Docstring

> Both halves of "can this process serve", on ONE connection.
>
> Reachable and current are different questions: a database that answers
> `SELECT 1` while four migrations behind is reachable and useless, and
> until this existed the only symptom was a 500 from whichever call
> touched a missing column first.
>
> One session for both, deliberately. Asked on a probe endpoint, which
> under load is called far more often than anything else here -- two
> sessions per call is how a readiness check becomes the thing that
> exhausts the pool it exists to report on.
>
> Lives here so the interface layer stays free of SQL, and returns plain
> booleans so it stays free of the infrastructure's types as well.

## `Container._announce_once`, [line 270](../../../../../backend/src/sro/container.py#L270): Docstring

> Write the schema line to the log the first time anybody probes.
>
> Not from the lifespan, where it belongs on the face of it: a check
> there opens a connection before the process serves anything, and every
> app instance would hold one from boot. The contract suite builds many
> apps and exhausted Postgres on the first run of exactly that -- which
> is a fair warning about what it would do to a deployment that starts
> several workers against a small connection limit.
>
> A probe is where the fact is wanted anyway, it already has the session
> open, and nothing that matters is lost: a deployment probes readiness
> within seconds of starting, and a developer sees the line the first
> time they or their tooling ask.

## `Container.read_spend`, [line 306](../../../../../backend/src/sro/container.py#L306): Docstring

> What this tenant has been billed since midnight, on this clock.
>
> A method rather than a factory like the two above, and the reason is
> the plain one: ``spent_today`` is a bare function, so there is no
> class to construct and a factory would be a wrapper for its own sake.
> Not "nothing route-supplied to hold" -- the tenant IS route-supplied,
> it arrives on the ``ctx`` below, and ``ServeShapes`` holds nothing
> route-supplied either. ``record_offer`` next door was a bare function
> too, and became a class anyway, because it took a bare ``tenant_id``.
>
> That is the line: takes the whole context and never a bare
> ``tenant_id``, so the one seam where passing the wrong tenant is the
> failure stays out of the interface layer -- the same reason
> ``ServeShapes.execute`` takes one, and the reason ``RecordOffer``
> exists as a class at all. ``now`` is supplied here because which day
> is being asked about is a decision no route may make: one that read a
> clock would answer for the server's day.

## `Container.record_offer`, [line 310](../../../../../backend/src/sro/container.py#L310): Docstring

> A factory, where ``read_spend`` above is a method, and not because
> this one has more to hold: ``record_offer`` is a bare function like
> ``spent_today``, but it takes a bare ``tenant_id``. A route calling it
> would unpack the caller itself, at the one seam where passing the
> wrong tenant is the failure. ``RecordOffer`` takes the context
> instead, and the clock ``clamped`` needs comes from here so that no
> route reads one.

## `Container._patient_asker`, [line 313](../../../../../backend/src/sro/container.py#L313): Docstring

> Built on the first pass that needs it -- a second SDK client is a
> socket pool, and a deployment that never mines should not open one --
> and rebuilt whenever `asker` is replaced, which is how a suite drives
> two different answers through one container.

## `Container.mine_pass`, [line 319](../../../../../backend/src/sro/container.py#L319): Docstring

> The model-first rig's pass, which until now had no caller in `src/`.
>
> `asker` is handed over as `Asker | None` rather than through
> `asker_or_refuse` here: a factory that raised would make this method
> itself unbuildable, and a deployment with no key would fail at
> construction instead of at the one call that needs a model.
>
> Not `mine_observations` above. That one clusters a week of observation
> into task candidates with no model in the loop at all; this one packs
> one window, makes one call and writes one `mining_passes` row.

## `Container.mine_lately`, [line 329](../../../../../backend/src/sro/container.py#L329): Docstring

> The rig's miner, on a loop rather than on a person's press.
>
> Both halves had a person in them: `mine_pass` was reachable from a door
> and a script, `read_gestures` from a door and a crontab line in
> `sro.cli.read_cron`. The reader is handed over here so the sweep does
> them in the only order that is not a waste of money -- a mining pass
> packs readings, and an unread gesture has none. The window is
> `mining_window_hours`, the same one the pre-rig sweep looks back over,
> and it is deliberately wider than the interval -- evidence uploaded
> late still gets mined, and mining the same window twice is what the
> pass is built to survive.

## `Container.read_gestures`, [line 337](../../../../../backend/src/sro/container.py#L337): Docstring

> This tenant's unread gestures, which until now had no caller in
> `src/`. Same shape as `mine_pass` above and the same reason: `asker`
> is handed over as `Asker | None` rather than through `asker_or_refuse`
> here, so a deployment with no key fails at the one call that needs a
> model rather than at construction.
>
> `self.blobs` is the same store `ingest_observation` already writes an
> upload's screenshots into -- the one source `read_new_gestures` reads
> a thin gesture's picture back from.

## `Container.read_chat`, [line 349](../../../../../backend/src/sro/container.py#L349): Docstring

> The chat door's reader, which until now had no caller in `src/`.
>
> `gemini_plan_model` and NOT `gemini_mine_model` beside it. A chat door
> and a mining door look like they should share a model and must not: an
> operator is standing at a screen waiting for this answer, so it is the
> fast one -- the same trade `gemini_intent_model` records having
> measured at ~2.3s against ~4.8s for the pro model. This is the rig's
> own wiring: `api.py:1507` hands `understand` `settings().plan_model`.
>
> Not `resolve_intent`. That one resolves an utterance over this tenant's
> *skills* with no model in the loop at all; this one resolves it over
> the *workflows* a mining pass read, and it spends money doing it.
>
> `asker` is handed over as `Asker | None` rather than through
> `asker_or_refuse` here, for `mine_pass`'s reason: a factory that raised
> would make this method itself unbuildable, and a deployment with no key
> would fail at construction instead of at the one call that needs a
> model.

## `Container.plan_lookups`, [line 358](../../../../../backend/src/sro/container.py#L358): Docstring

> Where to look for the answer to one question.
>
> `gemini_plan_model` for `read_chat`'s reason, which applies harder
> here: somebody is waiting on an answer, and a read that takes the slow
> model has spent the difference before the first system is even asked.

## `Container.run_lookups`, [line 368](../../../../../backend/src/sro/container.py#L368): Docstring

> Going and looking, through the operator's own browser.

## `Container.record_attempt`, [line 389](../../../../../backend/src/sro/container.py#L389): Docstring

> What somebody asked for, and what came of it. See
> `sro.domain.observation.attempts` for what belongs there.

## `Container.fire_trigger`, [line 392](../../../../../backend/src/sro/container.py#L392): Docstring

> `start_run` and `pursuits` are the job half, beside the skill half's
> `dispatcher`: a trigger can name a mined workflow now, and one that
> does is started through the same use case `POST /v1/workflow-runs`
> uses, spawned the same way.

## `Container.agents`, [line 424](../../../../../backend/src/sro/container.py#L424): Docstring

> Drivers that perform in an operator's own browser.

## `Container.browsers`, [line 427](../../../../../backend/src/sro/container.py#L427): Docstring

> The only way to open, find or release a browser.
>
> Everything that used to take ``self.browser`` takes this instead, so
> an unowned session cannot be produced by anything this system runs.

## `Container.ask_about_the_offer`, [line 695](../../../../../backend/src/sro/container.py#L695): Docstring

> The card's way into the conversation the chat door already runs.

## `Container.draft_for_the_asker`, [line 698](../../../../../backend/src/sro/container.py#L698): Docstring

> Write the mail to whoever asked. It cannot send one.

## `Container.send_the_draft`, [line 701](../../../../../backend/src/sro/container.py#L701): Docstring

> Send the mail a person read and pressed. It cannot write one.

## `Container.say_the_run_started`, [line 704](../../../../../backend/src/sro/container.py#L704): Docstring

> The other half of the spine: what came of the answer.

## `Container.from_the_mail`, [line 707](../../../../../backend/src/sro/container.py#L707): Docstring

> The rung that reads an arriving mail for what it asks.
>
> `Asker | None` rather than through `asker_or_refuse` here, for the
> reason every other factory gives: a container that raised would be
> unbuildable on a deployment with no key, instead of refusing at the one
> call that needs a model. The guard is in `FromTheMail.execute`.

## `Container.can_gather`, [line 724](../../../../../backend/src/sro/container.py#L724): Docstring

> Whether a run of a mined job can go and find a value nobody typed.
>
> One place, because four now ask: the chat door (so the card says "I
> will look in your mail" rather than demanding), the trigger door (so a
> watch on a job may be made at all), the mail look itself, and
> `/v1/shapes` (so the OFFER a browser draws from a prefix match says the
> same thing as the one it draws from a sentence).
>
> The same pair `start_workflow_run` builds its gather out of: a mailbox
> to read and a model to read it with. A deployment missing either still
> asks for the values, because on that one nothing can go and find them.

## `Container.start_workflow_run`, [line 759](../../../../../backend/src/sro/container.py#L759): Docstring

> The press on a mined job. Not `start_run` above, which mints the row
> for a skill run keyed on a `RunId`.
>
> `SocketChannel` over the sockets this worker already holds, rather than
> a second channel: `DeviceSockets` mints the command ids and correlates
> the answers, and a run that opened its own would be talking to a
> browser nobody else could hear. The stop register and the approval
> register are the process-wide ones for the same reason -- the tap and
> the stop button arrive on routes in this process, and a second register
> is a tap nothing is waiting on.
>
> `gemini_plan_model` plans and `gemini_rescue_model` rescues: a clean
> step never touches the expensive one, and the wiring is the rig's own
> (`api.py:1140`).
>
> `verified_writes` reads `knowledge-base/index/write-endpoints.json`,
> cached by `load_verified_writes` -- an empty ledger where the
> knowledge base is not checked out beside this deployment, never an
> error.

## `Container._drafting`, [line 783](../../../../../backend/src/sro/container.py#L783): Docstring

> Bound to one request, so the mailbox is read as the right person.

## `Container._drafting_for`, [line 786](../../../../../backend/src/sro/container.py#L786): Docstring

> The same, for an offer -- which names its mail before any run has
> been started to hang one on.

## `Container.list_workflow_runs`, [line 789](../../../../../backend/src/sro/container.py#L789): Docstring

> The runs of mined jobs, newest first. Not `list_runs` above, which
> lists skill runs keyed on a `RunId`.

## `Container.get_workflow_run`, [line 792](../../../../../backend/src/sro/container.py#L792): Docstring

> One run of a mined job. Not `get_run` above, for the same reason.

## `Container.abort_workflow_run`, [line 795](../../../../../backend/src/sro/container.py#L795): Docstring

> The stop button on a run of a mined job. Not `stop_run` above, which
> reaches a skill run through `uow.runs` on a `RunId`.
>
> Both process-wide registers, and both for the reason `start_workflow_run`
> gives: the task that honours a stop is waiting on the ones this container
> handed it, and a use case built with registers of its own would set a
> flag nothing ever reads and release a wait nobody is holding.

## `Container.approve_workflow_step`, [line 798](../../../../../backend/src/sro/container.py#L798): Docstring

> The Yes on a run of a mined job, and the other half of the seam
> `abort_workflow_run` above opens.
>
> The same process-wide `approvals` for the reason `start_workflow_run`
> gives: the task parked on a person is waiting on the register this
> container handed it, and a use case built with one of its own would
> release a wait nobody is holding.
>
> The clock, because the row says WHEN the write was let out. A route
> never reads one.

## `Container.mcp_server`, [line 804](../../../../../backend/src/sro/container.py#L804): Docstring

> A tool per runnable skill. One server per process: tenant comes from
> the bearer token on each MCP request, not from how this is built --
> and the use cases are passed as factories, not instances, so each
> request gets its own `UnitOfWork` the same way an HTTP route does.

## `Container.claim_the_runs`, [line 245](../../../../../backend/src/sro/container.py#L245): Comment

Code: `connection = await self.engine.connect()`

> AUTOCOMMIT, and this is not a style choice. A session advisory lock
> is held until it is released or the SESSION ends -- a commit does not
> drop it -- so nothing here needs a transaction. Without this the
> connection sits `idle in transaction` for the entire life of the
> process, and that is not merely untidy: it holds back the xmin
> horizon, so `VACUUM` cannot reclaim a dead row anywhere in the
> database, and it blocks `CREATE INDEX CONCURRENTLY`, which waits for
> every transaction older than itself to finish.
>
> Watched happening: a concurrent index build on this deployment's own
> store sat on `wait_event = virtualxid` behind exactly this session
> and never finished.

## `Container.restore_device`, [line 286](../../../../../backend/src/sro/container.py#L286): Comment

Code: `return RestoreDevice(self.unit_of_work())`

> No drivers, where `revoke_device` above has them: letting a browser
> back in opens no socket, and a use case with no `AgentDrivers` cannot
> grow one by accident.

## `Container.read_spend`, [line 307](../../../../../backend/src/sro/container.py#L307): Comment

Code: `async with self.unit_of_work() as uow:`

> Entered here, not inside ``spent_today``: a unit of work has no
> repositories until its session opens, and ``over_cap``'s other
> callers pass one that is already open.

## `Container.mine_pass`, [line 326](../../../../../backend/src/sro/container.py#L326): Comment

Code: `ours=frozenset(host_port for host_port, _ in self.settings.our_own_origins()),`

> `work_only` reads a workflow's own systems, which have no path --
> so only the host:port half of `our_own_origins` applies here.

## `Container.create_trigger`, [line 377](../../../../../backend/src/sro/container.py#L377): Comment

Code: `can_gather=self.can_gather,`

> The same pair `start_workflow_run` builds its gather out of, so
> this door and the run door agree about what a job needs typed.

## `Container.register_device`, [line 443](../../../../../backend/src/sro/container.py#L443): Comment

Code: `def register_device(self) -> RegisterDevice:`

> -- observation ---------------------------------------------------------

## `Container.converse`, [line 688](../../../../../backend/src/sro/container.py#L688): Comment

Code: `self.read_chat(),`

> The rig's jobs, asked before the taught skills. An operator
> typing at a browser whose rig holds the job they mean was being
> answered out of a skills library that does not.

## `Container.converse`, [line 689](../../../../../backend/src/sro/container.py#L689): Comment

Code: `can_gather=self.can_gather,`

> The same two things `start_workflow_run` builds its gather out
> of. Asked here so the card a person reads says what the run will
> actually do: a deployment with no connector still demands the
> values, because on that one nothing can go and find them.

## `Container.converse`, [line 690](../../../../../backend/src/sro/container.py#L690): Comment

Code: `plan_lookups=self.plan_lookups(),`

> The door that owns a question. `/v1/ask` has always decided
> which of the two worlds a sentence belongs to; this door never
> asked, and answered questions with proposals to open screens.

## `Container.converse`, [line 692](../../../../../backend/src/sro/container.py#L692): Comment

Code: `answers=IsItAnAnswer(self.asker, model=self.settings.gemini_plan_model),`

> Whether what somebody typed while a question stands is the answer
> to it. The fast model, for `read_chat`'s reason: an operator is
> standing at the panel waiting to find out what happens to the
> sentence they just pressed Enter on.

## `Container.from_the_mail`, [line 713](../../../../../backend/src/sro/container.py#L713): Comment

Code: `clock=self.clock,`

> The same one a run uses. An offer that names the values it is
> about is an offer somebody can answer; the run gathers anyway, so
> this is the same work moved to where the decision is made.
> For the one thing this door says in the operator's own thread:
> that a reply has answered the question standing there.

## `Container.start_workflow_run`, [line 772](../../../../../backend/src/sro/container.py#L772): Comment

Code: `vault=self.vault,`

> Where a password comes from when a step types one. The evidence
> never held it: the recorder struck the field out, and this is the
> only place a run can get one.

## `Container.start_workflow_run`, [line 773](../../../../../backend/src/sro/container.py#L773): Comment

Code: `retrieve=self.retrieve_knowledge(),`

> What is already known about a field the run is about to write,
> so the person who taps Approve is shown it. Built here and not
> in the runner, which never learns what a vector store is.

## `Container.start_workflow_run`, [line 774](../../../../../backend/src/sro/container.py#L774): Comment

Code: `gather=GatherContext(`

> Where a value comes from when nobody typed one: the operator's
> own mailbox, reached as them.

## `Container.start_workflow_run`, [line 779](../../../../../backend/src/sro/container.py#L779): Comment

Code: `ids=self.ids,`

> What names the message a run writes when it comes up short and
> asks the operator for what it could not find.

## `Container.start_workflow_run`, [line 780](../../../../../backend/src/sro/container.py#L780): Comment

Code: `asker_drafts=self._drafting,`

> And the mail to whoever sent the request, for the case the panel
> cannot answer: the operator did not write it and does not know.
> A closure for `gather`'s reason -- the drafter needs this
> request's own tenant and operator, and the runner has no
> `RequestContext` to give it.

## `_build_vault`, [line 880](../../../../../backend/src/sro/container.py#L880): Comment

Code: `if settings.vault_project:`

> A named project means a deployment, and a deployment keeps its
> secrets where the rest of its secrets are. The file vault stays the
> laptop's and the suite's: chosen by what is configured rather than by
> an environment name, so a developer pointing at a real project gets
> the real thing and nobody has to remember a second switch.

## `build_container`, [line 953](../../../../../backend/src/sro/container.py#L953): Comment

Code: `tools=McpToolCaller(_servers(settings.mcp_servers), vault=built_vault),`

> The vault, because a connector's bearer is per tenant and lives
> there. Without it `McpToolCaller` refuses rather than calling with
> no credential.

## `build_container`, [line 985](../../../../../backend/src/sro/container.py#L985): Comment

Code: `dispatcher=ApiRunDispatcher(settings.api_url, credentials),`

> Mints its own short-lived credential for the trigger's principal, so
> a scheduled run is asked for by the person who put it on the clock.

## `build_container`, [line 951](../../../../../backend/src/sro/container.py#L951): Comment

Code: `vault=(built_vault := ForgetsRefusalOnWrite(_build_vault(settings))),`

> Every write to the vault lifts a standing credential refusal on that key.
> Wrapped here, once, so no door that stores a password can forget to.
