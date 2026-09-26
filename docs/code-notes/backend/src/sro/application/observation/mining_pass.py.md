# Notes for `backend/src/sro/application/observation/mining_pass.py`

Comments and docstrings moved out of [`backend/src/sro/application/observation/mining_pass.py`](../../../../../../../backend/src/sro/application/observation/mining_pass.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L1): Docstring

> One pass, end to end: pack, ask, check, resolve, store, age the pool.
>
> Ported from `new_agent_arch/src/rig/mine.py` in full, plus `propose` from
> `new_agent_arch/src/rig/umbrella.py`. Everything above `propose` in that second
> file is `sro.domain.skill.umbrella`, which is pure; `propose` asks a model, so
> it is here with the use case that pays for it.
>
> **Not `observation/mine.py`.** That name is taken, and by a different miner:
> `MineObservations` clusters a week of observation into task candidates with no
> model in the loop at all. This is the model-first rig's pass -- one window, one
> call, one `mining_passes` row -- and the two have nothing in common but the
> verb. Two miners, two files, and neither one importing the other.

## `MineResult`, [line 89](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L89): Note on the line above

Code: `learned_parameters: int = 0`

> Parameters a job gained because this pass saw it done a second time.
>
> A pass that keeps nothing has still learnt something if it recognised a job
> and found out what varies in it -- which is the difference between watching
> the same work twice and understanding it.

## `MineResult`, [line 99](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L99): Note on the line above

Code: `read: int = 0`

> Gestures this sweep read before it mined, where a sweep did the reading.
>
> Zero from a pass asked for directly -- `MinePass` reads nothing, and a
> route's caller has its own reader. `MineLately` fills it in, because
> "nothing was kept" means one thing after a hundred fresh readings and
> another after none.

## `MineResult`, [line 104](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L104): Note on the line above

Code: `unplaced: int = 0`

> How many of the window's gestures the pass said it could not place.
>
> A count and not the ids: the ids are gesture rows this pass has just been
> shown and the console can reach either way, and a list of thirty-six
> strings per pass is a paragraph of noise on a row of figures.
>
> Beside `coverage` and not inside any workflow. It is what was left of the
> WINDOW when every job in it had been described, which is a fact about the
> reading -- it lived on `Workflow` until 2026-09-15, where four readers took
> it for a property of the job it happened to be attached to and refused to
> serve, schedule or fire it.
>
> The model's own claim, unverified. It cites roughly one gesture per step
> and calls the rest unplaced, so this runs high: on the first real cross-tab
> evidence this system mined, a third of the thirty-six named were gestures
> supporting the emitted job's own steps.

## `propose`, [line 107](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L107): Docstring

> One pass. Returns what it proposed and what the call cost.
>
> One sample. Plurality voting over repeated samples gained 0.4% at twenty
> times the cost in published work, and that paper's thesis is that voting
> helps LESS as models get stronger. `MINE.thinking` is the knob that replaced it.

## `mine`, [line 127](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L127): Docstring (debt)

> One reading of one tenant's day.
>
> One pass at a time, for the reason the reading loop takes a lock one module
> over: two concurrent callers both read the known workflows before either
> saves, so the same job is proposed twice, billed twice and stored twice --
> `resolve` cannot see a row that has not been written yet. This pass costs a
> 150K-token call to the pro model, so the race is far more expensive here
> than it is there.
>
> Keyed by tenant, like the reading lock and for the same reason: what the
> lock is for is two passes racing over one tenant's workflows, and a single
> global name would make two DIFFERENT tenants take turns for nothing.
>
> ponytail: a process-local lock. Claim rows in the database if this ever
> becomes more than one process.
>
> `uow` is already open: the pass commits its own writes and never enters or
> leaves the block, so the caller owns the session.
>
> `kb` is empty at every call site in this repo, and stays a parameter on
> purpose -- the decision, recorded here so it is not mistaken for the
> `MINE.thinking` / K_POOL_DAYS shape a third time.
>
> It differs from those two in the way that matters: it is not a tuned
> constant whose value nobody justified, it is an INPUT whose absence costs
> nothing and whose presence is already paid for correctly. `window.pack`
> subtracts tokens(kb) from the budget before it fills anything, so a caller
> that passes a knowledge base gets a smaller window rather than a prompt
> over the 200K price boundary. Removing it would delete that subtraction and
> the only seam a knowledge base can enter the prompt through, to save four
> signatures a `str`.
>
> What is genuinely undecided is not this parameter. 296 knowledge-base
> exchange files exist as data, and nothing has specified WHICH of them a
> given window should be shown -- all of them is far past the budget, and
> "the relevant ones" is a retrieval design with its own measurements to
> make. It is left empty, and it is left named.

## `learn_parameters`, [line 156](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L156): Docstring (debt)

> Diff a job's two doings and keep what they disagree about.
>
> Returns how many parameters this pass TOUCHED -- the ones it named for the
> first time plus the ones whose range it widened -- so a pass can say it
> learnt something rather than only that it recognised something. A widening
> is learning: `seen_values` promises every value observed, and a pass that
> adds a third one to a control it already knew did real work and used to
> report nothing. Nothing is removed: a control that stopped varying may
> simply not have been reached this time, and forgetting a parameter on that
> evidence would be worse than carrying one too many.
>
> ponytail: read-modify-write inside one pass's transaction, where the rig
> had it across two connections. `one_at_a_time` serialises passes inside ONE
> process and nothing between two, so a second process mining the same tenant
> can still lose a widening. The lost update is a parameter value, not a
> workflow, and the next doing of the job re-derives it.

## `_names_of`, [line 222](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L222): Docstring

> Every name a stored parameter answers to, its own included.
>
> `names` is absent on everything learnt before it existed, and those entries
> answer to exactly the one name they were written with.

## `_known_by`, [line 229](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L229): Docstring

> The stored parameter that is this control under another of its names.
>
> The page names one field twice -- `Customer Type` on the label,
> `customertype-customerType` on the input -- and which of them a recording
> carries is a fact about the recording. The real `Create a Customer Type`
> was captured both ways and came to declare four parameters for two fields:
> four boxes on the offer card, two of them asking for values nobody has ever
> typed.

## `_folded`, [line 243](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L243): Docstring

> One entry per control, for a job that already has two.
>
> The fix above stops a second entry being written; this is what clears the
> ones already stored. A job mined before it keeps both entries until the
> next pass touches it, and that pass is where the two are recognised as one
> -- the values of each are kept, because `seen_values` promises every value
> observed and the entries being folded observed different doings.
>
> The surviving name is the first one, which is the entry that has been on
> this job longest.
>
> **And where the names cannot decide, the values do.** An entry stored
> before controls were keyed carries a name the model wrote and nothing else,
> so it shares no name with the entry the evidence later produced and no key
> to compare -- two opinions about one control, agreeing on nothing a string
> comparison can see.
>
> Measured on the deployment 2026-09-19. `Delete a Customer Type` held
>
>     {"name": "Customer Type",   "seen_values": ["GDD"]}
>     {"key":  "filterComboBox",  "seen_values": ["GDD", "GSQ", "GZ4"]}
>
> -- one field, the filter the customer type is typed into, declared twice.
> A job declaring two parameters demands two values before it will run, and
> nobody has ever been asked for a `filterComboBox`, so the job stopped
> before its first step on a name the operator has no way to answer.
>
> The same subtraction `_same_control` makes below and for the same reason:
> one entry's every observed value already recorded against the other was
> read off the same typing. It carries the same cost, stated there -- two
> genuinely distinct controls that varied over one value set merge, and the
> second loses its machine name.

## `_same_typing`, [line 275](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L275): Docstring

> Whether two stored parameters were read off the same typing.
>
> Either one's values wholly inside the other's, which is what two readings
> of one control look like when one of them has seen more doings than the
> other. Two empties are not evidence of anything and never match.

## `_same_control`, [line 282](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L282): Docstring (debt)

> The stored parameter that is this one under the model's own name.
>
> `_by_control` names a control by its `item_id` -- `basePriority` -- and the
> model names the same control by the label the operator reads -- `Base
> Priority`. Neither is wrong and they never match as strings, so a job that
> the model declared parameters for grew a second parameter per control on
> its second doing. The real acme store carried `Create a Work Operation`
> with `Operation` beside `operationCode`, `Description` beside
> `longDescription` and `Base Priority` beside `basePriority`, which reaches
> a runner as six inputs to fill in for three fields.
>
> Matched on the values rather than the names, because the values are the
> evidence and the two names are two opinions about it. A learned parameter
> whose every observed value is already recorded against a stored one was
> read off the same typing.
>
> ponytail: two genuinely distinct controls that varied over the same value
> set -- two Yes/No toggles -- merge into one, and the second loses its
> `item_id` name. `planning.value_for` still finds it by `field_label`, so
> the cost is a machine name, not a parameter. Compare on the cited gesture
> ids instead if that ever bites.

## `_grow`, [line 295](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L295): Docstring

> Take this doing's steps, where it does everything the stored job does.
>
> A stored job's steps never grew. `Resolution.contains` has been computed
> since identity was written and read by nothing, and its own note names
> this caller: *"Mine contains theirs" is the case for replacing*.
>
> What it cost to be missing, measured on the deployment 2026-09-21: an
> operator did `Create a Customer Type` twice, filling `Department` and
> `Manufacturer` both times with different values -- two doings varying a
> control, which is this system's whole bar for a parameter. The job learnt
> nothing, because `learn_parameters` compares the stored job with the
> proposal and the stored job was a doing that had never reached those
> controls. It could not, ever, however many times they were used.
>
> **The steps are taken whole, not merged.** A proposal is one coherent
> reading of one doing; a synthesis of two readings is a job nobody
> performed, and this one drives a browser in a warehouse. Containment is
> what makes taking them safe: every step the stored job has, this doing has
> too.
>
> The title, the parameters and everything else the job has learnt stay as
> they are -- only what it DOES is replaced -- and what is keyed to a step's
> number moves with it. See `where_steps_moved`.
>
> A field a run learned (X10) is the one step no doing shows: it cites
> nothing. It is carried over, with its locator, before the write it fills
> (`keeping_fields`); re-derived away, its parameter would stay declared
> with nothing filling it and every later run would leave it out.

## `_packed`, [line 322](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L322): Docstring

> A pooled gesture as `pack` would have built it. `pack` takes the pool
> already packed -- it is the one input that does not arrive as a Gesture --
> and adds K_POOL_BONUS itself, so nothing here touches the strength.

## `_billed`, [line 556](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L556): Docstring

> One row per reading of the day, written whether it found anything or
> not -- including when it was refused, which is the only record left of a
> call that cost money and returned nothing.

## `fill_in_passwords`, [line 580](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L580): Docstring

> Every stored job given the credential step nobody could cite, and how
> many changed.
>
> The pass above adds it to a PROPOSAL, which is right for a job being mined
> for the first time and does nothing at all for one already stored: a
> re-mine of a job the rig holds resolves as `same_job`, the proposal is
> dropped, and the stored steps -- the ones a run actually performs -- stay
> as they were. An operator whose sign-in job was mined last week would wait
> forever for a step that is only ever added to something thrown away.
>
> So it is applied to the store too, on the same rules, and it is idempotent:
> a job whose credential gesture is already cited is left exactly alone, so
> running this every pass costs a read.
>
> Beside `rekey_workflows` and for its reason -- a rule that changed after a
> job was mined has to reach the jobs mined before it, or the fix only helps
> whoever arrives next.

## `rekey_workflows`, [line 649](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L649): Docstring

> Every stored workflow's shape key recomputed from its cited gestures,
> and how many changed.
>
> The key is what `identity.resolve` compares a new proposal against. When
> the rule that makes it changes -- the text rung stopped taking page copy
> -- keys mined before the change no longer match keys mined after, and a
> job the rig already holds could be proposed again as a new one. Run once
> at startup; a key that already agrees is left alone, and a pass that
> changes nothing writes nothing.

## `MineResult`, [line 86](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L86): Comment

Code: `pass_id: str = ""`

> The pass is the thing with a cost, so it is the thing with an id. Every
> workflow this pass kept carries it, and the bill for a day of mining is
> SUM(cost_usd) over the passes -- not over the workflows, where the same
> figure was written once per workflow found.

## `MineResult`, [line 92](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L92): Comment

Code: `coverage: Coverage = field(default_factory=lambda: Coverage(0.0, 0.0, 0.0))`

> Not optional: every pass measures its window, and an empty window
> measures as zeroes rather than as nothing. A `| None` here put a
> branch in the route that no pass can reach.

## `MineResult`, [line 95](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L95): Comment

Code: `thought_tokens: int = 0`

> Part of out_tokens, as on Answer: `MINE.thinking` exists to spend these.

## `MineResult`, [line 98](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L98): Comment

Code: `error: str | None = None`

> What the model said went wrong, when something did -- and what the cap
> said, when it was the cap. A pass that was refused and a pass that
> honestly found nothing are the same result without this.

## `MineResult`, [line 101](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L101): Comment

Code: `left_out: int = 0`

> Evidence this pass did not read, and evidence it could not read. The
> window drops what will not fit the budget; a pooled id whose gesture row
> has since been deleted cannot be packed at all. Both are counted rather
> than left to be inferred from a number that came out smaller than
> expected.

## `MineResult`, [line 103](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L103): Comment

Code: `lopsided: bool = False`

> The reading was concentrated in part of the window: K_MIN_COVERAGE or
> K_MAX_SKEW, whichever it failed. Long-context citation bias is real and
> model-specific, and this is the pass saying it happened.

## `propose`, [line 121](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L121): Comment

Code: `raw = cast(list[object], answer.data["workflows"])`

> A cast and not a check: `ask` already turned an answer whose `workflows`
> is missing or not a list into no answer, and dropped each job that broke
> MINE's schema (`MINE.unit`), so one bad job costs itself and not the pass.

## `mine`, [line 141](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L141): Comment

Code: `logger.warning("%s for %s, nothing mined", why, tenant_id.value)`

> Before anything is read and long before anything is asked -- and before
> `fill_in_passwords` too. That call used to run first, inside this same
> lock, and read (and on a job needing repair, write) the tenant's whole
> workflow store whether or not the day's cap had already been reached: a
> capped tenant still paid for a store read and a possible write every
> sweep. This is the most expensive call in the system, so a cap checked
> after the window is packed is a cap that has already paid for the pass
> it stops -- checked here, a capped tenant does no work at all. No
> `mining_passes` row either: the row exists to record a call that cost
> money, and this pass never made one.

## `mine`, [line 143](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L143): Comment

Code: `filled = await fill_in_passwords(uow, tenant_id=tenant_id)`

> After the cap is checked and before the reading, and cheap once the cap
> has confirmed there is a reading to do: the rule that adds a credential
> step reached proposals the moment it was written, and a job already
> stored is re-proposed as `same_job` and dropped -- so without this the
> fix only ever helps whoever mines a sign-in for the first time after it.
> Inside the lock, because it writes workflows this pass is about to
> compare against.

## `learn_parameters`, [line 169](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L169): Comment

Code: `folded = _folded(stored.parameters)`

> The repair first, and whatever else this pass does or does not learn.
>
> A job mined before a control's names were recorded holds one entry per
> name -- the deployment's `Create a Customer Type` had four for two fields
> -- and the operator meets that as four boxes on an offer card. Folding it
> here rather than only on the path that learns something means a job is
> repaired by any pass that recognises it, not only by one that happens to
> see a new value.

## `learn_parameters`, [line 177](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L177): Comment

Code: `return 0`

> Nothing was LEARNT. A fold is not learning -- it is this pass
> noticing that two of the job's parameters were always one.

## `learn_parameters`, [line 178](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L178): Comment

Code: `by_name = {str(p["name"]): p for p in stored.parameters if "name" in p}`

> A third doing widens what an existing parameter has been given rather
> than being discarded. This always diffs the STORED steps -- doing #1 --
> against the proposal, so a name already present used to be skipped
> outright and `seen_values`' promise of "every value observed" was two
> values, forever. A parameter's range is the useful part of it: a runner
> asked for `$statusCombo` wants to know it has been Active, Closed and
> Staged, not only the first two.

## `learn_parameters`, [line 193](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L193): Comment

Code: `"names": list(parameter.names),`

> Every name this control answers to, so the doing after
> this one recognises it however the page named it then.

## `learn_parameters`, [line 194](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L194): Comment

Code: `"key": parameter.key,`

> The page's own name for the control, where a recording
> carried one: two fields can share a label and two fields
> cannot share an itemId.

## `learn_parameters`, [line 196](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L196): Comment

Code: `"in_all": parameter.in_all,`

> Whether every doing compared reached it. A control two
> doings varied is a parameter; one a third doing never
> reached belongs to a route, and a run taking the other
> route must not stop for want of it.

## `learn_parameters`, [line 197](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L197): Comment

Code: `**({"required": parameter.required} if parameter.said is not None else {}),`

> Whether the PAGE says it must be filled -- the star on
> its own label, which the recording carried and nothing
> read until 2026-09-22. See `LearnedParameter.required`:
> not `in_all`, which measures what the operator happened
> to do rather than what the form demands.
>
> Only where the page SPOKE. `demanded` falls back to the
> star in the names when this key is absent, so writing a
> silence down as `False` would turn "nobody said" into
> "the form says optional" -- and a later recording that
> does carry the star would lose to it.

## `learn_parameters`, [line 201](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L201): Comment

Code: `known = _names_of(existing)`

> The names widen the same way the values do. A parameter first learnt
> from a recording that carried only a label is how a job came to hold
> two entries for one field; a stored parameter that has since been
> seen under the page's own name will not do it again.

## `learn_parameters`, [line 204](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L204): Comment

Code: `named = named or existing["names"] != known`

> Writing the names down is worth a save even when no value changed.
> It is what lets the fold below see that this entry and the one under
> the page's own name for the same control are one -- a job stored
> before any of this has nothing else to recognise itself by.

## `learn_parameters`, [line 205](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L205): Comment

Code: `if parameter.said is not None and existing.get("required") != parameter.required:`

> And what the PAGE said about it, where a recording has now carried
> it. A parameter that already exists took this branch and only this
> branch, and this branch wrote names, key and values -- so a job
> could never learn that a field is mandatory after the first time it
> was seen, however many recordings said so.
>
> Measured on the deployment 2026-09-22. The recorder was reading
> `aria-required` and `allowBlank`, the gestures carried it, the pass
> at 07:49 widened two parameters of this very job, and all four
> entries still held nothing about what the form demands.
>
> Only where the page actually SPOKE. `required` falls back to the
> star in the names when this is absent, so a silence written down as
> `False` would turn "nobody said" into "the form says optional" --
> and that is a claim about a warehouse nobody made.

## `learn_parameters`, [line 217](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L217): Comment

Code: `stored.generalise_title()`

> And the name stops describing the first doing. A title is minted from one
> occurrence, values and all, and this is the only moment the system finds
> out that one of those values varies -- so the job is renamed where it is
> learnt rather than left reading "Create Customer Type DSS" over a
> parameter that has since been DSS, DPP, CCD and CCF.

## `_packed`, [line 330](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L330): Comment

Code: `stream_id=gesture.stream_id,`

> So a pooled gesture joins its own browser's run rather than a
> nameless one shared with every other pooled item. `pack` reads this
> to admit a chosen item's lead-up with it.

## `_one_pass`, [line 343](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L343): Comment

Code: `started_at = now.isoformat()`

> The caller's clock, not the server's, so a test can move it and so the
> day a pass is billed to is the day its caller meant.

## `_one_pass`, [line 345](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L345): Comment

Code: `attribute(tenant=tenant_id.value, pass_id=pass_id)`

> So every line this pass writes -- what it proposed, what it refused and
> why, what it recognised -- says which tenant's day it was reading and
> which reading it was.

## `_one_pass`, [line 347](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L347): Comment (debt)

Code: `gestures = list(await uow.gestures.gestures_for(tenant_id))`

> ponytail: this reads the tenant's WHOLE HISTORY, not a day. Neither
> `gestures_for` nor `intents_for` takes a time bound, so every pass
> deserialises every gesture ever captured -- request and response bodies
> included -- and `frequencies_over` and `shared_values` below then walk
> all of it. That set only grows. Faithful to the rig, and defensible only
> while a pass is dominated by one 150K-token model call; the ceiling is
> the day the scan costs more than the call. The upgrade is the same seam
> the reading loop names: a time-bounded read on `GestureRepository`, which
> the rig had in SQL. The two are one fix, and fixing only the reading loop
> fixes half of it.

## `_one_pass`, [line 349](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L349): Comment

Code: `driven = {gesture_id for gesture_id, intent in intents.items() if was_our_own_driving(intent)}`

> What this browser did while it was driving a run of its own is not
> somebody working, and the reading loop marked it rather than hiding it
> -- see `domain/observation/driving.py`. Dropped HERE as well as there,
> because mining reads a gesture whether or not it carries a reading: one
> the model was never asked about still packs, still scores and can still
> end up in a candidate. Skipping it in only one of the two places would
> be the rule with a copy per caller that this system keeps not having.

## `_one_pass`, [line 360](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L360): Comment

Code: `linked = {gesture_id for ids in crossings.values() for gesture_id in ids}`

> Two ways a gesture can belong to work in another tab, and the second was
> missing until 2026-09-14. A shared VALUE says the two systems carry the
> same thing; a shared SITTING says somebody was working in both. The value
> rule cannot see "read the mail, create what it asks for", because a mail
> nobody typed into carries nothing across -- and on the real acme store it
> linked 23 of 555 gestures where the browser's own timeline holds 219
> inside a sitting that went to another system and came back.
>
> `K_SITTING_GAP_S` is the bound `checks` already uses for what counts as
> one doing, tied to the extension's own tail. `ours` is this deployment,
> which nobody works in.

## `_one_pass`, [line 364](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L364): Comment

Code: `carried = await uow.pool.waiting(tenant_id)`

> The pool stores ids; the window takes evidence. This join is the only
> place the two meet, and a pooled id whose gesture row is gone joins to
> nothing -- so it is named here rather than disappearing from a list
> comprehension. Nothing deletes a gesture today, which is exactly why the
> day something does, this is the only line that would have noticed.

## `_one_pass`, [line 369](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L369): Comment

Code: `pooled: list[Packed] = []`

> Waiting earns priority. A flat carry-over bonus reorders nothing, so the
> window showed the same strongest items every pass: on a 3,240-gesture
> all-tabs day, passes two through ten packed the identical 468 and ten
> passes had shown 19% of the day. K_POOL_WAIT per pass waited is what
> rotates the day through the window. `pack` adds its flat K_POOL_BONUS on
> top of whatever strength arrives here.

## `_one_pass`, [line 377](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L377): Comment

Code: `in_pool = set(pooled_ids)`

> `pooled_ids` is the LIVE pool, so a retired gesture lands in `fresh` and is
> packed at its own strength. That is what retirement means here -- see
> pool.K_POOL_AGE: the entry loses K_POOL_BONUS after six readings, not its
> place in the window. Excluding retired ids from `fresh` too would make a
> gesture the budget dropped six times unreadable forever, and nothing ever
> un-retires.

## `_one_pass`, [line 363](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L363): Comment

Code: `stored_cites = await uow.workflows.placed(tenant_id)`

> What any stored job cites, retired ones included, is not read again --
> neither as fresh evidence nor out of the pool. Every pass used to re-send
> the gestures of every known job, so the model re-read and re-proposed the
> jobs it had already found, at the price of the call, and each duplicate it
> minted grew the known list the next pass paid to send as well.
>
> A new doing of a known job is new gestures, and those are read: that is
> how the job is recognised and learns what varies. Nothing downstream needs
> the old doing in the window -- `learn_parameters` and `_grow` read the
> stored job's citations from `by_id`, the whole store, and `known` is
> re-shaped from the same.
>
> Measured read-only on the local store, 2026-09-23: tenant `new` sent 104
> already-cited gestures in a 254-gesture window; after, none, and the
> budget went to 15 more unplaced ones. Where the unplaced backlog fits in
> one window the prompt shrinks outright -- `rigproof`, 48K tokens to 16K.
>
> A doing recognised as a stored job is not saved as a job of its own, so
> nothing in the steps cites it: it is recorded as placed against that job
> (`place`, below), or the pass after would send all of it again, every
> pass, for good (review, 2026-09-23).
>
> A pooled gesture a job has since cited is handed to `add_unclaimed` as
> claimed, so it leaves the pool rather than waiting in it for a place it
> will never be given.

## `_one_pass`, [line 385](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L385): Comment

Code: `known = [`

> A stored shape is a CACHE of a rule, and the rule can change.
>
> `shape_key` gained the screen on 2026-09-21, and every job mined before
> that carries a shape computed without one. Compared as they stood, a
> proposal's screen-aware shape would match none of them, every known job
> would come back `new`, and one pass would save a second copy of all 22.
> So the known set is re-shaped here, from its own cited evidence, by the
> same function the proposal below uses -- which makes the comparison
> like-with-like today and on whatever the rule becomes next.
>
> Free in practice: these gestures are already loaded, and a tenant has
> tens of jobs against hundreds of thousands of gestures.

## `_one_pass`, [line 406](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L406): Comment

Code: `residue = (answer.data or {}).get("unplaced")`

> `ask` already refused an answer whose `unplaced` breaks the schema, and
> this is a figure on a billing row rather than anything a reader gates on --
> so no answer leaves a zero and costs the pass nothing.

## `_one_pass`, [line 424](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L424): Comment

Code: `evidence = {item.gesture_id: by_id[item.gesture_id].system or "" for item in window.items}`

> `validate` needs the system each cited gesture happened on, not just
> the set of ids: a workflow that names a system none of its evidence
> touched is the one lie an architecture built to find cross-system jobs
> cannot afford. "" for a gesture whose system could not be established,
> which `validate` reads as "unknown" rather than as a system of its own.

## `_one_pass`, [line 425](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L425): Comment

Code: `shown = {item.gesture_id: by_id[item.gesture_id] for item in window.items}`

> The same window, as gestures, for the two passes below that ADD a
> citation to a proposal.
>
> `validate` refuses a workflow citing a gesture outside the window --
> rightly: a job may only be built out of what was read. But
> `with_passwords` and `with_the_press` both searched `by_id`, which is
> every gesture this tenant has ever produced, so either could reach
> past the window and hand `validate` a citation it was bound to
> refuse. The proposal died for a citation the model never made.
>
> Measured on the deployment 2026-09-20, on nearly every pass:
>
>     Delete a Customer Type: 1 step(s) repointed at the control the
>                             operator pressed
>     Delete a Customer Type: refused -- unknown gesture (ges_60e165c1)
>
> -- the repoint and the refusal, one line apart, all evening. A job
> this tenant already has, re-proposed and re-refused every pass, at
> the price of the model call that proposed it.

## `_one_pass`, [line 428](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L428): Comment

Code: `placed: list[Workflow] = []`

> Every proposal that survived `validate`, whether or not it was saved. A
> proposal that resolved onto a stored workflow still read the window and
> still cited real gestures -- it produced no new row, which is not the
> same as having explained nothing. Measured: an identity re-run proposed
> three, kept none, and reported coverage 0.00 with lopsided=True while
> having read the whole window correctly. `kept` answers "what is new";
> this answers "what was accounted for", and coverage and the pool both
> want the second.

## `_one_pass`, [line 430](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L430): Comment

Code: `one_occurrence(proposal, by_id)`

> Before anything reads the citations. A model told that an
> operator repeats a job answers with one job citing every doing,
> and `shape_key`, `learn_parameters` and `_by_control` are all
> wrong about a workflow built that way -- see `one_occurrence`.
> Narrowing first means `validate` judges the job that will
> actually be stored, and refuses it for an uncited step if the
> doing it kept cannot supply one.

## `_one_pass`, [line 431](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L431): Comment

Code: `typed = with_passwords(proposal, shown)`

> After the narrowing and before the judging. The credential
> gesture is invisible to a model -- redaction leaves it no value
> and no name to point at -- so the step that types a password is
> added from the evidence rather than asked for, and it is judged
> like any other step: `validate` sees a step citing a real
> gesture of this doing.

## `_one_pass`, [line 438](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L438): Comment

Code: `pressed = with_the_press(proposal, shown)`

> And the opposite failure: a gesture the model could see and
> passed over. A step that cites the login card rather than the
> Sign In button inside it runs, answers ok, and signs nobody in.

## `_one_pass`, [line 445](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L445): Comment

Code: `for order, used in uses_edges(proposal, by_id).items():`

> And whether the operator did this block more than once in the
> sitting it was read from. A job the model summarised as "add an
> equipment type" whose evidence shows three added in a row is a
> job that can be asked for three at a time -- and until somebody
> asks for three, it runs exactly as it always did.
> Which step took its value from which, read off the evidence.
>
> Before `validate`, because validate REFUSES a bad edge -- a step
> using a later one, or one that is not there -- and an edge this
> wrote is exactly as suspect as an edge a model wrote. The rule
> here only ever looks backwards, so the check should never fire;
> a producer trusted because it is careful is a producer nobody
> checks.

## `_one_pass`, [line 466](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L466): Comment

Code: `logger.info(`

> Said out loud, because a job refused in silence is a job
> nobody can fix. The pass has always carried these and only
> ever counted them, so the row a person reads says a number
> and the log says nothing at all.
>
> Measured on the deployment 2026-09-20: `Create a Client` was
> proposed on two passes running -- the operator had just
> demonstrated it three times, and the miner even found the
> repeat -- and kept on neither. Which gate refused it, and
> why, was not recoverable from anything this system stores.

## `_one_pass`, [line 474](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L474): Comment

Code: `lost = undeliverable(proposal, by_id)`

> Dropped rather than refused: the JOB is sound and only its
> declaration of what varies is not, so refusing it would throw
> away a working job over a spare field. Dropping leaves the job
> runnable on the values its recording carries, which is what a
> job with no parameters has always done, and a later pass
> re-derives the parameter properly from a second doing.

## `_one_pass`, [line 484](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L484): Comment

Code: `proposal.shape_key = [`

> In time order, which is the order the browser's tail arrives in
> and the only order a shape can be matched against. See
> `shape.in_time_order`.

## `_one_pass`, [line 490](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L490): Comment

Code: `resolution = resolve(proposal, known + kept, signs_in_to=lands)`

> Resolved against what is stored plus what this pass has already kept,
> and always before its own save -- which is what makes matching a
> proposal against itself unreachable rather than guarded. `known`
> alone was not enough: two proposals of one job inside a single pass
> both read an empty store and both saved.

## `_one_pass`, [line 492](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L492): Comment

Code: `logger.info(`

> What became of it, said out loud.
>
> A pass reporting "0 job(s) kept of 7 proposed" is reporting three
> different things at once -- refused, recognised as one already
> stored, or the same evidence read twice -- and only the first of
> them is a problem. Measured on the deployment 2026-09-20: the
> operator demonstrated `Create a Client` three times, the miner
> kept it, and the passes after that said `0 kept` because it was
> being recognised. Nothing anywhere could tell that apart from the
> job being thrown away, and I read it as thrown away.

## `_one_pass`, [line 514](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L514): Comment

Code: `result.learned_parameters += await learn_parameters(`

> The same job, done again, on different evidence -- which is
> the only thing that can tell a parameter from a constant. One
> doing of "Create Work Activity TEST1" cannot say whether
> TEST1 names this activity or every activity; two doings that
> disagree about it can. Recorded on the stored workflow rather
> than the proposal, because the proposal is about to be
> discarded and the job is what learns.

## `_one_pass`, [line 522](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L522): Comment

Code: `if resolution.contains:`

> And the job itself grows, where this doing wholly contains
> it. AFTER the parameters, and the order is the whole of why
> it works: `learn_parameters` compares the stored job against
> this proposal, and a job that had already taken the
> proposal's steps would be comparing a doing with itself --
> every control reached by both, no value different from
> itself, and nothing learnable ever again.

## `_one_pass`, [line 533](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L533): Comment

Code: `result.lopsided = result.error is None and (`

> Only where a model answered. A refused pass cited nothing, so coverage
> is 0.0 and this read True on every one of them -- the passes table
> publishing a citation-bias verdict on a reading that never happened,
> which is the table a person actually reads. Recoverable from `error`;
> nobody should have to.

## `_one_pass`, [line 538](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L538): Comment

Code: `await uow.pool.add_unclaimed(`

> `window.left_out` is pooled beside what the pass read and could not place.
> Evidence the budget dropped never got a FIRST look, which is a worse case
> than the 74% recall the pool exists for, not an exempt one -- and left
> unpooled it earns no K_POOL_BONUS, so on the next pass it competes on
> exactly the terms that already lost it. Past one window's worth of
> evidence that is the same tail losing forever while `left_out` reports it
> every time.
>
> Safe against a double add: `pack` puts each candidate in `items` or in
> `left_out`, never both, and `add_unclaimed` leaves an already-pooled
> gesture -- one that was pooled and still did not fit -- with the age it
> has earned rather than restarting its clock.
>
> `claimed` is every cited id and is never narrowed to this pass's own
> FRESH evidence: a pooled gesture is packed into the window beside the
> fresh ones, so a pass can cite evidence that is only in the pool, and
> a citation left in the pool ages out and retires despite having been
> placed. The two arguments are siblings and only one of them is about
> the window.
>
> Plus any pooled gesture a stored job cites (see `stored_cites`): not
> shown, so never claimed by this pass, and never going to be shown again.
>
> Which narrowing matters, recorded so nobody hunts the other one
> twice: narrowing `claimed` to the WINDOW's own ids changes nothing
> and cannot be tested, because `validate` has already refused any
> workflow citing an id outside `window.items`. Narrowing it to the
> fresh ids is the failure above, and is what the test plants.

## `_one_pass`, [line 543](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L543): Comment

Code: `if result.error is None or answer.in_tokens:`

> Exactly once, and only on a pass the model read. K_POOL_AGE is six
> READINGS of patience; counting attempts meant six 503s -- or an expired
> key, or a model name the API 404s, which findings.md records as the
> shipped default -- retired the whole pool having read nothing at all. A
> second call here would halve it, and a refused one spends it for free.
>
> "The model read it" is `in_tokens`: a raised call -- a 503, an expired key,
> a model name the API 404s -- comes back with no usage and ages nothing. A
> call the model was billed for reading ages the pool even when its answer
> was unusable (blocked, truncated, or breaking MINE's schema): the window
> was shown, and not ageing it hands the same window back with its bonus,
> billed again, the same way, forever. A schema-valid answer that found no
> workflows is a reading like any other.

## `_one_pass`, [line 544](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L544): Comment

Code: `await uow.pool.age(tenant_id, shown=tuple(item.gesture_id for item in window.items))`

> Only what the window actually showed. An entry the budget left
> out was not read and has not used up its patience -- ageing it
> anyway retired 2,630 of a 3,240-gesture day unread.

## `_one_pass`, [line 546](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L546): Comment

Code: `billed = _billed(pass_id, tenant_id, started_at, result)`

> In a finally, so the row exists whatever the work above did. It is
> the only record left of a call that cost money, and it was written
> last: anything raising after the model answered -- a store that fell
> over mid-save -- lost the bill entirely, while leaving the workflows
> already saved pointing at a pass_id with no row behind it.
>
> The commit is here rather than after the block for the same reason:
> on the happy path the workflows, the pool and the bill land in one
> transaction.

## `_one_pass`, [line 550](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L550): Comment

Code: `await uow.rollback()`

> The session is already dead. Postgres refuses every statement on
> a transaction that has raised -- InFailedSQLTransactionError --
> so this write failed for the same reason the one above it did,
> and its DBAPIError would replace the exception that caused it.
>
> The rollback costs nothing that is not already lost: Postgres
> discarded this transaction's workflows the moment the statement
> failed. Measured against the suite's own Postgres, before this:
> `passes: 0, workflows: 0` and a DBAPIError in place of the real
> one. The rig never met this because its `store.execute` opened a
> connection per statement, so every save was its own committed
> transaction and the bill after a failed one simply landed. One
> session is the port's shape, and this is what that shape costs.

## `fill_in_passwords`, [line 582](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L582): Comment (debt)

Code: `by_id = {gesture.id: gesture for gesture in await uow.gestures.gestures_for(tenant_id)}`

> The whole doing, not only what is cited: the credential gesture is by
> definition the one nothing cites, so a read narrowed to the citations
> could never find it. Bounded by the span `with_passwords` then
> applies -- this reads a tenant's gestures once per pass.
>
> Once, and before the loop over stored jobs -- not once per job. It used
> to live inside the loop, so this note's "once per pass" was true of the
> intent and false of the code: a tenant with N stored jobs paid for the
> whole-store read N times, once per pass really meaning once per job that
> pass touched. Moved up so the code says what the note always claimed.
>
> ponytail: whole-store read per pass; a `between(first, last)` query when
> a tenant's day stops fitting comfortably in memory.

## `fill_in_passwords`, [line 586](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L586): Comment

Code: `found = repeated_block(workflow, by_id)`

> Three healings, and any one of them is a reason to save.
> `with_passwords` adds the step a model cannot see; `with_the_press`
> repoints a step a model aimed at the page instead of the button on
> it; and the repeat is what the evidence says about how many times the
> block was done.

## `fill_in_passwords`, [line 588](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L588): Comment

Code: `if workflow.repeat != found:`

> Set and cleared. A job whose repeat no longer holds -- re-mined,
> its evidence aged out, the doing it was read from gone -- goes back
> to a job that does one thing once rather than keeping a block nothing
> supports.

## `rekey_workflows`, [line 659](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L659): Comment

Code: `if any(cited not in by_id for cited in wanted):`

> Only over the whole evidence. A key recomputed over the survivors of
> a pruned batch would be shorter than the job -- and an empty one
> matches nothing, which is the duplicate this exists to prevent.

## `_grow`, [line 312](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L312): Comment

Code: `stored.signs_in = proposal.signs_in`

> The steps are the proposal's now, so whether the job signs in is the
> proposal's reading of them too. The healing pass would reach the same
> answer at the start of the next pass; a run in between would read a stale
> one.

## `_one_pass`, [line 473](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L473): Comment

Code: `proposal.signs_in = signs_in(proposal, by_id)`

> Decided here, once, for every job that survived the gates -- see
> `checks.signs_in`. After `work_only`, which refuses the sign-in that moved
> the browser along as not a job worth offering; what is left and still signs
> in is a job a run may splice in to get back through a sign-in page, and one
> whose run may end `held` when the browser has moved past its page.

## `_grow`, [line 307](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L307): Comment

Code: `if credentials_typed(proposal, by_id) - credentials_typed(stored, by_id):`

> Growth takes the doing's steps wholesale, so a doing that typed a credential
> the job does not -- per field, so a second factor counts as much as a first
> password -- would turn the job into one that signs in first -- and every
> run of it would then ask for, and type, a credential the job never needed.
> The parameters were already learnt from this doing one call up; only the
> steps are refused.

## `_one_pass`, [line 391](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L391): Comment

Code: `lands = {`

> Where each stored sign-in job signs in, for `resolve`: two jobs signing in
> to one system are one job whatever path they took (see `identity.resolve`).
> Only jobs already marked `signs_in`, and only while their evidence is held;
> a proposal adds itself below once it has been marked, so two proposals of
> one sign-in inside one pass fold too.

## `fill_in_passwords`, [line 591](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L591): Comment

Code: `marked = _judged(workflow, by_id)`

> Healed onto stored jobs by the same rule as new ones, and in both
> directions: a job stored before the mark existed reads false until its
> evidence is read here, and one whose evidence now says otherwise is
> corrected rather than left to a run.

## `_evidenced`, [line 603](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L603): Note on the function

> Whether every gesture a job cites is stored -- the one precondition for
> judging it from its evidence.

## `_judged`, [line 608](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L608): Note on the function

> The one decider of `signs_in`, used by `fill_in_passwords` and
> `decide_sign_ins` alike, and always after the password steps and presses
> are healed in (on a copy, so judging writes nothing): the stored steps of a
> job mined before the healing existed lack them, and `signs_in` asks whether
> every writing step is a sign-in step.
>
> A job without its evidence -- no cites, or cites never stored -- is
> `false`. Gestures are never deleted, and every use of `true`
> (`signs_in_to`, `signs_in_at`, `recorded_login`) needs those gestures, so
> `false` hides nothing, and the job is not left undecided to be re-read on
> every sweep.

## `evidence_of`, [line 617](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L617): Note on the function

> The cited gestures of some jobs, widened to the sitting around each
> (`K_SITTING_GAP_S`): everything `signs_in`, `with_passwords` (between the
> first and last cite), `with_the_press` (`SOON_S` after a click),
> `signs_in_to` and `recorded_login` read. Bounded by the jobs asked about,
> never the tenant's whole history. Shared with `scripts/migrate_vault_keys.py`.

## `mining_lock`, [line 637](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L637): Note on the function

> The name of a tenant's mining lock (`AccountLocks.hold_named`), held by
> `mine` -- and so by the `fill_in_passwords` healing inside it, which saves
> whole workflows -- and by the sweep while it decides that tenant's jobs.
> A Postgres advisory lock, so it holds across workers; an in-process lock
> let two workers mine, heal and grow one tenant at once.

## `decide_sign_ins`, [line 641](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L641): Note on the function

> Decides one tenant's undecided jobs (live, `signs_in IS NULL`), new
> gestures or not: 0069 stored `false` on every existing job and only new
> gestures ever re-judged one, so a quiet system never decided anything.
> Only those jobs' evidence is read (`evidence_of`).
>
> Written column-only, as a compare-and-set that succeeds only while the
> column is still NULL (`decide_signs_in`): a decision already made is never
> overwritten, and nothing but the column is written. New gestures re-judge
> a decided job through `fill_in_passwords`, as before.

## `propose`, [line 116](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L116): Comment

Code: `day = [item.evidence for item in arrange(window.items)]`

> arrange() and not window.items directly. `pack` sorts the window into time
> order and every reader downstream depends on that -- checks.coverage
> slices it into TIME deciles, and its skew figure is only comparable across
> passes while those deciles mean the same thing. So the reordering happens
> here, at the one place the evidence becomes a prompt, exactly as
> algorithms.md's pseudocode has it: `chosen.sort(key=at)` upstream,
> `arrange(chosen)` at assembly.
