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

## `MineResult`, [line 87](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L87): Note on the line above

Code: `learned_parameters: int = 0`

> Parameters a job gained because this pass saw it done a second time.
>
> A pass that keeps nothing has still learnt something if it recognised a job
> and found out what varies in it -- which is the difference between watching
> the same work twice and understanding it.

## `MineResult`, [line 97](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L97): Note on the line above

Code: `read: int = 0`

> Gestures this sweep read before it mined, where a sweep did the reading.
>
> Zero from a pass asked for directly -- `MinePass` reads nothing, and a
> route's caller has its own reader. `MineLately` fills it in, because
> "nothing was kept" means one thing after a hundred fresh readings and
> another after none.

## `MineResult`, [line 102](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L102): Note on the line above

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

## `propose`, [line 106](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L106): Docstring

> One pass. Returns what it proposed and what the call cost.
>
> One sample. Plurality voting over repeated samples gained 0.4% at twenty
> times the cost in published work, and that paper's thesis is that voting
> helps LESS as models get stronger. `MINE.thinking` is the knob that replaced it.

## `mine`, [line 126](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L126): Docstring (debt)

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

## `_billed`, [line 606](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L606): Docstring

> One row per reading of the day, written whether it found anything or
> not -- including when it was refused, which is the only record left of a
> call that cost money and returned nothing.

## `fill_in_passwords`, [line 631](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L631): Docstring

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

## `rekey_workflows`, [line 667](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L667): Docstring

> Every stored workflow's shape key recomputed from its cited gestures,
> and how many changed.
>
> The key is what `identity.resolve` compares a new proposal against. When
> the rule that makes it changes -- the text rung stopped taking page copy
> -- keys mined before the change no longer match keys mined after, and a
> job the rig already holds could be proposed again as a new one. Run once
> at startup; a key that already agrees is left alone, and a pass that
> changes nothing writes nothing.

## `MineResult`, [line 84](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L84): Comment

Code: `pass_id: str = ""`

> The pass is the thing with a cost, so it is the thing with an id. Every
> workflow this pass kept carries it, and the bill for a day of mining is
> SUM(cost_usd) over the passes -- not over the workflows, where the same
> figure was written once per workflow found.

## `MineResult`, [line 90](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L90): Comment

Code: `coverage: Coverage = field(default_factory=lambda: Coverage(0.0, 0.0, 0.0))`

> Not optional: every pass measures its window, and an empty window
> measures as zeroes rather than as nothing. A `| None` here put a
> branch in the route that no pass can reach.

## `MineResult`, [line 93](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L93): Comment

Code: `thought_tokens: int = 0`

> Part of out_tokens, as on Answer: `MINE.thinking` exists to spend these.

## `MineResult`, [line 96](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L96): Comment

Code: `error: str | None = None`

> What the model said went wrong, when something did -- and what the cap
> said, when it was the cap. A pass that was refused and a pass that
> honestly found nothing are the same result without this.

## `MineResult`, [line 99](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L99): Comment

Code: `left_out: int = 0`

> Evidence this pass did not read, and evidence it could not read. The
> window drops what will not fit the budget; a pooled id whose gesture row
> has since been deleted cannot be packed at all. Both are counted rather
> than left to be inferred from a number that came out smaller than
> expected.

## `MineResult`, [line 101](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L101): Comment

Code: `lopsided: bool = False`

> The reading was concentrated in part of the window: K_MIN_COVERAGE or
> K_MAX_SKEW, whichever it failed. Long-context citation bias is real and
> model-specific, and this is the pass saying it happened.

## `propose`, [line 120](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L120): Comment

Code: `raw = cast(list[object], answer.data["workflows"])`

> A cast and not a check: `ask` already turned an answer whose `workflows`
> is missing or not a list into no answer, and dropped each job that broke
> MINE's schema (`MINE.unit`), so one bad job costs itself and not the pass.

## `mine`, [line 140](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L140): Comment

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

## `mine`, [line 142](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L142): Comment

Code: `if await fill_in_passwords(uow, tenant_id=tenant_id):`

> After the cap is checked and before the reading, and cheap once the cap
> has confirmed there is a reading to do: the rule that adds a credential
> step reached proposals the moment it was written, and a job already
> stored is re-proposed as `same_job` and dropped -- so without this the
> fix only ever helps whoever mines a sign-in for the first time after it.
> Inside the lock, because it writes workflows this pass is about to
> compare against.
>
> Then the transaction ends, whatever was healed (a commit, or a rollback
> when nothing changed): the heal's locked re-read
> holds a job's row lock even when it finds nothing left to do, and the pass
> next asks the model -- minutes, at worst -- during which every run's
> learning on that job (`Teach.learn`, `locators`, `learn_field`) would wait.

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
>
> Still true after M1, which made the MODEL spend incremental and not this
> read: `pool.retired()` now joins it, one row per gesture ever pooled. A
> pass that asks nothing still reads it all (review M3, accepted).

## `_one_pass`, [line 350](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L350): Comment

Code: `driven = {gesture_id for gesture_id, intent in intents.items() if was_our_own_driving(intent)}`

> What this browser did while it was driving a run of its own is not
> somebody working, and the reading loop marked it rather than hiding it
> -- see `domain/observation/driving.py`. Dropped HERE as well as there,
> because mining reads a gesture whether or not it carries a reading: one
> the model was never asked about still packs, still scores and can still
> end up in a candidate. Skipping it in only one of the two places would
> be the rule with a copy per caller that this system keeps not having.

## `_one_pass`, [line 361](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L361): Comment

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

## `_one_pass`, [line 365](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L365): Comment

Code: `carried = await uow.pool.waiting(tenant_id)`

> The pool stores ids; the window takes evidence. This join is the only
> place the two meet, and a pooled id whose gesture row is gone joins to
> nothing -- so it is named here rather than disappearing from a list
> comprehension. Nothing deletes a gesture today, which is exactly why the
> day something does, this is the only line that would have noticed.

## `_one_pass`, [line 379](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L379): Comment

Code: `pooled: list[Packed] = []`

> Waiting earns priority. A flat carry-over bonus reorders nothing, so the
> window showed the same strongest items every pass: on a 3,240-gesture
> all-tabs day, passes two through ten packed the identical 468 and ten
> passes had shown 19% of the day. K_POOL_WAIT per pass waited is what
> rotates the day through the window. `pack` adds its flat K_POOL_BONUS on
> top of whatever strength arrives here.

## `_one_pass`, [line 387](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L387): Comment

Code: `in_pool = set(pooled_ids)`

> `pooled_ids` is the LIVE pool. A retired entry is not fresh either (see
> `retired` below): it was read K_POOL_AGE + 1 times, or it is this
> browser's own driving, or it went stale.
>
> It used to be: a retired gesture landed back in `fresh` and was packed at
> its own strength, on the reasoning that excluding it would make "a gesture
> the budget dropped six times" unreadable. But the age counts READINGS
> (`age(shown=...)`), not passes over it, so a retired entry is one the model
> has already read seven times. On the QA box, 2026-09-25, those came back
> every pass: `left_out` stayed near 1,157 against a window of 191, the sweep's
> walk ran up to eight passes after every arrival, and 35 of 40 passes that
> day had no new input.

## `_one_pass`, [line 366](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L366): Comment

Code: `ours_driving = tuple(entry.gesture_id for entry in carried if entry.gesture_id in driven)`

> A gesture can be pooled before its reading says this browser was driving a
> run: the reading comes later, or the run was recorded later. Once it says
> so, the gesture leaves `by_id` above, and the pool entry used to join to
> nothing. It was reported as "pooled gesture(s) have no row" on every pass
> (82 of them on the QA box, every one with a row) and never retired, since
> only a reading ages an entry. It is retired here, once, with its reason.
> The warning below is now only for an entry whose gesture row is really gone.

## `_one_pass`, [line 396](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L396): Comment

Code: `read = frozenset(entry.gesture_id for entry in carried if entry.age > 0)`

> What has been mined, kept where it already was. A gesture a pass read and
> a job cited is placed (`stored_cites`). One read and not cited sits in the
> pool with `age > 0`. One read seven times, or ours, is retired. So `unread`
> is exactly what no pass has read: fresh gestures, plus pooled ones the
> budget left out (`age == 0`). Nothing new is stored to know it, and the
> mark is set by `pool.age`, the pass's last write, committed in the same
> transaction as the jobs it kept. A pass that dies before that commit has
> read nothing, and the next one reads it.
>
> `pack` fills the window with `unread` only; what was read joins as the
> unread gestures' neighbours, bounded (see `window.pack`). A job whose
> halves reached two passes is only put together when the model sees both
> halves at once.
>
> "Read" never expires (review M4, accepted). A gesture mined before its
> reading arrived, or before a prompt fix such as MINE v2, is not mined again
> with it. There is no automatic re-mine on a prompt version bump, because
> re-reading the whole store costs what the idle passes cost. The lever, if
> one is wanted, is to reset `age` to 0 for the entries to re-read.

## `_one_pass`, [line 419](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L419): Comment

Code: `if unread.isdisjoint(item.gesture_id for item in window.items):`

> A window that holds nothing unread is not sent. Measured on the QA box: of
> 2,358 passes, 2,156 (91%, $960.92) came after no new capture, and passes over
> input already read "kept" 38 jobs. The model is not deterministic, so a
> second reading of the same evidence does not agree with the first; it adds
> another copy. The QA store's 0-parameter "Create a Customer Type" beside the
> 4-parameter one is such a copy (see the test
> `test_a_new_doing_grows_the_job_and_no_empty_copy_is_minted`).
>
> The idle pass still writes its row (cost 0, `left_out` 0). The sweep's gate
> (`MineLately._worth_a_pass`) reads the last row, and without this one it
> would open again on every sweep until new capture arrived.
>
> Two passes at once for one tenant queue on `mining_lock`. The second one
> reads the pool the first committed, finds nothing unread, and asks nothing
> (`TestWhatAPassHasMined` proves it against real Postgres).

## `_one_pass`, [line 441](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L441): Comment

Code: `left_out=len(`

> How much this pass left unread, not what `pack` did not take. Pooled
> evidence already read and left out of the window is context and nobody's
> backlog. Counted the old way, it kept `left_out` above zero forever, and
> the sweep's gate kept walking. A pass whose answer could not be used
> leaves its window unread too, and says so; the gate walks on while this
> is above zero and the last pass's model read something.

## `_one_pass`, [line 364](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L364): Comment

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

## `_one_pass`, [line 402](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L402): Comment

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

## `_one_pass`, [line 429](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L429): Comment

Code: `residue = (answer.data or {}).get("unplaced")`

> `ask` already refused an answer whose `unplaced` breaks the schema, and
> this is a figure on a billing row rather than anything a reader gates on --
> so no answer leaves a zero and costs the pass nothing.

## `_one_pass`, [line 451](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L451): Comment

Code: `evidence = {item.gesture_id: by_id[item.gesture_id].system or "" for item in window.items}`

> `validate` needs the system each cited gesture happened on, not just
> the set of ids: a workflow that names a system none of its evidence
> touched is the one lie an architecture built to find cross-system jobs
> cannot afford. "" for a gesture whose system could not be established,
> which `validate` reads as "unknown" rather than as a system of its own.

## `_one_pass`, [line 452](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L452): Comment

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

## `_one_pass`, [line 455](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L455): Comment

Code: `placed: list[Workflow] = []`

> Every proposal that survived `validate`, whether or not it was saved. A
> proposal that resolved onto a stored workflow still read the window and
> still cited real gestures -- it produced no new row, which is not the
> same as having explained nothing. Measured: an identity re-run proposed
> three, kept none, and reported coverage 0.00 with lopsided=True while
> having read the whole window correctly. `kept` answers "what is new";
> this answers "what was accounted for", and coverage and the pool both
> want the second.

## `_one_pass`, [line 457](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L457): Comment

Code: `one_occurrence(proposal, by_id)`

> Before anything reads the citations. A model told that an
> operator repeats a job answers with one job citing every doing,
> and `shape_key`, `learn_parameters` and `_by_control` are all
> wrong about a workflow built that way -- see `one_occurrence`.
> Narrowing first means `validate` judges the job that will
> actually be stored, and refuses it for an uncited step if the
> doing it kept cannot supply one.

## `_one_pass`, [line 458](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L458): Comment

Code: `typed = with_passwords(proposal, shown)`

> After the narrowing and before the judging. The credential
> gesture is invisible to a model -- redaction leaves it no value
> and no name to point at -- so the step that types a password is
> added from the evidence rather than asked for, and it is judged
> like any other step: `validate` sees a step citing a real
> gesture of this doing.

## `_one_pass`, [line 465](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L465): Comment

Code: `pressed = with_the_press(proposal, shown)`

> And the opposite failure: a gesture the model could see and
> passed over. A step that cites the login card rather than the
> Sign In button inside it runs, answers ok, and signs nobody in.

## `_one_pass`, [line 472](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L472): Comment

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

## `_one_pass`, [line 493](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L493): Comment

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

## `_one_pass`, [line 501](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L501): Comment

Code: `lost = undeliverable(proposal, by_id)`

> Dropped rather than refused: the JOB is sound and only its
> declaration of what varies is not, so refusing it would throw
> away a working job over a spare field. Dropping leaves the job
> runnable on the values its recording carries, which is what a
> job with no parameters has always done, and a later pass
> re-derives the parameter properly from a second doing.

## `_one_pass`, [line 511](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L511): Comment

Code: `proposal.shape_key = [`

> In time order, which is the order the browser's tail arrives in
> and the only order a shape can be matched against. See
> `shape.in_time_order`.

## `_one_pass`, [line 517](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L517): Comment

Code: `resolution = resolve(proposal, known + kept, signs_in_to=lands)`

> Resolved against what is stored plus what this pass has already kept,
> and always before its own save -- which is what makes matching a
> proposal against itself unreachable rather than guarded. `known`
> alone was not enough: two proposals of one job inside a single pass
> both read an empty store and both saved.

## `_one_pass`, [line 523](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L523): Comment

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

## `_one_pass`, [line 553](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L553): Comment

Code: `result.learned_parameters += await learn_parameters(`

> The same job, done again, on different evidence -- which is
> the only thing that can tell a parameter from a constant. One
> doing of "Create Work Activity TEST1" cannot say whether
> TEST1 names this activity or every activity; two doings that
> disagree about it can. Recorded on the stored workflow rather
> than the proposal, because the proposal is about to be
> discarded and the job is what learns.

## `_one_pass`, [line 561](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L561): Comment

Code: `if resolution.contains:`

> And the job itself grows, where this doing wholly contains
> it. AFTER the parameters, and the order is the whole of why
> it works: `learn_parameters` compares the stored job against
> this proposal, and a job that had already taken the
> proposal's steps would be comparing a doing with itself --
> every control reached by both, no value different from
> itself, and nothing learnable ever again.

## `_one_pass`, [line 572](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L572): Comment

Code: `result.lopsided = result.error is None and (`

> Only where a model answered. A refused pass cited nothing, so coverage
> is 0.0 and this read True on every one of them -- the passes table
> publishing a citation-bias verdict on a reading that never happened,
> which is the table a person actually reads. Recoverable from `error`;
> nobody should have to.

## `_one_pass`, [line 577](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L577): Comment

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

## `_one_pass`, [line 518](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L518): Comment

Code: `if resolution.kind == "fragment":`

> Refused by name, not stored and not placed. A piece of a stored job, with
> no parameters of its own, is not a job (see `identity.resolve`). Its
> gestures go to the pool as read, like any refused proposal's.

## `_one_pass`, [line 583](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L583): Comment

Code: `if answer.data is not None:`

> Exactly once, and only on a pass whose answer could be used. `age` is
> now the mark that a window was mined, so it is set only when the answer
> parsed (GC 10: an unusable answer is unsure, not an answer). K_POOL_AGE
> is readings, not attempts; a raised call (a 503, an expired key, a model
> name the API 404s) comes back with no usage and touches nothing.
>
> An answer the model was billed for and that could not be used (blocked,
> truncated, or breaking MINE's schema) leaves its window unread and counts
> a failed reading on each entry shown (`age(failed=True)`). Before M1 round
> 1 it aged the window, which after M1 meant mined: a truncated answer lost
> its whole window. Counting is what stops the other failure, the same
> window billed the same way for ever: K_MINE_ATTEMPTS failed readings and
> the entry retires as unminable, said in the log.

## `_one_pass`, [line 584](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L584): Comment

Code: `await uow.pool.age(tenant_id, shown=packed)`

> Only what the window actually showed. An entry the budget left
> out was not read and has not used up its patience -- ageing it
> anyway retired 2,630 of a 3,240-gesture day unread.

## `_one_pass`, [line 596](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L596): Comment

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

## `_one_pass`, [line 600](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L600): Comment

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

## `fill_in_passwords`, [line 633](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L633): Comment (debt)

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

## `_healed`, [line 655](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L655): Comment

Code: `found = repeated_block(workflow, by_id)`

> Three healings, and any one of them is a reason to save.
> `with_passwords` adds the step a model cannot see; `with_the_press`
> repoints a step a model aimed at the page instead of the button on
> it; and the repeat is what the evidence says about how many times the
> block was done.

## `_healed`, [line 657](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L657): Comment

Code: `if workflow.repeat != found:`

> Set and cleared. A job whose repeat no longer holds -- re-mined,
> its evidence aged out, the doing it was read from gone -- goes back
> to a job that does one thing once rather than keeping a block nothing
> supports.

## `rekey_workflows`, [line 677](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L677): Comment

Code: `if any(cited not in by_id for cited in wanted):`

> Only over the whole evidence. A key recomputed over the survivors of
> a pruned batch would be shorter than the job -- and an empty one
> matches nothing, which is the duplicate this exists to prevent.

## `_grow`, [line 314](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L314): Comment

Code: `await decide(uow, tenant_id, stored, by_id)`

> The steps changed, so whether the job signs in or out is decided again, from
> the evidence of the steps it has now -- not copied from the proposal, and not
> carried by the whole-job save above, which never writes a stored job's
> verdict (F3). The healing pass would reach the same answer at the start of
> the next pass; a run in between would read a stale one, and R1 would offer a
> sign-in the grow had just made.

## `_one_pass`, [line 500](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L500): Comment

Code: `proposal.signs_in, proposal.signs_out = judged(proposal, everything) or (None, None)`

> Decided here for every job that survived the gates -- see `checks.signs_in`
> and `checks.signs_out` -- and decided again whenever a grow, a heal or a
> learn changes the steps (`chores.decide`). After `work_only`, which refuses the sign-in that moved
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

## `_one_pass`, [line 408](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L408): Comment

Code: `lands = {`

> Where each stored sign-in job signs in, for `resolve`: two jobs signing in
> to one system are one job whatever path they took (see `identity.resolve`).
> Only jobs already marked `signs_in`, and only while their evidence is held;
> a proposal adds itself below once it has been marked, so two proposals of
> one sign-in inside one pass fold too.

## `_mend`, [line 644](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L644): Note on the function

> One locked job: its steps healed and saved whole if they changed, then its
> verdict decided by `chores.decide` -- by the same rule as new jobs, and in both
> directions: a job stored before a verdict existed is decided here, and one
> whose evidence now says otherwise is corrected rather than left to a run.
> The verdict is never carried by the save: a whole-job save does not write a
> stored job's `signs_in` or `signs_out` (`SqlWorkflowRepository.save`).
> Counted once per job, whether its steps, its verdict or both changed. Each
> is logged by what it did: a heal names the steps, a decision (in
> `chores.decide`) names the verdict -- a job whose verdict alone changed is
> not reported as healed.

## `mining_lock`, [line 663](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L663): Note on the function

> The name of a tenant's mining lock (`AccountLocks.hold_named`), held by
> `mine` -- and so by the `fill_in_passwords` healing inside it, which saves
> whole workflows -- and by the sweep while it decides that tenant's jobs.
> A Postgres advisory lock, so it holds across workers; an in-process lock
> let two workers mine, heal and grow one tenant at once.

## `propose`, [line 115](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L115): Comment

Code: `day = [item.evidence for item in arrange(window.items)]`

> arrange() and not window.items directly. `pack` sorts the window into time
> order and every reader downstream depends on that -- checks.coverage
> slices it into TIME deciles, and its skew figure is only comparable across
> passes while those deciles mean the same thing. So the reordering happens
> here, at the one place the evidence becomes a prompt, exactly as
> algorithms.md's pseudocode has it: `chosen.sort(key=at)` upstream,
> `arrange(chosen)` at assembly.

## `fill_in_passwords`, [line 634](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L634): Note

Code: `for listed in await uow.workflows.known(tenant_id):`

> The listing is read without a lock, only to find the jobs that need healing.
> A job that does is read again under its row lock and healed from that read, so
> a `learn_field` that grew it meanwhile is saved with it, not overwritten by the
> listing's copy -- `save` writes the whole job, steps and all. Only the jobs
> that change are locked, so a pass that heals nothing holds no job's row across
> its model call.

## `learn_parameters`, [line 166](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L166): Note

Code: `stored = await uow.workflows.get(tenant_id, known_id, lock=True)`

> Locked: this read ends in a `save` of the whole job, and a job grown by
> `learn_field` between an unlocked read and that save lost its field step while
> its learned locators stayed renumbered -- the next run pinned those steps and
> drove a save with a field's locator.

## `_one_pass`, [line 348](../../../../../../../backend/src/sro/application/observation/mining_pass.py#L348): Comment

Code: `everything = {gesture.id: gesture for gesture in gestures}`

> Every gesture the tenant has, before this browser's own driving is left out
> of the window. A verdict is judged against this (`chores.judged`) for a new
> proposal and for a grow, as the heal and the sweep judge it: judged against
> the window instead, a Log Out followed by this browser signing back in read
> `False` in the pass and `True` at the next heal (F3 round 2, M1). Only the
> model's window and the pool lose our own driving.
