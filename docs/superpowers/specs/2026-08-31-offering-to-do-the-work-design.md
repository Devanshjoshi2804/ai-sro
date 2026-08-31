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

And afterwards it shows what it made, and offers to take it back — rather than
asking whether it went well:

```
Created NDPCK — north dock picking, priority 5.

  [ Undo that ]        [ It's wrong — I'll fix it ]
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

**And it shrinks as the version earns it.** A preview on every press, forever,
is the thing the research is bluntest about: requiring approval for every action
an agent takes defeats the point of automating it. The ceremony is tied to the
rung, not to the press:

| Rung | What the operator sees before it runs |
|---|---|
| first press, `RECORDED` | every step and every value |
| `ASSISTED`, streak below `REQUIRED_CLEAN_RUNS` | one line and `Do it`; the steps behind a disclosure for anyone who wants them |
| `AUTONOMOUS` | nothing beforehand. It runs and says what it did |

Two things this deliberately is not. It is not a preference — an operator cannot
turn the preview off, because the point is that the *version* earned it and the
evidence for that is the track record, not somebody's patience. And it is not a
new ladder: the rows above are the rungs that already exist, read for a purpose
they were not being read for.

The published case for this shape is Grid AI's, where approval on every change
gave way to auto-execution with a notification after a run of consecutive
approvals, and adoption was *higher* than in versions that offered full autonomy
from the start. That is the same argument the promotion ladder already makes;
this only makes the panel say it.

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

The panel shows what was made, and offers to take it back. It asks nothing.

```
Created NDPCK — north dock picking, priority 5.

  [ Undo that ]        [ It's wrong — I'll fix it ]
```

**The output, not "Done".** `Run.derived` already holds what the skill read back
after its write, because a step that creates something reads it again to check
it. That read-back is the record, in the system's own words, and it is what the
panel shows. Where a run derived nothing, the panel says only that it finished
and names the step it finished on — an honest "I cannot show you what I made" is
better than an assured "Done" over a record nobody has seen.

**Undo instead of a question.** The first draft of this design asked "did that
come out right? Yes / No". That is a survey, and operators stop answering
surveys. Undo is a thing they *want*, so pressing it costs them nothing to be
honest about — and it is a strictly better failure signal for exactly that
reason. The research is unambiguous: a visible undo is the closest thing to a
universal trust mechanism in agentic interfaces, because trust requires knowing
you can recover from a mistake.

**Undo is evidence, never inference.** It is offered only when the tenant has a
skill that reverses this one, and reversing is not something this system will
guess at:

- the run's mutating call is a `POST` to some resource shape, and
- a runnable skill in the library makes a `DELETE` on that same shape, and
- the run derived the identifier that skill needs.

All three or no button. `url_shape` already answers the first two and it is the
same function induction uses to decide two calls are the same call. Nothing is
proposed as an undo because a model thought it looked like one.

Where there is no undo, the second action stands alone: *"It's wrong — I'll fix
it"*, which says

> *"Fix it the way you meant. I'm watching, and I'll learn from that."*

**Either press marks the run wrong.** `POST /v1/runs/{id}/wrong` sets
`Run.wrong_because` — `"undone by the operator"` or their note — and `judge()`
returns `FAILED` whatever the steps did. It breaks the clean streak and counts
toward demotion. **This is the one failure mode the ladder is blind to today**:
`judge()` reads statuses, media and escalations, every one of which can be
perfect while the record created is wrong.

**Silence means it was fine.** Nothing is asked, so nothing goes unanswered, and
a run nobody touched is judged exactly as it is judged today. The two actions
stay available on the last finished run so an operator who closed the panel and
came back can still reach them, and only the person whose browser ran it can
press either — they are the only one who saw what it produced, and a guess in
the track record is worse than a silence.

After an undo or a repair, their manual work is captured by passive observation,
becomes occurrence N+1 of the same candidate, and re-induction happens on the
next mine. Nothing is asked of them that they were not already about to do.

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
- To let anyone but the operator the run was performed for call its result
  wrong.
- To offer an undo it inferred. Three facts or no button.
- To let an operator dismiss the preview. The version earns that, on its track
  record, or it does not have it.
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
- **Preview shrinks**: a first press shows every step; the same version with a
  clean streak shows one line; an autonomous version shows nothing beforehand.
  Reverting the rung check makes all three identical, which is the defect.
- **Output**: a run with derived values shows them; a run with none says so
  rather than reporting "Done".
- **Undo offered**: a `POST` run with a matching `DELETE` skill and a derived
  identifier offers it; missing any one of the three does not. Reverting the
  identifier check offers an undo that cannot name what it would remove.
- **Ladder**: a press promotes to `ASSISTED` and no further; `promoted_from`
  distinguishes it; a version needing authorisation still refuses without a
  name.
- **Wrong result**: `judge()` returns `FAILED` for a run marked wrong however
  clean its steps; the streak breaks; three in a row demote. Reverting the
  `wrong_because` check makes a wrong run clean again. A run nobody touched is
  judged exactly as it is today — silence is not a verdict.
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
| 3 | See what was made, and take it back | assisted, with the ladder able to see a bad result |
| 4 | Type any task, not only the offered one | assisted, across the library |
| 5 | Stop being asked, once the version has earned it | the ladder's rungs, finally visible to the operator |

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
   steps, why it counts as a failure rather than as a note, and why it is
   collected as an undo they wanted rather than as a question they answered.

## What the field already solved, and what it did not

Checked before this was planned, so the parts that are ours are ours on purpose:

- **Task mining discovers and then stops.** UiPath Task Mining and Power
  Automate's Process Advisor both record desktop actions and surface automation
  opportunities — and hand off to a developer to build the automation in an IDE.
  The industry path is discovery to implementation by an engineer. Nobody closes
  the loop to "shall I do that one for you now", which is the whole of this
  design and why there was no pattern to copy for it.
- **Approval on every action is the known failure.** The human-in-the-loop
  literature is direct about it: requiring approval for every action defeats the
  point of automating it. That is what the first draft of this spec did.
- **Progressive delegation is the answer, and we already have it.** The pattern
  is to let the user's own approval history set the pace, expanding autonomy on
  demonstrated reliability rather than demanding it at launch. That is the
  promotion ladder, built and running; what was missing was the panel reading
  it.
- **Undo beats confirm.** A visible undo is described as the closest thing to a
  universal trust mechanism in agentic interfaces. This design had a
  satisfaction question instead, which is a survey, and surveys go unanswered.
