# Notes for `backend/src/sro/application/execution/plan_step.py`

Comments and docstrings moved out of [`backend/src/sro/application/execution/plan_step.py`](../../../../../../../backend/src/sro/application/execution/plan_step.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/execution/plan_step.py#L1): Docstring

> The model call that turns one step of a demonstrated job into one command.
>
> Ported from `plan_step` and `plan_by_sight` in
> `new_agent_arch/src/rig/planner.py`. The pure half -- the schemas, the words,
> the value rule and the replayability rule -- is
> `sro.domain.execution.planning`, and the locator ladder is
> `sro.domain.execution.evidence`; this is the half that asks a model and
> assembles the payload.
>
> The model answers a small shape -- which kind of command, which action, which
> value, which url -- and this assembles the rest. The locators never come from
> the model: they are built from the cited evidence, and the extension tries them
> in order. What the model decides is only what to do with them, and it is told
> to prefer driving the interface over replaying a call.
>
> That preference was measured, not assumed. Blue Yonder signs every write with a
> `CSRF-ENCRYPT-TOKEN` header and the rig strikes it out at its boundary:
> `sro.domain.recording.sensitivity` is the rule that classifies it, and
> `test_an_http_plan_replays_the_recorded_call_with_redacted_headers_dropped` is
> what holds this module to it. An `http.send` replaying the recorded call would
> send the marker as its token and be refused; clicking Save lets the page mint
> its own. So `http.send` is for a step whose evidence carries a call and no
> usable target -- and a struck-out header is never sent as its marker under
> any plan.
>
> One narrow exception, and it is opt-in per call: `verified_writes` -- see
> `sro.domain.execution.verified_writes` -- is a ledger of `(method, path)`
> pairs this deployment has individually watched succeed, edit, verify, revert.
> For a call that matches one, a header the extension itself has a live source
> for (today, only `CSRF-ENCRYPT-TOKEN`) is named in the plan's `live_headers`
> rather than left off; the extension fetches the value off the page it is
> already in, and it is never carried on the wire from here. Everything else --
> an unverified call, or a header the extension has no live source for -- keeps
> the rule above exactly as it was.
>
> An instance count of those headers used to stand here in place of the name. It
> was taken over a capture store that was a scratchpad and is gone, nothing in
> this repository reproduces it, and the rule does not rest on it -- so it is the
> header and its guard that are cited instead.

## module, [line 40](../../../../../../../backend/src/sro/application/execution/plan_step.py#L40): Note on the line above

Code: `SecretFor = Callable[[str], Awaitable[str | None]]`

> Where a password comes from when a step types one: the vault, by key.
>
> A callable rather than the vault itself, so this module -- which builds one
> command out of one step -- does not learn what a vault is. `run_workflow` holds
> the real one; a run with no vault configured passes nothing, and a step that
> needs a password says so rather than typing a blank.

## module, [line 42](../../../../../../../backend/src/sro/application/execution/plan_step.py#L42): Note on the line above

Code: `ACTIONS: frozenset[str] = frozenset(get_args(Kind))`

> What a `ui.perform` may ask for: the gesture kinds the recorder records, and
> no others. One list, because a plan the extension is asked to perform is a
> gesture the recorder could have seen -- `PLAN_STEP`'s schema offers the model exactly
> these, and `test_the_actions_offered_are_the_actions_accepted` fails if the two
> ever part.

## module, [line 44](../../../../../../../backend/src/sro/application/execution/plan_step.py#L44): Note on the line above

Code: `VALUED = ("type", "select", "upload", "press")`

> The actions that carry a value. A click types nothing.

## `_replay_of`, [line 47](../../../../../../../backend/src/sro/application/execution/plan_step.py#L47): Docstring

> The recorded call as a payload, re-aimed at this run's values, and the
> plan that aimed it. `None` where it must not go out as it stands.
>
> Two refusals, and they are different failures. A call is `unreplayable`
> when its recorded bytes cannot be sent at all. A call is un-AIMABLE when
> this run was given values, the call is one the ledger has watched succeed,
> and `write_plan_for` could not work out which of its fields the values
> belong in -- sending it then would send the DEMONSTRATION's values, so the
> operator asks for `GPDP` and the warehouse is told `GGD` and answers 201
> for it.
>
> Gated on the LEDGER, and that is what makes the second refusal narrow
> enough to be right. A run holds its values for the whole job, so "this run
> has values" says nothing about whether a given call carries any of them,
> and refusing on that alone turned every replay into a click. It also
> catches what inspecting the body cannot: the ledger's own gotcha is
> `csttyp truncates at 4 chars`, so the operator typed `ZV9680`, the body
> went out as `ZV96`, and no value in the body equals anything anybody was
> seen typing.
>
> Both callers are here -- the model's `http.send` and the replay the
> evidence decides on its own -- so what goes on the wire cannot differ by
> who asked for it.

## `replay_without_asking`, [line 84](../../../../../../../backend/src/sro/application/execution/plan_step.py#L84): Docstring

> The one command a step can be planned without asking anybody.
>
> The evidence says which call the step made, `write_plan_for` says where
> this run's values go in it, and the ledger says this deployment has already
> watched that `(method, path)` succeed. Nothing is left for a model to
> decide, so nothing is asked -- and that is worth more than the vision call
> it saves. A step planned by a model is planned again from scratch every
> run: the same job sends `http.send` on Tuesday and clicks Save on
> Wednesday, and the one step that changes warehouse state is the one where
> that matters. Deterministic where the evidence is complete, a model only
> where it is not.
>
> Narrow on purpose. Only a call already in the ledger, which is the same
> gate `live_headers` sits behind -- and the same reason: an unverified write
> replayed from a recording sends a struck-out `CSRF-ENCRYPT-TOKEN` and is
> refused, so the module's standing preference for driving the interface is
> exactly right for every call this does not cover.
>
> The rescue still asks. A replay that failed by status is precisely when
> clicking Save is the right next move, and `run_workflow` puts this first in
> the ladder rather than in place of it.

## `_a_cascade`, [line 119](../../../../../../../backend/src/sro/application/execution/plan_step.py#L119): Docstring

> Whether the doing this call came from wrote more than once.
>
> **One logical create is often several physical resources.** Creating a
> client on the real platform fires four POSTs behind one Save -- addresses,
> clients, clientWarehouse, packingConfigurations -- each carrying an id the
> one before it returned (`knowledge-base/KNOWLEDGE-BASE.md` 3b, watched on
> the live host). A replay sends ONE call. The record it makes is the first
> of four, the status says 201, the belts agree, and the run reports `held`
> over half a client.
>
> Measured on this machine's store, 2026-09-19, over every mined job of three
> tenants: four steps stand on a doing that wrote twice. `new`'s `Create a
> Supplier` step 13 is the cascade proper -- `PUT /wm/addresses/{id}` then
> `POST /wm/suppliers` -- and acme's `Create a Carrier Cross Reference` and
> `Create a Work Operation` each POST twice into one collection, which is two
> records from one press.
>
> So the replay refuses and the ladder behind it clicks Save, which is what
> the page is for: the page fires the whole cascade, in order, with the ids
> it just received. Nothing is lost -- the deterministic path is an
> optimisation over a step that already worked through the interface.
>
> Counted per DOING and never across the step's cites. A step cites one
> gesture per demonstration, so counting every cited call reads two doings of
> one write as a cascade -- which on this store would have refused eight
> steps instead of four, including the one this deployment runs live.
>
> Only writes the LEDGER recognises. A page also fires keepalives, telemetry
> and performance beacons from the same click -- `sessionKeepAlive` and
> `webPerformanceEntries/batch` are in this evidence -- and a rule that
> counted those would refuse every real write on the platform.

## `_primary`, [line 126](../../../../../../../backend/src/sro/application/execution/plan_step.py#L126): Docstring

> The gesture this step is planned from.
>
> `primary_gesture` prefers one the extension can act on and so skips a
> scroll -- but a step citing nothing else is not a step to give up on, and
> falls back to the first cited gesture rather than planning nothing.
>
> Told which names the run holds a value under, so a step that types into a
> control this run has a value for is aimed at that typing. A blank is not a
> value, for `typed_values`' reason.

## `_ladder`, [line 132](../../../../../../../backend/src/sro/application/execution/plan_step.py#L132): Docstring

> The demonstration's ladder, with what a run learned on top.
>
> Never instead: the recorded identity stays underneath, because a page that
> is repaired tomorrow should go back to being found the strong way, and a
> learned locator that has itself gone stale is one rung that misses rather
> than a step with nothing to try.

## `_clicking`, [line 140](../../../../../../../backend/src/sro/application/execution/plan_step.py#L140): Docstring

> A click on the control this ladder names, carrying no value.

## `_option_named`, [line 351](../../../../../../../backend/src/sro/application/execution/plan_step.py#L351): Docstring

> The row this step's demonstration chose, said for THIS run's value.
>
> A filter box does not offer its options by the value alone. Measured on
> the deployment 2026-09-22: typing `NWTS` offered `NWTS in Customer Type`,
> `NWTS in Description` and two more, and the demonstration clicked the
> first -- an `li` with `role=option` whose whole text is that sentence.
>
> So the row cannot be found by the value: a text match on `NEX` finds the
> GRID's own cell instead, clicks it, and opens the record rather than
> filtering to it. That is what happened at 15:57, on the first run after
> this compound shipped.
>
> The demonstration carries the template. Its option said
> `<what was typed> in Customer Type`, so the recorded value is replaced
> with the one this run was given and the rest is the page's own wording,
> never invented here. Empty where the step shows no list, or where the
> recorded option does not contain what was recorded as typed -- both are
> cases this cannot write a name for, and a guessed name clicks something
> nobody demonstrated.
>
> Ext's own xtype for the list is `boundlist`; an application subclassing it
> keeps the word, and this deployment's is `rpBoundList`. Matched on the
> ending so both answer, and on the component rather than the DOM, because a
> bound list renders as anonymous divs with generated ids.

## `_point_on`, [line 370](../../../../../../../backend/src/sro/application/execution/plan_step.py#L370): Docstring

> A point the model gave, if it is inside the picture it was shown.
>
> Off the viewport is a guess, and this rung's whole rule is that it does not
> guess: the picture IS the viewport, so a point outside it was not seen.

## `plan_by_sight`, [line 379](../../../../../../../backend/src/sro/application/execution/plan_step.py#L379): Docstring

> The rung below the locator ladder: find the control by looking.
>
> Asked once, after both evidence rungs missed with `control_not_found`, and
> only with a picture to look at. The answer is a point, sent as
> `ui.perform_at`; the runner records the step matched by sight and marks the
> job stale, the same instinct as `css_path` catching what `component` and
> `role_and_name` missed -- one rung lower down.

## `_replay_of`, [line 64](../../../../../../../backend/src/sro/application/execution/plan_step.py#L64): Comment

Code: `if verified and wanted and not any(values.get(name, "").strip() for name in wanted):`

> And the same refusal for a run that was given NOTHING.
>
> The guard above asks "were we handed values we could not place", which a
> run holding none can never fail -- so the one case where replaying the
> recording is most certainly wrong was the one case it let through.
> Measured on the deployment 2026-09-16: an operator pressed a card, the
> gather came back empty because the model answered one round with a 5xx,
> and the run replayed the demonstration's own body -- the code somebody
> typed days ago, into a warehouse, as if it had been asked for today.
>
> `wanted_by` asks the question without the values: which parameters does
> THIS call's body carry. A call that carries none still replays exactly as
> it was demonstrated, which is what most calls are and what they have
> always done.
>
> Refused when NONE of them was given. When some were, the replay goes out
> with those and without the rest: `write_plan_for` drops the body key of
> every parameter nobody gave, and refuses a call whose path names one, so
> an absent optional value is never sent from the recording (§6.6.6).

## `_replay_of`, [line 66](../../../../../../../backend/src/sro/application/execution/plan_step.py#L66): Comment

Code: `recorded = call.request_body.text if call.request_body else None`

> `aimed` where there is one, and the recorded bytes where there is nothing
> to aim -- a job with no parameters replays exactly as it was
> demonstrated, which is what it has always done and what most calls still
> are.

## `_replay_of`, [line 69](../../../../../../../backend/src/sro/application/execution/plan_step.py#L69): Comment

Code: `"url": aimed.url if aimed is not None else call.url,`

> The plan's url where there is a plan: a delete's value is in its
> path, and the recording's url names the demonstration's record.

## `_replay_of`, [line 73](../../../../../../../backend/src/sro/application/execution/plan_step.py#L73): Comment

Code: `if verified:`

> A struck-out header is not sent as its marker -- that much holds for
> every call. For a call this deployment has individually watched succeed,
> a header the extension itself knows a live source for is asked for
> instead of being left off: dropping `CSRF-ENCRYPT-TOKEN` sends a Blue
> Yonder write the app will refuse before routing it, the third 404 shape
> `knowledge-base/KNOWLEDGE-BASE.md` names. Named, not sent: the extension
> fetches the value itself, off the page it is already in, and it never
> reaches the backend at all.

## `replay_without_asking`, [line 106](../../../../../../../backend/src/sro/application/execution/plan_step.py#L106): Comment

Code: `payload["starts_on"] = starts_on`

> The page this call may open a tab at, and only ever for the run's
> first command -- `run_workflow` passes it for that one alone.
>
> An `http.send` never carried this before because it never needed to:
> the steps that walked the browser to the form ran first and left a
> tab on the origin. A job whose write goes out as a call performs none
> of them, so this IS the first command, and the session it needs lives
> in that origin's cookies. `opensFor` in `commands.js` still refuses a
> `starts_on` naming another system, so this can only open the page the
> call is going to.

## `plan_step`, [line 184](../../../../../../../backend/src/sro/application/execution/plan_step.py#L184): Comment

Code: `"step_page": (primary.page_url or primary.url) if primary else None,`

> The real page, not `trim()`'s starred path shape: a step deep in a
> job was demonstrated on a specific screen, and the planner can only
> say "navigate there first" if it is told where there is.

## `plan_step`, [line 186](../../../../../../../backend/src/sro/application/execution/plan_step.py#L186): Comment

Code: `"previous_attempt_left": None`

> The rescue sees two pictures: the page now (first image) and the
> page the failed attempt left behind (second), named here so the
> model knows which is which.

## `plan_step`, [line 191](../../../../../../../backend/src/sro/application/execution/plan_step.py#L191): Comment

Code: `"screenshot": None`

> Named by position: second when the page as it is now was
> photographed too, the only image when it was not.

## `plan_step`, [line 197](../../../../../../../backend/src/sro/application/execution/plan_step.py#L197): Comment

Code: `ensure_ascii=False,`

> The redaction marker is «redacted»; the default ensure_ascii would
> write it into the prompt in a form nothing else in this system uses.

## `plan_step`, [line 232](../../../../../../../backend/src/sro/application/execution/plan_step.py#L232): Comment

Code: `payload["starts_on"] = starts_on`

> Same as the deterministic replay below, and for the same
> reason. `run_workflow` passes this for the run's FIRST
> command only, so a model that chooses a call for the step a
> run begins at can open the page it needs -- a resumed run
> lands on one of those, and without this it answers
> `no_tab_for_origin` to an operator who has no tab there.

## `plan_step`, [line 243](../../../../../../../backend/src/sro/application/execution/plan_step.py#L243): Comment

Code: `why = f"recorded call is not replayable; {why}"`

> Falls through to the ui.perform below rather than returning
> "none": a step the operator performed by clicking Save is still
> performable by clicking Save, and planning nothing burns it.

## `plan_step`, [line 245](../../../../../../../backend/src/sro/application/execution/plan_step.py#L245): Comment

Code: `why = f"the recorded body cannot be re-aimed at this run's values; {why}"`

> The run was given values and nothing could work out where they go.
> Sending the recorded body would send the DEMONSTRATION's values --
> the operator asks for `GPDP` and the warehouse is told `GGD`, and
> answers 201 for it. So this falls through the same way an
> unreplayable body does, to the interface where the values reach
> the form through `value_for` as they always have.
>
> Gated on the LEDGER, and that is what makes it narrow enough to
> be right. A run holds its values for the whole job, so "this run
> has values" says nothing about whether a given call carries any
> of them, and falling through on that alone turned every replay
> into a click. A `(method, path)` this deployment has individually
> watched succeed is a real state change, and one this run cannot
> aim is the one place a stale value costs a record.
>
> It also catches what inspecting the body cannot. The ledger's own
> gotcha is `csttyp truncates at 4 chars`: the operator typed
> `ZV9680`, the body went out as `ZV96`, and no value in the body
> equals anything anybody was seen typing. A rule that looked for
> the demonstrated value inside the bytes would find nothing and
> send the truncation.

## `plan_step`, [line 247](../../../../../../../backend/src/sro/application/execution/plan_step.py#L247): Comment

Code: `asked = data.get("action") if data.get("action") in ACTIONS else primary.action.kind`

> Both the plan the model asked for and the one it gets when its http.send
> cannot be replayed. One path, so the downgrade cannot drift from the plan
> it is downgrading to.

## `plan_step`, [line 248](../../../../../../../backend/src/sro/application/execution/plan_step.py#L248): Comment

Code: `action = primary.action.kind if needs_a_secret(primary) and asked not in VALUED else asked`

> A step that types a credential types it, whatever the model says.
>
> The model's answer wins over the evidence above, and `click` is a legal
> answer -- so a step whose evidence is a redacted `type` came back as a
> click at the password box, which left `VALUED` and took the credential
> branch below with it: no vault lookup, no refusal naming what it wanted,
> no value. Measured on the deployment 2026-09-22, run `run_2a9d4c7d`:
> `{"action": "click", "value": null}` at `input#password`, the field left
> empty, and the screen rung held it anyway.
>
> The evidence is the authority here and nowhere else in this function: a
> credential step exists to put a credential in a box, and an action that
> cannot carry a value is not a way of doing that.

## `plan_step`, [line 250](../../../../../../../backend/src/sro/application/execution/plan_step.py#L250): Comment

Code: `if action not in VALUED:`

> A step that was asked for a value and is about to be performed by an
> action that cannot carry one. `VALUED` says a click types nothing, so the
> value is dropped here and the command goes out carrying the locators of
> whatever the RECORDING clicked -- the run creates the record with the
> demonstrated choice, the save returns 2xx, and `verify` holds it by
> status. The operator asked for ENVEYO and got ConnectShip (TanData), and
> nothing anywhere says so.
>
> `undeliverable` exists for this failure and cannot see this route: it
> asks whether `value_for` would FIND the name, and here it does -- through
> `step.parameters` -- and the plan then throws the answer away. Nor can it
> be decided when the job is mined: the action is the model's to choose at
> plan time, so a step whose recorded gesture is a click is routinely
> planned as a `type` and delivers its value perfectly well. The only
> moment the truth is known is this one.
>
> Real, and in the store: acme's `Create a Carrier Cross Reference` is done
> entirely with dropdowns -- every cited gesture is a click with no value
> -- and declares `Carrier`, `Service Level` and `External System Name`.
> `StartWorkflowRun` refuses a press that leaves a declared parameter
> empty, so the operator is made to supply all three, and a click step
> cannot apply any of them.
>
> Refused rather than logged. A job that stops and says why costs an
> operator a minute; a job that writes the wrong carrier into a warehouse
> and reports success costs somebody a day finding it.
>
> Two clicks are how a person answers one of these, and two clicks are how
> this does it. `opened` says which half is being planned: the first sends
> the demonstrated click, which opens the list and answers nothing, and the
> second clicks the row whose text IS the value asked for. Nothing is
> guessed -- the row is named by the operator's own answer, so a control
> carrying that text either exists on the page or the browser says
> `control_not_found` and the step fails, which is where the refusal below
> left it anyway.
>
> Only for a step that changes nothing. The opening click goes out from
> inside the planning loop, ahead of the gate that withholds a write from a
> dry run and parks one on a person -- the same place `navigate` already
> sends from, and safe there for the same reason: opening a list, like
> going to a page, is not the writing.

## `plan_step`, [line 278](../../../../../../../backend/src/sro/application/execution/plan_step.py#L278): Comment

Code: `secret = None`

> A control the recording was never allowed to keep a value for. The value
> comes from the vault at this moment, by a key built from the system and
> the field's own name -- never from the evidence, which still holds
> nothing but the fact that there was a password here.
>
> An absent secret is a refusal with the key in it, not a blank typed into
> a login form: a blank submits, fails, and looks to everybody like the job
> being broken.

## `plan_step`, [line 287](../../../../../../../backend/src/sro/application/execution/plan_step.py#L287): Comment

Code: `here = look.url or (look.elsewhere if look.elsewhere_is_ours else "")`

> For the page the browser is ACTUALLY in front of, and only then the
> one the recording names.
>
> `secret_key_for` reads the origin off the recorded gesture, which is
> right while the browser is on the page that was recorded. A sign-in
> that bounced somewhere else is the case it is wrong for, and it is
> also the case a sign-in step is most often in.
>
> Measured on the deployment 2026-09-20, run `run_b949148d`: `Log in
> using Azure B2C SSO` is mined entirely on
> `blueyonderalphaus.b2clogin.com`, the live sign-in bounced to
> Keycloak, and this asked for -- and typed -- the b2clogin password
> on the Keycloak form. The page said *Invalid username or password*.
> A credential in the wrong system's box is worse than a step that
> fails: it spends an account's lockout budget, and it is the
> operator's account.
>
> `elsewhere_is_ours` and not `elsewhere`: the browser answers with the
> tab in front when this run pinned none, and a password for whatever
> window happened to be open is a credential prompt for a system
> nobody named.

## `plan_step`, [line 293](../../../../../../../backend/src/sro/application/execution/plan_step.py#L293): Comment

Code: `return Planned(`

> The refusal carries what it wanted as STRUCTURE and not only as
> prose. The operator who has to fix this is a person in a
> warehouse with a panel open: they have no console, no shell and
> no reason to know what a vault key is, so the panel has to be
> able to draw "this job needs your password for <system>" and a
> box -- which it cannot do by parsing a sentence.

## `plan_step`, [line 308](../../../../../../../backend/src/sro/application/execution/plan_step.py#L308): Comment

Code: `"value": secret`

> str(), because nothing validates the model's answer against the
> schema: a `"value": 123` otherwise reaches the extension as an int.

## `plan_step`, [line 313](../../../../../../../backend/src/sro/application/execution/plan_step.py#L313): Comment

Code: `"locators": [rung.as_payload() for rung in _ladder(primary, learned)],`

> The evidence's ladder, never the model's: the model chooses which
> control the step means, the demonstration says where that control is.
>
> With what a previous run FOUND at the top of it, where one did. The
> demonstration's own identity for this control has already failed at
> least once by then -- that is the only way anything gets written
> there -- and the locator that worked instead costs a DOM query to
> try. Measured on the deployment, 2026-09-17: three runs in one
> afternoon each spent two model calls and a screenshot re-deriving
> that the control is called "Customer Types".

## `plan_step`, [line 320](../../../../../../../backend/src/sro/application/execution/plan_step.py#L320): Comment

Code: `chosen = str(payload["value"]) if action in VALUED and payload.get("value") else ""`

> A value typed into a box that answers with a list is not yet an answer.
>
> The two-click compound above handles a step whose demonstration CLICKED
> a combobox: open the list, then click the row whose text is the value.
> A step whose demonstration TYPED into one gets here instead, because a
> type carries a value and the compound only ever ran for actions that do
> not -- so it typed the filter and stopped, with the list open and the
> grid untouched.
>
> Measured on the deployment 2026-09-22 at 09:51. `Delete a Customer Type`
> typed MRN5 into the filter box, the suggestion list offered "MRN5 in
> Customer Type", nothing clicked it, and the next step failed with "the
> customer type row is not selected". The demonstration shows the click --
> three of them, on `rpBoundList`, cited by this very step -- and the job
> records one step, so the runner performed one act.
>
> Read off the step's own evidence and never assumed: only where a cited
> click landed on a bound list. A form whose box takes a value and closes
> is untouched.
>
> And the second half is decided by the list being open, not by the model
> saying "type" a second time. Re-asked with the list in front of it, the
> model answers "click" -- which is the right act -- and a click fell
> through to the plain payload: a click on the box itself, which let Ext
> pick whatever row it liked. Measured on the deployment 2026-09-22 at
> 13:12: MRN1 typed, the list offered it under four columns, and the run
> applied "Create Shipment By = MRN1". The row this step's demonstration
> chose is known either way; the value is the run's own, under whatever
> name the box answers to.

## `plan_by_sight`, [line 392](../../../../../../../backend/src/sro/application/execution/plan_step.py#L392): Comment

Code: `why = f"no screen to look at: {look.refused}" if look.refused else "no screen to look at"`

> With the browser's own reason, where it gave one. "no screen to look
> at" alone is the same sentence for a refused focus, a tab that went
> away and a picture of zero size, and a step that fails for a reason
> nobody can read is a step nobody can fix.

## `plan_by_sight`, [line 417](../../../../../../../backend/src/sro/application/execution/plan_step.py#L417): Comment

Code: `clearing = points_at in ("what_reveals_it", "what_is_in_the_way")`

> Not on the screen, and something on the screen would reveal it.
>
> Measured on the deployment, 2026-09-17: the step clicks the "Customer
> Types" tab, and this rung answered "not currently visible ... it is
> likely under the 'Partners' menu which needs to be opened first" --
> the right answer, as prose, with no way to act on it. The job then
> ran by its call, which is the fallback and not the point: a job whose
> write has no call would have stopped there holding the fix.
>
> The same two-click shape a dropdown already uses: this one opens, the
> runner plans again with a fresh picture, and the second answers the
> step. `opened` is the runner's guard, so a planner that only ever
> opens things spends its budget rather than looping.
> The point it just gave, when it says that point opens the way.
> `opened` no longer means "already opened once, so stop". The runner
> bounds how many things one rung may open (`K_OPENINGS`) and refuses
> the rest; what this rung must not do is keep pointing at the same
> thing, which the fresh picture it is shown each time is what settles.
> Two ways a screen is not ready for the step, and one answer to both:
> click it and look again. A menu to open is the control being
> somewhere else; a dialog to dismiss is something on top of it.

## `plan_by_sight`, [line 433](../../../../../../../backend/src/sro/application/execution/plan_step.py#L433): Comment

Code: `offered = {"x": data.get("x"), "y": data.get("y")} if clearing else None`

> And whether it pointed at something this rung could not use. The
> alternative is reading the same prose twice and not knowing whether
> the model would not point or pointed off the picture.

## `plan_by_sight`, [line 441](../../../../../../../backend/src/sro/application/execution/plan_step.py#L441): Comment

Code: `if not (`

> Inside the picture, or nowhere: a point off the viewport is a guess.

## `plan_by_sight`, [line 445](../../../../../../../backend/src/sro/application/execution/plan_step.py#L445): Comment

Code: `action = data.get("action")`

> Nothing validates the model's answer against the schema; the enum is
> checked here, as `plan_step` checks its own.

## `plan_by_sight`, [line 416](../../../../../../../backend/src/sro/application/execution/plan_step.py#L416): Comment

Code: `if points_at != "the_control":`

> The enum alone decides. `points_at` is required by `SEE_STEP`'s schema and
> `ask` refuses an answer without it, so an answer that reaches here always
> carries one. The `found`-only fallback was for a deployment pinned to an
> earlier model; the model is pinned on the record now, so there is none.
