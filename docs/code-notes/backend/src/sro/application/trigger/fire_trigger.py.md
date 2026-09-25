# Notes for `backend/src/sro/application/trigger/fire_trigger.py`

Comments and docstrings moved out of [`backend/src/sro/application/trigger/fire_trigger.py`](../../../../../../../backend/src/sro/application/trigger/fire_trigger.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/trigger/fire_trigger.py#L1): Docstring

> A clock asking for a task to be done.
>
> Nobody is watching, which is what every check here is about. The trigger's
> standing authorisation is what a write goes out on; what it runs is re-read
> rather than trusted, because a skill may have been re-induced into something
> that changes a system since the day somebody put it on a schedule.
>
> Two things a trigger can run, and the difference is where the safety lives. A
> SKILL is checked here: `runnable`, `changes_the_system`, `blank_inputs`. A
> mined JOB is checked by the run itself -- `run_workflow` is dry until somebody
> presses through to live, a live write parks for a person until the job has
> `earned` the right by `K_EARNED_RUNS` state-verified runs, and every step is
> verified before the next one starts. So the workflow path here is plumbing
> rather than a second ladder: what it must not do is invent a weaker one.

## `Fired`, [line 31](../../../../../../../backend/src/sro/application/trigger/fire_trigger.py#L31): Note on the line above

Code: `confirmation_id: ConfirmationId | None = None`

> Set where nothing was started because somebody has to say yes first.
>
> Beside ``run_id`` rather than instead of it, and neither is a failure: a
> fire that became a card is the trigger working exactly as its author asked
> it to.

## `Fired`, [line 33](../../../../../../../backend/src/sro/application/trigger/fire_trigger.py#L33): Note on the line above

Code: `skipped: str | None = None`

> Why nothing was started. Not an error: a disabled trigger and a skill
> that has stopped being runnable are both ordinary, and a scheduler that
> treated them as failures would retry them all night.

## `FireTrigger`, [line 36](../../../../../../../backend/src/sro/application/trigger/fire_trigger.py#L36): Docstring

> The only thing a schedule calls.
>
> Takes no ``RequestContext``: there is no request and no caller. The tenant
> and the principal come off the trigger, which is why the repository's
> ``find`` is the one tenant-blind read in the system.

## `start_for`, [line 211](../../../../../../../backend/src/sro/application/trigger/fire_trigger.py#L211): Docstring

> Start the run a trigger asks for, at the rung it asks for.
>
> Module-level because two callers need it and they must not disagree. A fire
> starts a run here; a confirmation somebody approved starts one too, and the
> second used to call `execute_skill` directly -- which quietly dropped the
> trigger's `device_id` and drove a browser this deployment owns instead of
> the operator's own. The run then failed to attach to a CDP endpoint nobody
> was listening on, and the card had already been marked approved.
>
> ``authorized_by`` overrides the trigger's, because an approved card runs
> under the name of whoever pressed the button rather than whoever made the
> trigger.

## `start_job_for`, [line 254](../../../../../../../backend/src/sro/application/trigger/fire_trigger.py#L254): Docstring

> Start the mined job a trigger asks for, in the browser it names.
>
> Module-level for `start_for`'s reason, which is the one that matters most
> here: two callers need this -- a fire, and a card somebody approved -- and
> the second one calling `StartWorkflowRun` itself is how the skill path
> once dropped the trigger's `device_id` and drove the wrong browser.
>
> Live, always. A dry run of a scheduled job sends nothing and verifies
> nothing; it is a trigger that appears to work. What keeps it safe is not
> dryness, it is the ladder underneath: a live write parks for a person
> until the job has EARNED the right, and `earned` is three runs whose every
> write a state belt saw.
>
> `allow_focus` is the trigger's own `may_take_focus`, which defaults to off:
> a schedule that fires at 3am has no business taking somebody's screen.
>
> Claimed and then spawned, exactly as `POST /v1/workflow-runs` does. A fire
> that awaited the whole run would hold a worker's activity slot for its full
> duration -- the same failure `start_for` records above -- and a run nobody
> holds a reference to is one the loop may collect mid-gesture.
>
> **A dispatcher wins where there is one**, which is `start_for`'s rule and
> exists for the same reason: the socket to that Chrome is held by whichever
> process the extension connected to, and the scheduler's worker is not that
> one. Started in-process there, `StartWorkflowRun` looks for the browser in
> its own empty register and every scheduled job is skipped forever with
> "not connected". `start_run` remains the path for a deployment with no
> dispatcher at all.

## `blank_inputs`, [line 295](../../../../../../../backend/src/sro/application/trigger/fire_trigger.py#L295): Docstring

> The values this skill needs that nothing supplied.
>
> Public because the offer a watch turns into has to say the same thing
> before the press rather than after it: a card that starts a run which then
> fails teaches nobody. One definition, so the sentence on the card and the
> reason for the skip cannot come to disagree.
>
> A parameter present but empty counts: a relay's template renders
> `{{order}}` to nothing at all when the mail did not hold one, and an empty
> string reaches a run as a value rather than as an absence.
>
> Optional ones do not. A demonstration proved the record is created without
> that field, and `execute_skill` sends the absent form it actually sent, so
> a mail that named no Delta Priority is not a mail that named nothing --
> it is one doing what the operator who skipped that box did.

## `_because`, [line 299](../../../../../../../backend/src/sro/application/trigger/fire_trigger.py#L299): Docstring

> The one sentence somebody reads before deciding.
>
> A subject where a mail carried one, because that is what the person
> approving actually recognises. Otherwise what kind of trigger this was --
> which is thin, and thin is better than a sentence this code invented about
> a message it did not read.

## `FireTrigger.execute`, [line 58](../../../../../../../backend/src/sro/application/trigger/fire_trigger.py#L58): Docstring

> Fire it.
>
> `message` is what a mail relay or a watching browser said. Only the
> names this trigger declared it would take are read from it; everything
> else it runs with is what it was created with.

## `FireTrigger._ask_a_person`, [line 113](../../../../../../../backend/src/sro/application/trigger/fire_trigger.py#L113): Docstring

> The fire becomes a card instead of a run.
>
> The values are frozen now rather than re-read when somebody answers:
> what they approve has to be what is written in front of them, and a
> trigger edited in between would turn a yes to one thing into a yes to
> another.
>
> One helper for both kinds. The card names whichever of the two the
> trigger names, and every other field is the same question -- a second
> copy of this, per kind, is two cards that drift.
>
> **And one standing ask per question.** An arrival rule fires on every
> navigation that COMMITS its page, and a sign-in flow commits its own
> page several times -- the form, the POST, the redirect back. Each fire
> wrote another card. Measured on the deployment 2026-09-20: one rule,
> `trg_a925ce7d`, three identical "Log in to Keycloak -- an arrival
> trigger fired. Shall I?" cards stacked in the panel, none of them
> answered, and every further landing adding a fourth.
>
> A queue of prompts is the thing this design exists to not be, and it
> says so where the offers are made: *one at a time, anywhere*.
>
> Identical, and not merely same-trigger: a mail watch names the order
> number it read, and two different mails asking about two different
> orders are two questions however much of the rule they share. Same
> values and same sentence is the same question, whoever asks it.

## `FireTrigger._fire_a_job`, [line 155](../../../../../../../backend/src/sro/application/trigger/fire_trigger.py#L155): Docstring

> A mined job, started in the operator's own browser.
>
> Almost nothing is checked here, and that is the point. `run_workflow`
> is dry until somebody presses through to live; a live write parks for a
> person until the job has EARNED the right by `K_EARNED_RUNS` runs whose
> every write a state belt verified; each step is verified before the
> next is sent; and `StartWorkflowRun` itself refuses a job with a
> declared parameter left blank, a job whose evidence has gone, and a
> browser already driving something else. Repeating any of that here
> would be a second ladder that can disagree with the first.
>
> What IS checked here is what only this call site knows: that the job
> still exists.
>
> Whether the run needs a browser is not checked here either. A Steel
> tenant's run drives none, and an extension tenant's run with no
> `device_id` is refused as not connected by `StartWorkflowRun.execute` --
> in process, or behind the dispatcher's POST to the press -- which the
> fire reports as a skip.

## `FireTrigger.__init__`, [line 55](../../../../../../../backend/src/sro/application/trigger/fire_trigger.py#L55): Comment

Code: `self._start_run = start_run`

> `None` in a process that cannot drive a browser, the same shape
> `dispatcher` already has: a worker with no channel to an extension
> skips the fire rather than failing to construct.

## `FireTrigger.execute`, [line 64](../../../../../../../backend/src/sro/application/trigger/fire_trigger.py#L64): Comment

Code: `await self._forget(trigger_id)`

> A schedule that outlived its trigger. It removes itself rather
> than firing into nothing every hour until somebody notices.

## `FireTrigger.execute`, [line 87](../../../../../../../backend/src/sro/application/trigger/fire_trigger.py#L87): Comment

Code: `trigger.disable("the skill now changes the system; authorise this trigger again")`

> The skill was re-induced into something that writes. The
> authorisation on this trigger was given for a task that did
> not, and it does not carry over.

## `FireTrigger.execute`, [line 93](../../../../../../../backend/src/sro/application/trigger/fire_trigger.py#L93): Comment

Code: `return Fired(trigger_id, skipped="nothing said " + ", ".join(blank))`

> A mail that matched the rule but named no order. Every relay
> sends some of these -- an autoreply, a thread with the number
> only in an attachment -- and each one would otherwise be a
> run that starts, asks the warehouse for nothing, and fails.
> Skipped here, where the reason is still legible.

## `FireTrigger.execute`, [line 96](../../../../../../../backend/src/sro/application/trigger/fire_trigger.py#L96): Comment

Code: `asked = await self._ask_a_person(`

> Nobody is here.

## `FireTrigger.execute`, [line 104](../../../../../../../backend/src/sro/application/trigger/fire_trigger.py#L104): Comment

Code: `logger.info("trigger %s could not reach its browser: %s", trigger_id, unreachable)`

> A laptop that is closed. Ordinary, and not a reason to stop
> the trigger: it will be open again before the next one.

## `FireTrigger._ask_a_person`, [line 129](../../../../../../../backend/src/sro/application/trigger/fire_trigger.py#L129): Comment

Code: `logger.info(`

> Said out loud: a fire that produced no new card is a fire,
> and a rule that looks like it stopped firing is a rule
> somebody goes looking for a fault in.

## `FireTrigger._fire_a_job`, [line 168](../../../../../../../backend/src/sro/application/trigger/fire_trigger.py#L168): Comment

Code: `await uow.workflows.get(ctx.tenant_id, str(trigger.workflow_id))`

> Read for its existence and nothing else: a trigger whose job has
> been deleted since must not become a card asking somebody to approve
> a run of it, and the confirmation path returns before anything else
> would look. `start_job_for` reads it again for what it contains.

## `FireTrigger._fire_a_job`, [line 184](../../../../../../../backend/src/sro/application/trigger/fire_trigger.py#L184): Comment

Code: `logger.info("trigger %s did not start its job: %s", trigger.id, refused)`

> A closed laptop is a `Conflict` out of `StartWorkflowRun`, not a
> `DispatchFailed`: the job path has no dispatcher, it presses the
> same door the console does. Raised out of here it would reach the
> scheduler as a failed activity and be retried all night, which is
> what the skill path's catch has always existed to prevent -- and
> a browser being closed is the most ordinary thing there is.
>
> `RunRefused` too, and deliberately not a disable: a job whose
> cited evidence has aged out is refused today and proven again by
> the next pass that reads those gestures back.

## `FireTrigger._fire_a_job`, [line 186](../../../../../../../backend/src/sro/application/trigger/fire_trigger.py#L186): Comment

Code: `trigger.fired(now, run_id)`

> The run is already committed, on its own unit of work, and this is a
> second transaction. A failure in between leaves a run started and a
> trigger that does not know it fired, so the next tick fires again;
> two concurrent ticks both read the pre-`fired` row and both start.
>
> Left as two on purpose. Both outcomes are already caught downstream
> and caught better than a claim here would catch them: the partial
> unique index on running runs refuses a second run for the same
> browser, and `tool_calls.remember` refuses the same job's same write
> with the same values inside half an hour. A claim taken before the
> start would have to be released on every refusal path above --
> a closed laptop, an aged-out job -- and a released claim that missed
> one of them is an arrival trigger that silently drops the mail it
> was fired for.

## `start_for`, [line 224](../../../../../../../backend/src/sro/application/trigger/fire_trigger.py#L224): Comment

Code: `raise DispatchFailed("this trigger runs a job, not a skill")`

> `Trigger` names one or the other, and this is the skill half. A job
> goes to `start_job_for` above, which is not this function's business
> to reach into -- `FireTrigger` routes on the same field.

## `start_for`, [line 227](../../../../../../../backend/src/sro/application/trigger/fire_trigger.py#L227): Comment

Code: `run_id = ids.new_run_id()`

> Named before it starts, the same reason the console does this --
> `wait=False` alone is not fire-and-forget: the durable adapter's
> fast path only takes it once a run id is already there to
> return, and without one every fire blocked a worker activity
> slot for the run's full duration regardless of the flag.

## `start_for`, [line 240](../../../../../../../backend/src/sro/application/trigger/fire_trigger.py#L240): Comment

Code: `if dispatcher is None:`

> The channel to that browser is held by whichever process the extension
> connected to, and this is not that process.

## `start_for`, [line 250](../../../../../../../backend/src/sro/application/trigger/fire_trigger.py#L250): Comment

Code: `may_take_focus=trigger.may_take_focus,`

> Whether this fire may move the operator's tab. A schedule that runs
> at 3am has no business taking a screen, and a trigger the operator
> set up to watch may.

## `start_job_for`, [line 264](../../../../../../../backend/src/sro/application/trigger/fire_trigger.py#L264): Comment

Code: `named = authorized_by or (trigger.authorized_by.value if trigger.authorized_by else None)`

> The name is on the record already: `WorkflowRun.started_by` is the
> context's principal, which for a fire is the trigger's author and for an
> approved card is whoever pressed it.

## `start_job_for`, [line 266](../../../../../../../backend/src/sro/application/trigger/fire_trigger.py#L266): Comment

Code: `raise DispatchFailed("this trigger writes and names nobody who authorised it")`

> `Trigger` refuses this at creation. A row written before that check
> existed is still a row, and this is the last place to notice.

## `start_job_for`, [line 289](../../../../../../../backend/src/sro/application/trigger/fire_trigger.py#L289): Comment

Code: `await performing`

> Nothing to hold the task, so it is awaited rather than dropped: a
> coroutine created and discarded is a run that never happens, and
> "the trigger fired" would be a lie told with a run id.

## `_because`, [line 304](../../../../../../../backend/src/sro/application/trigger/fire_trigger.py#L304): Comment

Code: `article = "an" if trigger.kind.value[0] in "aeiou" else "a"`

> "an arrival trigger fired", not "a arrival trigger fired". The sentence
> is read by the person deciding whether to let a write out, and one that
> cannot manage its own article reads as a system that is guessing.
