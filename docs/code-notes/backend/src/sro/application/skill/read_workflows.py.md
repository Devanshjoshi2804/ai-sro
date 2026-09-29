# Notes for `backend/src/sro/application/skill/read_workflows.py`

Comments and docstrings moved out of [`backend/src/sro/application/skill/read_workflows.py`](../../../../../../../backend/src/sro/application/skill/read_workflows.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/skill/read_workflows.py#L1): Docstring

> Every workflow a tenant has, and the evidence any one of them cites.
>
> Ported from `new_agent_arch/src/rig/api.py:812` (the listing) and `:904` (the
> evidence). Two reads in one module because they are the two halves of one
> door -- a listing, and the evidence underneath a row of it -- and because
> neither writes. `serve_shapes` keeps that same promise for the extension's
> list; this is the console's, which is a different question about the same
> rows: not "what can be matched against a live tail" but "what has become of
> this job".
>
> **The listing's history is narrowed from the rig, deliberately.** There,
> `history` answered seven things per workflow and cost five queries to do it,
> one of them per-workflow `counsel`. Three are ported -- the run tally, the
> weak-locator count and whether the job's writes go unasked -- and each is here
> because nothing else this backend serves can answer it:
>
> - `total` and `held` come off `WorkflowRunRepository.tallies`, which is one
>   grouped read for the whole tenant rather than one per row. The rig issued
>   two index counts per workflow; `serve_shapes` learned that the per-workflow
>   form degrades exactly as a customer succeeds, and this route is drawn on a
>   console screen every few seconds.
> - `stale` is the count of steps a run last matched through a weak locator,
>   written by the runner's `mark_stale`. This is its only reader, as it was in
>   the rig: without it a job's page can move under it for a week and the first
>   anybody hears is the run that breaks.
> - `earned` is whether this job may write without asking a person first. It is
>   read from `proofs` and never from the tally beside it -- a job with a
>   hundred held runs and nothing in its register has earned nothing.
>
> `counsel`, the offer fates it is derived from, and the last run are not here.
> The first two are `/v1/shapes`' answer already -- it serves the k a job is
> offered at, and computing it a second time here is a second place the offer
> policy lives -- and the runs, whole, with their steps and their approvals, are
> `/v1/audit`'s. A field that already has a door is not worth two.
>
> **The evidence is complete rather than trimmed**, as the rig's is, and for its
> reason: `application.skill.from_rig` turns a mined step into something
> replayable out of exactly this shape, and a route called `evidence` that
> quietly ships part of the evidence is the defect this project keeps finding.
> Cited gestures only, though -- not the stream and not the store. A workflow is
> a claim about specific evidence, and the largest real one cites 35 of 387
> gestures.
>
> An unknown workflow is `NotFound` out of the repository, and never an empty
> answer: `sro.interface.http.errors` maps it to a 404 once, for every route. A
> listing that answered "this job cites nothing" to a job that does not exist
> would tell a caller their bridge is fine and their workflow is empty.

## `KnownWorkflow`, [line 17](../../../../../../../backend/src/sro/application/skill/read_workflows.py#L17): Docstring

> One workflow with what has become of it.
>
> The workflow whole, rather than the handful of its fields a card draws:
> `parameters` is the pass's own model output and exists nowhere else a
> reader can reach, so a route emitting its siblings is likeliest to drop it.
>
> What the pass could not place is no longer here. It was a fact about the
> window that arrived attached to whichever job the model happened to emit,
> and four readers took it for a property of that job.

## `KnownWorkflow`, [line 23](../../../../../../../backend/src/sro/application/skill/read_workflows.py#L23): Note on the line above

Code: `proven: int`

> Runs toward `earned`: live, held, every write verified by state. The
> same proofs the verdict is read from, so the count and the yes cannot
> disagree.

## `CitedEvidence`, [line 29](../../../../../../../backend/src/sro/application/skill/read_workflows.py#L29): Docstring

> What one workflow cites, in the shape a runner's bridge consumes.
>
> `recordings` is the distinct capture streams those gestures arrived on,
> which is the one input the caller would otherwise have to reach into a
> column for: the backend needs it for `Provenance`, and getting it wrong
> there mis-states whether a skill's values were ever diffed.
>
> `missing` is the cited ids the store no longer holds, in cited order.
> The rig reported it and this route dropped it, which made the module
> docstring's "the evidence is complete rather than trimmed" false on the
> one field that says so: `from_rig.plans_for_step` skips a citation with no
> gesture, so the bridge builds a plan missing a step and, without this,
> nothing tells the caller before it runs one.

## `ReadWorkflows`, [line 35](../../../../../../../backend/src/sro/application/skill/read_workflows.py#L35): Docstring

> The console's list of this tenant's jobs.
>
> A class taking a `RequestContext`, as `ReadAudit` beside it is, and not a
> container method like `read_spend`: that one is a method only so a clock
> can be handed to a bare function, and nothing here reads a clock. What
> both shapes keep is the property that matters -- handed a bare
> `tenant_id`, the route would unpack the caller itself, which puts the
> tenant boundary in the interface layer at the one seam where passing the
> wrong tenant is the failure.

## `ReadEvidence`, [line 72](../../../../../../../backend/src/sro/application/skill/read_workflows.py#L72): Docstring

> Everything one workflow cites, for the bridge that replays it.

## `ReadWorkflows.one`, [line 40](../../../../../../../backend/src/sro/application/skill/read_workflows.py#L40): Docstring

> One job, by id, with nothing counted.
>
> `execute` above reads tallies, a stale count and the earned verdict for
> every job the tenant holds, which is right for a board and wrong for
> the question "what is this one called and what does it declare" -- asked
> by a browser once per frame it sees a matching mail in.

## `ReadWorkflows.execute`, [line 46](../../../../../../../backend/src/sro/application/skill/read_workflows.py#L46): Comment

Code: `tallied = await uow.workflow_runs.tallies(ctx.tenant_id)`

> One grouped read for the tenant, before the loop, and never one
> per row: see the module docstring.

## `ReadWorkflows.execute`, [line 55](../../../../../../../backend/src/sro/application/skill/read_workflows.py#L55): Comment

Code: `total, held = tallied.get(workflow.id, (0, 0))`

> Absent means never run, which the store's GROUP BY gives no
> row for at all.

## `ReadWorkflows.execute`, [line 56](../../../../../../../backend/src/sro/application/skill/read_workflows.py#L56): Comment

Code: `proofs = await uow.workflows.proofs(ctx.tenant_id, workflow.id)`

> Read once for both: `earned` is this count against a floor.

## `ReadEvidence.execute`, [line 78](../../../../../../../backend/src/sro/application/skill/read_workflows.py#L78): Comment

Code: `workflow = await uow.workflows.get(ctx.tenant_id, workflow_id)`

> Tenant-scoped, and this is the whole of the 404: a workflow of
> somebody else's is not found rather than read.

## `ReadEvidence.execute`, [line 79](../../../../../../../backend/src/sro/application/skill/read_workflows.py#L79): Comment

Code: `cited = tuple(dict.fromkeys(ordered_cites(workflow)))`

> `ordered_cites` and not `cited_ids`, which is the same set: the
> mining pass and `rekey_workflows` already read citations in step
> order through this function, and a second spelling of it here is
> a second answer to what a job's evidence is. Nothing downstream
> can tell the two apart -- `ids` is a filter and the gestures come
> back on their own clock -- so this is reuse and not a guarantee.
> `recordings` below is where the order is load-bearing.

## `ReadEvidence.execute`, [line 80](../../../../../../../backend/src/sro/application/skill/read_workflows.py#L80): Comment

Code: `gestures = await uow.gestures.gestures_for(ctx.tenant_id, ids=cited) if cited else ()`

> Not a null check. `gestures_for` with no ids is `IN ()` against
> Postgres, and a workflow that cites nothing is a real row.

## `ReadEvidence.execute`, [line 84](../../../../../../../backend/src/sro/application/skill/read_workflows.py#L84): Comment

Code: `recordings=tuple(dict.fromkeys(gesture.stream_id for gesture in gestures)),`

> In the order the gestures were read -- their own clock --
> and not sorted: a `Provenance` reads these as the streams a
> job's evidence arrived on, oldest first.

## `ReadEvidence.execute`, [line 85](../../../../../../../backend/src/sro/application/skill/read_workflows.py#L85): Comment

Code: `missing=tuple(gid for gid in cited if gid not in held),`

> In cited order -- step order, which `plans_for_step` walks
> -- and not the order the store failed to return them in.

## `KnownWorkflow`, [line 25](../../../../../../../backend/src/sro/application/skill/read_workflows.py#L25): Note on the line above

Code: `offered: bool`

> Whether the chat would offer this job: not a chore, not a mail-only
> doing, not a fragment, and the one copy of its title. The panel's
> "Learned from what you do here" lists only these; the console reads
> every job, so nothing leaves this listing.

## `ReadWorkflows.execute`, [line 52](../../../../../../../backend/src/sro/application/skill/read_workflows.py#L52): Comment

Code: `offered = real_jobs(((one.workflow, one.by_id) for one in every), held=held_by)`

> The chat's own rule (`real_jobs`, which `rank_jobs` ranks within): every
> job it would ever offer, copies collapsed by the same tie-break. One rule
> in one place, so the panel, the shapes and the chat cannot disagree about
> what is a job.
