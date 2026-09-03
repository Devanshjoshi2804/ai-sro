# The model-first agent architecture

A second architecture for turning a day of somebody's browsing into work the
system can do. It runs beside the one in
[`docs/17-agent-architecture.md`](../17-agent-architecture.md), shares its
extension and nothing else, and exists to test one claim:

> **A model reading everything beats arithmetic reading call shapes, when the
> job spans two systems.**

The current pipeline is deliberate about the opposite — evidence decides
identity, a model only writes the sentence. That rule bought something real and
this document does not throw it away. It moves it: identity stays deterministic
and stays exact-set equality, but the set is no longer the ordered call shape.
It is the evidence a model cited.

Everything here is a design. Nothing in it is built yet.

This file is the argument and the evidence.
[`algorithms.md`](algorithms.md) beside it is the mechanics — fifteen algorithms
written to be implemented, each naming the paper it came from or admitting it
has none. The spec is
[`docs/superpowers/specs/2026-09-03-model-first-workflow-mining-design.md`](../superpowers/specs/2026-09-03-model-first-workflow-mining-design.md).

---

## The whiteboard

```
   U1 ─▶ 43g ───────────────▶ F₁ ═══▶ intents
         │                     ▲
         │  each gesture       │
         └──────────────────────
   Flash                            ┌── I_i ──┐
     │                              │         │
     ▼                              ▼         │
   U2  (57g)                    F_ii          │
     │                              │         │
     ▼                              ▼         │
   U3  (20g) ──────────────▶  Pro ◀──── 27 ───┘
                                │
                          25 ─▶ 3 archived
                                │
                                ▼
                          W ◀── proven workflow
```

Read left to right: one operator's day is forty-three gestures. Every gesture
goes through a fast model on its own and comes back with an intent. A second
operator's day is fifty-seven, a third's twenty. All of it — the gestures, their
intents, everything captured underneath — goes to a large model in one pass,
which reads twenty-seven intents, keeps what it can prove, and archives the
rest. What comes out is a workflow.

The arrows that fall from U1 down to U2 and U3 are the part that is easy to miss
and is the whole point: **an intent nobody could place in one operator's stream
is not thrown away.** It waits, and it is read again next to somebody else's
evidence. A supplier created in Blue Yonder by one person and the status change
done in SAP by another are one job, and only a pass that can see both at once
will ever say so.

---

## Why the pipeline we have cannot do this

Not a criticism of it. It was built to be unable to, on purpose, and three of
those decisions are exactly what a cross-system job runs into.

| Where | What it does | What that costs here |
|---|---|---|
| `observation/segment.py` | partitions the day **by host** before anything else | a two-system job is two candidates, structurally, forever |
| `observation/mine.py` | key is `(principal_id, signature)`, compared for **exact equality** | one extra page, one redesigned form, one additional `GET` in the shape — a second candidate that can never pair with the first |
| `_variants()` / `_workflows()` | overlap ≥ 0.60 · same host · adjacent within 5 min · at least twice | five constants, tuned once, on one WMS |
| the pre-filter's ceiling | `MOST_PAIRS = 20` per sweep | a model bill that does not scale with open tabs, bought by never letting the model see most of the day |
| the mining threshold | three doings of the same shape | a job done twice, or done once by each of two people, is invisible |

The published literature says the same thing from the outside. Robotic Process
Mining (Leno et al., ICPM 2020 — the reference deterministic pipeline, and open
source) states its own hard problem plainly: raw UI logs arrive as **one
undifferentiated event stream with no case identifiers**, so segmenting it into
per-task episodes is the unsolved core of the field. Our `segment.py` is one
answer to that question, and it is a good one, and it is still a set of constants
that decide where a task begins.

There is measurement on how badly such constants travel. A change-point
segmentation threshold tuned on its source domain scored **F1 0.538** there,
**0.119** when moved to a different environment, and **0.851** when re-tuned on
the target by an oracle. The threshold was not wrong. It was local.

---

## What the evidence says about the bet

Research was run for this design and stopped partway: twenty-three sources
fetched and claims extracted, six adversarial verification votes completed. The
verified six are the Microsoft Copilot scope claims and the UiPath patent. The
rest are extracted from primary sources but not independently re-checked, and are
marked where they carry weight.

### Nobody ships this yet. One vendor has patented it.

- **Microsoft Power Automate Process Mining Copilot** (verified, high
  confidence, three votes, against
  `learn.microsoft.com/en-us/power-automate/faqs-copilot-in-process-mining`):
  the LLM is a natural-language layer *on top of* conventional process mining —
  schema automapping at ingestion, insight surfacing, Q&A over already-structured
  event logs from a data lake. It never reads raw gestures, screenshots or
  accessibility trees. The mining itself is deterministic. Hallucination is
  mitigated by an in-product warning that outputs must be validated by a human.
- **UiPath, 2023**: roughly seventy proprietary specialised models for screen
  understanding, task mining and document processing. Generative models were used
  to suggest labels, not to induce workflows. A hybrid, not a model-first design.
- **UiPath patent US12469272B2** (verified against Google Patents; filed
  2023-07-20, **granted 2025-11-11**): per-user recorder processes capture
  screenshots and video frames plus button clicks, mouse movement, entered text,
  window lifecycle events, browser history and running applications; a server
  trains a generative model to recognise applications, screens and UI elements,
  and only then trains on individual user interactions with those elements. It is
  framed as AI-driven workflow aggregation and pattern discovery scored for
  automation potential, with listeners tracking multiple applications at once.

  That is this document, filed two years ago and granted ten months ago. Two
  things follow. The direction is not eccentric — the largest vendor in task
  mining has staked it. And before anything here ships to a customer, somebody
  who reads patents should read that one.

### Direct measurement in favour

- Zero-shot reconstruction of user task descriptions from raw browser interaction
  logs reached **0.911 average cosine similarity** to ground truth across
  **2,022 tasks** — model-first induction from UI event streams, without any
  exact-signature engineering (WorkflowView, 2026).
- The same work reports that deterministic and deep-learning clustering of UI
  actions into activities is **noise-sensitive and fails to generalise across
  applications**, which is the failure our signature equality has already shown.
- A small model matches a frontier one at this job: **Phi-4 (14B) at MRR 0.89 /
  Recall@1 0.85** on per-sequence activity inference. Per-gesture work does not
  need the expensive model.
- The two-tier shape is already validated elsewhere: one model call per low-level
  event for abstraction, one batched call per day for integration, explicitly to
  manage token limits, reaching **~90% average accuracy** abstracting raw
  multi-sensor events into activity labels (2024).
- Grounding is what makes generated workflows trustworthy. Free-generated
  workflow JSON hallucinated **up to 21% of steps**; forced to select from
  retrieved, real components, that fell to **under 7.5% at every model size, and
  1.9% at 7B** (NAACL 2024). An order of magnitude, for one architectural
  decision.

### Direct measurement against, and what each one changed

Each of these altered the design rather than merely worrying it.

**Models are not stable across passes.** Measured nondeterminism at temperature
zero: **43% (gpt-4o), 10.6% (claude-3.5), 50.4% (gemini-1.5)**. Across nine
meaning-preserving prompt variants, only **9 of 2,070** model-scenario pairs were
perfectly stable. And a model asked to re-judge its own earlier verdict disagrees
with itself at **~90%**.

→ So the large model never decides whether a workflow it is proposing is the same
as one it proposed before. It may have an opinion; the verdict is set overlap on
cited gesture identifiers. See *Identity*, below.

**Long contexts are read unevenly.** Citation generation shows strong primacy
bias — in one benchmark **81.8% of citations landed on the first two of five
context documents**. Fine-grained attribution is much weaker than document-level
attribution (**evidence-span F1 5.56–75.07** against **document-level F1
38.91–93.74**). Models also omit citations entirely when the output shape lets
them.

→ So citation is mandatory and validated, and the pass is measured for *coverage
across its window*, not only for whether the identifiers it cited exist.

**Batching degrades the per-item answer.** Semantic interference, position bias
and diluted attention; accuracy decays roughly exponentially in batch size
(`A(T) = A_max · e^(−β(T−1))`) while throughput saturates (`y(T) = T/(aT+b)`).

→ So per-gesture calls stay one gesture per call. Bundling them to save money
costs accuracy, and the money it saves is small.

**Abstraction loses events.** Against **17,165 ground-truth events**, a
model-generated log held **15,420**, of which **12,741 were correct — about 74%
of ground truth**, at an edit-distance alignment of 0.83. Reported failure modes:
faulty chain-of-thought, spurious aggregation of repeated events into self-loops,
and worst performance on the do-nothing class.

→ So carryover is not an elegance. At roughly three-quarters recall, a quarter of
every window needs a second reading, in different company.

**Adding a model does not automatically win.** In one 2026 study a trivial
frequency baseline beat an LLM at next-skill prediction (**34.9% vs 20.5%**);
fine-tuning on mined skills produced negative transfer (**44.2% vs 55.8%
zero-shot**); and the mined skill taxonomy did not generalise past its source
data. Order-invariant representations specifically degraded cross-application
reconstruction.

→ So: keep the deterministic pipeline as the comparison arm rather than assuming
this replaces it, never fine-tune on our own mined workflows, and keep temporal
order in every representation we build.

### A second pass, on two narrow questions

A follow-up run asked only two things the first had left thin: what actually
reduces citation primacy bias in a long window, and how anyone else stitches two
applications into one workflow. Ninety claims from twenty-three primary sources,
seventy-five adversarial verification votes. The aggregation stage of that run
malfunctioned and its summary is discarded; what follows is read from the votes
themselves, and several claims were corrected by their verifiers rather than
killed.

**Position bias is not the reliable thing I assumed.** A SIGIR 2026
reproduction study (*Lost in the Evidence?*, arXiv 2605.27105) **failed to
reproduce the U-shaped "lost in the middle" curve at all**, finding flat
performance across positions in its setup. A multilingual study (*Beyond
Early-Token Bias*, arXiv 2505.16134) found position bias is **model-specific and
language-specific** — Qwen2.5-7B, DeepSeek-7B and Mistral-7B favour *late*
context, not early — with roughly ten percentage points between the best and
worst position, and far larger effects in some languages (Hindi ~15.6%, English
~4.3%).

Two consequences. The coverage check stays, but it must measure skew **in
whichever direction it appears** rather than looking for a primacy bias we
assumed. And whatever this family of models does on this evidence is a thing to
measure, not to read off a paper.

**A cheap mitigation that backfires.** The same study tested explicitly marking
which context is most relevant — *"the most relevant context to the query is
marked as 1"* — and it **reduced accuracy in all five languages tested**. It also
found that accuracy drops most when the evidence sits mid-context and **output
entropy does not rise**: the model stays confident while using the wrong span.
So a confidence signal will not catch this, and helpful hints about what matters
are not free.

**Ordering does move the number, and multi-hop is where it moves.** Testing
three prompt orderings on long-context grounded QA (arXiv 2502.12462), accuracy
on a two-supporting-fact task at 64K tokens ranged **0.28 to 0.44 by ordering
alone**, with question-first strongest at long context. The reproduction study
found single-hop QA largely order-stable while multi-hop is order-sensitive, with
salient-evidence-last increasingly winning as context grows. Reading a workflow
out of a window is multi-hop by construction — the steps are scattered — so this
is our case, not the stable one.

**Citation before reasoning, not after.** *Long-Context LLMs Meet RAG* (arXiv
2410.05983, ICLR 2025) found that an explicit intermediate step identifying
relevant passages *before* answering beats answering implicitly. The same paper
found RAG quality is **non-monotonic in retrieved passages** — it improves, then
declines as hard negatives accumulate — and offers a training-free reordering
that puts the highest-scoring evidence at the start *and* end, with the weakest
in the middle. Its gains are negligible on small sets and significant on large
ones, which is exactly the regime a full window is in.

**What does not transfer.** LongCite's coarse-to-fine pipeline (arXiv 2409.02897)
is a **training-data construction method, not an inference-time technique** — the
verifiers killed that framing specifically, and its 72.0 citation F1 against
GPT-4o's 65.6 comes from fine-tuning, which we are not doing. ALR² (arXiv
2410.03227) likewise needs supervised fine-tuning of a 35B model for its +8.4 EM;
its useful warning is that *naive* prompting to retrieve supporting facts first,
without that training, produces very high ungrounded-citation rates.

**Self-consistency voting defaults to off, and is measured rather than
believed.** Sampling many answers and taking the plurality gave **0.4%
improvement from one sample to twenty on HotpotQA at roughly twenty times the
token cost** (arXiv 2511.00751); best case anywhere was 1.6% at ~15x. In
automated scoring, going from one sample to seven produced **no statistically
significant gain** (arXiv 2604.26954).

The evidence needs reading carefully rather than quoting, because two of these
results do not transfer the same way.

*When Self-Consistency Backfires* (arXiv 2608.11403) found majority voting
**hurts** accuracy on 56.6% of problems for Qwen2.5-7B and 65.7% for
Llama-3-8B, worst case losing 47 points. Those are 7–8B open models. **Nothing
in that paper says the same happens to a frontier model**, and it should not be
quoted as though it does.

The diminishing-returns result is the one that does bear on us, and it bears in
a direction worth stating plainly: its whole thesis is that voting helps **less
as models get stronger**, and its headline measurement was taken on
Gemini-2.5-Flash-Lite — a weak model, where voting had the most room to help,
and gained 0.4%. Moving to a stronger model moves *along* that trend, not
against it. So "our models are newer" is an argument for expecting less from
voting, not more.

That is still an argument from somebody else's benchmark, on somebody else's
task. **Sample count is therefore a knob on the umbrella pass, defaulting to 1,
and verification measures it on our own windows** — do repeated passes over one
window propose the same workflows, and does a plurality over three passes beat a
single pass at three times the price? If it does, we turn it up. Two published
papers are a reason to set a default, not a reason to skip an experiment that
costs one afternoon.

What the same studies point at as the better lever: **temperature sampling
itself helped** even where ensembling did not, and **reasoning effort has a
significant positive linear relationship with accuracy**. Reasoning effort is
the first knob to turn, before sample count.

One thing that does not need settling either way: identity was already moved off
model judgement entirely, so none of this touches whether two workflows are the
same job.

**Cross-system stitching has a quantified non-model baseline.** Cross-organisational
process mining that reconstructs one process model from logs with independently
managed, non-uniform ID systems — no shared case ID, our exact problem — reports
**over 98.4% precision and over 94.2% recall on BPIC 2012 and 2017**, by
detecting activity connections between adjacent event pairs and expanding
iteratively, relying on **shared data items across the separate logs**. Not a
model anywhere in it.

That is a direct argument for a signal this design was not using: **a value
typed into one system and appearing in a call to another is a stitch, and it is
arithmetic.** `Intent.values_seen` already captures it. Added below.

EC-SA-Data (arXiv 2206.10009) solves the same correlation problem by
probabilistic optimisation over three objectives — model conformance, data
attribute constraints, and minimised variance of activity durations — but needs
a pre-specified process model and explicit constraints as input, which is the
thing we do not have and are trying to derive. GUI-ReWalk composes multi-app
trajectories as "strides" joined when a model infers a semantically related goal
for the next application, and labels the whole thing **retrospectively** from the
full sequence — the umbrella pass, arrived at independently.

**Two failure modes worth naming.** Multi-application agent tasks fail far more
than length-matched single-application ones, so context switching is itself the
bottleneck; and a documented cross-app failure is **losing window focus during a
hand-off, so data meant for the second application is typed back into the
first**. Our per-step `origin` exists for other reasons and defends against
exactly that.

**Verify against state, not against a picture.** A propose-then-verify evaluator
(IRA) that grounds completion judgements in environment state — configs, files,
settings — rather than a model's reading of a screenshot scored **86.9% against
78.8%**, with human agreement on its verdicts at **94.0% (κ 0.84)**. Its
taxonomy is the useful part: evidence is visible-state, hidden-state, or
artifact, and **artifact verification was the largest category, 192 of 321
tasks** — most real task completions leave their proof somewhere other than the
visible screen. The runner's verification changes accordingly.

**A caution about asking people.** In a click-stream segmentation study, four
domain experts who work on the product daily estimated the median time to
complete a booking at 420, 120, 120 and 180 seconds. The measured value was
**66 seconds**. Evidence over interview, including when the interview is with the
person whose job it is.

### Cost, at current prices

| | input | output |
|---|---|---|
| **Gemini 3.8 Flash** (introductory, to 2026-12-31) | $0.75 / 1M | $3.75 / 1M |
| Gemini 3 Flash | $0.50 / 1M | $3 / 1M |
| Gemini 3.1 Pro, ≤ 200K prompt | $2 / 1M | $12 / 1M |
| Gemini 3.1 Pro, > 200K prompt | **$4 / 1M** | **$18 / 1M** |
| Batch API | 50% off | 50% off |
| Flash-Lite (image and video input) | $0.25 / 1M | $1.50 / 1M |
| Context caching | $0.20 / 1M read | + $4.50 / 1M per hour stored |

**Which model does which job is configuration, not architecture.** Gemini 3.8
Flash is described as the strongest workhorse for long-horizon planning and
agentic work, which is exactly the runner's step-planner and arguably the
umbrella pass too — at $0.75 against Pro's $2 per million input, a 150K-token
window pass costs a third as much. Whether it is good enough at reading a whole
day's evidence is a question our own windows answer, so the umbrella model is a
setting and the first verification run compares them on identical input. Do not
assume the expensive model is required; do not assume the cheap one suffices.

(The Cyber variant is irrelevant here — it is a restricted-access model for
vulnerability finding and patching, not for reading telemetry.)

Per-event inference runs roughly 500 ms to several seconds, which is a real
throughput ceiling; the standard advice is to gate events before calling a model
at all. This design declines that advice deliberately — every gesture is read —
and the cost is named rather than discovered.

The **200K boundary is the one number that changes a decision**: crossing it
doubles the input price. So the umbrella window is bounded by tokens, not by a
gesture count, and what does not fit waits in the pool.

### The data boundary

Sending live WMS payloads and screenshots to a hosted model is the part of this
that is somebody's compliance problem, not just an engineering choice.

- Zero data retention on the Gemini Developer API applies to **paid tiers only**;
  on paid, prompts and responses are not used to improve the provider's products.
- **Enabling Search grounding breaks it**: prompts, context and output are stored
  for thirty days with no opt-out. This system must never turn grounding on.
- Explicit context caching stores content for its TTL and must be avoided where
  retention is absolute; implicit caching (48-hour, project-isolated) is stated
  not to violate it.
- Files uploaded through the File API — screenshots — **persist until deleted by
  the caller**. Deleting them is our job.

For comparison, UiPath's shipped practice: application allowlisting at the
recorder, PII masking *server-side after upload* via Azure Cognitive Services,
encryption in transit and at rest, region-pinned storage, thirty-day soft delete,
credit-card data forbidden outright, and the consent burden placed on the
customer. Our existing rule — credential values never reach storage at all,
matched by field name — is stricter than that, and now protects the model
boundary as well as the evidence plane.

The alternative worth remembering for later: on-device inference, with only
privacy-compliant textual abstractions leaving the machine.

---

## 1 · The shape of the system

One process, three loops, one store. It lives in `new_agent_arch/` as its own
`uv` project with a path dependency on `backend/`, and it reuses what would
otherwise be rebuilt — the extension wire schemas, the Gemini client, blob
storage, config loading — while importing none of `observation/`, `induction/`,
`domain/skill/` or Temporal. Those are the things under test. The dependency
points one way only; the backend's import-linter contracts are untouched.

```
  operator Chrome × N  (each one a stream)
    extension ──── capture NDJSON ────▶ ┌──────────────────────────────────┐
              ◀─── driver commands ──── │  rig service, one process         │
                                        │                                  │
                                        │  INGEST                          │
                                        │    store the batch verbatim      │
                                        │    every gesture → Flash → Intent│
                                        │                                  │
                                        │  MINER, per tenant               │
                                        │    when the window is full:      │
                                        │      window + carryover + known  │
                                        │      workflows + knowledge base  │
                                        │        → Pro → ProvenWorkflow[]  │
                                        │      three checks on the answer  │
                                        │      unclaimed intents → pool    │
                                        │                                  │
                                        │  RUNNER                          │
                                        │    chat or form → values         │
                                        │    per step: look, plan, perform,│
                                        │      verify                      │
                                        └───────────────┬──────────────────┘
                                                        │
                                          one page: streams · intents ·
                                          workflows with their evidence ·
                                          chat and form · the live run
```

Four records. Everything else is derived and can be thrown away.

| Record | Holds | Written by |
|---|---|---|
| `Gesture` | the evidence, verbatim: gesture, correlated requests, page events, screenshot and AX references, `stream_id`, tenant | ingest |
| `Intent` | one model's reading of one gesture, stored **beside** it and never replacing it | ingest |
| `ProvenWorkflow` | narrative, systems, ordered steps each citing gesture identifiers, declared parameters | miner |
| `Run` | the values, and per step: the prompt, the command sent, what came back, both screenshots, the verdict | runner |

### The evidence unit

A `Gesture` is what `recorder.js` already emits, plus everything correlated to
it. Nothing is reshaped — the shapes are the ones
[`docs/14-extension-protocol.md`](../14-extension-protocol.md) froze.

```
Gesture
  id           ges_<32 hex>          ← what a proven step cites
  stream_id    device + principal
  at · url · tab_id · frame_url
  gesture      kind · target { role, name, text, testId, cssPath, xpath,
                               component { framework, xtype, itemId,
                                           fieldLabel, query, chain } }
               · value · secret · modifiers
  requests     [ full exchange: method, url, headers, request_body,
                 status, response_body, duration_ms ]
  page_events  [ navigated · loaded · dialog_opened · … ]
  ax_ref       blob, where we have one
  shot_ref     blob, from chrome.tabs.captureVisibleTab
```

### The accessibility-tree question

An accessibility tree needs `chrome.debugger`, and Chrome banners every tab it is
attached to for as long as it is attached. The protocol is explicit that passive
capture never takes it — that is ADR 008's whole shape.

So "the whole accessibility graph on every gesture" costs a permanent debugger
banner across every watched tab, all day. Three ways to live with that:

1. Permanent debugger attach. Full AX, permanent banner, an operator who is
   being told all day that something is debugging their browser.
2. **No AX during capture.** Lean on the ExtJS `component` chain `recorder.js`
   already extracts — `xtype`, `itemId`, `fieldLabel`, `query`, `chain`. On Blue
   Yonder this is close to as good as an AX tree and it is free.
3. Attach the debugger only while a run is executing, where the banner is honest
   about what is happening and lasts a minute.

**Chosen: 2 for capture, 3 for runs.** Revisit only if the component chain proves
thin on a system that is not ExtJS.

### The one deterministic rule

Everything in this architecture is the model's to decide — where a task begins,
what is one job, which values vary, what to call it — with a single exception:

> **A step must cite gesture identifiers, and those gestures must exist.**

That is not a heuristic and it is not pattern matching. It is referential
integrity, and it is the same instinct as `_believable()` in the existing
`understand.py`: a model may say anything it likes, and only what points at real
evidence survives. The measured payoff is an order of magnitude fewer
hallucinated steps.

---

## 2 · The two model calls, and the pool

### Call one — Flash, once per gesture

Fires the moment a gesture lands. Input is kept small on purpose, because
bundling per-item work into shared calls measurably degrades each item's answer.

```
in   this gesture: target fingerprint, value (unless it was a credential),
       url, tab
     its correlated requests — method, URL, status, bodies trimmed to keys
       and short values; the full bodies stay in the store, cited by id
     the page events around it
     the last eight intents on this stream, one line each   ← continuity, cheap
     the screenshot, only when the target fingerprint is thin

out  Intent {
       gesture_id
       act          "typed a client code"      — what the human did
       object       "supplier" · "address" · …
       system       the host, resolved to a named system
       page         where they were
       values_seen  [ { field, value } ]
       continues    gesture_id | null           — same doing as the one before?
       confidence
       why          one sentence
     }
```

At Gemini 3.8 Flash's introductory $0.75 per million input tokens and a trimmed
record of roughly 400–900 tokens, that is about **$0.0005 a gesture** — a
two-thousand-gesture day for around **a dollar**. Screenshots only where they are
needed is what keeps that true, and Flash-Lite at $0.25 is where per-gesture work
goes if the cheaper model reads a gesture as well, which is a thing to measure
rather than assume.

### Call two — Pro, once per window

The window is **not a fixed number of gestures**. It fills to roughly 150K tokens
and stops, because crossing 200K doubles the input price. Minimum twenty-five
gestures, so a quiet morning still gets read. This is the honest reading of "no
cap": no cap on *what kinds* of evidence go in, a cap on *tokens per pass*, and
the pool catches the overflow.

```
in   WINDOW     every gesture since the last pass, in order, each with its
                intent and its full requests — bodies inline until the budget
                is spent, then by reference the model can ask to open
     CARRYOVER  intents from earlier passes that no workflow claimed —
                tenant-wide, so one operator's leftovers sit beside another's
                evidence
     KNOWN      the proven workflows we already hold, with their cited
                gesture sets and the systems they touch
     KB         docs/13 Blue Yonder knowledge, the SAP notes, the system map

out  [ ProvenWorkflow {
         title · narrative
         systems     [ "blue-yonder", "sap" ]
         steps       [ { order, says, system, cites: [ ges_… ], parameters } ]
         parameters  [ { name, seen_values, where } ]
         same_as     workflow_id | null     ← an opinion, not the verdict
         unproven    [ ges_… ]              ← what it could not place
       } ]
```

### The three checks

The only code in the system that overrules a model, and none of it looks at a
URL.

**One — the identifiers exist.** A step citing a gesture that is not in the store
rejects the whole workflow, and the bad identifiers are logged. Citation is
mandatory: models omit citations wherever the output shape lets them, which
inflates apparent accuracy, so an uncited step is a rejected step.

**Two — coverage.** Which parts of the window were cited at all. Primacy bias in
long contexts is measured and large; a pass that only ever cites its first third
is telling us the window is too long, and the budget comes down. It is a cheap
instrument against a failure that is otherwise invisible.

**Three — identity, by overlap rather than by opinion.** This is two questions,
not one, and cited-gesture-ID overlap only answers the first.

*Is this a re-read of evidence already processed?* Gesture IDs are
per-occurrence, so two independent doings of the same job cite disjoint sets —
Jaccard 0 between them. Comparing raw cited-ID sets therefore only catches the
miner re-reading a window it has already read (a re-run after a crash, an
overlapping window boundary). It cannot say whether *today's* supplier job is
the *same job* as last Tuesday's — and that question is the one that makes a
repeated task worth automating at all. It is also exactly the question the
architecture this document replaces answers with `(principal_id, signature)`.
Removing the signature without replacing what it answered would be a hole, not
a simplification.

*Is this the same job as one seen before, on different evidence?* Answered by a
second, derived key — not the call shape, not an embedding, still arithmetic:

```
shape_key(workflow) =  [ (system, target_identity, action_kind)
                          for each cited gesture, in evidence order ]

target_identity, first that exists:
    component.itemId     "clientCode"                            ← ExtJS,
                                                                     stable
    component.query      "panel#clients textfield#clientCode"      across
    role|name             "textbox|Client Code"                     runs
    testId
```

Built from the same `recorder.js` fingerprints the runner already turns into
locators — nothing new is captured for it. It is UI-level, not network-level: the
same fields get touched every time a person does the job, so the key survives an
extra background `GET`, a redesigned endpoint, or one optional page in a way an
ordered call shape never could.

Compared by **containment**, not Jaccard: `|A ∩ B| / min(|A|, |B|)`. Jaccard
would call "create supplier" (3 steps) and "create supplier, then add an item,
then set status in SAP" (12 steps) two different jobs, because the smaller set
drowns in the union. Containment says the three-step job sits inside the
twelve-step one — true, and exactly the variant relation the panel should
surface, the way `TaughtTogether` already treats one skill taught from two
candidates of different shape.

```
occurrence identity   Jaccard on cited gesture IDs        "is this a re-read?"
job identity           containment on the shape key         "is this that job?"

    ≥ 0.5  → the same job, seen again
    < 0.5  → a new job
```

0.5 is the single tunable constant in the whole architecture. It earns its place
by being measurable: too high and a re-read of the same evidence mints a
duplicate, too low and two different jobs sharing one lookup step collapse into
one. Both failures are visible in a re-run over evidence already read, and in a
re-run with the gesture order shuffled — which is why both are verification
steps rather than assumptions.

The model's `same_as` is read and recorded, and it does not decide either
question. A model asked to re-judge its own earlier verdict disagrees with
itself at roughly 90%, which is exactly what `same_as` asks it to do.

Notice what survives from the architecture this replaces. Identity is still
deterministic, still exact arithmetic, still computed the same way on every
pass, still unable to answer differently on a second reading of the same
evidence — the property `docs/17` spends its argument defending, and the reason
mining can re-run without breeding duplicates. What changed is only what the key
is built from: not `(principal_id, ordered call shape)`, brittle to one extra
page, but a key derived from the evidence a model pointed at, which survives a
redesigned form and spans two hosts.

### A fourth signal: a value that crossed a system boundary

Cross-organisational process mining reconstructs one process from logs with no
shared case identifier at **over 98.4% precision and 94.2% recall**, and it does
it by linking on **shared data items across the separate logs**. That signal is
already sitting in our evidence and this design was not using it.

```
shared_values(A, B) = { v : v ∈ A.values_seen ∧ v appears in B's requests
                            or B.values_seen, and v is not trivial }
```

A supplier name typed into Blue Yonder that then appears in an SAP request body
is not a coincidence and it is not an opinion — it is arithmetic over evidence
we already store. It joins `shape_key` as a stitch signal: two candidate halves
that share a non-trivial typed value are far likelier to be one job, and the
umbrella pass is told so rather than being left to notice.

Trivial values are excluded by length and by how often they appear across the
tenant's evidence — a facility code every call carries links nothing, a supplier
name typed twice in four minutes links a great deal. That exclusion is a
frequency count, not a pattern.

### How the window is put to the model

Ordering is not cosmetic here. On a two-supporting-fact task at 64K tokens,
accuracy ranged **0.28 to 0.44 by prompt ordering alone**, and multi-hop tasks
— which is what reading a workflow out of a window is — are the order-sensitive
kind. So the arrangement is a decision, and it is one to re-measure rather than
settle once:

- **The task first, and again at the end.** Question-first ordering was
  strongest at long context, and restating the constraints after the evidence
  costs almost nothing.
- **Citations before narrative** in the output. An explicit step that identifies
  the relevant evidence *before* composing the answer measurably beats composing
  first. The output schema orders `cites` ahead of `says` for that reason, not
  for tidiness.
- **Strongest evidence at both ends, weakest in the middle.** The training-free
  reordering from *Long-Context LLMs Meet RAG*, whose gains appear specifically
  once the evidence set is large. For us "strongest" is the carryover pool and
  the gestures with high-confidence intents.
- **No hints about what matters.** Explicitly marking the most relevant context
  was measured to *reduce* accuracy in all five languages tested. We do not tell
  the model which gesture we think is important.
- **No multi-sample voting.** Plurality voting over repeated samples gained
  **0.4% at twenty times the cost**, and *hurt* accuracy on the majority of
  individual problems in one study — 56.6% and 65.7% for two models — with the
  damage hidden by the aggregate. The lever instead is **reasoning effort on the
  umbrella pass**, which does show a significant positive relationship with
  accuracy.

### The pool

```
pass N      window (everything new) + pool
                │
                ▼  Pro
            proven workflows ──▶ their cited gestures leave the pool
            unproven         ──▶ enter the pool at age 0

pass N+1    the pool ages by one. Past age 6, or seven days,
            an entry retires — kept in the store, out of the prompt.
```

The pool is **tenant-wide, not per stream**. That is what makes the whiteboard's
downward arrows real: a supplier created in Blue Yonder by one operator and a
status set in SAP by another are two halves in one pool, and a pass that sees
both can say they are one job.

It is also load-bearing rather than decorative. Model abstraction over raw event
streams was measured at roughly **74% recall**; a quarter of every window is
dropped or mislabelled on any given reading. Without a pool those gestures are
simply lost. With one they are read again, next to different neighbours.

### What this replaces, line by line

| Today | Here |
|---|---|
| host partition, 3-minute idle, 30-minute span | a window bounded by tokens; the model decides boundaries |
| `(principal_id, signature)`, exact equality | cited-gesture-set overlap, exact arithmetic |
| variants: overlap ≥ 0.60, same host | one pass reads both and says |
| workflows: different host, within 5 minutes, at least twice | native — a cross-system job is one workflow, not a pair |
| `MOST_PAIRS = 20` | the token budget for a pass |
| three doings of one shape | whatever the model can prove; a single occurrence is a workflow marked unproven |

---

## 3 · The runner

### Two doors, one room

**Chat.** *"create supplier TestYonder9 for NEWTEST23 and set it live in SAP."*
Flash reads the utterance against the workflows we hold and answers
`{ workflow_id, values, missing }`. Missing values come back as a question in the
same thread. Nothing performs until the operator presses start — saying it offers
the work, pressing it authorises the work.

**Form.** Every proven workflow declares its parameters with the values it has
seen. The rig renders them as fields, prefilled. This is the fallback when
extraction misreads, and it is the honest first demonstration.

### What a step knows before any model is asked

A step cites gestures. Those gestures carry `recorder.js` fingerprints. So the
locator list the protocol wants is **built from the cited evidence, with no model
involved**, in the protocol's own priority order:

```
the cited gesture's target ──▶ locators [
    component      "panel#clients textfield#clientCode"
    role_and_name  "textbox|Client Code"
    text           "Client Code"
    test_id        "client-code"
    css_path       "div.x-panel > input:nth-of-type(2)"
  ]
                   ──▶ origin  scheme + host of that gesture's own request
```

**`origin` is per step, read from the gesture that step cites.** In a job that
spans two systems, the first four steps carry the Blue Yonder origin and the
fifth carries SAP's, because that is what their evidence says. This is the same
rule `AGENTS.md` already states about credentials — a step's credentials come
from the system it is calling — reached from the other direction. A workflow that
spans two systems can never post one customer's live session into the other,
because no step can name a system its own evidence never touched.

`allow_focus` is true when the run came from chat or the form: the operator asked
for this and is watching. It is never set on anything the miner starts by itself.

### The loop

```
for each step:

    ui.url + screenshot(inline)      where are we, what is on the screen,
            │                        and the text digest that came with it
            ▼
    FLASH plans exactly one command
      given: the step's sentence, its cited evidence, the built locators,
             the screenshot, the current URL
            │
            ├── ui.perform     locators from evidence; action and value
            ├── http.send      the cited exchange, parameters substituted
            └── navigate       when the page is wrong for this step
            ▼
    the extension performs, and answers
      { performed, matched_by, candidates }
            ▼
    verify against STATE, not against a picture:
      the response body the command itself returned
      + a read the cited evidence shows the page makes
      + the screenshot, last and least
            │
        held ──▶ the next step
            │
     failed or unclear
            ▼
    PRO retries once, given the failure, both screenshots, the full cited
    evidence and the workflow so far
            │
     still failed ──▶ stop, say what it saw, ask the operator
```

**Why verification does not trust the screenshot.** A propose-then-verify
evaluator grounded in environment state rather than a model reading a picture
scored **86.9% against 78.8%**, with human agreement on its verdicts at 94.0%.
More to the point, it found most task completions leave their proof somewhere
other than the visible screen — **artifact verification was 192 of 321 tasks**,
the largest category by far. A supplier that was created is proved by the `201`
and the identifier in the response body, or by a read that returns it; the
screen showing a green toast is the weakest of the three and the easiest to be
wrong about. So the response body is read first, a confirming read second where
the cited evidence shows the page performs one, and the picture is what remains
when neither exists.

Flash plans; Pro rescues. A clean step never touches the expensive model, and
only the steps that surprise us cost what surprises cost. The measurement behind
that split: small models match frontier models at this class of inference, so
paying Pro prices to click a field named *Client Code* buys nothing.

`matched_by` is recorded on every performed gesture, and it is a health signal
rather than a receipt. The protocol says it plainly: a step that only ever
matches on the last fallback is a step about to break. When `component` and
`role_and_name` both miss and `css_path` catches it, the run **succeeds and the
workflow is flagged stale** — the same instinct as a vision rung that finds a
button somewhere new, one rung lower down.

### The bounds

This drives a real browser signed into a real warehouse system. These are not the
place to be economical.

- **An origin allowlist per run** — the systems the workflow's own evidence names
  and nothing else. A planned command to any other host is refused by the rig
  before it reaches the extension.
- **Dry run by default, the first time a workflow executes.** Reads and
  navigations go out; anything that writes is shown in full and withheld. A
  person presses through to a live run. After one clean live run, the workflow
  may start live.
- **A stop button**, which sends `abort`, checked between every step.
- **A step budget** — the workflow's step count plus a little slack, then stop. A
  model looping on a form is money spent and a warehouse confused.
- **Every exchange stored**: the prompt, the chosen command, the extension's
  answer, both screenshots. *Why did it do that* has a file.

### What a run leaves behind

```
Run
  workflow_id · values · started_by (the utterance, or the form) · live | dry
  steps [ RunStep {
      order · says
      planned_by   flash | pro
      command      the exact envelope sent
      result       performed · matched_by · candidates | status and body | error
      before/after screenshot references and their text digests
      verdict      held | failed | unclear, and the model's sentence
  } ]
  outcome · and, for a dry run, the write it produced and withheld
```

---

## What is deliberately not built

- **No promotion ladder, no circuit breaker, no blast radius.** They exist and
  work in `backend/`, and rebuilding them proves nothing about the claim being
  tested. Their substitute here is the dry-run default, the origin allowlist, and
  a person watching. **If anything from this architecture is ever to run
  unattended, it goes through the real governance first.** That boundary stays
  sharp.
- **No fine-tuning on mined workflows.** Measured negative transfer: 44.2%
  against 55.8% zero-shot, and a taxonomy that did not survive contact with a
  second domain.
- **No embeddings for identity.** Same reason as the pipeline it sits beside: a
  key that answers differently on a second pass makes a second candidate that can
  never pair, and the failure is silent.
- **No gating of which gestures get read.** The standard advice for per-event
  model calls is to filter first. This design refuses it on purpose, and pays.

---

## Reading it back

Everything above leaves something a person can open.

| Question | Where the answer is |
|---|---|
| Why was this offered? | the workflow's cited gestures, and the evidence under each |
| What did the model think this gesture was? | the `Intent` stored beside it, with its one sentence |
| Why is this the same workflow as that one? | the overlap between their cited sets |
| Why is this a parameter? | the values seen at that site, across occurrences |
| What did it send? | the run's step, with the exact command envelope |
| What would it have sent? | a dry run's withheld write, in full |
| Why did the step fail? | both screenshots, the model's verdict, and `matched_by` |
| Is this workflow going stale? | which locator has been winning lately |
