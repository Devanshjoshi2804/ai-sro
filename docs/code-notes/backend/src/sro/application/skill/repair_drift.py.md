# Notes for `backend/src/sro/application/skill/repair_drift.py`

Comments and docstrings moved out of [`backend/src/sro/application/skill/repair_drift.py`](../../../../../../../backend/src/sro/application/skill/repair_drift.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/skill/repair_drift.py#L1): Docstring

> A skill adopting what its own verified runs have agreed about a control.
>
> ``LearnFromRun`` already writes down that *control X is found by Y, not by the Z
> it was taught with*, and stops there on purpose -- the comment there is about
> Healenium, which rewrites a locator on a test that may assert nothing. That
> caution does not apply to the knowledge store's settled answer, and the
> difference is the whole of
> ``docs/superpowers/specs/2026-08-28-a-skill-that-repairs-itself``:
>
> - **It asserted, and more than once.** A repair reads the store, not the run it
>   is triggered by. One escalation is a slow page, a race, a modal that was still
>   open; ``SETTLED`` verified runs agreeing is a control that moved.
> - **Nothing is rewritten.** A repair appends a version beside the old one, so
>   reverting is promoting the older one again.
> - **It re-earns its autonomy, not its right to work.** The repaired version
>   inherits the rung it was already trusted at, capped below ``AUTONOMOUS``, and
>   starts with an empty record. Surviving one run is not ten clean ones; it is
>   also not a reason to stop doing the job a person is still authorising.
>
> Only the drifted step changes. Every other step is the same object as before,
> because a repair is the old version with one plan replaced -- never a fresh
> induction of a skill nobody demonstrated again.
>
> Where the evidence cannot name a locator this step carries, no version is
> written and a person is asked. That covers the vision rung -- a model read
> pixels and chose, and letting that write the skill is a model marking its own
> homework -- and it covers a plan carrying two locators of the strategy the
> evidence names, where adopting one of them would be a guess about which.
>
> Where the evidence never agrees with itself, a person is asked too, and that is
> the third answer. A control reached the taught way on some runs and another way
> on others settles nothing, ever: the store goes on recording both, no version is
> written, every run pays the escalation again, and nobody is told -- the operator
> sees a skill that simply never gets faster. It is still not adopted on a
> majority. A locator that only ever matches when the taught one failed has not
> proved itself; it has proved the taught one unreliable, which is a different
> fact and not one a machine may act on. So the counts are put to somebody who
> works there, once, and their answer adopts down the same path evidence does.

## module, [line 21](../../../../../../../backend/src/sro/application/skill/repair_drift.py#L21): Note on the line above

Code: `REPAIR = PrincipalId("drift-repair")`

> Named as the author and the promoter of a repaired version, because nobody
> else is. Not a person, and it does not pretend to be one: the person is whoever
> authorises the next run, which at every rung a repair can reach is still
> somebody. What this records is that no demonstration produced this version.

## module, [line 23](../../../../../../../backend/src/sro/application/skill/repair_drift.py#L23): Note on the line above

Code: `SETTLED = 3`

> How many verified runs have to agree before a drift is adopted.
>
> Once is noise -- a page that had not settled, a modal still closing, a race
> between a render and a click -- and a version rewritten on one escalation is a
> version rewritten by a bad afternoon. Twice is a coincidence, which is the same
> number and the same reasoning as ``WORTH_OFFERING``: this system has counted
> three doings before offering a task since the day it started counting anything,
> and a repair is a larger claim than an offer, not a smaller one.
>
> Three is also what makes the chain terminate. The store is asked for the newest
> three claims about the control; once the repair is adopted the step leads with
> the locator that worked, later runs find it where they were taught, and the
> claims stop saying it drifted. A drift is adopted once, not once per run.

## module, [line 25](../../../../../../../backend/src/sro/application/skill/repair_drift.py#L25): Note on the line above

Code: `WINDOW = REQUIRED_CLEAN_RUNS`

> How far back a control is read before calling it contested.
>
> Not a number of its own: it is the streak the drift is denying. ``AUTONOMOUS``
> asks for ten clean runs in a row, and a run that fell through its plan to reach
> this control is never one of them -- so if inside the last ten claims about a
> control the store holds ``SETTLED`` runs saying it moved and ``SETTLED`` saying
> it did not, this skill has spent the whole climb unable to start it, and will
> go on doing that forever because neither reading will ever outlast the other.
>
> Both sides have to reach ``SETTLED``, which is the same bar and the same
> reasoning as adoption: one observation is a slow page, three is a fact, and a
> control is only *contested* when there are two facts. Three drifted claims and
> one that was not is not a contest -- it is a settled drift with a flake in it,
> and the next agreeing run adopts it. That asymmetry is deliberate: asking is
> cheap, but a question nobody needed to answer is how a question surface becomes
> one nobody reads.

## `Drift`, [line 29](../../../../../../../backend/src/sro/application/skill/repair_drift.py#L29): Docstring

> One step whose control the store no longer places where it was taught.
>
> Either because it has settled somewhere else, or because it has not settled
> anywhere -- ``against`` is which.

## `Drift`, [line 34](../../../../../../../backend/src/sro/application/skill/repair_drift.py#L34): Note on the line above

Code: `agreed: int = SETTLED`

> Verified runs, inside the window, that reached the control by ``matched``.

## `Drift`, [line 36](../../../../../../../backend/src/sro/application/skill/repair_drift.py#L36): Note on the line above

Code: `against: int = 0`

> Verified runs inside the window that did not. Zero is a settled drift;
> anything at all here is a contest, and a contest is never adopted on the
> count.

## `Drift`, [line 38](../../../../../../../backend/src/sro/application/skill/repair_drift.py#L38): Note on the line above

Code: `answer: str | None = None`

> What somebody said when the contest was put to them, if anybody has.

## `RepairDrift`, [line 61](../../../../../../../backend/src/sro/application/skill/repair_drift.py#L61): Docstring

> Adopt, into a new version, the locator the store's evidence has settled on.

## `_answer`, [line 151](../../../../../../../backend/src/sro/application/skill/repair_drift.py#L151): Docstring

> What somebody decided about a contested control, if anybody has.
>
> Read through the same port the evidence is read through rather than through
> `AskAbout.settled`, which opens a unit of work of its own -- entering this
> one twice leaves the caller's block without a session. An answer is a claim
> like any other and the history of the question's key is where it lands.

## `_reading`, [line 161](../../../../../../../backend/src/sro/application/skill/repair_drift.py#L161): Docstring

> What the store makes of this control: settled elsewhere, contested, or
> nothing worth acting on.
>
> Settled first, and that ordering is the point. A drift that took a few flaky
> runs to establish itself has both readings in its window and is still a
> drift -- the newest claims agree, so it is adopted and never asked about.

## `_contested`, [line 168](../../../../../../../backend/src/sro/application/skill/repair_drift.py#L168): Docstring

> A control the last ``WINDOW`` verified runs cannot agree about.
>
> ``None`` unless one locator was named by ``SETTLED`` separate runs *and*
> ``SETTLED`` separate runs found the control some other way. Both sides have
> to clear the bar adoption clears: below it, the minority is a slow page and
> the majority is on its way to settling on its own.
>
> Where two locators both clear it, the more-claimed one is what the question
> leads with -- it is a question, not an adoption, and the counts go with it.

## `_settled`, [line 183](../../../../../../../backend/src/sro/application/skill/repair_drift.py#L183): Docstring

> What the store says found this control, where it has stopped changing.
>
> ``None`` unless the last ``SETTLED`` claims about it are all from separate
> verified runs, all say it drifted, and all name the same thing as having
> found it. Anything less is one run's opinion, and a version is not rewritten
> on one run's opinion.

## `_adopt`, [line 196](../../../../../../../backend/src/sro/application/skill/repair_drift.py#L196): Docstring

> Append the repaired version and walk it to the rung it inherits.

## `_trying_first`, [line 240](../../../../../../../backend/src/sro/application/skill/repair_drift.py#L240): Docstring

> The same step, with the locator that worked tried first.
>
> The others are kept, in order, behind it: they resolved on the day this was
> demonstrated, and a screen that changes back is not a screen this skill
> should have to be taught twice.

## `_contest`, [line 266](../../../../../../../backend/src/sro/application/skill/repair_drift.py#L266): Docstring

> The counts, the cost, and the two things somebody could do about them.
>
> "Which locator should this use?" is unanswerable on its own -- nobody knows
> what that means about a screen they cannot see. What is answerable is *this
> button is reached one way on seven runs in ten and another way on the other
> three, and the skill cannot get faster while that is true*: somebody who
> works in that warehouse knows whether the screen has two of these, or one
> that is slow to render, or one that moved during a release.

## `_note`, [line 296](../../../../../../../backend/src/sro/application/skill/repair_drift.py#L296): Docstring

> Why this version exists, in the words the console shows.
>
> A skill that quietly rewrites itself is one nobody can trust, so the runs
> that proved the change are named in the provenance rather than only in a log.

## `Drift.worked`, [line 41](../../../../../../../backend/src/sro/application/skill/repair_drift.py#L41): Docstring

> The one locator this step carries that the evidence names.
>
> ``None`` where nothing it carries does -- which is what the vision rung
> records -- and ``None`` where two of them do. The evidence names a
> *strategy*, not a locator, so a plan holding two CSS paths cannot say
> which of them the driver used, and promoting the first of them is how a
> destructive control ends up tried ahead of the one that worked. Both are
> a question for a person rather than a guess.

## `Drift.adopted`, [line 48](../../../../../../../backend/src/sro/application/skill/repair_drift.py#L48): Docstring

> The locator to put in front of this step's plan, if anything says to.
>
> A settled drift says to. A contested one says so only through a person:
> the same locator, reached through the same repair, so there is one way a
> locator changes and one audit trail rather than two.

## `Drift.contest`, [line 57](../../../../../../../backend/src/sro/application/skill/repair_drift.py#L57): Docstring

> What the contest is addressed by: the control, not the skill.
>
> The same button contested across five skills is one question. The store
> is keyed by control already, and so is this.

## `RepairDrift.execute`, [line 67](../../../../../../../backend/src/sro/application/skill/repair_drift.py#L67): Docstring

> The new version's number, or ``None`` when nothing has settled.
>
> Triggered by a run that finished, and decided by what every run before
> it wrote down. A run whose assertions failed proves the skill and the
> system disagree, and which of the two is wrong is exactly what it does
> not establish -- so it is not even a reason to look.

## `RepairDrift._drifted`, [line 113](../../../../../../../backend/src/sro/application/skill/repair_drift.py#L113): Docstring

> Every step of this version the store no longer agrees with.

## `RepairDrift.execute`, [line 69](../../../../../../../backend/src/sro/application/skill/repair_drift.py#L69): Comment

Code: `return None`

> Somebody has taught this since the run started. Their version
> is later evidence than anything here, and appending a repair
> of an older one would put it in front of theirs.

## `RepairDrift.execute`, [line 76](../../../../../../../backend/src/sro/application/skill/repair_drift.py#L76): Comment

Code: `return None`

> Two runs finished together, or a demonstration landed
> while this was reading. Whoever got there first wrote a
> version this one has not seen, and appending on top of a
> skill that has moved is how one of two repairs disappears
> with a green log to show for it. The store still says the
> control drifted, so the next run adopts it.

## `RepairDrift.execute`, [line 99](../../../../../../../backend/src/sro/application/skill/repair_drift.py#L99): Comment

Code: `for drift in drifts:`

> Outside the transaction: `AskAbout` opens its own unit of work, and
> entering the same one twice leaves the outer block without a session.

## `RepairDrift.execute`, [line 100](../../../../../../../backend/src/sro/application/skill/repair_drift.py#L100): Comment

Code: `if drift.adopted is None and drift.answer is None:`

> Nothing to adopt and nobody has said what to do about it. A
> contest already answered is not asked again -- `raise_question` is
> idempotent anyway, and so is this.

## `RepairDrift._drifted`, [line 126](../../../../../../../backend/src/sro/application/skill/repair_drift.py#L126): Comment

Code: `key=f"control {taught.describe()}",`

> The same key `LearnFromRun` writes: the control, not the
> skill. Two skills clicking one button are two observations
> of where that button is.

## `_adopt`, [line 209](../../../../../../../backend/src/sro/application/skill/repair_drift.py#L209): Comment

Code: `stage=PromotionStage.RECORDED,`

> Appended where every version is appended. The rung it inherits is set
> below, once it is on the skill.

## `_adopt`, [line 210](../../../../../../../backend/src/sro/application/skill/repair_drift.py#L210): Comment

Code: `track_record=TrackRecord(),`

> None of the old one's record: the climb back to unattended starts at
> zero, because agreeing runs are not clean ones.

## `_adopt`, [line 217](../../../../../../../backend/src/sro/application/skill/repair_drift.py#L217): Comment

Code: `repaired_from=run.id.value,`

> `induced_by` was the requester of the proving run, which read as
> a person having produced this. Nobody did, and `repaired_from` is
> what says so somewhere a screen can filter on rather than only in
> the sentence below. The recordings stay: they are what every value
> this version sends still came from, and dropping them would make a
> fixed-value write skill read as one that had been diffed.

## `_adopt`, [line 224](../../../../../../../backend/src/sro/application/skill/repair_drift.py#L224): Comment

Code: `inherited = (`

> `Skill.runnable` serves the newest version that is not RECORDED, so this
> one takes over from the one it repairs the moment it is saved -- and a
> version that took over at SHADOW would withhold every write. A skill that
> repaired itself would stop doing the work, which is the opposite of
> healing.
>
> So it inherits the rung, capped below AUTONOMOUS. At ASSISTED a named
> person authorises every run; that person is the safety, and they are still
> there, looking at a version that differs from the one they were happily
> running by a single locator several verified runs proved. Unattended is
> the one rung nobody is watching, so it is the one a repair may not
> inherit: a version nobody has watched re-earns the right to act unwatched,
> from the empty record above.

## `_adopt`, [line 230](../../../../../../../backend/src/sro/application/skill/repair_drift.py#L230): Comment

Code: `fresh.promote(`

> Through `promote`, one rung at a time, rather than assigning the stage
> behind the guard's back -- and with the truthful promoter and the
> run's clock. `acknowledging_fixed_values` says what is true of an
> inherited rung: a fixed-value write skill only reaches ASSISTED
> because somebody read what it sends, and this version sends the same
> thing.

## `_adopt`, [line 235](../../../../../../../backend/src/sro/application/skill/repair_drift.py#L235): Comment

Code: `from_where="repair",`

> A blank `promoted_from` beside a named `promoted_by` reads as a
> row written before this field existed -- which this is not.
> `"repair"` says plainly that the climb was mechanical: nobody
> reviewed this particular version, it inherited a rung the one it
> replaced had earned.

## `_contest`, [line 281](../../../../../../../backend/src/sro/application/skill/repair_drift.py#L281): Comment

Code: `worked.describe() if worked is not None else "demonstrate the step again",`

> Answered with exactly what the plan calls the locator, because
> that answer is what adopts it -- through the same repair a settled
> drift takes, so there is one way a locator changes.
