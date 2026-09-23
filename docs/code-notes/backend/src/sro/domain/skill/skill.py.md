# Notes for `backend/src/sro/domain/skill/skill.py`

Comments and docstrings moved out of [`backend/src/sro/domain/skill/skill.py`](../../../../../../../backend/src/sro/domain/skill/skill.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/domain/skill/skill.py#L1): Docstring

> Skill aggregate. See docs/06-glossary.md#skill.

## `SkillStep`, [line 24](../../../../../../../backend/src/sro/domain/skill/skill.py#L24): Note on the line above

Code: `tool_plan: ToolPlan | None = None`

> Somebody mapped this step onto a connector's tool. Beside the other two
> rather than instead of them: a step that can be a call, a gesture *and* a
> tool call is one a run can perform three ways, and which it took is what
> the medium on the outcome says.

## `SkillStep`, [line 28](../../../../../../../backend/src/sro/domain/skill/skill.py#L28): Note on the line above

Code: `narration: str = ""`

> What the operator said while doing this step.
>
> Kept apart from ``intent`` on purpose: intent is derived from what was
> observed and is the same on every replay, narration is a transcript and is
> a model's reading of a microphone. One field holding either would make them
> indistinguishable at review, which is where the difference matters most.

## `SkillStep`, [line 30](../../../../../../../backend/src/sro/domain/skill/skill.py#L30): Note on the line above

Code: `branch_hint: str | None = None`

> A path the operator described but did not demonstrate. A question for a
> reviewer -- never executed, because nothing was recorded doing it.

## `SkillStep`, [line 33](../../../../../../../backend/src/sro/domain/skill/skill.py#L33): Note on the line above

Code: `of_doings: int = 0`

> How many demonstrations of this task contained this step, out of how
> many were aligned. `0 of 0` is a step from a version induced before this
> was recorded, or one nothing counted.
>
> A count and not a verdict. Induction already refuses a pair that disagrees
> about what the task is, and keeps a step both demonstrations made even when
> the wider set is thinner -- and until now it said so only in a log line
> nobody reads. A reviewer looking at a step that three of four doings made
> is looking at the one fact that decides whether it belongs, which is what
> conformance checking has shipped as a graded fitness score since 2010
> while this gate stayed binary.
>
> Never read by the runner. What a step's rarity MEANS is settled at
> induction by `standing_of`, from these same counts and from the
> parameterisation; a run re-deciding it from a number on the step would be
> a second opinion about a question already answered with more evidence.

## `SkillStep`, [line 35](../../../../../../../backend/src/sro/domain/skill/skill.py#L35): Note on the line above

Code: `when: str | None = None`

> The parameter whose presence decides whether this step happens at all.
>
> A form's optional field: one demonstration typed here and the other left it
> alone, and both created the record. Supplied, the step runs; left out, it is
> skipped and the field goes over the wire the way the demonstration that
> skipped it sent it.

## `Provenance`, [line 63](../../../../../../../backend/src/sro/domain/skill/skill.py#L63): Docstring

> Where a version came from. Never optional.

## `Provenance`, [line 64](../../../../../../../backend/src/sro/domain/skill/skill.py#L64): Note on the line above

Code: `recording_ids: tuple[RecordingId, ...]`

> The demonstrations this version descends from.
>
> Descends from, not "were performed against it": a repaired version carries
> the recordings of the version it repairs, because every value it sends and
> every step but one came from them and how many there were is a live safety
> rule -- ``from_one_demonstration`` decides whether a write skill's values
> were ever diffed, and a version that dropped them would read as diffed and
> climb a rung nobody meant it to. What that field must not do is imply
> somebody demonstrated *this* version, and ``repaired_from`` below is how a
> reviewer tells the two apart without reading prose.

## `Provenance`, [line 67](../../../../../../../backend/src/sro/domain/skill/skill.py#L67): Note on the line above

Code: `induced_by: PrincipalId`

> Who produced this version. ``drift-repair`` where the system did, which
> is not a person and does not pretend to be one.

## `Provenance`, [line 71](../../../../../../../backend/src/sro/domain/skill/skill.py#L71): Note on the line above

Code: `repaired_from: str | None = None`

> The run that closed the evidence a repair adopted, where no demonstration
> produced this version at all.
>
> A field of its own rather than a sentence in ``note``: "was this written by
> a person or by the system" is the first question anybody asks about a
> version that changed itself, and an answer only prose can give is an answer
> no screen and no query can filter on.
>
> A run id as text, not a ``RunId``: an execution is a different aggregate,
> and a skill importing one to name it would point the dependency the wrong
> way round for the sake of a type.

## `Provenance`, [line 73](../../../../../../../backend/src/sro/domain/skill/skill.py#L73): Note on the line above

Code: `aligned_recording_ids: tuple[RecordingId, ...] = ()`

> Which of ``recording_ids`` shaped the *steps* -- the subset ``align_all``
> actually diffed, as opposed to the ones read only for what they proved a
> parameter could be.
>
> The distinction this field exists to hold: a version induced from four
> demonstrations used to cite all four in ``recording_ids`` whether or not a
> given one ever touched a step, and a reader checking why a skill declared a
> parameter no step could fill had no way to see that two of the four never
> reached the steps at all -- only the parameters. Both the four and the
> fewer were true and told apart nowhere.
>
> A subset of ``recording_ids`` rather than a second list, so the two can
> never drift into naming different recordings by construction; the
> invariant below is what keeps that true rather than a docstring's word for
> it.
>
> Empty for every version induced before this field existed, and empty is
> not a claim that none of its recordings shaped the steps -- it is the
> honest admission that nobody wrote down which ones did. Reading it as
> "zero" would be the exact mistake this field was added to stop: a false
> claim standing in for missing data.
>
> One case a reader has to know to interpret this correctly rather than
> guess: where the pair looped, `InduceSkill` deliberately excludes the rest
> of the history from `align_all` -- see ADR 015 -- so a looping version's
> ``aligned_recording_ids`` is only the pair, never the whole of
> ``recording_ids``, on purpose. The other demonstrations are still cited,
> because they still proved parameters; they just never got a say in what
> the steps are, and this field is where that says so.

## `SkillVersion`, [line 88](../../../../../../../backend/src/sro/domain/skill/skill.py#L88): Docstring

> One revision. Steps and parameters are fixed; only the stage moves.

## `SkillVersion`, [line 97](../../../../../../../backend/src/sro/domain/skill/skill.py#L97): Note on the line above

Code: `promoted_from: str = ""`

> Where the review that put this version at its current stage happened.
> Every writer names itself, so blank means exactly one thing: nobody has.
>
> - `"console"` -- somebody sitting down with the evidence, through
>   `PromoteSkill`.
> - `"preview"` -- an operator reading the steps and the values in the
>   panel and pressing once, at the screen it will act on, with a stop
>   button in front of them.
> - `"earned"` -- `earn()`. Not a review at all: the streak did it, and
>   nobody was asked. Kept apart from blank for the same reason
>   `promoted_by` is `None` here rather than some system principal -- a
>   streak is a basis, and writing nothing would make it indistinguishable
>   from a version nobody has looked at.
> - `"repair"` -- `repair_drift`'s inherited climb back to the rung the
>   version it replaced had earned. Mechanical, not a person's read of this
>   version; the person is `REPAIR`, the review is nobody's.
> - `""` -- `demote()`, disambiguated by `demotion_reason` rather than by
>   this field; the three places a version is reset to `RECORDED` for a
>   fresh review (`map_step_to_tool`, `add_assertion`, `repair_drift`'s new
>   version before it climbs back up); and every row written before this
>   field existed.
>
> `"console"` and `"preview"` are both reviews, and the second is a real
> reading of what the ladder asks for -- but they are not the same review,
> and somebody auditing a library has to be able to tell them apart and
> disagree with one of them. A value that has to be decoded by joining it
> to `promoted_by` or `stage` is not one a reviewer can filter a list by,
> which is why every writer, including the ones with no human in them,
> names itself rather than leaving blank to mean more than one thing.

## `SkillVersion`, [line 99](../../../../../../../backend/src/sro/domain/skill/skill.py#L99): Note on the line above

Code: `track_record: TrackRecord = field(default_factory=TrackRecord)`

> What this version has actually done. Autonomy is earned from this, never
> granted by a click.

## `SkillVersion`, [line 101](../../../../../../../backend/src/sro/domain/skill/skill.py#L101): Note on the line above

Code: `summary: str = ""`

> What this version does, in a sentence.

## `SkillVersion`, [line 103](../../../../../../../backend/src/sro/domain/skill/skill.py#L103): Note on the line above

Code: `demotion_reason: str | None = None`

> Why this version was pulled back down, when it was.

## `SkillVersion`, [line 105](../../../../../../../backend/src/sro/domain/skill/skill.py#L105): Note on the line above

Code: `starts_on: str | None = None`

> The page the task was demonstrated on.
>
> A skill taught by clicking names no URL on any step, so a run could only be
> performed by an operator who had already navigated to the right screen --
> and one who had not got the same thirteen `control_not_found` lines as one
> whose browser was on the wrong system entirely. This is what the recorder
> saw, on the frame the demonstration opened with.
>
> Only where every demonstration of the task began on the same screen. Two
> that began on different ones are saying the screen is not part of the task,
> and a run that navigated on that evidence would be guessing.

## `SkillVersion`, [line 107](../../../../../../../backend/src/sro/domain/skill/skill.py#L107): Note on the line above

Code: `systems: tuple[str, ...] = ()`

> Every system this version touches, derived from what it was taught on.
>
> Here rather than on the objective key, and the difference matters: the key
> is compared for equality, and that comparison is what pairs two
> demonstrations of one task. One stray host in one of them -- an identity
> provider, a CDN that answered once -- would make two keys unequal, and the
> pair would silently never pair.
>
> Empty for everything taught before this existed, which is what they were: a
> version that touches one system says so with `target_system` alone.

## `SkillVersion`, [line 109](../../../../../../../backend/src/sro/domain/skill/skill.py#L109): Note on the line above

Code: `loops: tuple[Loop, ...] = ()`

> Blocks of steps the task does once per thing in a list.
>
> Empty for every skill taught before this existed, and for most after: a loop
> is only ever recorded where two demonstrations did the same block a
> different number of times and the system's own answer said how many.

## `SkillVersion`, [line 111](../../../../../../../backend/src/sro/domain/skill/skill.py#L111): Note on the line above

Code: `when_to_use: str = ""`

> When to reach for it.
>
> Together with ``summary`` this is what an operator's request is matched
> against, so it is editable: a skill described in words nobody searches with
> is a skill nobody finds. Editing it changes what is found, never what runs.

## `_writes`, [line 366](../../../../../../../backend/src/sro/domain/skill/skill.py#L366): Docstring

> Whether performing this step changes something outside this system.
>
> One definition, because three rules read it -- whether a version writes at
> all, which of its steps go unchecked, and what a run below the assisted
> rung is allowed to send. They disagreed once already.

## `SkillVersion.inputs`, [line 124](../../../../../../../backend/src/sro/domain/skill/skill.py#L124): Docstring

> The values somebody has to supply for a run to be worth starting.
>
> Optional ones are not among them. A demonstration proved the warehouse
> accepts the record without that field and `absent_as` records exactly
> what it sent instead, so a run with nothing in it is a run that does
> what that demonstration did -- not one that fails.
>
> This was every INPUT parameter, which made a skill with any optional
> field impossible to put on a trigger at all: `CreateTrigger` demanded a
> value for the four boxes an operator had deliberately left empty, and
> the only way past it was to invent one.

## `SkillVersion.describe`, [line 127](../../../../../../../backend/src/sro/domain/skill/skill.py#L127): Docstring

> Reword what this version is for. A label, never a behaviour.

## `SkillVersion.crosses_systems`, [line 134](../../../../../../../backend/src/sro/domain/skill/skill.py#L134): Docstring

> Whether performing this version touches more than one system.
>
> Such a version is performed only in a browser that is signed in to all
> of them -- the operator's own -- because this deployment holds one
> session per system and never two at once.

## `SkillVersion.changes_the_system`, [line 138](../../../../../../../backend/src/sro/domain/skill/skill.py#L138): Docstring

> Whether performing this version writes anything.
>
> A tool call counts when whoever mapped it said it writes. Nothing else
> can say: MCP declares no such thing and a tool named `send_message` is
> a name, not a promise -- so this reads the decision rather than the
> word.

## `SkillVersion.from_one_demonstration`, [line 142](../../../../../../../backend/src/sro/domain/skill/skill.py#L142): Docstring

> Induced from a single run, so nothing was diffed.
>
> Every value in it is the value that run happened to send. That is a
> legitimate skill -- it replays one act exactly -- and it is a different
> thing from a skill whose constants were held across two runs.
>
> A repaired version answers this the same way the version it repairs
> does, which is why it keeps that version's recordings: what changed was
> one locator, and every value it sends is still the value those
> demonstrations carried.

## `SkillVersion.needs_a_person`, [line 146](../../../../../../../backend/src/sro/domain/skill/skill.py#L146): Docstring

> Whether some step can only be performed as a gesture.
>
> A step with no network plan is a click or a keystroke, and `judge`
> makes any run that performs one DEGRADED -- a medium that is not
> NETWORK, by the rule that a gesture means the recorded call no longer
> works. DEGRADED resets the clean streak, so such a version cannot
> accumulate one and can never reach the top of the ladder.
>
> That is a fact about the skill rather than about how it has been going,
> and it is the difference between "not yet" and "not ever". Somebody
> watching the streak sit at zero deserves to be told which one they are
> looking at.

## `SkillVersion.unchecked_writes`, [line 150](../../../../../../../backend/src/sro/domain/skill/skill.py#L150): Docstring

> The steps that change the system and prove nothing about the result.
>
> A write whose two demonstrations returned different statuses and shared
> no stable response field comes out of induction with no post-condition
> at all. Performing it can then only fail by not being sent -- the
> warehouse can reject it, ignore it, or do something else entirely, and
> the run says the step was fine.

## `SkillVersion.not_ready_for_autonomy`, [line 154](../../../../../../../backend/src/sro/domain/skill/skill.py#L154): Docstring

> Why this version may not run unattended, or ``None`` when it may.
>
> Here rather than at each caller, because there were three of them and
> they disagreed: the console passed everything and the promotion gate
> passed only `verifiable`, so a version refused at the gate was told
> "no step of this skill cannot be checked" -- a sentence that is not
> even wrong. What refuses a promotion and what a screen says about it
> have to be the same sentence.

## `SkillVersion.verifiable`, [line 167](../../../../../../../backend/src/sro/domain/skill/skill.py#L167): Docstring

> Whether a run of this can be checked.
>
> Two conditions, because one was not enough. Something must be checked
> at all -- a skill with no assertion anywhere produces runs that only
> ever prove a request was sent. And every step that *changes* the system
> must be among the checked: this was `any`, so a version whose read step
> asserted and whose writes did not counted as verified on the strength
> of the one step nobody is worried about.
>
> Either way it may run assisted forever; it may never run unattended.

## `SkillVersion.record_run`, [line 170](../../../../../../../backend/src/sro/domain/skill/skill.py#L170): Docstring

> Count a finished run against this version.
>
> `revising` names a verdict this same run has already been counted
> under, and replaces it rather than adding beside it -- see
> `TrackRecord.instead_of`. `CallRunWrong` is the only caller that has
> one: it judges a run `FinishRun` finished and judged minutes earlier.

## `SkillVersion.earn`, [line 179](../../../../../../../backend/src/sro/domain/skill/skill.py#L179): Docstring

> Move up if the record now says so. Returns the rung, or None.
>
> Promotion by hand made a version's stage a fact about somebody's
> afternoon rather than about the skill: the ladder was always meant to be
> earned, and waiting for a click is not evidence. Nobody is named as the
> promoter because nobody was asked -- the runs were.

## `SkillVersion.demote`, [line 197](../../../../../../../backend/src/sro/domain/skill/skill.py#L197): Docstring

> Pull a version back down. Not a promotion in reverse: this happens
> automatically, without a human, which is exactly why it is a separate
> method with a reason attached.

## `SkillVersion.loop_at`, [line 290](../../../../../../../backend/src/sro/domain/skill/skill.py#L290): Docstring

> The loop whose body this step belongs to, if any.

## `SkillVersion.loop_from`, [line 293](../../../../../../../backend/src/sro/domain/skill/skill.py#L293): Docstring

> The loop this step's response feeds, if any. Read when the step
> finishes, because that is the moment the list -- and so the count of
> iterations -- exists at all.

## `Skill.runnable`, [line 339](../../../../../../../backend/src/sro/domain/skill/skill.py#L339): Docstring

> The newest version something may actually be asked to run.
>
> A second demonstration lands at RECORDED, which the runner refuses, and
> matching always offered the newest version there was -- so re-teaching a
> working skill took it offline: every match answered with a version that
> could not run, and the only way back was to promote the new one.
>
> Falls back to nothing rather than to the newest: a skill with no
> runnable version is a skill nobody should be offered.

## `Skill.add_version`, [line 354](../../../../../../../backend/src/sro/domain/skill/skill.py#L354): Docstring

> Append. Existing versions are never mutated by a re-induction.

## `SkillVersion.promote`, [line 217](../../../../../../../backend/src/sro/domain/skill/skill.py#L217): Comment

Code: `raise InvariantViolation(`

> The argument for a preview being a review is that the operator
> read what this run would do. Nobody reads what ten future
> unattended runs will do.

## `SkillVersion.promote`, [line 222](../../../../../../../backend/src/sro/domain/skill/skill.py#L222): Comment

Code: `raise InvariantViolation(`

> The ladder's own backstop, protected from the press that would
> undo it. A version is only ever carrying a `demotion_reason`
> because it failed three runs in a row and was pulled back
> automatically -- and the one thing that must not put it straight
> back is the same kind of press that was failing. Without this, a
> task that is wrong every single time never stays demoted: it is
> demoted on the third wrong run and restored by the operator's
> very next press, forever.
>
> The refusal is a sentence an operator reads, not a field name,
> because this is raised through `RunFromPreview` and lands in the
> panel beside the button they just pressed. What it asks for is
> the rung the ladder exists to provide: somebody sitting down in
> the console with the evidence -- the failed runs, the steps, the
> assertions -- rather than somebody mid-task reading a preview of
> the one run in front of them. A console promotion clears
> `demotion_reason` below, which is what lets the version run
> again, and that is exactly the person this refusal holds out for.

## `SkillVersion.promote`, [line 233](../../../../../../../backend/src/sro/domain/skill/skill.py#L233): Comment

Code: `raise InvariantViolation(`

> Shadow is where an unpaired write belongs by default: it produces
> the request and withholds it, which is exactly what a reviewer
> needs to see. Above that it is sent, and every send is the same
> send -- one demonstration had nothing to diff against, so the
> values are the ones that run happened to carry. Creating the same
> record twice is the polite failure; the impolite one is a skill
> that quietly writes to the same id every night.

## `SkillVersion.promote`, [line 247](../../../../../../../backend/src/sro/domain/skill/skill.py#L247): Comment

Code: `if from_where != "preview":`

> The count that demoted it, cleared by the person who looked -- and
> only by them.
>
> `should_demote` is a standing condition rather than an event: it is
> re-asked after every run, so a version demoted at three failures went
> straight back down on its next run whatever that run did -- and it
> could not do better, because shadow withholds the writes a clean run
> would need. Promoting it was futile and looked like a bug in the
> ladder. The streak is left alone: it is progress towards autonomy and
> nobody may grant it by pressing a button.
>
> A preview promotion is not that person. The clearing was written for
> a console promotion, where somebody sat down with the failures and
> decided they were understood; the operator pressing `Do it` mid-task
> has read the steps and the values of the one run in front of them and
> nothing at all about the runs that failed before it. Clearing the
> count on their behalf would hand every failing version a fresh three
> lives on every press, which is the same hole the refusal above closes
> from the other side -- that one stops a version that has already been
> demoted from being put back, this one stops a version from never
> being demoted in the first place. Both are needed: a version sitting
> at one or two failures carries no `demotion_reason` for the refusal
> above to catch, so a press that cleared the count would walk it back
> to zero and the third failure would never arrive.

## `SkillVersion._check_parameters_declared`, [line 263](../../../../../../../backend/src/sro/domain/skill/skill.py#L263): Comment

Code: `named = step.placeholders | ({step.when} if step.when else frozenset())`

> ``when`` names a parameter the same way a template does, and an
> undeclared one is the same bug: a step conditional on something
> nobody can supply is a step that never happens.

## `SkillVersion._check_loops`, [line 282](../../../../../../../backend/src/sro/domain/skill/skill.py#L282): Comment

Code: `raise InvariantViolation("loops may not overlap")`

> Nested and overlapping loops are refused rather than
> supported: what they would mean at run time is a decision
> nobody has had to make yet, and a version that means two
> things is worse than one that refuses to exist.
