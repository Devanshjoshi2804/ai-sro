# Notes for `backend/src/sro/domain/execution/write_plan.py`

Comments and docstrings moved out of [`backend/src/sro/domain/execution/write_plan.py`](../../../../../../../backend/src/sro/domain/execution/write_plan.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/domain/execution/write_plan.py#L1): Docstring

> The call a step would send, re-aimed at this run's values.
>
> `plan_step` has always replayed a recorded call byte for byte: the payload it
> builds carries `call.request_body.text` and nothing puts the run's values into
> it. So a replay of `Create a Customer Type` created the customer type the
> DEMONSTRATION created -- `GGD`, every time, whatever the operator asked for.
> `value_for` exists and is called only on the `ui.perform` paths.
>
> This is the arithmetic that fixes it, and it is arithmetic rather than a model
> because the evidence settles it. Measured on the deployment's own store,
> 2026-09-15: the three real bodies of that job carry **46 keys each, the same
> key set every time, 44 of them byte-identical across all three**, and the two
> that differ are the two the operator typed. A body is a constant with slots in
> it, and the recording says which are which.
>
> **Two joins, and each catches what the other cannot.**
>
> The first is a diff, and it needs no names. A step cites the gestures that
> prove it, and a job demonstrated twice cites both doings -- step 6 of that
> workflow cites two gestures, one carrying `"customerType":"GGD"` and the other
> `"customerType":"GKB"`. The keys whose values differ between two bodies sent to
> the same endpoint are the keys the job varies. Nothing is inferred.
>
> The second decides which of the run's values goes in which slot, and it is the
> rule this codebase already applies in two other places -- `network_from_rig._bind`
> binds only where "value must be one of the seen values", and `shape.typed_at`
> joins a parameter to a gesture through `seen & put_by(gesture)`. A value binds
> to a slot only where it is one the operator was seen typing there.
>
> **The name join is refused, and the real body is the counter-example.** A
> parameter is named for its control (`control_name`: an ExtJS `itemId`, else the
> field label, else the target's name), so it arrives as
> `customertype-longDescription` while the body key is `longDescription`. A suffix
> match looks obvious and is already ambiguous on the only real body there is: it
> carries both `palletBuildingConsolidateBy` (the code the API stores, `""`) and
> `displayedPalletBuildingConsolidateBy` (the label the API ignores, `"Inherit
> from transport mode"`). A control ending `…ConsolidateBy` matches both, one of
> them writes and the other does nothing, and telling them apart needs a
> longest-match tiebreak on a correspondence nothing guarantees -- `item_id` is
> the page's vocabulary and a body key is the API's. That is a heuristic wearing
> arithmetic's clothes.
>
> **Every refusal is a refusal, never a guess.** Ambiguity in either direction, or
> a value this run supplied that no key carries, returns `None` -- and the step is
> performed through the interface exactly as it is today. The case that makes this
> matter is in the ledger's own notes: `csttyp truncates at 4 chars`, and the
> captured lifecycle shows a harness asking for `ZV9680` while the body goes out
> as `ZV96`. Where the form transformed what was typed, the typed value is not in
> the body, nothing binds, and a plan that quietly kept the demonstration's value
> would create the demonstration's record again. Refusing sends it to the
> interface, where it already works.
>
> **No template machinery.** `network_from_rig._bind` carries a `@@SRO-PARAM-{}@@`
> sentinel and `$`-escaping because the skill pipeline must STORE a template and
> render it months later, with `absent_as` and `unquoted_as` reconstructing an
> absence nobody kept. A run holds the body and the values in one stack frame and
> substitutes immediately, so none of that exists here. The rule is borrowed; the
> apparatus is not, and `absent_as`/`unquoted_as` must not be imported. The 28
> empty strings in that body are structurally unbindable -- `typed_values` drops
> an empty string, so no `seen_values` can contain one -- and they go out exactly
> as the form sent them, which is what the form sends for a box nobody touched.

## `WritePlan`, [line 19](../../../../../../../backend/src/sro/domain/execution/write_plan.py#L19): Docstring

> One call, ready for the wire, with this run's values in it.

## `WritePlan`, [line 23](../../../../../../../backend/src/sro/domain/execution/write_plan.py#L23): Note on the line above

Code: `filled: Mapping[str, str]`

> Body key -> the parameter whose value now sits there.
>
> What the result card reads back. `made_by`'s suffix rule cannot help on this
> endpoint -- the identifier is `customerType`, which ends in none of
> `id`/`code`/`name`/`number`/`key` -- but the plan already knows which keys
> this job varies, so those are the keys worth showing the operator, with
> whatever the warehouse echoed back in them rather than what was sent.

## `WritePlan`, [line 25](../../../../../../../backend/src/sro/domain/execution/write_plan.py#L25): Note on the line above

Code: `confirm: Mapping[str, str]`

> Body key -> the value this run put there, for the keys a read can settle.
>
> `filled` narrowed to the slots the demonstration's OWN answer gave back
> unchanged, which is the only honest set to check a read against.
>
> Measured over the 94 recorded creates whose request and response are both
> JSON objects (`knowledge-base/http/exchanges/*.jsonl`): **16 of them send a
> value that appears nowhere in the answer**, and they are one pattern. The
> form posts the CODE into a `…Description` key and the server stores the
> resolved LABEL -- `allocationAssetGroupDescription` sent `ZV9054` and came
> back `Any Handling unit for pallet movement`; `holdTypeDescription` sent
> `ZV86092` and came back `QA Hold`. The record is right; the field simply
> does not hold what was posted into it.
>
> A read-back that looked for `ZV9054` in such a record would find nothing and
> call a perfectly good create failed -- which stops the run and empties the
> job's register of verified effects. So a slot is compared only where the
> demonstration proves it is comparable.
>
> No name rule anywhere in this, deliberately. Matching `…Description` by its
> spelling is the same suffix heuristic the module docstring rejects for
> binding, and it is wrong for the same reason: `palletBuildingConsolidateBy`
> and `displayedPalletBuildingConsolidateBy` are the page's vocabulary, not a
> contract. The demonstration already shows which slots the server rewrites.

## `WritePlan`, [line 27](../../../../../../../backend/src/sro/domain/execution/write_plan.py#L27): Note on the line above

Code: `entry: VerifiedWrite`

> The ledger row this call is proven under. Kept so a reader of the run can
> see which watched endpoint authorised sending bytes instead of clicking.

## `seen_values`, [line 30](../../../../../../../backend/src/sro/domain/execution/write_plan.py#L30): Docstring

> Every value each declared parameter has been observed taking.
>
> The domain twin of `application.skill.from_rig.bindings_for`, and
> deliberately not shared with it: that one reads a model's raw answer and
> runs safe-naming and collision-dropping over it, while this reads a stored
> `Workflow` whose names already went through exactly that.

## `_same_endpoint`, [line 45](../../../../../../../backend/src/sro/domain/execution/write_plan.py#L45): Docstring

> Whether two calls are the same write, so their bodies may be diffed.
>
> Method and origin and path. The query is left out for `verified_write_for`'s
> reason: a write does not become a different endpoint because one recording
> carried `?siteId=SG` and the next did not.

## `_bodies_of`, [line 53](../../../../../../../backend/src/sro/domain/execution/write_plan.py#L53): Docstring

> Every demonstration of this step's write, as parsed JSON objects.
>
> One per cited gesture that produced a call to the same endpoint. A job
> demonstrated once yields one, which is the honest answer: with a single
> doing nothing distinguishes a slot from a constant, and the diff below
> returns nothing rather than guessing.

## `_record`, [line 74](../../../../../../../backend/src/sro/domain/execution/write_plan.py#L74): Docstring

> One recorded body as the record it describes, envelope removed.
>
> Blue Yonder answers a create with `{"@type": "ResponseBodyWrapper",
> "data": {…}}`, which `verify.made_by` unwraps for the same reason: read at
> the top level the answer has no fields of the record in it at all.

## `_echoed`, [line 87](../../../../../../../backend/src/sro/domain/execution/write_plan.py#L87): Docstring

> The keys the server gave back exactly as they were sent, every time.
>
> Asked of the demonstrations' own answers, which is the only place the
> question can be settled without a rule about names. A key the server
> rewrites -- a `…Description` that stores the label for the code posted into
> it -- is one no later read can be checked against, because the record will
> never hold what was sent however correct it is.
>
> `all`, not `any`, and over the demonstrations that answered at all: one
> doing that echoed a key proves nothing if another rewrote it.
>
> `None` where NO demonstration answered, and that distinction is the whole
> care of this function. A capture with no response body is not evidence that
> the server rewrites anything -- absence of evidence about a slot is not
> evidence about the slot -- so the caller then checks every slot it filled,
> which is no weaker than the whole-body search this replaced and keeps the
> belt that catches a truncated code. An empty SET is a different fact: the
> demonstrations answered and agreed on nothing, so there is nothing a read
> could settle.

## `_returned`, [line 105](../../../../../../../backend/src/sro/domain/execution/write_plan.py#L105): Docstring

> The keys the record came back HOLDING, whatever value they held.
>
> `_echoed`'s weaker sibling, and the right question for a slot no
> demonstration filled. That one asks whether the server gave a key back
> unchanged, which is the test for trusting a value without looking. This
> asks only whether the key is IN the record the server returned -- which is
> what makes a read-back able to check it afterwards.
>
> The difference is not academic and it is not small. Measured on this
> deployment's own create, 2026-09-19: **46 keys sent, 43 in the record, 15
> echoed unchanged.** The 28 that disagree are the boxes nobody touched --
> sent as `""` and stored as `null` -- so the echo test excludes precisely
> the fields a request might name and a demonstration never filled, which is
> every field item 4 exists for.
>
> A key present in the record is a key the server acknowledges. Whether it
> accepted THIS value is a different question, and it is the one the
> read-back answers at run time -- and fails the step on.
>
> `all`, and `None` where no demonstration answered, both for `_echoed`'s
> reasons: one doing that returned a key proves nothing if another did not,
> and absence of evidence about a slot is not evidence about the slot.

## `_slots`, [line 128](../../../../../../../backend/src/sro/domain/execution/write_plan.py#L128): Docstring

> The keys the job varies: present in every doing, differing in at least one.
>
> `present in every doing` matters as much as `differing`. A key one recording
> carried and the next did not is a form that changed between them, not a
> value somebody typed, and substituting into it would send a field the
> demonstration never proved.

## `wanted_by`, [line 157](../../../../../../../backend/src/sro/domain/execution/write_plan.py#L157): Docstring

> The parameters whose values this step's own body carries.
>
> Asked WITHOUT the run's values, which is the whole point of it: the
> question "does this call need a value from this run" has to be answerable
> before anybody knows whether the run has one. `_assigned` answers a
> narrower question -- which parameter owns which slot, given what this run
> was given -- and it cannot see a parameter the run is missing, because a
> parameter with no value never appears in `values` to be matched.
>
> That blind spot is what let a run with NO values replay a demonstration
> byte for byte: every guard downstream asked "were we given values we could
> not place", and a run given nothing has none to fail to place.
>
> Empty for a call that carries no parameter at all -- most calls -- which is
> what keeps this from turning every replay into a click.

## `_assigned`, [line 180](../../../../../../../backend/src/sro/domain/execution/write_plan.py#L180): Docstring

> Which parameter owns which slot, or None where that is not a fact.
>
> A parameter claims a slot when every value that slot has been seen taking is
> one the operator was seen typing into that parameter's control. Two
> refusals, both of them silence rather than a guess: a slot two parameters
> claim, and a parameter claiming two slots.

## `write_plan_for`, [line 261](../../../../../../../backend/src/sro/domain/execution/write_plan.py#L261): Docstring

> The call this step would send with this run's values in it, or None.
>
> `None` is not a failure. It is this module declining to answer, and every
> caller reads it the same way: perform the step through the interface, which
> is what happens today and what has always happened.

## `_path_owner`, [line 331](../../../../../../../backend/src/sro/domain/execution/write_plan.py#L331): Docstring

> The parameter this write's last path segment IS, where the doings prove it.
>
> `DELETE /data/WM/wm/customerTypes/MRN5`, then `.../DDLS`, then `.../ZQ46`:
> six demonstrations of `Delete a Customer Type` on the deployment, every one
> answered 200, and every last segment a value the operator typed into the
> job's one parameter. That is the binding, read off the evidence the same way
> `_assigned` reads a body slot -- a parameter owns the segment when every
> value the segment was seen taking is one it was seen taking.
>
> Two doings at least, with different segments: one proves nothing about
> what varies. Only answered calls that succeeded, because a demonstration
> that got a 404 demonstrated the wrong record. Every other segment must be
> the same across them, so this can only ever name the LAST one.

## `_path_plan`, [line 364](../../../../../../../backend/src/sro/domain/execution/write_plan.py#L364): Docstring

> The recorded call with this run's value where the demonstration's was.
>
> Nothing to read back afterwards, deliberately: `confirm` is empty, so
> `verify` holds it on the status -- and for a url that NAMES the record, a
> 2xx is the server saying which record it acted on.

## `demonstrated_writes`, [line 389](../../../../../../../backend/src/sro/domain/execution/write_plan.py#L389): Docstring

> The endpoints this job's OWN demonstrations proved, for this job alone.
>
> The ledger admits an endpoint once a run of ours watched it succeed, which
> no run of a job can do while the job cannot finish by the interface --
> `Delete a Customer Type` failed at its filter box for a day with six
> recorded, answered `DELETE`s in its evidence and nothing in the ledger.
>
> Narrow on purpose, and only the one shape the evidence makes airtight: a
> write whose last path segment `_path_owner` proves IS the job's parameter.
> The pattern is the literal path with that one segment as `{id}`. Nothing
> is stored; the tuple is added to this run's ledger and gone with it, so
> one job's demonstrations never license another job's call.

## `_undemonstrated`, [line 405](../../../../../../../backend/src/sro/domain/execution/write_plan.py#L405): Docstring

> Values for slots no demonstration varied, and only the provable ones.
>
> Four refusals, and each is the difference between filling a form and
> inventing an API.
>
> **A slot the body already sends.** Adding a key no recorded body carried is
> this system deciding what the endpoint accepts, from a dictionary that
> describes a screen. The form posts every field it has; a box nobody touched
> goes out as the empty string, and filling that is editing a request rather
> than composing one.
>
> **Or one a confirmed write learned** (`learned`, K1). That key is not a
> guess from a dictionary: the page's own call sent it on a write that was
> confirmed done, and `with_field` kept it as the parameter's `body_key`.
> The exemption belongs to that name alone (`learned.get(name) == slot`): a
> dictionary name that happens to map to the same key gets none of it. It
> still has to pass the next refusal: a learned slot the recorded response
> never names cannot be read back, and a write carrying it would be in doubt
> by construction -- so the plan declines rather than send it.
>
> **Not a slot the evidence already binds.** `_assigned` decided those from
> what the operator was seen typing, which is stronger than a declaration.
>
> **Only a slot the record comes back holding.** This is item 5 and it is the
> reason item 4 is safe at all: nothing demonstrated this slot, so a status
> proves nothing about it -- the request went and the field may have been
> ignored, renamed or silently dropped. A key the server returns is one a
> read-back can check; one it never returns cannot be checked at all, and a
> value written where nobody can confirm it is exactly the wrong record this
> whole ladder exists to prevent.
>
> Returned, and deliberately not ECHOED. The echo test asks whether a value
> came back unchanged, which is the test for trusting one without looking --
> and 28 of the 46 keys in this deployment's create are boxes nobody touched,
> sent as `""` and stored as `null`, so it would exclude exactly the fields
> this is for. Whether the server accepts THIS value is what the read-back
> answers, and fails the step on.
>
> **And never where the demonstrations answered nothing at all.** `None` is
> "no evidence about the record's shape", which is not evidence about it.

## `begins_again_at`, [line 430](../../../../../../../backend/src/sro/domain/execution/write_plan.py#L430): Docstring

> Where a run has to start over so the screen the stopped step needed is
> there again.
>
> A run that came up short of a value ends in front of a half-filled form.
> Resuming at the step that stopped re-types one field into whatever is on
> the screen a minute later -- which is right if the form is still open, and
> wrong every other way it can go: the operator navigated off it, the session
> timed out, the page reset. The step then acts on a screen that is not the
> one it was recorded against.
>
> So the run goes back to the beginning of the block that BUILT that screen:
> the first step after the last write before it. Everything from there to the
> stopped step is scaffolding and keystrokes -- pressing Add, opening a tab,
> typing into a form nothing has posted yet -- and re-performing it rebuilds
> the form the value is going into.
>
> **Nothing in that stretch wrote, and that is the whole safety argument.**
> The partition is at the last write precisely so a resumed run cannot
> re-perform one: a write that went out and may have landed is not a step to
> try again, and this returns a step strictly after every write the run
> performed. The same rule, and the same reasoning, as `scaffolding_for` --
> which is why they compute the same boundary and sit next to each other.
>
> `stopped_at` itself where there is nothing before it to rebuild from, which
> is a run that stopped on its own first step.

## `scaffolding_for`, [line 442](../../../../../../../backend/src/sro/domain/execution/write_plan.py#L442): Docstring

> The steps whose only job was to put the write's form on the screen.
>
> Measured on the deployment's own row: of the six steps of `Create a Customer
> Type`, only step 6 changes warehouse state. Steps 4 and 5 -- typing the code
> and the description -- make no network call at all; they are keystrokes into
> a form that step 6 posts. Step 2's thirty-four GETs are the screen loading.
> Replay the write and there is nothing left for the other five to do.
>
> Partitioned at the previous write rather than taken from the top, and that
> is what makes it right for a job with more than one write in it: a field
> typed at step 4 whose value leaves in a call fired at step 5 makes step 5 a
> write, so step 4 feeds step 5 and is collapsed only when step 5's own write
> is being replayed too.
>
> Nothing after the write is scaffolding, and a step that types a password
> never is -- its value was struck out of the evidence, so no replayed body
> can be carrying it.

## `wanted_by`, [line 165](../../../../../../../backend/src/sro/domain/execution/write_plan.py#L165): Comment

Code: `owner = _path_owner(step, by_id, call, seen)`

> And the one its PATH carries. A delete names its record in the url and
> sends no body at all, so a guard that only read bodies let a run holding
> no value replay the demonstration's own `DELETE .../customerTypes/MRN5`.

## `wanted_by`, [line 174](../../../../../../../backend/src/sro/domain/execution/write_plan.py#L174): Comment

Code: `claiming = [name for name, observed in seen.items() if _seen_in(taken, observed)]`

> The same claim `_assigned` makes, minus the run's values: a parameter
> owns a slot when every value that slot was seen taking is one the
> operator was seen typing into that parameter's control. Compared without
> case or edge spaces (`_seen_in`): the form upper-cases what was typed, so
> greyorange's recorded `NEW` is the `new` typed into Department. And one
> recorded body is enough (`_slots`): the seen values are what was typed, so
> a field holding one is a slot, not a constant (ruling 2026-09-28 -- a
> Create a Customer Type recorded once left its proven POST unplanned).

## `_assigned`, [line 188](../../../../../../../backend/src/sro/domain/execution/write_plan.py#L188): Comment

Code: `placed: set[str] = set()`

> Every parameter that turned out to have somewhere to go, which is not the
> same list as `claimed.values()` once two of them name one slot.

## `_assigned`, [line 196](../../../../../../../backend/src/sro/domain/execution/write_plan.py#L196): Comment

Code: `if len({values[name] for name in owners}) > 1:`

> Two parameters claiming one slot is a refusal only when they
> DISAGREE.
>
> This job declares four parameters for two values: `Customer Type` and
> `customertype-customerType` are the same thing under the label the
> operator reads and the key the form posts, and mining named both.
> Both then claim `customerType`, and refusing on the count alone made
> the write unreplayable for every run that supplied them -- which is
> every run the gather fills, because it answers for each parameter the
> job declares. Measured on the deployment 2026-09-16: the replay was
> refused, the ladder fell to a model, and the model pressed Save on a
> form that run had never filled.
>
> Two names for one value is not ambiguity. Two values for one slot is,
> and it still refuses: there is no way to tell which the operator
> meant, and a warehouse record is the wrong place to guess.

## `_assigned`, [line 213](../../../../../../../backend/src/sro/domain/execution/write_plan.py#L213): Comment

Code: `carried = {values[name] for name in placed}`

> Every value this run was given must have somewhere to go. A parameter the
> operator supplied that no key carries is the transformed-value case, and
> sending the body without it would send the demonstration's value in its
> place -- silently, because the endpoint answers 201 either way.
>
> Unless it is the SAME value that already went somewhere. Measured on the
> deployment 2026-09-16: mining declared this job's two fields four times
> -- `Customer Type`, the label an operator reads, beside
> `customertype-customerType`, the key the form posts -- and the gather
> answers for every parameter a job declares, so a run arrives holding four
> values for two slots. Two of them are placed and two are the same strings
> under another name, and refusing on that made the write unreplayable for
> every gathered run: the ladder then fell to a model, and the model
> pressed Save on a form that run had never filled.
>
> A value that equals one already in the body is carried, whatever it is
> called. A DIFFERENT value with nowhere to go is still the transformed
> case and still refuses -- that is the one this rule was written for.

## `_assigned`, [line 214](../../../../../../../backend/src/sro/domain/execution/write_plan.py#L214): Comment

Code: `if any(`

> `elsewhere` is the names that have a DECLARED slot to go to, which is the
> other half of "must have somewhere to go". A value that binds to a
> dictionary-named key is not a value with nowhere to go, and refusing the
> whole plan for it would mean a request naming one extra field falls back
> to the interface for every field -- the opposite of what naming it was
> for.

## `write_plan_for`, [line 278](../../../../../../../backend/src/sro/domain/execution/write_plan.py#L278): Comment

Code: `if any(`

> A step that types a password is not a step whose body this holds: the
> recorder struck the value out at the boundary, so there is nothing to
> substitute and `unreplayable` would already have refused a body carrying
> the marker. Belt and braces, and cheap.

## `write_plan_for`, [line 287](../../../../../../../backend/src/sro/domain/execution/write_plan.py#L287): Comment

Code: `return _path_plan(step, by_id, call, values, seen, entry)`

> No JSON body to aim. A form-encoded write is replayable byte for byte
> and this module has nothing to add to it, so it declines and the
> existing path sends it as it was recorded -- unless the value this
> run was given lives in the path, which is what a delete is.

## `write_plan_for`, [line 294](../../../../../../../backend/src/sro/domain/execution/write_plan.py#L294): Comment

Code: `also = _undemonstrated(`

> Worked out BEFORE the assignment, because the assignment has to know
> about it: a value with a declared slot to go to is not a value with
> nowhere to go, and refusing the whole plan for one would send every field
> through the interface because a request named one extra.
> `_returned` and not `_echoed`: the echo test is for trusting a value
> without looking, and this is the opposite -- a slot that will be looked
> at. See `_returned`, which carries the measurement.

## `write_plan_for`, [line 302](../../../../../../../backend/src/sro/domain/execution/write_plan.py#L302): Comment

Code: `named = frozenset(keys) | {name for name, slot in learned.items() if slot in also}`

> Every name with a declared slot, not only the ones actually filled -- but a
> LEARNED name only once its slot is filled. A learned key the recorded body
> lacks is not the empty string the form sends; left out, the field is simply
> missing, so a learned value `_undemonstrated` refused (the response never
> names the key) is a value with nowhere to go, and the plan declines (K1).
>
>
> "Every value must have somewhere to go" exists for the TRANSFORMED case:
> a value that should have gone into a varied slot and did not means the
> demonstration's value goes out in its place, silently, because the
> endpoint answers 201 either way. A field the dictionary names is not that
> case -- nothing is being substituted for it, the slot goes out as the
> empty string the form sends for a box nobody touched -- and refusing the
> whole replay for it would send every field through the interface, which
> cannot set that field either. The cost would be paid for nothing.

## `write_plan_for`, [line 306](../../../../../../../backend/src/sro/domain/execution/write_plan.py#L306): Comment

Code: `if not claimed:`

> Nothing to aim, which is not the same as a plan that changes nothing.
> A job with no parameters -- or a write carrying none of them -- has to
> replay BYTE FOR BYTE, and a plan built here would re-serialise the
> body instead: `{"a":1}` recorded goes out as `{"a": 1}`, different
> bytes for no reason and wrong outright for a body anything signs.
>
> Worse than the bytes, it would set `rewrote`. `verify` reads that as
> "the status no longer proves the demonstrated effect" and demands a
> read-back -- so a job nobody parameterised would stop asking for
> evidence it was never going to have, for a body nobody rewrote.

## `write_plan_for`, [line 310](../../../../../../../backend/src/sro/domain/execution/write_plan.py#L310): Comment

Code: `aimed = {key: value for key, value in bodies[0].items() if key not in left_out}`

> Without the keys of parameters nobody gave (`_owned_by_nobody_given`):
> the recorded value there is somebody else's, and an optional field the
> run leaves out is left out of the call, not filled from the recording.
>

> And the fields nobody demonstrated, where the record can be made to prove
> them.
>
> A job's slots are what two doings proved VARY, and the form posts far
> more than that -- 46 keys, 44 of them byte-identical across all three
> bodies. So a request naming `Department: Inbound` has named a slot this
> write already sends, as the empty string the form sends for a box nobody
> touched, and the value had nowhere to go.
>
> `keys` is `field_notes.keys_named`: the declared label-to-key join, with
> its own refusals. Not the suffix match this module argues against at
> length -- that argument is about INFERRING a correspondence from two
> strings, and this is reading one somebody wrote down.

## `write_plan_for`, [line 325](../../../../../../../backend/src/sro/domain/execution/write_plan.py#L325): Comment

Code: `**also,`

> Unconditionally, which is the whole of what makes the binding
> above safe: a slot no demonstration exercised has to PROVE it
> landed rather than be trusted to a status. `_undemonstrated`
> refuses any slot that cannot be read back, so everything here is
> provable by construction.

## `_path_plan`, [line 377](../../../../../../../backend/src/sro/domain/execution/write_plan.py#L377): Comment

Code: `if verified_write_for(replace(call, url=url), (entry,)) is None:`

> Matched against the same ledger entry again: a value that decodes to a
> traversal is refused by `verified_write_for`, never sent.

## `_owned_by_nobody_given`, [line 222](../../../../../../../backend/src/sro/domain/execution/write_plan.py#L222): Note

> The slots whose one owning parameter (by the values it was seen to take)
> was not given this run. Their keys are dropped from the replayed body, the
> API half of the rule that an absent optional value is never filled from
> the recording.

## `write_plan_for`, [line 288](../../../../../../../backend/src/sro/domain/execution/write_plan.py#L288): Note

Code: `owner = _path_owner(step, by_id, call, seen)`

> A body write whose path also names a parameter replays the recorded path.
> When that parameter was not given, the recorded id would be sent, so the
> write is not replayed at all.

## `_taken`, [line 149](../../../../../../../backend/src/sro/domain/execution/write_plan.py#L149): Note

> The values a slot held across the doings, as the text `seen_values` holds
> them: a string as itself, any other JSON scalar (number, bool, null) as its
> JSON text, so `10` reads as `"10"` and `true` as `"true"`. The one
> reading `wanted_by`, `_assigned` and `_owned_by_nobody_given` share, so a
> numeric slot is owned by its parameter like a string one -- and dropped from
> the body when that parameter was not given, rather than sent with the
> demonstration's number.

## `_assigned`, [line 198](../../../../../../../backend/src/sro/domain/execution/write_plan.py#L198): Comment

Code: `if owners and not isinstance(bodies[0][slot], str):`

> A given value is text; the slot it owns was recorded as a number, a bool or
> null. Putting the text in would change the slot's JSON type, and the
> read-back compares by equality, so the replay is refused and the step goes
> through the interface, as it did before non-string slots had owners.
> ponytail: refusal, not coercion; parse the value back to the recorded type
> when a numeric write needs the API lane.

## `learned_slots`, [line 237](../../../../../../../backend/src/sro/domain/execution/write_plan.py#L237): Docstring

> The keys learned fields put into this write's body: `{parameter: body_key}`.
> A field step learned by X10 cites nothing and fills one parameter, and
> `with_field` inserts it directly before the write it feeds, so the walk goes
> back from the write over exactly those steps and stops at the first step that
> is not one. A parameter whose slot was taken out (`"slot": False`,
> `without_slots`) is walked over but not taken.
