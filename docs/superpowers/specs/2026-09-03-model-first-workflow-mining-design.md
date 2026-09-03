# Model-first workflow mining

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
| How it executes | **The model plans, the extension performs.** The frozen `docs/14` command channel, in the operator's own Chrome. Not server-side computer use, not parameter substitution into recorded calls. |
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
3. **Identity by overlap.** Jaccard overlap between this workflow's cited gesture
   set and each known workflow's. **At or above 0.5 is the same workflow seen
   again; below it is a new one.** Exact arithmetic, identical on every pass, so
   re-running the miner over evidence it has already read cannot breed
   duplicates. The threshold is the one tunable constant in the system and
   verification step 2 is what measures it — a value that resolves a re-read to
   the workflow already held, and does not collapse two genuinely different jobs
   that share a lookup.

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
with `performed`, `matched_by` and `candidates`; a second screenshot; Flash
verifies. On failure or an unclear verdict, Pro retries once with both
screenshots, the failure, the full cited evidence and the workflow so far. Still
failed: stop and ask.

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
2. **Identity is stable across passes.** Re-run the miner over evidence it has
   already read. No new workflow appears; overlap resolves each proposal to the
   one already held. Repeat with the window's gesture order shuffled.
3. **Coverage is honest.** A pass over a deliberately over-long window reports
   citations concentrated in its opening, and the budget reduces in response.
4. **Citations are enforced.** A hand-edited model response citing a fabricated
   `ges_…` is rejected, and the rejection names the identifier.
5. **Carryover works across streams.** One operator does the Blue Yonder half,
   another does the SAP half within the pool's lifetime. A pass proposes the
   joined workflow.
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
