# A task done a thousand times

## What happened

An operator added four carrier cross references in a real WMS. The system
noticed, offered to do the next one, and induced this:

```
stage: shadow · steps: 2 · parameters: carrier, service_level, cod_address_id, cross_reference
  0  click span#button-1401-btnIconEl
  1  Click OK.
```

Two steps, both the same button, no typing at all. It derived the right four
parameters, so it understood what varied — and then produced something that
would click a button twice and create nothing.

The four demonstrations:

| | gestures | carrier | service | external system |
|---|---|---|---|---|
| 1 | 5 | — (opens by dismissing a dialog) | — | — |
| 2 | 8 | 005-BEST METHOD | LT | Enveyo |
| 3 | 14 | 001-DO NOT USE | LT | ConnectShip |
| 4 | 22 | Test Drive LLC | LTL | ConnectShip, plus a COD address lookup |

The owner's reading, which is the correct one: *all four are the same task.*
Adding a cross reference is sometimes done with every field and sometimes with a
few. That variation is the work, not noise in it.

## Why it produced two steps

`InduceSkill.execute(first, second=None, others=())` reads every occurrence, but
it does not use them for the same thing.

**Two** recordings — `first` and `second` — go to `align`, which pairs them on
the longest common subsequence of their gestures. Everything else goes to
`parameterise(frames_a, frames_b, others=history)` as *history*.

So the other occurrences shape the **parameters** and never the **steps**. That
is exactly what the stored skill shows: four parameters, correctly derived from
what varied across all four doings — and two steps, which is the longest run of
gestures the two aligned demonstrations happened to share.

The 22-gesture demonstration, the only one showing the COD address lookup,
contributed to naming `cod_address_id` and contributed nothing to the steps that
would fill it. The skill therefore has a parameter it has no step to use.

(Truncation is not the cause, though it is adjacent: `frames[:keep]` only cuts
when `loops.detect` finds the two runs are two lengths of one looping task, and
`keep` is `None` otherwise. It did not fire here.)

## The mistake this spec exists to avoid

The first fix proposed was a refusal: notice the skill is implausibly thin and
ask for another demonstration. The owner rejected it, correctly.

*A fifth demonstration teaches nothing.* The fifth will vary too, and pairing
and truncating will discard most of it again. The goal is not to find the doing
that is representative; it is to cover every way the task is really done.

## The decision

**Induction reads every occurrence of a task, and decides each step by how often
it appears rather than by whether all of them share it.**

Neither intersection nor union is right at scale:

- **Intersection** — what all demonstrations share — is what happens today. Every
  optional field disappears. At four doings it produced two steps.
- **Union** — everything anybody did — is worse at a thousand. It contains every
  mis-click, every field somebody typed and corrected, every interruption. The
  skill would learn the task plus a thousand accidents.

A thousand doings give something two cannot: **frequency**. That is the signal
this design turns on.

| how often a step appears | what it is |
|---|---|
| in nearly all of them | part of the task |
| in some, and always alongside a particular value | conditional — `SkillStep.when` |
| in almost none | not the task. A fumble, a correction, a phone call |

The domain already has the concept this needs. `SkillStep.when` is documented as
*"the parameter whose presence decides whether this step happens at all. A form's
optional field: one demonstration typed here and the other left it alone, and
both created the record."* `optional_fills` already computes it — for a pair.
What is missing is doing it across N.

Two consequences follow that are worth as much as the fix itself:

- **Variants stop being merged.** A thousand doings are not one shape. There is
  the quick way and the way with the address lookup. Frequency clustering
  separates them into genuine variants rather than averaging them into a skill
  that is neither. `JoinKind.VARIANT` already exists for this idea.
- **Evidence becomes a source of confidence, alongside runs.** Today confidence
  comes only from ten clean runs. A task witnessed a thousand times is known
  before it has run once — and that is a different, and in some ways better,
  kind of knowledge.

## Questions this spec must answer, and how

### 1. What counts as "nearly all"?

A threshold, and it cannot be a number this document invents. The honest default
is high — a step must appear in the large majority of occurrences to be
unconditional — with the number written where an administrator can read and
change it, next to `WORTH_OFFERING` and `REQUIRED_CLEAN_RUNS`, which are the
existing precedents for exactly this kind of constant.

**It must never be a model's judgement.** ADR 004 holds: no model decides
identity. A step's status is arithmetic over observed frames.

### 2. What makes a rare step noise rather than a rare branch?

This is the question the design can most easily get wrong, and the answer is not
frequency alone.

A step that appears in 3% of doings **and always when the same parameter was
supplied** is a branch — that is the `when` case, and it is exactly the COD
address lookup. A step appearing in 3% of doings with **no such correlation** is
noise.

So the rule is two-part: rarity alone drops nothing; rarity *without a value that
explains it* does. Where a rare step correlates with a value, it is kept as
conditional however rare it is — a branch taken once in a hundred times is still
part of the task, and dropping it is how a skill silently stops handling the case
somebody needs it for.

### 3. How does it scale past a few dozen?

`align` is a quadratic LCS over two runs, with a comment saying runs are a
handful of steps so the table is smaller than the code to avoid it. That is true
of two runs and false of a thousand pairs.

The shape that scales, once a reference is in hand: align each occurrence once
against it rather than every pair against every other. That is N alignments,
not N².

Choosing that reference does not scale the same way, and this spec should not
claim it does. The defensible choice is the occurrence whose steps are most
often present in the others — not the longest, not the most recent — but
"most often present in the others" is scored by comparing every candidate
against every other occurrence, which is all-pairs: O(N²) in the number of
occurrences, exactly the cost aligning-against-a-reference exists to avoid.
Picking a reference cheaply at a thousand occurrences is a real design problem
this spec has not solved; it names the ceiling rather than pretending the
single-reference shape already lifted it.

Retention bounds the problem in practice: evidence is kept 30 days, so the set is
a rolling window rather than all history. That is worth stating, because it means
a skill's understanding of a task ages out, which is a feature where a WMS is
re-configured and a bug where a task is seasonal. This spec does not solve the
seasonal case; it names it.

### 4. What happens to a skill already induced when the thousandth doing arrives?

Re-induction produces a new version, which is what the ladder is built for. The
question is when.

It must not be on every occurrence — a new version on each doing would reset the
clean-run streak forever and no skill would ever earn autonomy. It must not be
never, or a skill learned from four doings never improves on them.

The defensible rule: re-induce when the evidence would materially change the
skill — a step's status crossing the threshold, a new conditional appearing, a
variant separating out — rather than on a count. What "materially" means is the
one thing here a reviewer should look hardest at.

## What this must refuse

- To let a model decide whether a step belongs. ADR 004.
- To drop a rare step that correlates with a value. That is a branch.
- To keep a rare step that correlates with nothing. That is a fumble.
- To truncate one demonstration to the length of another. A short doing is
  evidence that steps can be **skipped**, never that they do not exist.
- To name a parameter it has no step to fill. That is the shape of today's
  defect: `cod_address_id` was derived from evidence whose steps were discarded.
- To re-induce so often that no version can ever earn a clean streak.

## What ships when

| | The operator gets | 
|---|---|
| 1 | Induction reads every occurrence instead of two, and never truncates. The carrier cross reference case produces a usable skill. |
| 2 | Steps are decided by frequency, with rare-but-correlated kept as `when` conditionals. |
| 3 | Variants separate instead of merging. |
| 4 | Re-induction when the evidence materially changes. |

Stage 1 alone fixes what was found today. Stages 2 and 3 are what make it hold
at a thousand.

## ADRs this needs

1. **A step's place in a task is decided by frequency.** Why neither intersection
   nor union is right, what the threshold means, why a rare step with a value
   behind it is a branch and a rare step without one is not, and why none of it
   is a model's judgement.
