# Notes for `backend/src/sro/application/trigger/create_trigger.py`

Comments and docstrings moved out of [`backend/src/sro/application/trigger/create_trigger.py`](../../../../../../../backend/src/sro/application/trigger/create_trigger.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/trigger/create_trigger.py#L1): Docstring

> Putting a task on a clock.
>
> Everything that can be refused is refused here rather than at three in the
> morning: a skill that has never earned a stage that may run, values the skill
> declares and nobody supplied, a write with nobody's name on it. A trigger that
> exists is a trigger that would work.

## `TriggerRefused`, [line 19](../../../../../../../backend/src/sro/application/trigger/create_trigger.py#L19): Docstring

> This trigger will not be created, and the reason is about the skill or
> the authority rather than about the request being malformed.

## `NewTrigger`, [line 26](../../../../../../../backend/src/sro/application/trigger/create_trigger.py#L26): Note on the line above

Code: `workflow_id: str | None = None`

> What this will run. Exactly one, refused below rather than by an
> `InvariantViolation` from `Trigger` -- a caller naming both deserves a
> sentence about it, not a 500.

## `NewTrigger`, [line 32](../../../../../../../backend/src/sro/application/trigger/create_trigger.py#L32): Note on the line above

Code: `from_message: tuple[str, ...] = ()`

> Parameters a message that fires this may name -- an order number in a
> mail. Everything not listed here is fixed at creation, so a relay cannot
> point a warehouse read at another facility.

## `NewTrigger`, [line 34](../../../../../../../backend/src/sro/application/trigger/create_trigger.py#L34): Note on the line above

Code: `watch: Watch | None = None`

> What makes a mail one of these, for a trigger the operator's own browser
> evaluates. The names it reads are its `from_message`; there is no second
> list to keep in step.

## `NewTrigger`, [line 36](../../../../../../../backend/src/sro/application/trigger/create_trigger.py#L36): Note on the line above

Code: `arrival: Arrival | None = None`

> The page whose arrival fires it -- the other rule a browser holds. An
> operator standing on the page where a job starts, saying "do this here".

## `NewTrigger`, [line 40](../../../../../../../backend/src/sro/application/trigger/create_trigger.py#L40): Note on the line above

Code: `authorized_by: bool = False`

> Whether the caller is standing behind every run this will start. The
> name comes from their credential, never from the request.

## `NewTrigger`, [line 45](../../../../../../../backend/src/sro/application/trigger/create_trigger.py#L45): Note on the line above

Code: `asks: bool = False`

> This watch asks a question rather than running anything. No skill and no
> job, because there is nothing to name: the mail carries a question and the
> answer is somewhere in the systems the operator works in.

## `CreateTrigger._for_a_question`, [line 147](../../../../../../../backend/src/sro/application/trigger/create_trigger.py#L147): Docstring

> A watch that asks rather than runs.
>
> The checks a job trigger makes are all about the thing it runs, and
> there is nothing here to check them against: no version to have earned
> a stage, no parameters to be missing, no write to authorise. What is
> left is what this kind can get wrong -- being asked of a browser that
> is not there, or being given no question to ask -- and the second is
> `Trigger`'s own invariant, checked here so a caller reads a sentence
> rather than a 500.

## `CreateTrigger._for_a_job`, [line 178](../../../../../../../backend/src/sro/application/trigger/create_trigger.py#L178): Docstring

> A trigger on a mined job.
>
> The checks are the ones this moment knows and a later one cannot. The
> job exists -- a schedule for one this tenant does not have is refused
> here rather than at 3am. It runs in a browser, because a workflow is a
> recording of somebody's own window and there is no headless path for one
> on the extension -- unless the tenant runs on Steel
> (`StartWorkflowRun.runs_on_steel`), where the server drives the run and no
> browser is named. An arrival or a watch always needs one: a browser is what
> sees those fire. And every parameter it declares has a value,
> from the trigger or from whatever fires it: `StartWorkflowRun` refuses
> a job with one left blank, which for a schedule means failing at 3am
> every night instead of being refused once, now, in front of a person.
>
> `writes` is True for a job and is not computed from its steps. It is a
> standing authority to drive somebody's browser through a recording of
> real work, and the honest reading of that is "this changes things" --
> so it needs a name behind it. What decides whether the write actually
> goes out unattended is not this flag at all: it is `earned`, three live
> runs whose every write a state belt verified, checked per run.

## `CreateTrigger.__init__`, [line 63](../../../../../../../backend/src/sro/application/trigger/create_trigger.py#L63): Comment

Code: `self._can_gather = can_gather`

> Whether a run can go and find a value nobody supplied. The same pair
> `start_workflow_run` builds its gather out of, asked here so this
> door and the run door make the same judgement: a deployment with no
> mailbox still refuses a trigger whose job would fail at 3am.

## `CreateTrigger.execute`, [line 80](../../../../../../../backend/src/sro/application/trigger/create_trigger.py#L80): Comment

Code: `raise TriggerRefused("only a mined job can be started by arriving somewhere")`

> Only a mined job, for now. A job knows the page it starts on --
> the candidate carried it before the job existed -- and a taught
> skill does not: there would be nothing to check the rule against,
> so "do this here" could name any page and fire on the wrong one
> forever. Refused rather than half-built.

## `CreateTrigger.execute`, [line 91](../../../../../../../backend/src/sro/application/trigger/create_trigger.py#L91): Comment

Code: `supplied = request.watch.reads if request.watch else request.from_message`

> A watch names the values it supplies by where it reads them out
> of the mail. One list, checked the same way -- a value pointed at
> a parameter this skill does not have is the same silent typo.

## `CreateTrigger.execute`, [line 95](../../../../../../../backend/src/sro/application/trigger/create_trigger.py#L95): Comment

Code: `raise TriggerRefused(`

> A typo here is silent otherwise: the mail's value is dropped
> for having the wrong name, and the trigger fires with nothing
> every time until somebody reads a run.

## `CreateTrigger.execute`, [line 105](../../../../../../../backend/src/sro/application/trigger/create_trigger.py#L105): Comment

Code: `raise TriggerRefused(`

> A trigger with a value missing fails every single time it
> fires, and nobody is watching when it does.

## `CreateTrigger.execute`, [line 116](../../../../../../../backend/src/sro/application/trigger/create_trigger.py#L116): Comment

Code: `trigger = Trigger(`

> A write that fires with nobody there used to be refused outright,
> because there was nowhere to ask. There is now: the fire becomes
> a card in `confirmations` and the run starts when somebody
> answers it, with their name on it. `auto_approve` remains the
> other honest answer -- a named person saying in advance that this
> one need not be asked about.

## `CreateTrigger.execute`, [line 140](../../../../../../../backend/src/sro/application/trigger/create_trigger.py#L140): Comment

Code: `await self._scheduler.schedule(trigger)`

> Before the commit, deliberately. A schedule for a trigger that
> was never stored fires once, finds nothing, and removes
> itself; a stored trigger with no schedule is a task somebody
> believes is covered and is not.

## `CreateTrigger._for_a_question`, [line 169](../../../../../../../backend/src/sro/application/trigger/create_trigger.py#L169): Comment

Code: `writes=False,`

> Neither, and both for the same reason: a read writes nothing, so
> there is no write to authorise and no card to ask anybody for.

## `CreateTrigger._for_a_job`, [line 182](../../../../../../../backend/src/sro/application/trigger/create_trigger.py#L182): Comment

Code: `workflow = await uow.workflows.get(ctx.tenant_id, str(request.workflow_id))`

> `get` raising is the existence check: a schedule for a job this
> tenant does not have is refused here rather than at 3am.

## `CreateTrigger._for_a_job`, [line 184](../../../../../../../backend/src/sro/application/trigger/create_trigger.py#L184): Comment

Code: `raise TriggerRefused("an arrival trigger needs the page it fires on")`

> The kind and the rule are one decision. A row with the kind
> and no page would be refused by `Trigger` as a 500 out of a
> route; here it is a sentence the caller can act on.

## `CreateTrigger._for_a_job`, [line 190](../../../../../../../backend/src/sro/application/trigger/create_trigger.py#L190): Comment

Code: `raise TriggerRefused(`

> Every declared parameter is required: `StartWorkflowRun`
> refuses a press that leaves one blank, because the planner
> would otherwise fall back to the value the RECORDING happened
> to contain and do the job with somebody else's client code.
>
> Unless something can go and find it. The same relaxation the
> run door makes and for the same reason: a deployment that can
> read the operator's mailbox has a second answer, and refusing
> here would mean a watch on "create a customer type" could only
> be made by somebody willing to map `customertype-longDescription`
> onto a line of the mail by hand. What it cannot find, it
> refuses at the step, with the names on the card.

## `CreateTrigger._for_a_job`, [line 223](../../../../../../../backend/src/sro/application/trigger/create_trigger.py#L223): Comment

Code: `watch=request.watch,`

> The rule a mail is recognised by. Carried here since a watch
> may name a job: without it the row would be a watch that
> matches nothing, which is a trigger that silently never fires.

## `CreateTrigger._for_a_job`, [line 237](../../../../../../../backend/src/sro/application/trigger/create_trigger.py#L237): Comment

Code: `await self._scheduler.schedule(trigger)`

> Before the commit, for the reason the skill path gives: a
> schedule for a trigger that was never stored fires once and
> removes itself, and a stored trigger with no schedule is a
> task somebody believes is covered and is not.
