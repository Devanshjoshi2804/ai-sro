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

## The decisions

**A verified run may write a new version of the skill it ran.** Only verified: a
run whose assertions failed proves the skill and the system disagree, and which of
them is wrong is exactly what it does not establish.

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

## What this refuses

- A run that did not verify writes nothing.
- A repair never invents a step that no run performed.
- A vision-proposed gesture never becomes a skill without a person.
- A repaired version never inherits the track record of the one it replaces.
- Nothing is edited in place; a repair that was wrong is undone by promoting the
  older version.

## Verification

- **Part 1** — unit: a verified UI run whose control was found by a different
  locator produces a new version whose plan names the locator that worked, with
  every other step byte-identical; a run that failed its assertions produces
  nothing; a vision-found control produces an offer rather than a version; the new
  version starts at the bottom of the ladder with an empty streak.
- **Part 2** — not yet. It starts with the argument about capturing during a
  repair run, and that belongs in an ADR before any code.
