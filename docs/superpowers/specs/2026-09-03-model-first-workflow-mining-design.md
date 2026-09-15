# Model-first workflow mining

> **Correction, 2026-09-14.** Where this document cites "86.9% against 78.8%"
> for state-grounded versus screenshot verification, with human agreement at
> 94% and "artifact verification 192 of 321 tasks": those figures could not be
> found in any paper, including the one this repository cites for them
> (arXiv:2410.00689, which reports 84.24% against 70.04% over 322 tasks, over
> 84% human agreement, and has no artifact category). The plan's conclusion --
> status first, read second, picture last -- is supported by the real numbers.
> Left in place rather than rewritten: this file is a record of what was
> planned and when. `verify.py` and `belts.py` carry the corrected figures.


## Context

The owner drew an architecture on a whiteboard: every captured gesture goes
through a fast model on its own for an intent, then the whole window — all the
intents, all the evidence underneath, across every operator's stream — goes to a
large model in one pass, which returns a proven workflow. Intents nobody could
place wait and are read again beside somebody else's evidence.

His words: *"each gestures matter... one workflow has gesture which is missed in
u3... don't block ourselves on network calls... this big workflow for the current
scenario can include creating supplier plus adding item in Blue Yonder plus
changing status in SAP."*

**Why the pipeline we have cannot do that.** Three of its deliberate decisions
stand directly in the way. `observation/segment.py` partitions the day by host
before anything else, so a two-system job is two candidates structurally and
forever. `observation/mine.py` keys on `(principal_id, signature)` compared for
exact equality, so one extra page or one redesigned form produces a second
candidate that can never pair with the first. And the pre-filter's constants —
overlap ≥ 0.60, same host, adjacent within five minutes, at least twice, at most
twenty pairs a sweep — were tuned once, against one WMS.

None of that is a defect. It is what the architecture chose, and
[`docs/17-agent-architecture.md`](../../17-agent-architecture.md) argues for it
well. This spec tests the opposite bet in a place where losing it costs nothing.

**The rationale, the research behind every number quoted here, and the full
architecture in prose live in
[`docs/new-agent-doc-arc/README.md`](../../new-agent-doc-arc/README.md).** This
document is the decisions and their interfaces.

## Decisions taken before design

Each was the owner's, chosen from alternatives offered:

| | Decision |
|---|---|
| Evidence source | **Live from the extension.** Its own ingest endpoint; the extension dual-posts. Not a replay of stored recordings. |
| Umbrella trigger | **Sliding window.** Fires as new gestures accumulate, continuously. Not idle-triggered, not on demand. |
| What a proven workflow becomes | **Executable.** The full loop, not an inspection report. |
| How it executes | **The model plans, the extension performs.** The frozen `docs/14` command channel, in the operator's own Chrome. Not server-side computer use, not parameter substitution into recorded calls. `backend/src/sro/application/skill/from_rig.py` and its siblings turn a mined workflow into the backend's skill shape — recorded calls with values substituted — for the backend's promotion ladder. That is the governance path anything unattended must pass through; it is not how a run performs. `new_agent_arch/src/rig/runner.py` is. |
| Starting a run | **Chat, with the form as fallback.** |
| Streams | **Multi-stream from day one.** Carryover is tenant-wide, so one operator's leftover intent can complete against another's evidence. |
| Reuse | **The backend may be reused.** Wire schemas, the Gemini client, blob storage, config — never `observation/`, `induction/`, `domain/skill/` or Temporal. |

Two decisions were taken during design, against measured evidence rather than
preference. Both are recorded here because they modify the whiteboard:

**A window is bounded by tokens, not by a gesture count.** Gemini Pro's input
price doubles above a 200K-token prompt ($2 → $4 per million). The window fills
to roughly 150K tokens and stops, with a floor of twenty-five gestures. This is
the honest form of "no cap": no cap on what kinds of evidence go in, a cap on
tokens per pass, and the carryover pool takes the overflow.

**A workflow's identity is set overlap on cited gesture identifiers, not the
model's opinion.** A model asked to re-judge its own earlier verdict disagrees
with itself at roughly 90%, and "is this the same workflow I proposed last pass?"
is exactly that question. The model's `same_as` is recorded and does not decide.

## Design

### Shape

One process in `new_agent_arch/`, its own `uv` project with a path dependency on
`backend/`, three loops over one store. The dependency points one way; the
backend's import-linter contracts are untouched.

```
extension ── capture ──▶  INGEST   store verbatim; each gesture → Flash → Intent
          ◀── commands ──  RUNNER  chat/form → per step: look, plan, perform, verify
                           MINER   window full → Pro over window + carryover
                                   + known workflows + KB → ProvenWorkflow[]
```

### Records

```
Gesture   id ges_<32 hex> · stream_id · tenant · at · url · tab_id · frame_url
          gesture { kind, target{role,name,text,testId,cssPath,xpath,
                    component{framework,xtype,itemId,fieldLabel,query,chain}},
                    value, secret, modifiers }
          requests[] (full exchanges) · page_events[] · ax_ref · shot_ref

Intent    gesture_id · act · object · system · page · values_seen[]
          continues · confidence · why
          — stored beside the gesture, never replacing it

ProvenWorkflow
          title · narrative · systems[]
          steps[] { order, says, system, cites: [ges_…], parameters }
          parameters[] { name, seen_values, where }
          same_as (opinion) · unproven[]

Run       workflow_id · values · started_by · live|dry
          steps[] { order, says, planned_by, command, result,
                    before/after shots, verdict }
          outcome · withheld writes
```

Event shapes are the protocol's, unchanged. Nothing is reshaped on the way in.

### Accessibility trees

An AX tree needs `chrome.debugger`, which banners every attached tab for as long
as it is attached; the protocol reserves it for the teaching tier for that
reason. **Capture uses the ExtJS `component` chain `recorder.js` already
extracts** — `xtype`, `itemId`, `fieldLabel`, `query`, `chain` — which on Blue
Yonder is close to as good and costs nothing. **The debugger attaches only while
a run executes**, where a banner is honest about what is happening and lasts a
minute. Revisit only if the component chain proves thin on a system that is not
ExtJS.

### Call one — Flash, per gesture

One gesture per call. Bundling per-item work into shared calls measurably
degrades each item's answer, and the money saved is small: at $0.50 per million
input tokens against a 400–900 token record, a gesture costs about $0.0003 and a
two-thousand-gesture day about sixty cents.

Input: the gesture, its correlated requests with bodies trimmed to keys and short
values, its page events, the last eight intents on that stream as one line each,
and the screenshot only where the target fingerprint is thin. Output is the
`Intent` above.

### Call two — Pro, per window

Input: the window (every gesture since the last pass, in order, with its intent
and its full requests — bodies inline until the budget is spent, then by
reference the model can ask to open), the carryover pool, the workflows already
held with their cited sets, and the knowledge base. Output is
`ProvenWorkflow[]`.

### The three checks

The only code that overrules a model. None of it inspects a URL, a body, or a
call shape.

1. **The identifiers exist.** A step citing a gesture not in the store rejects
   the workflow; the bad identifiers are logged. Citation is mandatory — models
   omit citations wherever the output shape allows, which inflates apparent
   accuracy — so an uncited step is a rejected step.
2. **Coverage.** Record which parts of the window were cited at all. Long-context
   citation shows strong primacy bias; a pass citing only its first third means
   the window is too long, and the token budget comes down.
3. **Identity, two layers, both arithmetic.** Cited-gesture-ID sets are
   per-occurrence — two independent doings of the same job cite disjoint IDs —
   so raw overlap on them only answers "is this a re-read of a window already
   processed?" (Jaccard, ≥ 0.5). Whether *this* proven workflow is the *same job*
   as one seen on different evidence is answered by a second key, derived from
   the same cited gestures: `shape_key = [(system, target_identity, action_kind)
   for each cited gesture, in order]`, where `target_identity` prefers
   `component.itemId` → `component.query` → `role|name` → `testId` — the
   `recorder.js` fingerprint the runner already turns into locators, UI-level
   rather than network-level. Compared by **containment**
   (`|A∩B| / min(|A|,|B|)`, not Jaccard) so a 3-step "create supplier" is
   recognised as sitting inside a 12-step "create supplier, add item, set status
   in SAP" rather than being called a different job. **0.5 is the one tunable
   constant in the system**; verification steps 2 and 2a are what measure it.

### Shared values as a fourth stitch signal

Cross-organisational process mining reconstructs one process from logs with no
shared case identifier at over 98.4% precision and 94.2% recall, by linking on
**shared data items across the separate logs**. That signal is already in our
evidence: a supplier name typed into Blue Yonder that reappears in an SAP request
body links the two halves, and it is arithmetic over `Intent.values_seen`, not an
opinion. Trivial values are excluded by length and by frequency across the
tenant's evidence — a facility code every call carries links nothing. The
umbrella pass is told which values crossed a boundary rather than left to notice.

### How the window is arranged

Ordering measurably changes the answer on multi-hop tasks — 0.28 to 0.44 by
ordering alone on a two-supporting-fact task at 64K — and reading a workflow out
of a window is multi-hop. Therefore:

- Task instruction **first and restated after the evidence**; question-first was
  strongest at long context.
- Output schema puts `cites` **before** `says`: identifying relevant evidence
  before composing the answer measurably beats composing first.
- Strongest evidence (carryover, high-confidence intents) at **both ends**,
  weakest in the middle — the training-free reordering whose gains appear
  specifically once the evidence set is large.
- **No relevance hints.** Explicitly marking the most relevant context was
  measured to *reduce* accuracy in all five languages tested.
- **Sample count defaults to 1**, and is a knob rather than a prohibition.
  Published gain was 0.4% at 20x cost — but measured on Gemini-2.5-Flash-Lite,
  and the backfire result (56.6% / 65.7% of problems made worse) is from 7–8B
  open models and does not transfer to a frontier model. What does bear on us is
  the direction: that paper's thesis is voting helping *less* as models get
  stronger, so newer models argue for expecting less, not more. Verification step
  3b settles it on our own windows. **Reasoning effort is the first knob**, which
  does show a significant positive relationship with accuracy.

### Which model runs which call

Configuration, not architecture. Gemini 3.8 Flash (introductory $0.75/1M in,
$3.75/1M out to 2026-12-31) is the strongest workhorse for long-horizon and
agentic planning, which describes both the runner's step-planner and possibly the
umbrella pass — at a third of Gemini 3.1 Pro's input price for a 150K-token
window. Whether it reads a whole day's evidence as well as Pro is answered by
verification step 3c on identical input, not assumed in either direction.
Per-gesture work starts on 3.8 Flash (~$0.0005 a gesture, ~$1 for a
two-thousand-gesture day) and moves to Flash-Lite if that reads a gesture as
well.

### The carryover pool

Gestures cited by a proven workflow leave the pool. Unplaced intents enter at age
zero, age by one each pass, and retire past age six or seven days — kept in the
store, out of the prompt. **The pool is tenant-wide**, which is what lets one
operator's Blue Yonder half meet another's SAP half.

It is load-bearing rather than decorative: model abstraction over raw event
streams was measured at roughly 74% recall, so a quarter of every window needs a
second reading in different company.

### The runner

A step cites gestures; those gestures carry fingerprints; so **the locator list
is built from the cited evidence with no model involved**, in the protocol's
priority order — `component`, `role_and_name`, `text`, `test_id`, `css_path` —
and `origin` is the scheme and host of that gesture's own request.

`origin` is therefore **per step**. In a job spanning two systems the Blue Yonder
steps carry Blue Yonder's origin and the SAP step carries SAP's, because that is
what their evidence says. Same rule `AGENTS.md` states for credentials, reached
from the other direction.

Per step: `ui.url` and an inline `screenshot`; Flash plans exactly one command
(`ui.perform`, `http.send` or `navigate`); the extension performs and answers
with `performed`, `matched_by` and `candidates`; then **verification against
state rather than against a picture** — the response body the command returned
first, a confirming read second where the cited evidence shows the page performs
one, the screenshot last and least. A state-grounded verifier scored 86.9%
against 78.8% for one reading screenshots, and most completions leave their proof
off-screen (artifact verification was 192 of 321 tasks in that study). On failure
or an unclear verdict, Pro retries once with both screenshots, the failure, the
full cited evidence and the workflow so far. Still failed: stop and ask.

`matched_by` is recorded as a health signal. When `component` and
`role_and_name` both miss and `css_path` catches it, the run **succeeds and the
workflow is flagged stale**.

`allow_focus` is true for runs started from chat or the form — the operator asked
and is watching — and never for anything the miner starts by itself.

### Entering a run

Chat: Flash reads the utterance against the workflows held and answers
`{workflow_id, values, missing}`; missing values are asked in the thread. Saying
it offers the work; pressing start authorises it. Form: the workflow's declared
parameters as fields, prefilled with last-seen values, for when extraction
misreads.

## What this must refuse

- **A command to a host outside the run's origin allowlist** — the systems the
  workflow's own evidence names — refused by the rig before it reaches the
  extension.
- **A live write on a workflow's first execution.** Dry run is the default:
  reads and navigations go out, writes are shown in full and withheld. A person
  presses through. After one clean live run the workflow may start live.
- **A run that exceeds its step budget** — the workflow's step count plus slack.
- **A workflow whose steps cite gestures that do not exist.**
- **Search grounding on any Gemini call.** It voids zero-data-retention:
  prompts, context and output stored for thirty days, no opt-out.
- **Screenshots left behind in the File API.** They persist until the caller
  deletes them; deleting them is part of the ingest path, not a cleanup job.
- **Anything unattended.** No promotion ladder, no circuit breaker and no blast
  radius are built here. Nothing from this architecture runs without a person
  watching until it goes through the real governance in `backend/`.

## Verification

1. **The cross-system claim, which is the whole bet.** Do the supplier job by
   hand across Blue Yonder and SAP, twice, with tabs interleaved. The miner
   returns **one** `ProvenWorkflow` naming both systems, with steps citing
   gestures from both hosts. The existing pipeline, over the same evidence,
   returns two candidates that pair only through a judged suggestion — record
   both outcomes side by side.
2. **Occurrence identity is stable across passes.** Re-run the miner over
   evidence it has already read. No new workflow appears; overlap resolves each
   proposal to the one already held. Repeat with the window's gesture order
   shuffled.
2a. **Job identity holds across independent occurrences.** Do the supplier job
   twice, on different days, no two cited-gesture sets in common. The
   `shape_key` containment score resolves the second occurrence to the workflow
   the first proved — proving overlap on cited IDs alone (0 here) would not.
   Then do a *different* job that shares one lookup step; containment must not
   fold it into the same workflow at the chosen threshold.
3. **Coverage is honest.** A pass over a deliberately over-long window reports
   its positional skew **in whichever direction it appears**, and the budget
   reduces in response. Position bias is model-specific — some models favour late
   context, and one reproduction study found no positional effect at all — so
   this measures our models on our evidence rather than assuming a primacy bias.
3a. **The window arrangement is measured, not assumed.** Run one window under
   question-first and under question-last, and with strongest-evidence-at-both-
   ends against evidence in capture order. Record the difference in workflows
   proven and citations produced. Ordering moved accuracy from 0.28 to 0.44 in
   published multi-hop work; if it moves nothing here, say so and stop paying
   attention to it.
3b. **Does repetition buy anything on our windows?** Run one window three times
   at sample count 1, and once at sample count 3 with a plurality over the
   workflows proposed. Compare workflows proven, citation stability, and cost.
   Published evidence says no (0.4% at 20x) but was measured on a weaker model
   and a different task; three passes over one window costs an afternoon and
   settles it for ours. Turn the default up only if this says to.
3c. **Is Pro needed for the umbrella pass?** Same window, same prompt, Gemini
   3.8 Flash against Gemini 3.1 Pro. Compare workflows proven, citation validity,
   coverage skew, and cost. Flash is a third of the input price; if it reads a
   day's evidence as well, the umbrella pass belongs on it.
4. **Citations are enforced.** A hand-edited model response citing a fabricated
   `ges_…` is rejected, and the rejection names the identifier.
5. **Carryover works across streams.** One operator does the Blue Yonder half,
   another does the SAP half within the pool's lifetime. A pass proposes the
   joined workflow. Repeat with the shared typed value changed in the second
   half, so no value crosses the boundary: record whether the join still
   happens, which is what says how much work the shared-value signal is doing.
6. **A run performs.** From chat, with one value withheld and asked back. Dry run
   first: the write is shown and withheld. Then live: the supplier exists in Blue
   Yonder and the status is set in SAP, and every step's record holds its
   command, its `matched_by` and both screenshots.
7. **The boundary holds.** A planned command to a host outside the allowlist is
   refused. `grep` the rig's stored prompts for a captured credential value:
   nothing.
8. **Cost is what we said.** A full day's ingest reports its Flash spend per
   gesture and its Pro spend per pass, and no pass exceeds a 200K-token prompt.

## Out of scope

- **The promotion ladder, the circuit breaker, blast radius.** They exist in
  `backend/`. Rebuilding them proves nothing about the claim under test.
- **Fine-tuning on mined workflows.** Measured negative transfer, 44.2% against
  55.8% zero-shot, and a taxonomy that did not survive a second domain.
- **Embeddings or model judgement for identity.** Same reason as the pipeline
  beside it: a key that answers differently on a second pass breeds a candidate
  that can never pair, and the failure is silent.
- **Gating which gestures are read.** The standard advice for per-event model
  calls is to filter first. Declined on purpose; the cost is named in the
  architecture document.
- **On-device inference and text-only abstractions**, the strongest available
  answer to the data boundary. Worth building the day this leaves a demo tenant.
- **A patent read.** UiPath holds US12469272B2, granted 2025-11-11, covering
  recorder-captured screenshots and interaction data training a generative model
  to recognise applications, screens and UI elements for workflow discovery.
  Somebody who reads patents should read it before any of this ships to a
  customer. That is not an engineering task and it is not in this plan.
