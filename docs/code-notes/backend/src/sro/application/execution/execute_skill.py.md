# Notes for `backend/src/sro/application/execution/execute_skill.py`

Comments and docstrings moved out of [`backend/src/sro/application/execution/execute_skill.py`](../../../../../../../backend/src/sro/application/execution/execute_skill.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/execution/execute_skill.py#L1): Docstring

> Perform a skill at L1: replay the calls the demonstration produced.
>
> What this is careful about, in order of how much damage the alternative does:
>
> - A mutation is sent at most once per run, and nothing here retries one. The run
>   is saved after every step, so a run left RUNNING with N outcomes says exactly
>   one thing: step N was in flight, and whether it landed is unknown. That is the
>   state a human has to be told about rather than a state a retry may guess at.
> - A stage that does not permit writes withholds them rather than skipping them.
>   A shadow run produces the full request it would have sent, which is the only
>   way to review one before allowing it.
> - A step whose headers cannot be resolved does not go out degraded.

## module, [line 70](../../../../../../../backend/src/sro/application/execution/execute_skill.py#L70): Note on the line above

Code: `MAX_RECORDED_BODY_BYTES = 64 * 1024`

> How much of a write's body a run will keep.
>
> Capture already bounds it -- a payload over the inline limit is a blob and
> never becomes a body template at all -- but a loop writes one body per thing in
> a list, and twenty-five of the largest inlined body would be a megabyte of run
> log nobody is going to read. This is the size a person reads, not the size the
> wire allows.

## module, [line 185](../../../../../../../backend/src/sro/application/execution/execute_skill.py#L185): Note on the line above

Code: `_LOOK_AGAIN = 0.4`

> How long to leave a screen that has not caught up yet, between looks.

## module, [line 187](../../../../../../../backend/src/sro/application/execution/execute_skill.py#L187): Note on the line above

Code: `NOTHING_ASSERTED = "the step asserts nothing"`

> Recorded as unchecked, because that is what it is.
>
> A step with no post-condition cannot fail one, so it came out "ok" and the run
> came out SUCCEEDED -- and everything reading that took it for a step that had
> been verified. It was performed. Nothing looked.

## module, [line 189](../../../../../../../backend/src/sro/application/execution/execute_skill.py#L189): Note on the line above

Code: `SCREEN_SETTLES_WITHIN = 2.0`

> And how long to keep looking. Long enough for a screen that is working and
> short enough that a step which is genuinely wrong is not a wait: what is being
> waited for is a page reacting to a gesture, not a warehouse deciding anything.

## module, [line 1206](../../../../../../../backend/src/sro/application/execution/execute_skill.py#L1206): Note on the line above

Code: `_Iterations = tuple[int, list[dict[str, str]]]`

> Which loop, and what its body is to be run with, one entry per thing.

## `_recordable`, [line 73](../../../../../../../backend/src/sro/application/execution/execute_skill.py#L73): Docstring

> The body to keep beside a write, and why it is missing when it is.
>
> Past the cap the body is dropped and *said* to be dropped rather than cut:
> a truncated body reads exactly like a whole one, and the reviewer this
> exists for would sign off a write on half of it.

## `NotRunnable`, [line 80](../../../../../../../backend/src/sro/application/execution/execute_skill.py#L80): Docstring

> The skill cannot be run as asked. Never a partial run: this is raised
> before anything is sent.

## `refuse_if_breaker_is_open`, [line 84](../../../../../../../backend/src/sro/application/execution/execute_skill.py#L84): Docstring

> Whether anything at all may be driven against this system right now.
>
> About the system's recent behaviour, not about what is being asked of it, so
> every rung asks it: a replay, and a pursuit working a task out on the screen.
> The pursuit did not, and the rung with no demonstration behind it was the one
> allowed to keep going after the others had been stopped.

## `ensure_runnable`, [line 99](../../../../../../../backend/src/sro/application/execution/execute_skill.py#L99): Docstring

> Everything that must hold before anything is sent, given a version
> that has already been resolved -- checked here rather than folded back
> into a single fetch-and-check step, so a caller that has already reached
> into a skill for some other reason (promoting it, for instance) can ask
> this about the exact object it is holding, before committing anything on
> the strength of the answer.
>
> This is the whole of what `StartRun._may_run` used to do inline: the
> stage/parameter/medium refusals and the circuit breaker, in the order
> that matters -- nothing here has side effects, so raising costs nothing
> to undo.

## `ExecutionRequest`, [line 119](../../../../../../../backend/src/sro/application/execution/execute_skill.py#L119): Note on the line above

Code: `run_id: RunId | None = None`

> Given by the caller when it has to know the id before the run ends --
> a console streaming the steps as they happen, for instance.

## `ExecutionRequest`, [line 121](../../../../../../../backend/src/sro/application/execution/execute_skill.py#L121): Note on the line above

Code: `device_id: DeviceId | None = None`

> Perform this in the operator's own browser rather than in one of ours.
>
> Which is how a skill runs against a system this deployment holds no
> credentials for: the request goes out of a page the operator is already
> signed in to. It also means the browser can close, and a run that loses it
> fails rather than being finished somewhere else.

## `ExecutionRequest`, [line 123](../../../../../../../backend/src/sro/application/execution/execute_skill.py#L123): Note on the line above

Code: `medium: Medium = Medium.NETWORK`

> Which rung performs the whole task.
>
> A choice, not a fallback. Swapping medium mid-run leaves the browser without
> the screen state the earlier steps would have produced, so the task is the
> unit that changes rung, and today a human picks it.

## `ExecutionRequest`, [line 125](../../../../../../../backend/src/sro/application/execution/execute_skill.py#L125): Note on the line above

Code: `may_take_focus: bool = False`

> Whether this run may bring a tab to the front of the operator's browser.
>
> Somebody watching a run they asked for is not interrupted by their tab
> changing; somebody typing at 3pm while a schedule fires behind them is.
> Default no, so a caller that has not thought about it does not take
> anybody's screen.

## `ExecutionRequest`, [line 127](../../../../../../../backend/src/sro/application/execution/execute_skill.py#L127): Note on the line above

Code: `intent: str = ""`

> The sentence the operator typed, carried onto ``Run.intent`` verbatim.
>
> Blank for a console run, a batch, a trigger -- everything that did not
> begin with somebody's own words. See ``Run.intent`` for why this is the
> one place it is kept.

## `Refused`, [line 130](../../../../../../../backend/src/sro/application/execution/execute_skill.py#L130): Docstring

> A safety limit stopped this before anything was sent.
>
> Separate from NotRunnable, which is about the skill: this is about the
> system's recent behaviour, and the answer is a person rather than a retry.

## `StartRun`, [line 134](../../../../../../../backend/src/sro/application/execution/execute_skill.py#L134): Docstring

> Create the run. Nothing has been sent when this returns.

## `ExecuteStep`, [line 192](../../../../../../../backend/src/sro/application/execution/execute_skill.py#L192): Docstring

> One step of one run.
>
> A step at a time because that is the unit a crash can be resumed at. It is
> also the unit that must not be retried blindly: the caller knows whether the
> step it is asking for has already been recorded, because the run says so.

## `FinishRun`, [line 1030](../../../../../../../backend/src/sro/application/execution/execute_skill.py#L1030): Docstring

> Close the run and decide what it says.
>
> Both paths end here -- in-process and durable -- which is why the knowledge
> write-back hangs off this and not off the workflow: a run that survives a
> restart teaches the store the same thing as one that did not.

## `ExecuteSkill`, [line 1073](../../../../../../../backend/src/sro/application/execution/execute_skill.py#L1073): Docstring

> Start, step through, finish. The in-process path.
>
> The durable path runs the same three use cases as separate activities, so a
> run that survives a restart is the same run, not a second implementation.

## `_origin_of`, [line 1126](../../../../../../../backend/src/sro/application/execution/execute_skill.py#L1126): Docstring

> The page a step acts on, as a bare scheme and host.
>
> The step's own recorded call where it has one, because a skill's steps do
> not all belong to the same system: a workflow checks the WMS and then
> records the receipt in the ERP, and a driver bound to one origin for the
> whole run would attempt the second half in the first half's tab.
>
> Where the step has no call of its own -- a UI-only step, or one whose host
> is parameterised -- the version answers instead, from the first step that
> names one. A parameterised host is no answer at all: the placeholder is not
> filled in until the step runs, and a tab cannot be chosen by a template.
>
> And where the whole skill recorded no call, the system it belongs to
> answers. A task taught entirely by clicking -- which is most of them, and
> every one taught on a screen that renders itself from a bundle -- named no
> URL anywhere, so it was driven in whichever tab happened to be in front:
> the exact coin toss this function exists to prevent, and one that reads as
> thirteen steps of `control_not_found` rather than as a wrong tab. The
> version already knows its systems and a connection already knows its host,
> so nothing here is inferred -- it is the origin the operator authenticated.

## `_origin_of_system`, [line 1141](../../../../../../../backend/src/sro/application/execution/execute_skill.py#L1141): Docstring

> The origin of the one system this skill belongs to.
>
> Only when there is exactly one. A workflow across two systems whose steps
> named no URL cannot be placed by this -- picking either would send half the
> run to the wrong tab, and the frontmost page is at least honestly a guess.

## `_iterations_of`, [line 1209](../../../../../../../backend/src/sro/application/execution/execute_skill.py#L1209): Docstring

> The things this loop will act on, read out of the answer that listed them.
>
> A sentence instead, where the answer does not hold them: a list that is
> missing, or things that do not carry what the demonstration proved they
> carry, is a system that has changed under a skill -- which is a step that
> failed saying so, never a run that does something a guessed number of times.

## `_derive`, [line 1235](../../../../../../../backend/src/sro/application/execution/execute_skill.py#L1235): Docstring

> The values this step's response hands to later ones.
>
> A derived parameter that cannot be extracted is left unbound on purpose: the
> step that needs it then fails with the parameter's name, which points at the
> response that was supposed to carry it rather than at the step that broke.

## `_may_be_retried`, [line 1248](../../../../../../../backend/src/sro/application/execution/execute_skill.py#L1248): Docstring

> Whether sending this step again is safe, on the evidence of the attempt.
>
> Not on the diagnosis. The healer reads a 302 as proof the request was turned
> away at a login page, which it sometimes is -- and is also exactly what a
> successful form POST answers with. Both look identical from here, so the one
> that decides is whether a mutating request went out at all: a status code
> means the application answered, and an answered POST that is sent again is
> how one create becomes two.

## `_missing_named`, [line 1278](../../../../../../../backend/src/sro/application/execution/execute_skill.py#L1278): Docstring

> The headers a step said it had no live value for.
>
> Read back off the step's own words rather than threaded through a second
> return value: the message is the record, and a healer that diagnosed from
> something the record does not show would be repairing a failure nobody can
> see afterwards.

## `StartRun.check`, [line 140](../../../../../../../backend/src/sro/application/execution/execute_skill.py#L140): Docstring

> Everything ``execute`` would refuse for, without starting anything.
>
> For a caller that schedules the run somewhere else and answers before it
> begins. Without this, a refusal -- a skill at a stage that may not run, a
> breaker asking for a person -- happened inside the workflow, after the
> request had already answered 201 with a run id for a run that was never
> created. The console then watched that id forever, which is the one
> outcome a breaker exists to prevent.

## `ExecuteStep.has_more`, [line 220](../../../../../../../backend/src/sro/application/execution/execute_skill.py#L220): Docstring

> Whether this run has another position to perform.
>
> For the durable path, which cannot count the steps up front: a loop's
> body occupies as many positions as the system said there were things,
> and that number arrives partway through the run.

## `ExecuteStep._heal`, [line 342](../../../../../../../backend/src/sro/application/execution/execute_skill.py#L342): Docstring

> Ask the healer whether this failure is one the session explains.

## `ExecuteStep._budget_for`, [line 371](../../../../../../../backend/src/sro/application/execution/execute_skill.py#L371): Docstring

> One budget per run, so a repair that did not take is not repeated.

## `ExecuteStep._bearer`, [line 374](../../../../../../../backend/src/sro/application/execution/execute_skill.py#L374): Docstring

> An access token for this system, if one has been established.

## `ExecuteStep._ui_for`, [line 384](../../../../../../../backend/src/sro/application/execution/execute_skill.py#L384): Docstring

> The browser this run is performed in, and the page in it.
>
> A run bound to a device never falls back to the deployment's own
> browser. That one is signed in as somebody else, on a screen nobody
> demonstrated, and quietly using it would be worse than not running.
>
> The origin goes with it. An operator's Chrome has a dozen tabs and only
> one of them is the system this skill was taught on; without being told
> which, the extension can only take the frontmost page, and a run that
> guesses wrong performs a warehouse task on somebody's email.

## `ExecuteStep._caller_for`, [line 406](../../../../../../../backend/src/sro/application/execution/execute_skill.py#L406): Docstring

> Whose session the call goes out under. Same rule as the browser.

## `ExecuteStep._perform_in_ui`, [line 413](../../../../../../../backend/src/sro/application/execution/execute_skill.py#L413): Docstring

> Perform one step of a task that is being run in the browser.
>
> The write rule is the same as at L1 and matters more here: a click is
> indistinguishable from a call once it has happened, so a stage that may
> not write may not click either.

## `ExecuteStep._check_on_screen`, [line 497](../../../../../../../backend/src/sro/application/execution/execute_skill.py#L497): Docstring

> What the screen says, after the gesture that was supposed to change it.
>
> Only where the demonstration proved something visible, so a step whose
> evidence is a response body costs no screenshot. A screen that cannot be
> read is not a failed step -- the gesture landed, and calling the task
> wrong because a capture failed would be worse than saying what happened.
>
> Looked at again while it has not settled, because a driver answers the
> moment it dispatches the gesture: the extension's `perform` returns
> before the page has done anything at all. Checking once would call every
> screen that takes a moment a failed task, which is a worse lie than the
> one this exists to stop. Only a step that is failing pays for the
> looking; a screen that already says what it should is read once.

## `ExecuteStep._escalate`, [line 522](../../../../../../../backend/src/sro/application/execution/execute_skill.py#L522): Docstring

> Try the next rung, if the policy allows one and the run may act.
>
> Shadow never drives the interface. A withheld call is a call that did not
> happen; a click on the same screen is a call that did, and a rehearsal
> that quietly changed a warehouse would be worse than no rehearsal.

## `ExecuteStep._escalate_to_vision`, [line 604](../../../../../../../backend/src/sro/application/execution/execute_skill.py#L604): Docstring

> The last rung, if the policy allows it and it is configured.
>
> Every attempt is recorded whether or not the model was reached: a run
> that would have escalated and could not is a different fact from a run
> that never tried, and only one of them means the deployment is missing
> a rung.

## `ExecuteStep._rest_of`, [line 904](../../../../../../../backend/src/sro/application/execution/execute_skill.py#L904): Docstring

> Follow this read's own paging until there is nothing after it.

## `ExecuteStep._perform_with_tool`, [line 930](../../../../../../../backend/src/sro/application/execution/execute_skill.py#L930): Docstring

> Call the connector this step was mapped onto.
>
> The one kind of step nobody demonstrated, so there is no recorded call
> to replay and no recorded gesture to fall back to -- `escalation.py`
> says as much, and every failure here stops rather than trying a lower
> rung at a door the connector already answered.

## `FinishRun.execute`, [line 1043](../../../../../../../backend/src/sro/application/execution/execute_skill.py#L1043): Docstring

> End the run, and let the ladder read what happened.
>
> `stopped` is for a run that could not continue rather than one that ran
> and failed its checks -- a detached performer that raised, and in time a
> person who pressed stop. Both are FAILED, and both count against the
> skill: three in a row demote it. That is defensible for a real fault and
> arguable for a deliberate stop, and the alternative is a fourth verdict,
> a migration, and a rewrite of promotion. Not yet.

## `ExecuteSkill.execute`, [line 1097](../../../../../../../backend/src/sro/application/execution/execute_skill.py#L1097): Docstring

> Start it and see it through, in one call.

## `ExecuteSkill.begin`, [line 1100](../../../../../../../backend/src/sro/application/execution/execute_skill.py#L1100): Docstring

> Write the row, refuse it here if it is going to be refused.
>
> Everything that says no -- the circuit breaker, the blast radius, a
> stage that may not send a write, a version that does not exist -- says
> so from here, so a caller that means to perform the run detached still
> gets its answer as a `4xx` rather than in a task nobody is awaiting.

## `ExecuteSkill.resume`, [line 1103](../../../../../../../backend/src/sro/application/execution/execute_skill.py#L1103): Docstring

> Perform a run whose row already exists.
>
> Split out so a caller can be told the run's id before the last step
> rather than after it. A run in an operator's own browser is watched
> while it happens, and a console cannot watch a run whose id arrives with
> the answer.

## `refuse_if_breaker_is_open`, [line 90](../../../../../../../backend/src/sro/application/execution/execute_skill.py#L90): Comment

Code: `connection = await uow.connections.find_by_system(ctx.tenant_id, system)`

> Failures somebody has already looked at stop counting. Without this the
> breaker asks for a person and gives them nothing to do: every run is
> refused until the window ages out, including the one that would show the
> fault is already fixed.

## `ensure_runnable`, [line 108](../../../../../../../backend/src/sro/application/execution/execute_skill.py#L108): Comment

Code: `for system in version.systems or (skill.objective_key.target_system,):`

> Every system it touches, not only the one it is keyed by: a workflow
> that writes into a second system must be stopped by that system's
> breaker, and keying alone would hide exactly that.

## `StartRun._may_run`, [line 150](../../../../../../../backend/src/sro/application/execution/execute_skill.py#L150): Comment

Code: `if request.device_id is not None:`

> One run per browser, which the rig has had since migration 0043 and
> this path had in no form at all -- not the index, not even the read.
> Two triggers firing two skills at one device in the same minute both
> started, and their clicks interleaved in one window: the corrupted
> form against a live warehouse that 0043 was written about.
>
> The read names the run that has the browser, which is what a person
> can act on. `uq_runs_one_running_per_device` is the guard: there are
> awaits between here and the commit, and a read alone loses that race
> -- demonstrated against real Postgres on the rig's own path.

## `StartRun._may_run`, [line 152](../../../../../../../backend/src/sro/application/execution/execute_skill.py#L152): Comment

Code: `if busy is not None and busy != str(request.run_id or ""):`

> `!= request.run_id`: a caller that minted the id and is
> re-entering its own run is not a second press.

## `StartRun.execute`, [line 163](../../../../../../../backend/src/sro/application/execution/execute_skill.py#L163): Comment

Code: `id=request.run_id or self._ids.new_run_id(),`

> Minted by whoever asked, where they need to know it before it
> finishes: a console cannot stream a run whose id only arrives
> with the last step.

## `ExecuteStep.execute`, [line 229](../../../../../../../backend/src/sro/application/execution/execute_skill.py#L229): Comment

Code: `connections = await uow.connections.list_for_tenant(ctx.tenant_id)`

> Read here because a step's credentials depend on which system it
> is calling, and a workflow's steps do not all call the same one.

## `ExecuteStep.execute`, [line 234](../../../../../../../backend/src/sro/application/execution/execute_skill.py#L234): Inline

Code: `return run.steps[index]`

> already done; never send it twice

## `ExecuteStep.execute`, [line 236](../../../../../../../backend/src/sro/application/execution/execute_skill.py#L236): Comment

Code: `nxt = next_step(version, run)`

> Which step of the plan this position is, and -- inside a loop -- which
> thing it is acting on this time round. The two are the same number for
> every skill without loops, which is every skill taught before them.

## `ExecuteStep.execute`, [line 246](../../../../../../../backend/src/sro/application/execution/execute_skill.py#L246): Comment

Code: `outcome = await self._perform_with_tool(run, step, values=values)`

> Chosen by the step, not by the run. A run's medium says which rung
> it is being performed at; a tool plan says this particular step
> goes through a connector, and the two are different questions. A
> run asked for in the interface still clicks, because that is
> somebody deliberately watching it happen.

## `ExecuteStep.execute`, [line 269](../../../../../../../backend/src/sro/application/execution/execute_skill.py#L269): Comment

Code: `produces = tuple(`

> Every value this step hands forward, not the first: one call can
> return an id and the code the next call needs alongside it.

## `ExecuteStep.execute`, [line 288](../../../../../../../backend/src/sro/application/execution/execute_skill.py#L288): Comment

Code: `healed = await self._heal(ctx, run, skill, step, outcome, failure)`

> A session that aged out is not a broken skill, and the run should not
> need a person to say so. Repair what the target system owns, once,
> and let the step speak for itself; anything the healer cannot explain
> is left exactly as it failed.

## `ExecuteStep.execute`, [line 247](../../../../../../../backend/src/sro/application/execution/execute_skill.py#L247): Comment

Code: `outcome = replace(`

> Diagnosed and not repaired. The diagnosis is the useful half: a
> step that says "assertion_failed" sends somebody to read the
> skill, and this one was turned away at a login page by a system
> nobody is signed into any more.

## `ExecuteStep.execute`, [line 276](../../../../../../../backend/src/sro/application/execution/execute_skill.py#L276): Comment

Code: `outcome, derived, failure, iterated = await self._perform(`

> The same call again, so the same facts about it: `parameters`
> is what fills an optional nobody supplied with its absent form
> and what checks a value against the slot it goes in, and `feeds`
> is the list a loop is over. Handed only `produces`, the retry
> rendered a body with an empty parameter tuple and failed "no
> value for parameter" -- so a healed session expiry, the ordinary
> thing the healer exists for, became a hard failure on any skill
> with an unsupplied optional.

## `ExecuteStep.execute`, [line 260](../../../../../../../backend/src/sro/application/execution/execute_skill.py#L260): Comment

Code: `outcome = replace(`

> Repaired, and deliberately not retried: this step's write reached
> the application. Sending it again is how one create becomes two.

## `ExecuteStep._bearer`, [line 381](../../../../../../../backend/src/sro/application/execution/execute_skill.py#L381): Comment

Code: `logger.info("no access token for %s: %s", system, refusal)`

> Worth a line, not a failure: the run falls back to the session
> cookies and says so if those are gone too.

## `ExecuteStep._ui_for`, [line 401](../../../../../../../backend/src/sro/application/execution/execute_skill.py#L401): Comment

Code: `doing=step.intent if step is not None else "",`

> What this step is for, not what the skill is called: the band is
> read by somebody watching their own screen change, and "adding
> the work area" answers what is happening to them now.

## `ExecuteStep._perform_in_ui`, [line 423](../../../../../../../backend/src/sro/application/execution/execute_skill.py#L423): Comment

Code: `return StepOutcome(`

> The demonstration that skipped this field did not touch this
> control, so neither does this. Skipped rather than typed empty:
> an empty keystroke into a required-looking field is how a form
> ends up with a validation error nobody asked for.

## `ExecuteStep._perform_in_ui`, [line 476](../../../../../../../backend/src/sro/application/execution/execute_skill.py#L476): Comment

Code: `return self._failed(step, None, str(error), medium=Medium.UI, unreachable=True)`

> A laptop that closed, or no tab open on the system this step acts
> on. The driver already sorts those from a control that moved; this
> carries that distinction onto the run.

## `ExecuteStep._check_on_screen`, [line 502](../../../../../../../backend/src/sro/application/execution/execute_skill.py#L502): Comment

Code: `return (), tuple(dict.fromkeys(a.kind.value for a in step.assertions)) or (`

> Nothing here can be checked from the interface -- either the step
> asserts nothing at all, or what it asserts is a response body no
> rung in a browser can see. Silence was returned for both, and
> silence reads as a passing check to everything downstream.

## `ExecuteStep._escalate`, [line 569](../../../../../../../backend/src/sro/application/execution/execute_skill.py#L569): Comment

Code: `return await self._escalate_to_vision(`

> The recorded control is gone. Whether anything above may look at
> the screen instead is the policy's decision, not this method's.

## `ExecuteStep._escalate_to_vision`, [line 616](../../../../../../../backend/src/sro/application/execution/execute_skill.py#L616): Comment

Code: `ui = self._ui_for(run, version, step, connections)`

> The same browser the rungs below it were driving. A run bound to a
> device is performed in somebody's own Chrome, and a vision rung
> holding the deployment's driver would photograph a different screen
> and click on it -- signed in as somebody else, on a page nobody
> demonstrated. Falling back is the one thing it must not do.

## `ExecuteStep._escalate_to_vision`, [line 632](../../../../../../../backend/src/sro/application/execution/execute_skill.py#L632): Comment

Code: `failures, unchecked = (`

> The rung's own docstring says the model may claim a step is done and
> the demonstration's assertions decide. Nothing decided: a click a
> model chose by looking at a screenshot was recorded as a step that
> succeeded, and counted towards the version's promotion. Here is where
> they decide.

## `ExecuteStep._perform`, [line 696](../../../../../../../backend/src/sro/application/execution/execute_skill.py#L696): Comment

Code: `rendered = dict(values)`

> An optional field nobody supplied is sent the way the demonstration
> that skipped it sent it, filled in here rather than left to the
> template: `absent_as` is the demonstration's own JSON -- `null` for
> a number the form nulls, `""` for a text control it empties -- and
> the string form (the two characters `n`,`u`,`l`,`l`) is not the JSON
> value. Its own quotes come off before it goes in a text slot, since
> the slot is already quoted at emission for a string-typed field.
>
> Supplied empty counts as not supplied, because `_perform_in_ui`
> already reads it that way and skips the gesture: these values come
> off a form, and a form hands back `""` for the box nobody typed in.
> One run cannot mean two things depending on which medium performs
> it -- and an empty in an unquoted slot renders `{"deltaPriority":}`,
> which is not JSON at all.
>
> Everything else that goes into the body is encoded for the JSON
> string it lands in, and not merely the text slot the form nulls.
> A body leaf is a body leaf: `check dock 9` pasted raw into an
> unquoted one is not JSON, and `he said "go"` pasted into a quoted
> one writes the rest of the body itself. One `json.dumps` answers
> both -- the difference is only whose quotes are used, its own where
> the slot has none and the template's where it already wrote them --
> and for anything carrying neither a quote nor a backslash it changes
> nothing at all. Refusing such a value instead, which is what this
> did, made a task whose body is XML permanently unrunnable.
>
> Only the body gets the encoded form; the same value in a URL segment
> or a header is text. And a parameter that *is* the body gets none of
> it: there is no surrounding string to escape into.

## `ExecuteStep._perform`, [line 699](../../../../../../../backend/src/sro/application/execution/execute_skill.py#L699): Comment

Code: `if (absent := parameter.absent_value) is not None and not rendered.get(parameter.name):`

> `absent_value is not None` is what `optional` means; asked this
> way round because the value is wanted as well as the fact.

## `ExecuteStep._perform`, [line 698](../../../../../../../backend/src/sro/application/execution/execute_skill.py#L698): Comment

Code: `for parameter in parameters:`

> Last look before anything leaves: a value is substituted as text, so
> one that is not the shape its slot was demonstrated holding writes
> part of the body itself. `_check_runnable` has already refused what
> an operator supplied -- before step one, rather than halfway through
> a job -- and this is the same rule where the value came from
> somewhere it could not see: an earlier response, or the thing a loop
> is on this time round.

## `ExecuteStep._perform`, [line 716](../../../../../../../backend/src/sro/application/execution/execute_skill.py#L716): Comment

Code: `producer = next(`

> The step that would have minted this value, not merely some step
> that was withheld. Any withheld step used to count, so a step that
> failed for an unrelated reason -- a parameter nobody ever filled
> in -- was recorded as cleanly withheld, and the run it belonged to
> earned its way up the ladder on the strength of it.

## `ExecuteStep._perform`, [line 667](../../../../../../../backend/src/sro/application/execution/execute_skill.py#L667): Comment

Code: `return (`

> Not a fault: this rehearsal withheld the write that would have
> minted the value. A create chain -- post the address, then the
> client that names it -- can never be rehearsed to the end, and
> reporting that as a failed step meant every such skill failed
> its shadow run and could never earn its way off the rung.

## `ExecuteStep._perform`, [line 759](../../../../../../../backend/src/sro/application/execution/execute_skill.py#L759): Comment

Code: `calling = system_of(connections, url) or (`

> Whose session this call goes out under, decided by the host it is
> going to rather than by the skill it belongs to.
>
> Everything credential-shaped hangs off this: the stored cookie, the
> minted CSRF token, the live referer, and the bearer. A workflow's
> second half keyed to its first would fetch the WMS's live token and
> post it to the ERP -- one system's session handed to another, silently
> -- and would fail to authenticate against the ERP into the bargain.
>
> A host nobody has connected falls back to the skill's own system,
> which is every run there has ever been: a device run against a system
> this deployment holds no credentials for is the whole point of naming
> a device, and dropping its headers would break it.
> A host nobody has connected falls back to the skill's own system --
> every run there has ever been -- but only where the whole skill is
> that one system. A workflow's unconnected half falling back would
> resolve the *other* system's bearer and referer and send them there,
> which is the leak this per-call scope exists to close.

## `ExecuteStep._perform`, [line 771](../../../../../../../backend/src/sro/application/execution/execute_skill.py#L771): Comment

Code: `browser_session=run.device_id is not None,`

> The operator's own browser is the session. Nothing stored here is
> sent as one, and nothing stored here is required.

## `ExecuteStep._perform`, [line 774](../../../../../../../backend/src/sro/application/execution/execute_skill.py#L774): Comment

Code: `advice = (`

> A device run has already been given the browser's session, so
> what is missing here is a value minted per run -- and "connect
> the system" is advice that would not have helped: the token
> belongs to whichever session it was issued for, and this one is
> the operator's. Everything before the semicolon is the record the
> self-healer reads back, so only the advice changes.

## `ExecuteStep._perform`, [line 791](../../../../../../../backend/src/sro/application/execution/execute_skill.py#L791): Comment

Code: `detail = f"{run.stage} does not send writes; the request was produced, not sent"`

> The body as well as the line above it. Method and URL alone say
> nothing about what would have changed, and the body is where a
> reviewer sees whether the skill got the fields right -- it is the
> only copy there will ever be, since nothing sent it anywhere.

## `ExecuteStep._perform`, [line 814](../../../../../../../backend/src/sro/application/execution/execute_skill.py#L814): Comment

Code: `sent, oversize = _recordable(body) if mutating else (None, None)`

> A write keeps the body it sends, success or failure alike. The safety
> story here is that a person reviews what the skill did, and a step
> that records only "POST -> 201" makes that review impossible: it says
> a record was created and nothing about what is in it. On the failure
> side the same body is the only thing to debug with, and "the call may
> have arrived" is precisely when somebody needs to know what would
> have arrived. Only a write: a read's body is not what anybody reviews.

## `ExecuteStep._perform`, [line 820](../../../../../../../backend/src/sro/application/execution/execute_skill.py#L820): Comment

Code: `built_wrong = isinstance(error, MalformedRequest)`

> Which end failed. A request this end could not build was never in
> flight, so it neither warns about a write that may have landed nor
> excuses the skill that produced it.

## `ExecuteStep._perform`, [line 841](../../../../../../../backend/src/sro/application/execution/execute_skill.py#L841): Comment

Code: `answer = read_answer(response.text, url=url)`

> What it found, not only that it answered -- and for a write, what it
> created. A create returns the record it made, which is the one thing
> the person who asked wants to see, and discarding it left them
> looking at a status code for that too.

## `ExecuteStep._perform`, [line 843](../../../../../../../backend/src/sro/application/execution/execute_skill.py#L843): Comment

Code: `answer = await self._rest_of(caller, url, headers, answer)`

> And the rest of it. An operator who asks which suppliers exist is
> not asking for the first page; the paging is the system's own and
> this walks it in the dialect the demonstration proved.

## `ExecuteStep._perform`, [line 856](../../../../../../../backend/src/sro/application/execution/execute_skill.py#L856): Comment

Code: `return (self._failed(step, key, found, method=plan.method, url=url), {}, None, None)`

> The list this loop is over is not in the answer, or its things
> are not the shape the demonstration proved. Nothing is done a
> guessed number of times: the step says what it could not read.

## `ExecuteStep._perform`, [line 680](../../../../../../../backend/src/sro/application/execution/execute_skill.py#L680): Comment

Code: `return (`

> Refused before the first iteration, not after fifty writes.
> The same limit a batch of the same size would meet, because it
> is the same question: this many writes is a migration, and a
> migration is somebody's decision.

## `ExecuteStep._perform`, [line 886](../../../../../../../backend/src/sro/application/execution/execute_skill.py#L886): Comment

Code: `unchecked=() if step.assertions else (NOTHING_ASSERTED,),`

> The same fact the interface rung records, on the rung that
> runs far more often. A step with no post-condition cannot
> fail one, so it came back with an empty failure list -- and
> empty is what a fully checked step returns too. Everything
> downstream read the silence as "verified": `LearnFromRun`
> took a claim from it, and a reviewer reading the run saw a
> step that had been tested.

## `ExecuteStep._rest_of`, [line 916](../../../../../../../backend/src/sro/application/execution/execute_skill.py#L916): Comment

Code: `break`

> What was read is still true. Stopping here reports fewer
> records than exist, which the count beside them already says.

## `ExecuteStep._perform_with_tool`, [line 957](../../../../../../../backend/src/sro/application/execution/execute_skill.py#L957): Comment

Code: `async with self._uow as uow:`

> Claimed before the call and kept whatever it answers. A key
> released on failure would let a timeout -- the one case where the
> send may well have landed -- be retried into a second send, which
> is the thing this exists to prevent.

## `ExecuteStep._perform_with_tool`, [line 976](../../../../../../../backend/src/sro/application/execution/execute_skill.py#L976): Comment

Code: `answered = await self._tools.call(`

> The RUN's own tenant and requester, not a context passed down:
> the row is the authority on whose run this is, and a connector is
> reached with that operator's own grant or not at all. Each reads
> their own mail, so a run performed for one person must not reach
> another's mailbox.

## `FinishRun.execute`, [line 1056](../../../../../../../backend/src/sro/application/execution/execute_skill.py#L1056): Comment

Code: `apply_verdict(skill, run, now)`

> `apply_verdict` is the one place a run's verdict reaches a
> skill's track record and stage; `CallRunWrong` reaches the same
> function later for the same reason. `version` is looked up again
> rather than threaded through the return, only because the code
> below still needs it after the `with` block closes.

## `FinishRun.execute`, [line 1062](../../../../../../../backend/src/sro/application/execution/execute_skill.py#L1062): Comment

Code: `await self._learn.execute(`

> After the commit: what the run did is the record, and a failure to
> write down what was learned must not undo it.

## `FinishRun.execute`, [line 1066](../../../../../../../backend/src/sro/application/execution/execute_skill.py#L1066): Comment

Code: `version=version,`

> For the steps performed in the interface: which locator found
> the control is only meaningful beside the one it was taught
> with, and that lives on the version.

## `FinishRun.execute`, [line 1069](../../../../../../../backend/src/sro/application/execution/execute_skill.py#L1069): Comment

Code: `await self._repair.execute(ctx, run=run)`

> Also after the commit, and after the knowledge write: a repair is
> this run's evidence adopted into a new version beside the old one,
> and a run that already happened must not be undone by it. The
> version this run was performing is untouched -- another run in
> flight against it goes on doing exactly what it started doing.

## `ExecuteSkill.resume`, [line 1108](../../../../../../../backend/src/sro/application/execution/execute_skill.py#L1108): Comment

Code: `position = 0`

> Positions, not steps: a loop's body occupies as many of them as the
> system said there were things, and how many that is arrives partway
> through. The run itself is the record of where this has got to, so it
> is re-read each time rather than counted here.

## `ExecuteSkill.resume`, [line 1111](../../../../../../../backend/src/sro/application/execution/execute_skill.py#L1111): Comment

Code: `if self._stops.asked(run.id.value):`

> Between steps, never mid-command. A gesture already sent cannot be
> recalled from a warehouse, and a stop that ended the run while one
> was in flight would report a write as not having happened when it
> had. The cost is that stopping takes until the current step's
> deadline, which the console says rather than hides.

## `ExecuteSkill.resume`, [line 1123](../../../../../../../backend/src/sro/application/execution/execute_skill.py#L1123): Comment

Code: `self._stops.forget(run.id.value)`

> A run id is never reused, so nothing else would ever clear this.

## `_check_runnable`, [line 1177](../../../../../../../backend/src/sro/application/execution/execute_skill.py#L1177): Comment

Code: `if (`

> Authorisation is for changing the system. A skill that only reads asked
> for a name and told the operator it "performs real writes" while fetching
> a list -- which is both untrue and the kind of prompt that teaches people
> to click past prompts.

## `_check_runnable`, [line 1185](../../../../../../../backend/src/sro/application/execution/execute_skill.py#L1185): Comment

Code: `if version.loops and request.medium is not Medium.NETWORK:`

> A version that spans systems is performed in a browser signed in to all of
> them, and this deployment holds one session per system and never two at
> once. Refused here rather than discovered at step four, halfway through a
> job, with the first system already written to.

## `_check_runnable`, [line 1173](../../../../../../../backend/src/sro/application/execution/execute_skill.py#L1173): Comment

Code: `raise NotRunnable(`

> A loop's list is a response, and the rungs above L1 do not read
> responses: they click. Refused rather than performed once, which is
> what a body with no list to iterate would silently become.

## `_check_runnable`, [line 1197](../../../../../../../backend/src/sro/application/execution/execute_skill.py#L1197): Comment

Code: `required = {p.name for p in version.inputs}`

> `version.inputs` is the one definition of "values somebody has to supply
> for a run to be worth starting", and it has already changed once --
> optional parameters were folded out of it after a skill with any optional
> field turned out to be impossible to put on a trigger. Re-deriving the
> same expression here left that rule written in two places, so the next
> change to it would have been correct in one of them.

## `_check_runnable`, [line 1200](../../../../../../../backend/src/sro/application/execution/execute_skill.py#L1200): Comment

Code: `for parameter in version.parameters:`

> And what was supplied is the shape its slot holds. A template
> substitutes as text: a quantity given as `2,"approved":true` renders a
> valid body carrying a field no demonstration ever sent. Refused here,
> before the first step of a job, rather than at the step that would have
> sent it -- by which time the steps before it have already written.

## `_derive`, [line 1242](../../../../../../../backend/src/sro/application/execution/execute_skill.py#L1242): Comment

Code: `bound[parameter.name] = (`

> Reformatted on the way where the demonstrations were: the WMS
> answers `42` and the ERP is sent `LPN-00042`, and sending the bare
> number would be a write the target system rejects or, worse,
> accepts against the wrong record.
