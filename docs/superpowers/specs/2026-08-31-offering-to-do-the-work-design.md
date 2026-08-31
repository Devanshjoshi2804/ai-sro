# Offering to do the work, instead of asking to be taught

## The problem

This is what an operator sees today after doing the same job three times:

```
Create workOperations on bf56-kms-wms-web-np2.jdadelivers.com
Seen 3 times · about 40s each · 5.0 minutes so far
[Teach it]  [Not worth it]
```

Every line of it is written from the system's side. The title is an API
endpoint. "Seen 3 times" is telemetry about the person reading it. "Teach it"
asks them to do work *for us*, and "Not worth it" asks them to pass judgement on
our product. Nobody presses this, and the owner is right that nobody will.

The premise is the opposite one: keep learning their work, then offer to do it.
The operator's side of the bargain is that they carry on working.

## What it becomes

```
You've created 3 work operations here today — about 40s each.

    Want me to do the next one?

    [ Yes ]   [ No thanks ]
```

Then, on yes:

```
> create work operation NDPCK, north dock picking, priority 5

  I'll do this in your Work Operations tab:
     fill Operation      NDPCK
     fill Description    north dock picking
     set Priority        5
     press Save

  [ Do it ]   [ Change something ]
```

And afterwards:

```
Done — created NDPCK.
Did that come out right?    [ Yes ]   [ No ]
```

## Decisions taken before this was written

Recorded because each one closed off a design that looked reasonable:

- **The offer is for the *next* one, not the one in progress.** Completing a
  half-filled form is the higher-value moment and is planned second; it needs to
  recognise a task in flight rather than a finished pattern, and it reuses every
  piece built here.
- **Preview, then one press.** Not a rehearsal — a shadow run that withholds
  every write produces nothing the operator asked for, which is the "teach"
  problem wearing a different coat. Not a bare press either. They read what it
  intends and press once.
- **A wrong result counts as a failure.** Not merely recorded for a reviewer.
- **The correction is them fixing it while we watch**, not a form asking which
  step was wrong. They have to repair the record anyway; the repair is
  occurrence N+1 through the capture path that already exists.
- **Values arrive as a sentence**, parsed by the `ResolveIntent` that already
  exists, which refuses rather than guesses. A deployment with no model
  configured falls back to asking for each parameter by name.
- **No conversation store.** `Run.intent` already holds the sentence that caused
  a run, which is the audit trail that matters. A chat log is a second store
  nobody has asked to read.

## What already exists

Verified, with file references, because most of this spec is wiring rather than
building:

- `ResolveIntent` (`application/intent/resolve.py`) — a sentence to a chosen
  skill and its parameter values, refusing when ambiguous, matching literally
  when the model's confidence is below `_READ_FLOOR`. Reachable at
  `POST /v1/intent/resolve`.
- `TeachCandidate` (`application/observation/teach.py`) — a mined candidate to
  an induced skill, at `POST /v1/candidates/{id}/teach`.
- `ExecuteSkill` bound to the operator's own browser, at
  `POST /v1/skills/{id}/runs`, with `device_id`.
- The in-page band naming the step and offering to stop, and `POST
  /v1/runs/{id}/stop`.
- `Run.intent` (`domain/execution/run.py:77`).
- `TrackRecord.after(verdict, at)` (`domain/skill/track_record.py:87`), reached
  through `Skill.record(...)` (`domain/skill/skill.py:324`).
- `SkillStep.intent` — the operator's words for a step, which is what the
  preview renders.

## The design

### 1. The offer

`row()` in `new-chrome-extension/src/panel/panel.js` is replaced. It renders:

- **A headline in the operator's language.** `WorkflowInterpreter.name_task`
  writes one where a model is configured and `ProposeAboutCandidates` has run.
  Where it has not, the headline is derived from the signature's noun — the last
  path segment of the mutating call, split on case (`workOperations` → "work
  operations") — so the offer never depends on a model being present. **The raw
  signature is never rendered to an operator.**
- **A count as a reason, not a statistic.** "You've created 3 work operations
  here today" rather than "seen 3 times".
- **Two actions**: `Yes` and `No thanks`. `No thanks` is the existing dismiss
  call; the word "teach" appears nowhere.

### 2. Yes induces, without saying so

`Yes` calls the existing teach endpoint. The operator never hears the word.

Induction refuses in ways this surface has to answer for:

- `NothingToTeach` / thin evidence — one usable occurrence. The panel says:
  *"I've watched this 3 times but the doings differ too much for me to be sure —
  do one more and I'll try again."* It asks for nothing but their normal work.
- `InductionFailed` — the two recordings will not align. Same sentence. The
  candidate is left `NEW` so the next mine can pair it differently.

Neither is an error dialog. A refusal here is the system declining to guess,
which is the behaviour ADR 004 exists to protect, and it should read like
patience rather than failure.

### 3. The sentence, and the preview

The panel shows one input. What is typed goes to `POST /v1/intent/resolve`.

- Resolved to this skill with every parameter filled → render the preview.
- Resolved but incomplete → ask for the missing ones by name, using the label
  the screen uses, which `Parameter` already carries.
- Ambiguous, or resolved to a different skill → say which skills it might have
  meant and let them pick. `Resolution` already models this.
- No model configured → skip the parse and ask for each parameter directly. The
  offer still works; only the typing is longer.

The preview lists `SkillStep.intent` for each step and the value each will use.
It names the tab it will act in, from the version's `starts_on`.

### 4. The press, and the ladder

**This is the part that changes a governance rule, and it needs its own ADR.**

A freshly induced version is `RECORDED`. `_check_runnable` refuses to run one
because "a recorded skill has not been reviewed by anybody". After the preview it
has been reviewed by somebody: the operator, on the exact steps and the exact
values, at the screen it will act on, with a Stop button in front of them.

So `Do it` promotes the version to `ASSISTED` with the operator as
`promoted_by`, and records that the promotion came from a panel preview rather
than a governance screen — a new `promoted_from` on the version, so a reviewer
reading the console can tell the two apart and can disagree.

What does not change:

- Nothing above `ASSISTED` is reachable this way. `AUTONOMOUS` still needs ten
  consecutive clean runs, and this press is not one of them.
- A version whose skill `changes_the_system` still refuses to run above shadow
  without `authorized_by`, which the press supplies by name.
- The breaker, the blast radius and the device binding are untouched.

The run is started with `device_id`, `medium=ui`, `authorized_by` = the
operator, and `intent` = the sentence they typed.

### 5. Afterwards

When the run finishes the panel asks one question, once.

**Yes** — nothing new. The run's verdict stands as judged.

**No** — two things happen.

First, `POST /v1/runs/{id}/wrong`, carrying an optional note. This sets a new
field on the run and re-judges it: a run the operator says was wrong is
`Verdict.FAILED` whatever its steps did, so it breaks the clean streak and
counts toward demotion. **This is the one failure mode the ladder is blind to
today** — `judge()` reads statuses, media and escalations, all of which can be
perfect while the record created is wrong.

The domain gains exactly one concept: `Run.wrong_because: str | None`, set by a
person after the run finished, and `judge()` returning `FAILED` when it is set.
Nothing else in the ladder moves.

Second, the panel says:

> *"Sorry. Fix it the way you meant — I'm watching, and I'll learn from that."*

Their repair is captured by passive observation, becomes occurrence N+1 of the
same candidate, and re-induction happens on the next mine. Nothing is asked of
them that they were not already about to do.

### 6. The same box runs anything

The input is not only for the offered task. A sentence that resolves to any
skill in the library starts that skill, through the same preview and the same
press. The offer is a pre-filled message into it.

This falls out of using `ResolveIntent` rather than a form, and it is the reason
the sentence was chosen over one: a form can only ever run the one task being
offered.

## What this must refuse

- To run a skill whose induction refused. There is no partial skill.
- To run above `ASSISTED` on the strength of a panel press.
- To act on a sentence it is not sure about. `ResolveIntent` already refuses;
  the panel must render the refusal rather than pick the top match.
- To count a run the operator called wrong as clean, whatever its steps did.
- To ask the operator to demonstrate anything. Every path here either uses what
  was already watched or asks them to do their own job.

## Verification

Per section, with each new test proved by reverting the rule it defends:

- **Offer**: a candidate with no model-written title still renders a plain
  English headline; the raw signature never reaches the DOM; "teach" appears
  nowhere in the panel's rendered text.
- **Induction refusal**: a candidate with one usable occurrence renders the
  patience sentence and leaves the candidate `NEW`.
- **Preview**: every step is rendered by its `intent`; a resolution with a
  missing parameter asks for it by its screen label rather than its name.
- **Ladder**: a press promotes to `ASSISTED` and no further; `promoted_from`
  distinguishes it; a version needing authorisation still refuses without a
  name.
- **Wrong result**: `judge()` returns `FAILED` for a run marked wrong however
  clean its steps; the streak breaks; three in a row demote. Reverting the
  `wrong_because` check makes a wrong run clean again.
- **Re-induction**: a repair after a wrong run becomes occurrence N+1, and the
  next mine pairs it — an integration test over the mining path, not a unit
  test of the intention.
- **Browser**: the offer, the sentence, the preview, the press and the question,
  in a real Chrome against the stub.

## What ships when

| | The operator can | Autonomy |
|---|---|---|
| 1 | Be offered the next one, and say no | none — the offer alone |
| 2 | Type a sentence, read a preview, press once | assisted, per press |
| 3 | Say it came out wrong, and have that count | assisted, with the ladder able to see a bad result |
| 4 | Type any task, not only the offered one | assisted, across the library |

Each is usable alone. 1 and 2 are the smallest thing worth putting in front of a
warehouse; 3 is what stops it confidently repeating a mistake; 4 is the chat
surface, which is mostly the absence of a restriction rather than new code.

Mid-task completion — offering to finish the form they are inside — is the
follow-on project, and reuses all of this.

## ADRs this needs

1. **A preview an operator read is a review.** Why a panel press may promote a
   version to assisted, what it deliberately does not reach, and how a reviewer
   tells a preview-promotion from a governance one.
2. **A person can call a finished run wrong.** Why an operator's judgement of
   the result belongs in the track record beside the machine's judgement of the
   steps, and why it counts as a failure rather than as a note.
