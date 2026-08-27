# A field nobody filled, and a task nobody asked for

## Context

A real form has thirty fields. Two people creating the same kind of record fill
different subsets of them, and both are doing the job correctly — the goal is
satisfied either way. Induction today reads that as two different tasks and
refuses to learn anything, which means passive observation, which is the whole
premise, produces nothing on any form worth automating.

This was found on real evidence rather than reasoned about. Two work areas
created in Blue Yonder on 2026-08-27, watched passively, no demonstration:

```
201 {"workArea":"TWOTEST",  "workAreaDescription":"testing again",   "warehouseId":"SG",
     "deltaPriority":1,    "absolutePriority":3, "homeWorkAreaAbsolutePriority":2, "voiceCode":"1",
     "distanceThreshold":"", "pickExceptionDepositArea":""}

201 {"workArea":"THREE TE", "workAreaDescription":"testing for ai sro","warehouseId":"SG",
     "deltaPriority":null, "absolutePriority":2, "homeWorkAreaAbsolutePriority":3, "voiceCode":"2",
     "distanceThreshold":"", "pickExceptionDepositArea":""}
```

**The writes have the same shape.** Every field is present in both; the field
the operator skipped arrives as `null`. At the level of what changed in the
warehouse these are two doings of one task differing only in values, one of
which is nothing.

The refusal came from somewhere else entirely: `align`
(`application/induction/diff.py:243`) compares *gestures*, and one recording has
a `type` on Delta Priority that the other does not. `_evidential`
(`:225`) treats any action carrying a value as evidence, so the pair is
refused with "the runs are not two runs of one task". The system compared
keystrokes while the evidence for the task sat in the write.

**What already exists** (verified, file:line below): passive capture per watched
tab; segmentation that cuts a run at each change somebody caused; clustering by
exact signature; automatic learning at three doings (`LearnWhatRepeats`); the
two-run diff; the promotion ladder; `Medium.NETWORK | UI | VISION` with
escalation and computer-use gestures at the bottom; per-trigger `auto_approve`
and `authorized_by`; and a knowledge base whose `EntryKind.QUESTION` is
explicitly "something the system could not decide and will not guess at …
answered once, by somebody who works here".

**Decisions taken before this document**, in the owner's words where it matters:

- A field nobody filled is a **value, not a missing step**. The write is the
  contract; gestures are one way of producing it.
- **Both paths must survive.** Blue Yonder exposes an API; the next WMS may
  only expose a form. A skill keeps its network plan *and* its gesture plan, and
  a skipped field must not break either.
- A value from outside that no demonstration ever filled is **allowed** — the
  field is in the contract — but it is **asked about once and then remembered**.
- Everything answerable is settled **before the run starts**. A create that
  stops halfway leaves a bad record the WMS will not roll back.
- The ask is a **pre-flight, never an interruption**: "here is what I will do,
  with these values, saving you this long" — one press.
- It **goes away only where somebody said so, per trigger**. A skill does not
  acquire permission by running well ten times; a named person grants it for one
  task on one system.
- **If it knows, it does not ask.** Asking twice is not learning.

## The proposition this serves

Watch how the work is done. Learn it. Then, when the same work starts again,
offer: *"I can finish this — it takes you about four minutes."* One press. What
is automatic is the noticing and the preparation; what stays with a person is
the decision, until they hand that over deliberately.

---

## Part 1 — a skipped field is a value

`align` keeps its rule that an unmatched step which carried a value is a
disagreement, with one exception it can prove:

> An unmatched action is not a disagreement when the value it carried appears in
> that run's write under a key the *other* run's write also carries, holding
> nothing.

Both halves are read from evidence already stored. `type '1'` in run A appears
as `deltaPriority: 1` in A's body; B's body carries `deltaPriority: null`. The
key is present in both, so the field is part of the contract; the value is
present in one, so the field is optional. Nothing is inferred about a key that
appears in only one body — that is a genuine disagreement and still refuses.

Where the exception applies, the step becomes **conditional**:

- `SkillStep` gains `when: str | None` — the parameter whose presence decides
  whether the step runs.
- `Parameter` gains `optional: bool = False` and `absent_as: str | None = None`
  — the second being the form the field takes when nothing is supplied, read
  from the run that omitted it (`null` here, `""` for `distanceThreshold`) and
  never invented.

Both are document fields on the version, which is stored as JSONB through a
pydantic `TypeAdapter` (`infrastructure/db/codec.py`), so **no migration** —
the same precedent as `systems` and `loops`. Defaults are required: rows written
before this have neither key.

Required and optional are settled by evidence, in that order: a key filled in
every doing is required; a key present in every write but filled in only some is
optional. The page's own markers (`Work Area*`, `x-form-required-field`, which
the recorder already captures in `attributes`) corroborate and are stored as
knowledge, but never overrule what was actually done.

**Binding a gesture to a field.** A `type` action is bound to the body key whose
value equals what was typed, in that run's own write. Exact match only; a value
that appears under two keys binds to neither and the step stays unconditional.
This is the same instrument `Substitution` and the `sites` module already use to
prove parameters (`application/induction/sites.py`), applied one level earlier.

## Part 2 — both paths, one skill

Nothing here may cost the gesture path, because a WMS that exposes no writable
API is exactly the customer this system is for.

- **Network** — the body is rendered with the supplied values; an absent
  optional takes its absent form. One call, assertable, and the only medium a
  run can be `CLEAN` at (`domain/execution/verdict.py`).
- **UI** — a conditional step is performed when its parameter has a value and
  skipped when it does not. `_ui_for` (`execute_skill.py`) already holds the
  step; the skip is a guard at the top of it.
- **Vision** — the same skipping, with the gesture proposed by computer-use when
  the control cannot be found by locator. A control the model cannot identify is
  not a failure: it is a question, with the screenshot attached.

A skill whose gesture path is incomplete is not a broken skill — it runs on the
rung it has evidence for, and says which rungs it does not have.

## Part 3 — a value nobody has ever typed

A mail says "create work area PACK-3, distance threshold 50", and no recorded
doing ever filled `distanceThreshold`.

The value is allowed: the key is in every write, so it is part of the contract.
It is not sent unexamined. Before the run starts, the system records an
`Ambiguity` (`application/knowledge/open_questions.py`) keyed to that field on
that system — *"nobody here has ever filled distanceThreshold; send 50?"* — and
the answer becomes knowledge like any other, carrying who said it.

Asked once. The second mail of that kind runs straight through, because the
answer supersedes the question and every later decision reads it. A system that
asks the same thing twice has not learned anything.

The same seam takes the model's uncertainties: a control computer-use cannot
identify, two locators that both match, a value the intent parser read two ways.

## Part 4 — everything asked before anything is done

`_check_runnable` (`execute_skill.py`) already refuses a run missing a required
input. It gains the rest of the pre-flight:

1. Resolve every value — from the trigger, the message, the knowledge base.
2. Collect what is unknown: unanswered questions, values for never-filled
   fields, controls the last run had to escalate for.
3. If anything is unknown, the run **does not start**. It becomes an offer
   carrying its questions.
4. If nothing is unknown, it is still an offer — see Part 5 — unless this
   trigger was authorised to run without asking.

Nothing is discovered halfway. A question raised mid-run is a record half
created in a warehouse nobody can roll back.

## Part 5 — the offer

An offer is what the operator sees, and it is the same object whether it came
from a mail, a schedule, or from the system noticing the work starting in front
of it.

It carries: what will be done, on which system, with which values and where each
came from, what it is unsure about, and **how long it usually takes by hand** —
`median_duration_ms` is already computed on the candidate
(`domain/observation/candidate.py:176`).

Three ways it arrives:

- **The work starting again.** A watched tab is doing the first steps of
  something already learned. Recognition is exact, not a model's opinion: the
  calls seen so far are a prefix of a known skill's signature on the same host.
- **A message.** A mail or webhook fires an inbound trigger; the offer is what
  the pre-flight produced.
- **A schedule.** Same object, raised when the clock comes round.

Answering an offer is one press. Answering a question inside it is one press per
question, and each answer is remembered.

## Part 6 — when the asking stops

Per trigger, never per skill, and only where a named person said so — which is
`auto_approve` and `authorized_by` on `Trigger`, already built and already
refused unless a named person is behind it (`create_trigger.py`).

The ladder still gates what *may* run unattended: a version that has not earned
`AUTONOMOUS` cannot, whatever the trigger says, and a gesture-stepped run can
never be `CLEAN` so it can never earn it. Permission and reliability stay two
different things, and both are required.

## What this refuses

- A key present in one run's write and absent from the other's — a real
  disagreement about what the task is.
- A typed value that matches no key in that run's own write — the binding is not
  proved, so the step stays unconditional and the pair still refuses if it is
  unmatched.
- Sending a value for a field nobody has filled, before the question about it is
  answered.
- Starting a run with an unanswered question in it.
- Asking a question that has already been answered.
- Any of it on a version the ladder has not promoted, or a trigger no named
  person authorised.

## Verification

Per part, each new test proved by reverting the rule it defends:

- **Part 1** — unit: two doings differing only in an optional field induce, and
  the step is conditional; a key in one body and not the other still refuses; a
  typed value matching two keys binds to neither; the absent form comes from the
  evidence (`null` vs `""`), not a constant. Against the two real work-area
  recordings as a fixture.
- **Part 2** — unit: a conditional step with no value is skipped on the UI path
  and rendered as its absent form on the network path. Browser: a form filled
  twice with different subsets, replayed by clicking, produces the right record.
- **Part 3** — unit: a never-filled field raises a question rather than being
  sent; the same field asked twice reads the answer instead.
- **Part 4** — unit: a run with an unanswered question does not start; nothing
  is written.
- **Part 5** — unit: an offer carries its values, their sources and the time
  saved; recognition is a prefix match on the signature and nothing else.
  Browser: the panel offers while the operator is mid-task.
- **Part 6** — unit: an autonomous version with an unauthorised trigger still
  asks; an authorised trigger on a version that has not earned autonomy still
  refuses.

## What ships when

| Part | What is true afterwards |
|---|---|
| 1 | The work areas you created become a skill, with Delta Priority optional. |
| 2 | That skill runs by clicking on a WMS with no writable API. |
| 3 | A value nobody has typed can be used, once somebody has said it may. |
| 4 | Nothing starts that cannot finish. |
| 5 | The panel offers the job while you are doing it, and says what it saves. |
| 6 | A named person can let one task run without being asked. |

Parts 1 and 2 are the ones that make passive learning work at all. Part 5 is
what the operator actually experiences. Part 6 is the only part that lets
anything act unasked, and it is one decision by one person about one task.

## ADRs this needs

1. **A skipped field is a value.** Why an unmatched step may be dropped when the
   write proves the field is optional, and why that is not the guessing ADR 004
   forbids.
2. **An offer is how work begins.** Every run is offered before it acts, and the
   asking stops only where a named person said so, per trigger.
