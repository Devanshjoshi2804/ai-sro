# 015 — A step is decided by how often it happens

**Status:** accepted, 2026-09-01
**Relates to:** [004 — diff parameterisation](004-diff-parameterisation.md), [010 — a skipped field is a value](010-a-skipped-field-is-a-value.md)

## The problem

An operator added four carrier cross references in a real WMS. Sometimes they
filled every field, sometimes a few; one doing included an address lookup the
other three skipped. Induction produced a skill with **two steps — both the
same button — and a `cod_address_id` parameter no step could ever fill.**

That is not a bug in the aligner. It is what intersection means. `align` pairs
two runs and keeps the steps they share; everything past the second run is read
only for whether some doing left a field empty. Four doings of one task
therefore went in as one pair and two histories, and the address lookup left
with the run that made it — while its *value* survived, because the histories
still saw it. The skill named a field and had no way to type it.

The obvious repair is to keep everything anybody did. That works at four doings
and fails at a thousand. A day of real observation contains the task plus every
accident around it: a field typed and corrected, a grid sorted before the row
was found, a panel opened to check a code, a mis-click on a label. Union learns
all of it and replays all of it. Neither end of the range is survivable:
**intersection loses the task at four doings, union loses it at a thousand.**

## The decision

**How often a step happened decides its place in the task, and a value behind a
rare step makes it a branch rather than a fumble.**

`standing_of` reads an `Alignment` — which steps the doings had, and how many
doings contained each — and returns one of three standings per step.

- `ALWAYS`, for a step at or above `PART_OF_THE_TASK` of the doings.
- `CONDITIONAL`, for a step below it whose own keystroke fills a parameter some
  doing left empty. It becomes `SkillStep.when`, which has meant exactly this
  since it existed: the parameter whose presence decides whether the step
  happens at all.
- `NOISE`, for a step below it with nothing explaining when it happens.

**The threshold is a share, not a count**: two doings in three. A count would
mean something different every week — a step three doings made is the task when
there were four and a rounding error when there were four thousand — and a rule
whose meaning drifts with a task's popularity is not one anybody can reason
about. Two in three rather than a bare majority because at four doings, which is
the real case, a majority is one operator's habit; a rule that flips on a single
doing is not a rule.

**Who may change it: a person editing `PART_OF_THE_TASK`, reviewed like any
other change.** Not a tenant setting. A threshold that differs per deployment
means two installations disagree about what the same task *is*, and the first
question anybody asks about a wrong skill — "why did it keep that step" —
stops having one answer. It is also not a number this earns the right to tune
per customer: it decides only the steps nothing else explains, and the
argument below is that those are the cheap ones to get wrong.

## Why a rare step with a value behind it is a branch

Rarity on its own drops nothing, and this is the part that is easiest to get
backwards.

A step in three per cent of doings that appears **whenever one particular value
was supplied** is not a rare event. It is an ordinary event with a rare cause:
every doing that made it was a doing where somebody had that field to fill, and
the ninety-seven that skipped it are the ninety-seven where nobody did. The
count is low because the *condition* is rare, and the step is not optional at
all inside the case it belongs to. A branch taken once in a hundred times is
still part of the task, and a skill that drops it silently stops handling the
case somebody needed it for — which is precisely what happened to the address
lookup, and it left behind a parameter as the only trace that anything had gone.

A step in three per cent with nothing explaining it has no such account of
itself. It happened; nothing in the evidence says when it would happen again.
That is what a fumble looks like from the outside, and it is the one thing
rarity decides.

The correlation is read narrowly, from the keystroke only —
`Parameterisation.conditional_on`, which already draws this line for the two-run
case. The write that carries an optional field goes out on every run regardless,
carrying the absent form ADR 010 says it must. So a rare *write* is a fumble
however many nullable fields it fills in; only the typing is conditional on
somebody having something to type.

## Why none of this is a model's judgement

ADR 004 holds: no model decides identity. `standing_of` reads two facts — a
count `align_all` produced, and which parameter the diff already proved a
gesture fills — and nothing else. Both are checkable by re-reading the
recordings.

The tempting alternative is real: a model handed the four recordings would
almost certainly say the address lookup belongs and the double-click on the
label does not, and would say it in one call instead of two mechanisms. It
loses because it would say it just as fluently where the evidence says nothing,
and there is no way to tell those two answers apart afterwards. A count is
wrong in ways somebody can see; a reading is wrong in ways that look like the
right answer. This is the same trade `_find_produced` already makes when it
refuses to bind a value that matched by luck.

## What was argued about: ask the operator about every rare step

The alternative on the table was to decide nothing and show the minority steps
for review — every step under the threshold, rendered with its count, kept or
dropped by a person.

It is more honest per step and worse in aggregate. `_chosen_constants` records
what happened the last time this codebase asked an operator a question per
candidate: "fifteen questions arrived for one task and nobody would answer any
of them." A form of any size produces exactly that many rare steps — every
field somebody skipped, every stray click in every doing — and a review surface
that arrives with thirty questions is a review surface that gets dismissed, at
which point the steps are dropped anyway, by inattention rather than by rule.

It also asks the wrong person. The operator who demonstrated the task knows
what they were doing; the person reading the induction output a week later is
being asked to reconstruct whether a click in doing eleven was deliberate, from
a screenshot. The counts already know.

## What it gives up

**A genuinely rare branch demonstrated once, where the value correlation is
itself weak evidence.** One occurrence is one occurrence. A step seen once,
alongside a field filled once, is a correlation of a single point — and a
single point correlates with everything else that happened once. This decision
keeps that step as `CONDITIONAL` anyway, on the argument above, knowing the
evidence is thin.

It is thin in a cheap direction, which is why it is accepted rather than
solved here. A step wrongly kept as `CONDITIONAL` is skipped on every run where
nobody supplies that parameter — a fumble mis-read as a branch runs only when
an operator supplies exactly the field the fumble typed into, and otherwise
costs nothing but a line in a preview. A branch wrongly dropped costs the case
it existed for, on every run, silently. The asymmetry is the whole reason the
rule leans this way.

The gap the argument does leave is the other direction: a real branch
demonstrated once *without* a supplied value behind it — a step somebody takes
when the screen is in a particular state, say — comes out `NOISE` and is gone.
Nothing here catches that, and no threshold could: there is no evidence in the
recordings that distinguishes it from a mis-click. What answers it is the
mechanism already built for evidence that arrives later. A candidate is
"derived, and recomputable" — the doings are kept verbatim, so standing is
recomputed as more of them arrive, and a branch that happens a second time
stops being a single point without anybody re-teaching anything. Until then the
operator has the ordinary recourse for a skill that missed a case: demonstrate
it, which lands a new version carrying the step.

## Consequences

Induction can be handed every doing of a task rather than the first two, and
each step comes back with a place: run it, run it when this value is supplied,
or leave it out. The address lookup comes back as a `when` on the parameter it
fills, which is the shape `SkillStep` was already built for and the shape the
executor already runs.

Nothing about the two-run path changes. `align` is still the two-run function
and still refuses a pair that genuinely disagrees; a task demonstrated once has
every step at a share of one, so it comes out entirely `ALWAYS` — there is
nothing to disagree with it, and a rule that made a lone demonstration's steps
rare would refuse to learn a task done once.

This decides standing and does not emit anything. Which steps become
`SkillStep`s, and what `when` each one carries, is the next piece; keeping the
decision separate from the emission is what lets the threshold be argued about
without arguing about induction's output at the same time.
