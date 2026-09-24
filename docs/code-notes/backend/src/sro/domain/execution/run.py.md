# Notes for `backend/src/sro/domain/execution/run.py`

Comments and docstrings moved out of [`backend/src/sro/domain/execution/run.py`](../../../../../../../backend/src/sro/domain/execution/run.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/domain/execution/run.py#L1): Docstring

> One attempt to perform a skill against a live system.
>
> A run is the audit record. It exists before the first call is made and it is
> written to after every step, so a run that dies mid-flight still says exactly
> which calls were sent and which were not -- the question anybody asks first
> after an automated system touches a warehouse.

## `Medium`, [line 28](../../../../../../../backend/src/sro/domain/execution/run.py#L28): Note on the line above

Code: `TOOL = "tool"`

> A call through a connector the tenant configured, rather than a replay
> of one a demonstration produced.
>
> Its own word rather than NETWORK, though both are calls. A run record is
> read back months later to answer what actually happened, and one word
> meaning "the request the operator's own click made" in some records and
> "whatever a third party's connector decided to send" in others is a word
> that answers nothing. What they have in common -- deterministic, and
> checkable against a result -- is why `judge` treats them alike; what they
> do not is why a reader can tell them apart.

## `StepDisposition`, [line 41](../../../../../../../backend/src/sro/domain/execution/run.py#L41): Note on the line above

Code: `PERFORMED = "performed"`

> The call was sent and the system answered.

## `StepDisposition`, [line 43](../../../../../../../backend/src/sro/domain/execution/run.py#L43): Note on the line above

Code: `WITHHELD = "withheld"`

> A mutation the stage does not permit. Recorded in full, never sent --
> this is what a shadow run is for: proving what would happen.

## `StepDisposition`, [line 45](../../../../../../../backend/src/sro/domain/execution/run.py#L45): Note on the line above

Code: `SKIPPED = "skipped"`

> Nothing to do at this rung: the step has no network plan.

## `StepOutcome`, [line 60](../../../../../../../backend/src/sro/domain/execution/run.py#L60): Note on the line above

Code: `idempotency_key: str | None = None`

> Present for every mutating step, sent or withheld. Identifies the attempt
> so a retry can tell "already done" from "never started".

## `StepOutcome`, [line 62](../../../../../../../backend/src/sro/domain/execution/run.py#L62): Note on the line above

Code: `request_body: str | None = None`

> The body a write produced -- withheld, sent, or failed on the wire.
>
> A step that records only the method and the URL hides every decision
> induction made: which field became a parameter, what an optional one
> nobody supplied falls back to, whether a value landed in the right key.
> Withheld, that body exists nowhere else. Sent, "POST -> 201" says a record
> was created in a live warehouse and nothing about what is in it, and the
> review this system's safety rests on cannot be done. Failed, it is the only
> thing left to debug with, and the failure that says "the call may have
> arrived" is exactly when somebody needs to know what would have arrived.
>
> Writes only. A read's body is not what anybody reviews, and the UI medium
> has no body at all.

## `StepOutcome`, [line 66](../../../../../../../backend/src/sro/domain/execution/run.py#L66): Note on the line above

Code: `unchecked: tuple[str, ...] = ()`

> What this step asserts that nothing evaluated, and why.
>
> Empty means every post-condition the demonstration left here was actually
> tested. Anything else means the step was performed and not verified: it
> asserts nothing at all, or it asserts something no rung can see from where
> it ran, or the screen could not be read at the moment of looking.
>
> Beside ``assertion_failures`` rather than inside ``detail`` because the two
> are different facts and a rule has to be able to tell them apart. "Nothing
> failed" was read as "everything passed" by every caller that looked, and a
> step that checked nothing is exactly the step nothing should be learned
> from -- a version repaired on the strength of an unverified click is the
> system marking its own homework. A rule that reads free text is a rule any
> outcome can dress itself up to satisfy.

## `StepOutcome`, [line 68](../../../../../../../backend/src/sro/domain/execution/run.py#L68): Note on the line above

Code: `escalated_from: Medium | None = None`

> Set when a slower medium finished what a faster one could not. The run
> says which rung actually did the work, because a step that quietly needs the
> browser every time is a skill drifting from the system it was taught on.

## `StepOutcome`, [line 72](../../../../../../../backend/src/sro/domain/execution/run.py#L72): Note on the line above

Code: `plan_step: int | None = None`

> Which step of the version this was, when that is not ``index``.
>
> ``index`` is the position in the run's log, and for a skill without loops
> the two are the same number -- which is every skill taught before loops
> existed. A loop's body runs once per thing in a list, so the same step of
> the plan appears at several positions, and the run has to be able to say
> which one it was.

## `StepOutcome`, [line 74](../../../../../../../backend/src/sro/domain/execution/run.py#L74): Note on the line above

Code: `iteration: int = 0`

> Which time round the loop this was. Zero for everything else.

## `StepOutcome`, [line 76](../../../../../../../backend/src/sro/domain/execution/run.py#L76): Note on the line above

Code: `matched_by: str | None = None`

> Which locator strategy found the control, for a UI step. A step that only
> ever matches on the last fallback is about to break.

## `StepOutcome`, [line 78](../../../../../../../backend/src/sro/domain/execution/run.py#L78): Note on the line above

Code: `detail: str | None = None`

> Why it was withheld, skipped or failed. Never carries a response body.

## `StepOutcome`, [line 80](../../../../../../../backend/src/sro/domain/execution/run.py#L80): Note on the line above

Code: `unreachable: bool = False`

> This step failed because nothing was there to answer it.
>
> The call never left the machine, or left and nothing came back: a closed
> laptop, no tab open on the system, a connection that died before a response.
> Recorded as a flag rather than read back out of ``detail`` because the
> verdict turns on it -- a skill is not marked down for the state of somebody's
> browser -- and a rule that reads free text is a rule any failure can dress
> itself up to satisfy.
>
> Never set where the system answered. A 500 is an answer, and an answer is
> what a track record is about.

## `StepOutcome`, [line 82](../../../../../../../backend/src/sro/domain/execution/run.py#L82): Note on the line above

Code: `found_rows: int | None = None`

> How many records this response carried. Kept because a run that reports
> `GET … -> 200` has answered nothing: the number was in the response and was
> being thrown away.

## `StepOutcome`, [line 84](../../../../../../../backend/src/sro/domain/execution/run.py#L84): Note on the line above

Code: `found_total: int | None = None`

> How many exist, where the system said so beside the page.
>
> Distinct from ``found_rows`` because they disagree, and the disagreement is
> the whole point: 50 rows came back out of 330,140, and answering "how many
> suppliers are there" with 50 is a confident wrong number.

## `StepOutcome`, [line 86](../../../../../../../backend/src/sro/domain/execution/run.py#L86): Note on the line above

Code: `found_partial: bool = False`

> A page came back and nothing said how long the whole thing is. Then there
> is no count to report, and reporting one anyway is the failure this system
> exists to avoid.

## `StepOutcome`, [line 89](../../../../../../../backend/src/sro/domain/execution/run.py#L89): Note on the line above

Code: `found_values: tuple[tuple[str, tuple[str, ...]], ...] = ()`

> A few values each column holds, as pairs so this survives being stored.
>
> What the next question can be asked about: a column with three values is a
> filter somebody may want, and one nobody has to invent.

## `StepOutcome`, [line 91](../../../../../../../backend/src/sro/domain/execution/run.py#L91): Note on the line above

Code: `found_columns: tuple[str, ...] = ()`

> The columns of the result, in the order they should be shown. Carried
> because `jsonb` sorts an object's keys by length, so a row cannot be trusted
> to remember its own field order.

## `StepOutcome`, [line 93](../../../../../../../backend/src/sro/domain/execution/run.py#L93): Note on the line above

Code: `found_labels: tuple[str, ...] = ()`

> Each record as one readable line. Kept as text because `jsonb` sorts an
> object's keys by length, so the field ranking does not survive being
> stored.

## `StepOutcome`, [line 50](../../../../../../../backend/src/sro/domain/execution/run.py#L50): Note on the line above

Code: `@dataclass(frozen=True, slots=True)`

> Enough of the first records to recognise them. Bounded deliberately --
> this is an answer, not a copy of the customer's database.

## `Run`, [line 105](../../../../../../../backend/src/sro/domain/execution/run.py#L105): Docstring

> The aggregate. Steps are appended; nothing is ever rewritten.

## `Run`, [line 110](../../../../../../../backend/src/sro/domain/execution/run.py#L110): Note on the line above

Code: `stage: PromotionStage`

> The stage the skill was at when this ran. Copied, not referenced: a later
> promotion must not change the record of what was permitted at the time.

## `Run`, [line 116](../../../../../../../backend/src/sro/domain/execution/run.py#L116): Note on the line above

Code: `medium: Medium = Medium.NETWORK`

> The rung this run performs the task at. Recorded on the run rather than
> inferred from the steps, because "we ran this in a browser" is the first
> thing anybody asks about a run that behaved oddly.

## `Run`, [line 118](../../../../../../../backend/src/sro/domain/execution/run.py#L118): Note on the line above

Code: `device_id: DeviceId | None = None`

> The operator's own browser, when this run is performed there rather than
> in one the deployment owns.
>
> Recorded rather than resolved at each step: which browser a write went
> through is the first question about a run that touched the wrong record,
> and a device chosen fresh per step could answer it differently each time.

## `Run`, [line 120](../../../../../../../backend/src/sro/domain/execution/run.py#L120): Note on the line above

Code: `may_take_focus: bool = False`

> Whether this run is allowed to bring a tab to the front of the
> operator's browser.
>
> The trigger's decision, carried on the run because a run outlives the
> request that started it: a task somebody asked for and is watching may move
> their tab, and one a cron or a mail relay started at 3am may not. Default
> no -- a run that has not been told it may take somebody's screen has not
> been given permission to.

## `Run`, [line 122](../../../../../../../backend/src/sro/domain/execution/run.py#L122): Note on the line above

Code: `iterations: dict[str, list[dict[str, str]]] = field(default_factory=dict)`

> What each loop's body is to be run with, one entry per thing in the list.
>
> Written the moment the step that produces the list answers, because that is
> when the count exists at all -- and stored on the run rather than recomputed,
> so a run that resumes after a restart does the same iterations it started
> rather than whatever the system says now.

## `Run`, [line 124](../../../../../../../backend/src/sro/domain/execution/run.py#L124): Note on the line above

Code: `systems: tuple[str, ...] = ()`

> Every system this run touched, when that is more than one.
>
> `target_system` alone is where the work lands, and it is what a run is keyed
> by. For a workflow that also writes into a second system, being keyed by the
> first means the second's circuit breaker never sees the failure -- so the
> breaker is asked about all of them and, because of this, can be answered by
> all of them. Half a breaker protects nothing and reads as though it does.

## `Run`, [line 126](../../../../../../../backend/src/sro/domain/execution/run.py#L126): Note on the line above

Code: `target_system: str = ""`

> Which system this run wrote to.
>
> Copied from the skill rather than joined: the circuit breaker asks "how has
> this system behaved lately", and a join through a skill that has since been
> re-induced would answer a different question.

## `Run`, [line 128](../../../../../../../backend/src/sro/domain/execution/run.py#L128): Note on the line above

Code: `authorized_by: PrincipalId | None = None`

> Who authorised writes for this run. Required above shadow; a run that
> changed a warehouse names the human who allowed it.

## `Run`, [line 130](../../../../../../../backend/src/sro/domain/execution/run.py#L130): Note on the line above

Code: `derived: dict[str, str] = field(default_factory=dict)`

> Values read out of one step's response for a later step to use.
>
> Kept on the run rather than in memory because a run survives the process:
> the step that needs the item number may execute in a different worker from
> the step that read it. It is also the honest audit answer to "what value did
> it actually send", which the parameters alone cannot give.

## `Run`, [line 132](../../../../../../../backend/src/sro/domain/execution/run.py#L132): Note on the line above

Code: `may_change_the_system: bool = True`

> Whether the skill being run sends anything but reads.
>
> Authorisation is for changing a system. A read-only skill demanded a named
> human and told them it "performs real writes" while fetching a list -- untrue,
> and the kind of prompt that teaches people to click past prompts.

## `Run`, [line 139](../../../../../../../backend/src/sro/domain/execution/run.py#L139): Note on the line above

Code: `revisions: tuple[tuple[str, str, datetime], ...] = ()`

> Every value the operator changed while this was running: name, what they
> changed it to, and when.
>
> `parameters` alone would say what the later steps used but not that anybody
> chose it, and a run that wrote the wrong record is read afterwards by
> somebody asking exactly that. Append-only, like the steps: a second thought
> about the same name is another entry rather than an edit of the first.

## `Run`, [line 141](../../../../../../../backend/src/sro/domain/execution/run.py#L141): Note on the line above

Code: `wrong_because: str | None = None`

> Why the person this ran for said the result was wrong.
>
> `judge` reads statuses, media and escalations, and every one of them can be
> clean while the record the run created is not the one anybody wanted. That
> is the failure the ladder cannot see on its own, and the only witness is
> whoever was looking at the screen.
>
> Collected as an undo they wanted rather than as a question they answered:
> the press that takes the record back is the same press that says it was
> wrong, so being honest costs them nothing.

## `Run`, [line 143](../../../../../../../backend/src/sro/domain/execution/run.py#L143): Note on the line above

Code: `intent: str = ""`

> The sentence the operator typed to ask for this run, where one started it.
>
> `SkillStep.intent` is derived from what was observed and reads the same on
> every replay; this is the opposite kind of thing -- a transcript of what one
> person asked for, once. It is the audit answer to "why did this run happen
> at all", which nothing else on a run or its skill can give, and it lives
> here rather than in a second store because a run already outlives the
> request that started it and a second table would just be a join that can
> drift from this one.
>
> Blank for every run that did not begin with somebody typing a sentence: a
> console run against a chosen version, a batch, a trigger firing on its own
> schedule. Nobody asked those in words, so there is nothing to keep.

## `StepOutcome.step_index`, [line 100](../../../../../../../backend/src/sro/domain/execution/run.py#L100): Docstring

> The version step this outcome belongs to.

## `Run.writes_sent`, [line 161](../../../../../../../backend/src/sro/domain/execution/run.py#L161): Docstring

> Mutating steps that actually went out. What the blast radius counts.

## `Run.performs_writes`, [line 169](../../../../../../../backend/src/sro/domain/execution/run.py#L169): Docstring

> Whether this run's stage permits a mutation to leave the process.
>
> Shadow is the rehearsal rung: every read is real, every write is
> recorded and withheld. That is the whole difference between the two.

## `Run.values`, [line 173](../../../../../../../backend/src/sro/domain/execution/run.py#L173): Docstring

> Everything a template may reference: what was asked for, plus what
> the system has said so far.

## `Run.iterations_of`, [line 187](../../../../../../../backend/src/sro/domain/execution/run.py#L187): Docstring

> None where the list has not arrived yet, which is every moment
> before the step that produces it has answered.

## `Run.fail`, [line 207](../../../../../../../backend/src/sro/domain/execution/run.py#L207): Docstring

> End a run that could not continue, as opposed to one that ran and
> failed its checks. Both are FAILED; only this one has a reason that is
> not about assertions.

## `Run.called_wrong`, [line 216](../../../../../../../backend/src/sro/domain/execution/run.py#L216): Docstring

> The person this ran for says the result was wrong.
>
> Once. The first answer is the one they gave while looking at what it
> made; a second one later is somebody rewriting the record, and the
> track record has already been told.

## `Run.revise`, [line 227](../../../../../../../backend/src/sro/domain/execution/run.py#L227): Docstring

> Change what the steps still to come will run with.
>
> A run is watched while it happens, and a step that has not been sent can
> still be argued with -- the address was wrong, or the mail never said
> which one. What has already gone to the warehouse has gone: steps record
> what they sent, and nothing here rewrites them.
>
> Recorded as well as applied. "Who decided this run would use A000221"
> is the first question about a run that wrote the wrong thing, and the
> answer belongs on the run rather than in a log somewhere else.
>
> A name the skill never declared is refused rather than stored. It would
> reach nothing -- every step renders from the names its plan carries --
> so accepting it would record a decision with no effect, which reads
> afterwards as a change that was made and then ignored.
