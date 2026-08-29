# A skill that repairs itself

## Why now

A WMS changes. Blue Yonder moves a control, renames a field, ships a release, and
a skill taught last month stops matching the system it was taught on. Today that
does not break a run: escalation carries it through — a call that no longer works
falls to the screen, a control that has moved falls to the rung that looks at
pixels. The work gets done.

But the *skill* stays drifted, and the cost is not obvious until it is stated: a
UI or vision step can never be `CLEAN`, and `AUTONOMOUS` needs ten consecutive
clean runs. **A skill that heals by escalating works forever and can never again
run unattended.** It degrades quietly, one release at a time, and the only repair
is a person noticing and demonstrating again.

Half the loop already exists and is better than it looks. `LearnFromRun` writes
what a verified run proved into the knowledge store — including which locator
actually found each control, and whether that is the locator the demonstration
taught. Evidence outranks arrival order, so a later re-scrape cannot undo it.

What is missing is that **the version never adopts what the store already knows**.
Every run rediscovers the same drift, pays the same escalation, and forfeits the
same `CLEAN`.

## What this reverses, and why that is allowed now

`learn_from_run.py` stops short of repair on purpose, and says so:

> …evidence from a demonstration, and the healer's rule is that evidence is
> changed by demonstrating again. This is the same instinct as Healenium's store
> of healed locators, minus the part where the tool rewrites what the test said.

That caution is right about Healenium, which heals a selector on a test that may
assert nothing, and silently. It is wrong about a *verified* run here, and the
difference is the whole design:

- **A verified run asserted.** Its steps proved the outcome the demonstration
  proved. A passively mined episode has no assertions at all — so in this one
  respect a verified run is *stronger* evidence than the observation that taught
  the skill in the first place.
- **Nothing is rewritten.** A repair writes a new version beside the old one. The
  old one stays readable, and reverting is choosing it again.
- **It re-earns its place.** A repaired version starts at the bottom of the ladder
  and inherits none of the old one's clean streak. Surviving one run is not ten.
  *(Half of that last bullet was wrong. It is left standing because the section
  below is about why.)*

## The sentence above that was wrong

> A repaired version starts at the bottom of the ladder and inherits none of the
> old one's clean streak.

That is one sentence doing two jobs, and running them together is the whole
mistake.

**The streak** gates `AUTONOMOUS` — running with nobody watching. A repair must
reset it. Surviving one run is not ten, and unattended is exactly where a bad
repair would go unnoticed.

**The stage** gates something else entirely: whether a human-authorised run may
write at all. A repair has no business resetting that. At `ASSISTED` a named
person authorises every run; that person is the safety, and they are still there.
What they are looking at differs from the version they were happily pressing by a
single locator that a verified run proved.

Written as one sentence, "the bottom of the ladder" drops an `ASSISTED` version to
`SHADOW`. `Skill.runnable` serves the newest version that is not `RECORDED`, so
the repair takes over the moment it is saved — at the one rung where every write
is produced and withheld. **A skill that repairs itself stops doing the work.**
The operator's Tuesday task quietly creates nothing, and the only way back is
clean runs that a withholding rung cannot produce. Self-repair would punish a
skill for healing, which inverts the point of building it.

**The rule, corrected: a repaired version inherits the stage of the version it
repairs, capped below `AUTONOMOUS`, and always starts with an empty track
record.** Repairing a `SHADOW` version yields `SHADOW` — nothing was being sent,
and a repair is not a reason to start. Repairing `ASSISTED` yields `ASSISTED`: the
work continues, a human still presses. Repairing `AUTONOMOUS` yields `ASSISTED`,
not `AUTONOMOUS` — a version nobody has watched must re-earn the right to act
unwatched, and the cap is where "one run is not ten" actually belongs. The record
is empty either way, so the climb back to `AUTONOMOUS` starts from zero.

The rung is taken through the same `promote` the ladder uses, one step at a time,
rather than assigned behind the guard that refuses a stage with no promoter and no
time. What it names is the truth: the repair, and the run's clock.

## The decisions

**A verified run may write a new version of the skill it ran.** Only verified: a
run whose assertions failed proves the skill and the system disagree, and which of
them is wrong is exactly what it does not establish.
*(Wrong, and the section below is about why. What may write a version is
corroborated evidence; a run only triggers the look.)*

**A repair edits only what drifted.** The new version is the old one with the
changed steps replaced — never a fresh induction. The run says which steps
escalated and what worked; everything else is copied unchanged.

**A vision-sourced repair proposes; a person presses once.** At the UI rung the
control is found by the application's own structure — an accessible name, the
framework's component registry — so adopting it is learning from the system. At
the vision rung a model read pixels and chose. Letting that write the skill is a
model marking its own homework, and the next run performs what it invented. So it
becomes an offer with the screenshot attached, answered once, and the answer is
knowledge like any other.

**A field the operator filled that the skill does not know becomes a parameter.**
The same rule as optionality: what the history shows, the skill learns. A value
appearing in later doings that no version has a parameter for is evidence the form
has a field the skill is blind to.

**It is visible.** The console shows that a skill repaired itself, what changed,
and which run proved it. A skill that quietly rewrites itself is one nobody can
trust, and the audit is the difference between healing and drifting.

## In two parts, because they are not equally ready

**Part 1 — a locator that drifted.** The evidence is already recorded: the
knowledge store holds `control X is found by Y, not by the Z it was taught with`.
The repair is adopting it into a new version's `ui_plan`. Small, safe, and it
stops the most common drift — a renamed control — from costing a skill its
autonomy forever.

**Part 2 — a call that drifted.** When the endpoint itself moved, the network step
is wrong and the UI rung did the work instead. Repairing that needs the call the
browser actually made, and capture deliberately refuses to record anything while a
run is driving: *"a replay's clicks and the calls they set off, mined as though
somebody had done them."* That rule is right for passive mining and wrong here,
but changing it needs its own argument — a repair run is not a robot imitating a
person, it is the system doing a task it was asked to do and verifying the
outcome. Until that argument is made and written down, a drifted call asks for a
demonstration.

## The other sentence that was wrong

> A verified run may write a new version of the skill it ran.

**A single run cannot tell drift from noise.** It says the control was reached by
something other than what the step leads with. So does a page that had not
finished rendering, a modal that was still closing, a race between a click and
the thing it was aimed at. One escalation is all four of those and a control that
moved, and nothing on the run distinguishes them — which is why building the
repair on one produced every defect the review found, and not by accident:

- one flaky iteration out of twelve rewrote the plan for all twelve;
- twelve alternating runs produced thirteen versions, because every run
  rediscovered the same drift and every run was a fresh chance to react to it;
- a skill that asserted nothing repaired itself, because "no assertion failed"
  and "the assertions passed" are the same thing to a rule reading one run.

**And this system has not believed a single observation anywhere else since the
day it started counting.** `WORTH_OFFERING` is three: twice is a coincidence and
the operator knows it, and being asked about coincidences is how a
recommendation surface gets ignored. `AUTONOMOUS` asks for ten clean runs. The
knowledge store exists precisely so evidence accumulates and outranks arrival
order, and its own words are that an ambiguity resolved by whichever evidence
arrived first is a confident wrong answer with extra steps. The repair was the
one place in the system that acted on the first thing it saw.

**The rule, corrected: corroborated evidence may write a new version; a run only
triggers the look.** `LearnFromRun` already writes, from every verified run, that
*control X is found by Y, not by the Z it was taught with*, keyed by the control
rather than by the skill. A repair reads that history. Where the last three
claims about a control come from three separate verified runs, all say it
drifted, and all name the same thing as having found it, the drift is settled and
is adopted — once. Three, for the reason `WORTH_OFFERING` is three: a repair is a
larger claim than an offer, not a smaller one.

That ends the chain without a rule invented to end it. The repaired version leads
with the locator that worked, so what later runs write down is a control found
where it was taught, and there is nothing left to adopt.

**"Verified" has to be asked for, not inferred from the absence of a failure.** A
step with no assertions cannot fail one, so `ok` was true and the run came out
SUCCEEDED; a step whose screen could not be read produced silence, and silence
reads as a passing check. Both say so on the step now, in `unchecked`, beside the
failures — and a step nothing checked contributes no evidence about where a
control is. The gesture landed on something. That the something was the right
control is what the assertions were for.

**Evidence that never agrees with itself is a third answer, not a smaller
version of the first two.** The rule above settles a drift and refuses a guess,
and between them sits the case neither reaches: a control found the taught way
on some runs and another way on others. Nothing ever settles, so no version is
ever written, so every run rediscovers it and pays the escalation again — and
because a run that went to the browser is `DEGRADED` and `DEGRADED` clears the
streak, that skill **can never reach `AUTONOMOUS`, however many hundred times it
runs**. It works every time. The operator sees only a skill that never gets
faster, and nobody is ever told why.

The fix is not to adopt on the majority. `SETTLED = 3` exists so that one
escalation cannot rewrite a skill, and "the fallback matched more often" is the
same weak evidence with a bigger sample: a locator that only ever matches when
the taught one failed has not proved itself, it has proved the taught one
unreliable, and those are different facts. So it is the third case for
`EntryKind.QUESTION` — beside the vision rung and the un-nameable strategy —
asked once, keyed by the control the way the store already is, and carrying what
makes it answerable: which locator, how many verified runs behind each, and the
cost, that this step falls through its plan on *n* runs in *m* and the clean
streak unattended running needs will never start. Nobody can answer "which
locator should this use?"; somebody who works in that warehouse can answer that.

The answer adopts through `RepairDrift` exactly as an evidence-settled drift
does — same new version, same empty record, same inherited rung, same audit —
so there is one way a locator changes rather than two. Silence stays the
fallback: unanswered, the runs go on working and go on escalating, which is what
they did before. What was broken was nobody being told.

**When it is called contested: both readings clear `SETTLED`, inside a window of
`REQUIRED_CLEAN_RUNS`.** Symmetry with the adoption bar, and for the same
reason — one observation is a slow page and three is a fact, so a control is
contested only when there are two facts. Three claims that it drifted and one
that it did not is *not* a contest; it is a settled drift with a flake in it,
and the next agreeing run adopts it, which is why asking there would leave a
question on somebody's screen that nothing needed. A control with two
observations and no pattern is asked nothing at all. The window is the streak
the drift is denying: if inside the last ten claims about a control both
readings have three separate runs behind them, this skill has spent an entire
climb unable to start one and will go on doing that forever, because neither
reading will ever outlast the other. Settled is checked first, so a drift that
took a few flaky runs to establish itself is adopted and never asked about.

**Where the evidence cannot name a locator, nobody guesses.** What a run records
is a *strategy*. A step carrying two CSS paths cannot say which of them resolved,
and promoting the first of them put a destructive control ahead of the one that
had worked. Refused and asked about, beside the vision case. Plumbing the
identity out of the driver would fix this deployment's own Playwright driver and
not the operator's extension, which is a separate build reporting a strategy and
nothing else — so the refusing branch has to exist either way, and once it exists
it is the whole answer.

**A repaired version says the system wrote it.** `induced_by` was the requester of
the proving run, which reads as a person having produced it.
`Provenance.repaired_from` names the run in a field a screen can filter on, and
`induced_by` is `drift-repair`. The recordings stay, and this is a deliberate
disagreement with the review: they are what every value the version sends still
came from, and `from_one_demonstration` counts them to decide whether a write
skill's values were ever diffed. A repaired version that dropped them would read
as diffed and climb a rung nobody meant it to — a worse lie than the one it
would have fixed, and in the more dangerous direction.

**Two writers must not silently lose one.** Every version of a skill lives in one
JSONB document, so two that both appended read the same list and the second
overwrote the first. `latest_version` is already the count and already a column,
so it is the version counter: the write carries `WHERE latest_version = <what was
read>` and fails rather than lands. It costs the append path a conflict to
handle — a repair drops its version and the next run adopts it — and it protects
nothing else, because a concurrent promotion writes one field and the loser's
write is the whole truth about that field rather than half of a list.

## The track record, reconsidered

A repaired version starts with an empty record, and the question was whether that
means a skill which repairs itself can never climb. It does not, and the reason
is that the streak being cleared is already zero.

`judge` returns `DEGRADED` for any run with a step that did not happen at the
network rung or that escalated, and `DEGRADED` clears `clean_streak`. A drift is
only ever observed by a run that went to the browser — that is what observing it
means — so every run that corroborated it was `DEGRADED`, and the version being
repaired has a streak of zero at the moment it is repaired. The reset costs
nothing that was not already gone.

What the repair buys is the opposite. A skill drifting on a UI step could never
be `CLEAN` again and so could never reach `AUTONOMOUS` at all; adopting the
locator that works is what makes the climb possible in the first place. Kept as
it is.

## What this refuses

- A run that did not verify writes nothing, and a step nothing checked did not
  verify.
- One run writes nothing. Corroborated evidence writes, or nothing does.
- Evidence that contradicts itself writes nothing either, and is never resolved
  by which side of it is larger.
- A repair that cannot say which locator matched asks rather than guesses.
- A contested control is asked about once, by the control, however many skills
  are contesting it — and not at all until both readings are corroborated.
- A repair never invents a step that no run performed.
- A vision-proposed gesture never becomes a skill without a person.
- A repaired version never inherits the track record of the one it replaces.
- A repaired version never stands higher than the one it repairs, and never higher
  than `ASSISTED`.
- Nothing is edited in place; a repair that was wrong is undone by promoting the
  older version.

## Verification

- **Part 1** — unit: three verified UI runs agreeing that a control was found by a
  different locator produce a new version whose plan names the locator that
  worked, with every other step byte-identical; one such run, and then two,
  produce nothing; a run that failed its assertions produces nothing; a step
  nothing checked never settles anything; eleven iterations as taught and one
  fallen back settle nothing either; a vision-found control, and a strategy the
  step carries twice, produce a question rather than a version; the repaired
  version names `drift-repair` and the run that closed the evidence; a repair that
  loses a race to another writer is dropped rather than forced; the new version
  inherits the stage it repaired — `SHADOW` from `SHADOW`, `ASSISTED` from
  `ASSISTED`, `ASSISTED` from `AUTONOMOUS` — with an empty streak, and is in every
  case the version `Skill.runnable` then serves.
- **The contested control** — unit: two readings each corroborated inside the
  window raise exactly one question, carrying both counts and what the drift is
  costing; the same control contested again asks nothing more, and asks once
  however many skills reach it; three claims of drift against one of the taught
  way settle and adopt rather than asking, because that is a flake and not a
  contest; two observations and no pattern ask nothing; an answered question
  adopts through `RepairDrift`, producing the version an evidence-settled drift
  would have produced.
- **Part 2** — not yet. It starts with the argument about capturing during a
  repair run, and that belongs in an ADR before any code.
