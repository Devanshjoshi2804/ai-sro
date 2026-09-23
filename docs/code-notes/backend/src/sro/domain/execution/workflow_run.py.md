# Notes for `backend/src/sro/domain/execution/workflow_run.py`

Comments and docstrings moved out of [`backend/src/sro/domain/execution/workflow_run.py`](../../../../../../../backend/src/sro/domain/execution/workflow_run.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/domain/execution/workflow_run.py#L1): Docstring

> What a run leaves behind. *Why did it do that* has a file.
>
> The rig's `Run`, renamed: `sro.domain.execution.run.Run` is already the
> backend's own word for a different thing. Mutable, unlike most of this layer,
> because a run is written step by step -- the runner appends to `steps` as it
> goes and the orphan sweep rewrites the last verdict of a run nobody is driving.

## module, [line 6](../../../../../../../backend/src/sro/domain/execution/workflow_run.py#L6): Note on the line above

Code: `OUTCOMES = ("running", "held", "stopped", "refused", "aborted", "failed")`

> running: in flight. held: every step held. stopped: a step failed twice and
> the run stopped to ask. refused: a planned command named an origin outside the
> allowlist, or the step budget ran out. aborted: the stop button. failed: the
> browser went away.

## module, [line 8](../../../../../../../backend/src/sro/domain/execution/workflow_run.py#L8): Note on the line above

Code: `VERDICTS = (`

> awaiting: shown to a person and waiting on their word. done_by_operator: the
> operator performed it themselves before the rig was asked to finish the job.
> not_needed: the step existed to put a form on the screen and the write that
> form was for is going out as a call, so there is no form and nothing to fill.
>
> `not_needed` is the only verdict that means the rig DELIBERATELY did not do a
> step and the job is still whole, which is why it is not `skipped` -- `skipped`
> is the record's starting value and reads as "nobody got to it".

## `already_running`, [line 21](../../../../../../../backend/src/sro/domain/execution/workflow_run.py#L21): Docstring

> One browser, one hand -- said once, because two places discover it.
>
> The press reads `in_flight` and refuses, which is the friendly answer and
> the one that happens almost every time. The unique partial index on
> `(tenant_id, device_id) WHERE outcome = 'running'` refuses the ones that
> got past that read: between it and the commit there are two more awaits,
> and on one event loop a second press can be scheduled in either of them.
>
> The two must be indistinguishable. A caller able to tell "you were late"
> from "you lost a race" learns whether this deployment has a lock, and a
> refusal that reads differently on the rare path is a refusal nobody has
> ever seen rendered. So the sentence is here rather than spelled twice --
> the domain owns what the refusal says, and the two discoverers agree by
> construction rather than by somebody remembering.
>
> `run_id` is optional for one case only: the index refused the claim and the
> winner finished before the losing side could read back which run it was.

## `new_run_id`, [line 25](../../../../../../../backend/src/sro/domain/execution/workflow_run.py#L25): Docstring

> A workflow run's id -- and NOT an `sro.domain.shared.identifiers.RunId`.
>
> Same shape as `UuidFactory.new_run_id`: `run_` followed by 32 hex
> characters. Two id spaces that look alike -- that one names a row in the
> backend's own `runs`, this one a row in `workflow_runs` -- so a string that
> round-trips through the wrong repository will be looked up, found missing,
> and read as a run that does not exist rather than as a type error. The
> shape is the rig's and stays; the types are what keep them apart.

## `RunStep`, [line 30](../../../../../../../backend/src/sro/domain/execution/workflow_run.py#L30): Docstring

> One step of a run, as the panel and the register read it afterwards.
>
> `sent` is what was planned, not proof that it went out: a step parked on a
> person carries the command a tap would release, and `verdict == "awaiting"`
> is what tells the two apart. A reader treating `sent` as "this reached the
> warehouse" would report an unapproved write as a performed one.

## `RunStep`, [line 31](../../../../../../../backend/src/sro/domain/execution/workflow_run.py#L31): Note on the line above

Code: `order: int`

> Where this row sits in the run, and unique within it -- which is what
> the table's own key needs. The same thing as the workflow step's order for
> a job that does one thing once; for a job whose middle repeats, the second
> pass through the body is further along even though it is the same step.

## `RunStep`, [line 50](../../../../../../../backend/src/sro/domain/execution/workflow_run.py#L50): Note on the line above

Code: `notes: list[str] = field(default_factory=list)`

> What is already known about the values this step is about to write.
>
> Read off the knowledge base's `field` claims -- the vendor's own
> documentation, 404 of them -- and put in front of the person who taps
> Approve. Today one rule fills it: a value longer than the field holds,
> which is the sharpest instance of the one failure the ladder cannot see,
> because the warehouse answers 201 either way.
>
> A note and never a refusal. See `sro.domain.execution.field_notes`.

## `RunStep`, [line 52](../../../../../../../backend/src/sro/domain/execution/workflow_run.py#L52): Note on the line above

Code: `made: dict[str, str] = field(default_factory=dict)`

> What the warehouse called the record this step created, where it made
> one. Empty for every step that created nothing, which is most of them.
>
> The only place this exists: the panel says which records a run made, and
> an undo -- the day a tenant's evidence shows one being deleted -- has to
> address them by whatever the system called them.

## `RunStep`, [line 54](../../../../../../../backend/src/sro/domain/execution/workflow_run.py#L54): Note on the line above

Code: `of_step: int = 0`

> Which step of the JOB this is. `order` says where in the run it happened
> and these are the same number until a job repeats its middle.

## `RunStep`, [line 56](../../../../../../../backend/src/sro/domain/execution/workflow_run.py#L56): Note on the line above

Code: `item: int | None = None`

> Which thing on the list this was done for, counting from zero, or None
> for a step done once. What the panel says "item 3 of 5" from.

## `WorkflowRun`, [line 73](../../../../../../../backend/src/sro/domain/execution/workflow_run.py#L73): Note on the line above

Code: `items: list[dict[str, str]] = field(default_factory=list)`

> The things this run was asked to do the repeated block for, in order.
>
> A request input like `from_step`, never a progress marker: the runner reads
> it and does not write it. Empty is a run of a job that does one thing once,
> and a run of a REPEATING job given no items does its body once with the
> run's own values -- which is the same thing a job with no repeat does, and
> the reason nothing else in the loop had to learn about repeats.

## `WorkflowRun`, [line 75](../../../../../../../backend/src/sro/domain/execution/workflow_run.py#L75): Note on the line above

Code: `from_step: int = 0`

> How many steps the operator performed themselves before the offer was
> made. A request input, not a progress marker: the runner never advances it.
> Kept on the row because it is the fourth thing a press asks for, and a
> re-press that carries a different one finishes a different job under this
> run's id -- steps redone against a live warehouse, or steps nobody did
> recorded as done.

## `WorkflowRun`, [line 78](../../../../../../../backend/src/sro/domain/execution/workflow_run.py#L78): Note on the line above

Code: `withheld: list[dict[str, object]] = field(default_factory=list)`

> The writes a dry run produced and did not send, in full. This is what a
> person reads before pressing through to live.

## `WorkflowRun`, [line 86](../../../../../../../backend/src/sro/domain/execution/workflow_run.py#L86): Note on the line above

Code: `watched: bool = False`

> Whether somebody is standing in front of this run.
>
> The system has two ways to do the same job and they are not
> interchangeable. Replaying the call is fast, deterministic and invisible:
> the steps that only put the form on the screen are skipped, and the record
> appears without anything moving. Performing it is slower, costs a reading
> per step, and is the one a person can WATCH -- the fields fill, the button
> is pressed, and somebody at the screen can see their job being done and
> stop it.
>
> Written on the row rather than decided per step, because deciding per step
> is how a run came to skip the typing (it was going to post) and then press
> Save as if it had typed. One decision, for the whole run.
>
> A press in an open panel means "show me". A trigger at three in the morning
> means "just do it".

## `WorkflowRun`, [line 88](../../../../../../../backend/src/sro/domain/execution/workflow_run.py#L88): Note on the line above

Code: `doing: str = ""`

> What this run is doing when it has no step to show for it.
>
> Everything a run does is a step, with one exception: the gather runs BEFORE
> the first step, because a value nobody typed has to be found before
> anything can be planned with it. Measured on the deployment 2026-09-16 --
> an operator pressed "Yes, do it" and the card said "Step 0" for three and a
> half minutes while the run read their mailbox and the model retried a 5xx.
> The run was working the whole time and nothing anywhere said so.
>
> One line, in the words somebody watching would use, written before the
> looking starts and cleared when it ends. Empty for every run that only ever
> did its steps, which is what a run normally is.

## `WorkflowRun`, [line 90](../../../../../../../backend/src/sro/domain/execution/workflow_run.py#L90): Note on the line above

Code: `gathered: dict[str, dict[str, str]] = field(default_factory=dict)`

> Parameter -> where its value was read, for values nobody typed.
>
> A value the operator typed into the press needs no provenance: they are
> standing there and they meant it. A value read out of a mailbox is only as
> good as the message it came from, and both the person approving the write
> and an audit a month later have to be able to go and look -- so the message
> id and the span it was quoted from are kept beside the run.
>
> Empty for every run whose values came from a person, which is most of them
> and all of them before 2026-09-16.

## `WorkflowRun`, [line 92](../../../../../../../backend/src/sro/domain/execution/workflow_run.py#L92): Note on the line above

Code: `unasked: list[str] = field(default_factory=list)`

> What the request asked for that this job declares no parameter for.
>
> A job's parameters are what two doings proved VARY. `Create a Customer
> Type` declares two, because its two demonstrations differed in two fields
> and nothing else -- and the form has a dozen more, every one of them an
> ordinary thing for somebody to ask for.
>
> Ask for one and the run makes a record without it. That is right: nothing
> demonstrated that slot, and a run that wrote into it would be guessing at a
> warehouse. Saying nothing about it is not right, and it is the shape of
> every fault here worth having -- three things asked for, two in the record,
> and nothing naming the third.
>
> Names and never values. This is read by a panel and a log, and what
> somebody wrote in their own mail is theirs.

## `WorkflowRun`, [line 94](../../../../../../../backend/src/sro/domain/execution/workflow_run.py#L94): Note on the line above

Code: `needs: list[str] = field(default_factory=list)`

> What this run could not find a value for, and stopped to ask about.
>
> The run goes and looks for whatever nobody typed. When the looking comes
> back short the run ends -- it must, because a write with a blank in it is a
> wrong record -- and until now that was the end of the whole thing: the
> operator read "nobody gave a value for X, and your mail does not say
> either" and started over.
>
> So the names are kept, and what happens next is a question in their own
> conversation rather than a dead row. One question per value, in words; the
> answers come back as an ordinary sentence and the job runs with the full
> set on the yes they already gave.
>
> Empty for every run that found everything, which is nearly all of them.

## `WorkflowRun`, [line 96](../../../../../../../backend/src/sro/domain/execution/workflow_run.py#L96): Note on the line above

Code: `undoes_run: str | None = None`

> The run this one takes back, where it is an undo of one.
>
> The first place two jobs in this system are one piece of work. Pressing
> `Undo it` starts an ordinary run of an ordinary mined job, which is right --
> it goes through the same ladder, gate and belts as anything else -- and
> leaves the two with nothing between them: the delete goes off alone, and if
> it fails, the card that offered it is gone and nobody knows the record is
> still there.
>
> An id and never a status. Whether the undo worked is this run's own
> outcome, read where every other outcome is read.

## `WorkflowRun`, [line 98](../../../../../../../backend/src/sro/domain/execution/workflow_run.py#L98): Note on the line above

Code: `asked_the_asker: bool = False`

> Whether this run has already written to whoever sent the request.
>
> One mail per run, and read off the row rather than counted in a process: a
> worker that restarted between one stop and the next would otherwise buy
> somebody a second mail about one request. A mail cannot be unsent.

## `WorkflowRun`, [line 100](../../../../../../../backend/src/sro/domain/execution/workflow_run.py#L100): Note on the line above

Code: `awaiting: dict[str, str] | None = None`

> The outside conversation this run ended waiting to hear back on.
>
> A run that comes up short asks, and until now it could only ask the person
> with the panel open. The person who knows the answer is often somebody
> else -- whoever sent the mail that asked for the job -- and an answer that
> arrives in a mailbox has to be able to find the run waiting for it.
>
> None for every run nobody outside was asked about. See
> `domain/execution/waiting.py`, which holds the deadline: a pause with no
> end to it is not a pause.

## `WorkflowRun`, [line 102](../../../../../../../backend/src/sro/domain/execution/workflow_run.py#L102): Note on the line above

Code: `wrong_because: str | None = None`

> What the operator said was wrong with what this run made.
>
> The one failure the ladder cannot see. A step is settled by what the
> warehouse answered and, where the evidence records a read, by what that
> read showed -- and a record created exactly as asked that was not the
> record the person wanted passes both. A job read out of a sentence can be
> the wrong job, and the warehouse answers 201 for it.
>
> So the only witness is the person whose browser it ran in, and this is
> where what they said is kept. Null on every run nobody has reported, which
> is almost all of them.
