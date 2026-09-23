# Agent architecture

> **Superseded on 2026-09-07.** The mining half of this document (segment,
> cluster, the signature, the miner) is replaced by
> `docs/new-agent-doc-arc/README.md` and is being ported per
> `docs/superpowers/specs/2026-09-07-the-rig-into-the-backend-design.md`.
> The code as it stood is on the branch `backup/rule-based-mining`.
>
> **`new_agent_arch/` was deleted on 2026-09-14**, the last item on that
> spec's deletion list, once the shared-day measurement in
> `docs/new-agent-doc-arc/two-miners-one-day.md` was met. Everything it held
> is on the branch **`backup/the-rig`** — including the model bake-off
> harness (`scripts/bakeoff.py`, `compare.py`, `rotate.py`), which was never
> ported and has no equivalent in the backend. Recover it from there rather
> than rebuilding it.
>
> Documents under `docs/new-agent-doc-arc/` cite `new_agent_arch/...` paths
> throughout. Those citations are left as they were written: they are the
> record of what was measured and where, and rewriting them to point at
> files that no longer exist in this tree would make the record less true,
> not more.

How a task somebody did three times becomes a skill, and which agent owns each
step. Worked through one case: **create a supplier**, whose calls are a `PUT` to
an address and a `POST` to a supplier.

The rule the whole shape rests on: **evidence decides identity, a model writes
the sentence.** Every stage below is deterministic unless marked **M**, and
every **M** output is stored beside the derived fact it did not replace.

---

## The pipeline

```
                     the operator's own Chrome
                                │
   ┌────────────────────────────┴────────────────────────────┐
   │  0  CAPTURE            extension, passive                │
   │     gestures · calls · page events · screenshots          │
   └────────────────────────────┬────────────────────────────┘
                                │  batches of NDJSON
                                ▼
   ┌─────────────────────────────────────────────────────────┐
   │  1  ADMIT              observation/ingest.py             │
   │     stored verbatim; nothing is interpreted yet           │
   └────────────────────────────┬────────────────────────────┘
                                ▼
   ┌─────────────────────────────────────────────────────────┐
   │  2  SEGMENT            observation/segment.py            │
   │     a day → episodes. **Each host on its own stream**,    │
   │     partitioned first; then each stream is cut by a       │
   │     pause > 3 min (IDLE) or a span > 30 min (LONGEST).    │
   │     Kept only if it has one non-background call AND one   │
   │     gesture — reading a screen is not a task.             │
   │                                                          │
   │     Switching tabs does NOT cut an episode. A run used    │
   │     to end on any host change, and in a day of real       │
   │     recording 30 of 37 boundaries were that and nothing   │
   │     else — a mail client polling in the background cut    │
   │     every warehouse task in half.                         │
   └────────────────────────────┬────────────────────────────┘
                                ▼
   ┌─────────────────────────────────────────────────────────┐
   │  3  CLUSTER            observation/mine.py               │
   │     key = (principal_id, signature), compared for exact   │
   │     equality. Never a model, never an embedding: mining   │
   │     re-runs over evidence it has already read, and a      │
   │     key that answers differently on a second pass makes   │
   │     a second candidate that can never pair.               │
   └────────────────────────────┬────────────────────────────┘
                                ▼
                        TaskCandidate ×3
```

### What the signature is

For our case the three doings collapse to one candidate because all three
produced the same ordered call shape:

```
PUT data/WM/wm/addresses/*  →  POST data/WM/wm/suppliers
```

`*` is the shape of the URL, not the id in it — `induction/diff.py` produces it,
and clustering and pairing must ask the same question about a URL or a task will
cluster one way and pair another. The `GET`s that filled the form are
background: they are in the evidence, they are not in the signature.

**Three doings of the same shape is the threshold** for the panel to offer it.
Two identical shapes and one different is two candidates, one of which is never
offered.

---

## Every model call, and what is done with its answer

Nine places in the whole system call a model. Each one is listed with what it is
handed, what it gives back, and — the column that matters — **who decides what
happens to that answer.**

| # | Agent | Port | In → out | The answer is |
|---|---|---|---|---|
| 1 | **Namer** | `WorkflowInterpreter.name_task` | candidate evidence → `TaskName` | **written to the candidate's title.** Blank ⇒ the derived title stands. Cosmetic by construction: what a candidate *is* stays its signature. |
| 2 | **Variant proposer** | `.judge_join("variant", …)` | two candidates → `Judgement{joined, because}` | **a question on screen.** `joined=false` or an empty `because` is dropped. A pair a person already answered is never asked again. |
| 3 | **Workflow proposer** | `.judge_join("workflow", …)` | two candidates → `Judgement` | same. Only a person knows "receive in the WMS, then record in the ERP" is one job. |
| 4 | **Reader** | `.read` (`induction/understand.py`) | one demonstration → `Reading{title, steps, parameters, caveat}` | **filtered, then stored as `Evidence.PROPOSED`.** See below. |
| 5 | **Describer** | `induction/describe.py` | evidence → `summary`, `when_to_use` | prose on the skill. Composed *from* evidence; changes no step. |
| 6 | **Intent** | `IntentParser` | utterance → `Reading{mode, verb, …}` + `Extraction` | **validated, never trusted.** Must resolve to an objective key that already exists and parameters the skill already declares. |
| 7 | **Vision executor** | `VisionDriver` (`vision_step.py`) | screenshot + step → a gesture | bounded: ≤5 gestures, only the step's own gesture kind plus scroll/hover, no writes without authorisation, every call recorded. |
| 8 | **Transcriber** | `Transcriber` | audio → timed segments | **narration labels, evidence decides.** Lands in `SkillStep.narration`, never `SkillStep.intent`. |
| 9 | **Embedder** | `Embedder` | text → vector | *ordering only.* A failure costs the caller its ordering and nothing else. |

### The check that keeps #4 honest

```
model proposes a parameter  ──▶  is its literal value present in the
                                 captured frames?
                                     │              │
                                    yes            no
                                     ▼              ▼
                          kept, marked        DISCARDED
                          Evidence.PROPOSED   silently
```

`_believable()` in `understand.py`: *"a model can name any parameter it likes,
and only the ones pointing at a literal in the evidence survive."* A value
already recovered from a typed box wins over the model's name for it — two names
for one value would put two placeholders at one site and the second would
quietly win.

### What no model is allowed to touch

```
the calls            captured, byte for byte, never rewritten
the signature        (principal_id, ordered call shape) — exact equality
the objective key    derived from evidence at seal
which values vary    the two-run diff, not an opinion
the promotion rung   a record of runs nobody can fake
```

A model that renamed a candidate changes the sentence on screen and nothing
about which episodes belong to it. That separation is the reason the whole thing
can be explained after an incident.

---

## The background miner: how tasks get clubbed

This is the part that decides *what is one task* and *what is one job made of
two tasks*. It runs on a sweep, over evidence it has already read, and the whole
design is arranged so that **Gemini never scans anything.**

```
                        all candidates for a tenant
                                    │
        ┌───────────────────────────┴───────────────────────────┐
        │  DETERMINISTIC PRE-FILTER — plain arithmetic, no model  │
        │                                                        │
        │  _variants()          same operator, same host,        │
        │                       signature overlap ≥ 0.60,        │
        │                       and not already identical        │
        │                                                        │
        │  _workflows()         same operator, DIFFERENT host,   │
        │                       one followed the other within    │
        │                       5 min, on ≥ 2 occasions          │
        │                                                        │
        │  _settled()           drop any pair a person already   │
        │                       answered                         │
        └───────────────────────────┬───────────────────────────┘
                                    │  at most 20 pairs per sweep
                                    ▼
        ┌───────────────────────────────────────────────────────┐
        │  GEMINI — judge_join(kind, first, second)              │
        │  → Judgement{ joined: bool, because: str }             │
        └───────────────────────────┬───────────────────────────┘
                                    │
                    joined=false ───┤─── because="" ──▶ dropped, silently
                                    │
                                 joined=true
                                    ▼
        ┌───────────────────────────────────────────────────────┐
        │  A SUGGESTION ON A CARD — "Same task" / "Different"    │
        │  A person answers. Nothing is merged until they do.    │
        └───────────────────────────────────────────────────────┘
```

The ceiling matters as much as the filter: `MOST_PAIRS = 20` is *"a ceiling
rather than a budget: the answer is a sentence on a screen, and nobody's model
bill should scale with how many tabs somebody had open."*

And if Gemini is not configured at all, `_join` still runs — it falls back to
what the evidence says in the plainest words there are. The model reads a pair
better than a rule does, which is why it is asked where it can be; the system
without it is the system, degraded, not the system, broken.

### The two kinds of clubbing

|  | **Variant** | **Workflow** |
|---|---|---|
| Question | are these two shapes the same task? | are these two tasks one job? |
| Why they are separate | one extra page changes the signature, and identity is exact equality | **an episode is one host's** — segmentation partitions by host, so a two-system job is two candidates and always will be |
| Pre-filter | signature overlap ≥ 0.6, same host | different host, adjacent within 5 min, ≥ 2 times |
| Example | "create supplier" with and without the address lookup | "check the WMS, **then** record it in the ERP" |
| Taught by | `TaughtTogether` — one skill, both candidates spent | `TeachWorkflow` (removed 2026-09-24) |
| Diffed how | the two candidates' doings, against each other | **never against each other** — that would compare the WMS half with the ERP half. Each *occurrence of both halves together* is one demonstration of the whole job |

That last row is the subtle one. For a workflow, the pair is not the evidence —
the pair is the *hypothesis*. The evidence is the times the operator did both
halves in sequence, and two of those are the pair induction actually wants.

### Why the miner cannot use a model for identity

```
key = (principal_id, signature)     compared for exact equality
```

Not a model, not an embedding, not a similarity threshold — because mining
**re-runs over evidence it has already read.** Anything that answers slightly
differently on a second pass produces a second candidate, a second skill, and a
pair that can never pair. That failure is silent, which is what makes it the one
worth designing against.

So the split is: **arithmetic decides identity, Gemini decides wording and
proposes relationships, a person decides what is true.**

---

## Teaching: candidate → skill

```
   TaskCandidate  ──teach──▶  Recording (sealed)  ──induce──▶  SkillVersion
                                     │                              │
                     the calls, kept as evidence          steps · parameters
                                                          network_plan · ui_plan
                                                          assertions
```

Two demonstrations of the same objective are what **prove** a parameter:
`induction/diff.py` aligns them and a field that differs is an input, a field
that matches is fixed. One demonstration is enough to produce a skill through
`UnderstandRecording`, but its parameters are marked **a model's reading**
rather than proven, and the screen says so.

For our supplier:

```
$supplier_name   "TestYonder2" / "TestYonder7"   varies  → input
$client_name     "NEWTEST19"   / "NEWTEST23"     varies  → input
$facility        "SG"          / "SG"            same    → fixed
```

The `PUT` becomes step 1 and the `POST` step 2, each with the request the
demonstration actually sent as its template, and the assertion the run will be
checked against.

---

## Running it: the decision at each hand-off

```
  "create a supplier from this mail"
              │
              ▼
  ┌───────────────────────┐   Reading{mode, verb} + Extraction{values, missing}
  │ INTENT      (model)   │──────────────┐
  └───────────────────────┘              │  decision: does this resolve to a key
              │                          │  we already have?
              ▼                          ▼
  ┌───────────────────────┐        no ──▶ a question back to the operator.
  │ RESOLVER    (no model)│               Never an improvised call.
  └───────────┬───────────┘
              │  Resolution{skill, version, stage, missing, matched}
              │  ── stored beside the prose, so "why did it pick that"
              │     is answerable later
              ▼
      ┌───────────────┐
      │ missing != [] │──▶ ask for those fields. Saying something
      └───────┬───────┘    performs nothing: the skill is *offered*,
              │            and starting it is the operator's next act —
              │            which is what makes their confirmation the
              │            authorisation an assisted run records.
              ▼
  ┌───────────────────────┐
  │ SAFETY      (no model)│  breaker open? blast radius? stage allows a write?
  └───────────┬───────────┘  refused here, before anything is sent
              ▼
  ┌───────────────────────┐
  │ EXECUTOR              │  L1 network_plan ─ no model
  │                       │  L2 ui_plan + AX ─ no model
  │                       │  L3 vision       ─ model, bounded
  └───────────┬───────────┘
              ▼
  ┌───────────────────────┐  did the post-condition hold?
  │ VERIFIER              │  did the WMS actually change?
  └───────────┬───────────┘
              │
      ┌───────┴────────┐
     held            failed
      │                │
      ▼                ▼
   next step   ┌──────────────┐
               │ ESCALATOR    │  policy as data, not a model:
               └──────┬───────┘  next rung, or stop
                      ▼
              a rung that succeeded *because vision found the button
              somewhere new* succeeds AND reports the recipe is stale.
              It resets the streak rather than advancing it.
```

| Agent | Job | Model | Decides |
|---|---|---|---|
| **Intent** | utterance → objective key + parameters | Gemini Flash, structured output | nothing — proposes, and is validated |
| **Resolver** | objective → version, stage, what is missing | none | which skill, from stored facts |
| **Executor** | one step at the highest rung that works | none for L1/L2 | what to send, from the plan |
| **Vision executor** | L3 only | Gemini computer use | one gesture, inside hard bounds |
| **Verifier** | did it hold; did the WMS change | none, plus a model for ambiguity | clean / degraded / failed |
| **Escalator** | rung failed → next rung, or stop | policy as data | escalate or stop |

**A Temporal workflow never calls a model.** Every LLM call is an activity. A
workflow is replayed after a restart, and a model that answers differently on
replay produces a different history — which destroys the audit trail, the one
thing an enterprise cannot lose here.

---

## The rungs, and who chooses

```
L1  network replay   network_plan            milliseconds   total determinism
L2  UI replay        ui_plan + AX graph      seconds        high
L3  vision           Gemini computer use     tens of secs   none
```

The **task** is the unit that changes rung, not the step: swapping mid-run
leaves the browser without the screen state the earlier steps produced.

Verification is the control, not a component — every rung is checked the same
way, so a step that vision found somewhere new *succeeds* **and** reports that
the recipe is stale.

---

## What refuses what

```
recorded ──▶ shadow ──▶ assisted ──▶ autonomous
             writes     writes go     no human
             withheld   out, named    in the loop
```

- `SkillVersion.promote` refuses the last rung until the version is checkable
  and has **10 consecutive clean runs**; **3 consecutive failures** demote it,
  and no human is needed for that.
- A **circuit breaker** stops a run before it starts, on the system's recent
  behaviour rather than on what is being asked.
- **Blast radius** bounds writes per hour and items per request.
- A run that never reached the system is none of those failures.

---

## Reading it back

Everything above leaves something a person can open:

| Question | Where the answer is |
|---|---|
| Why was this offered? | the candidate's episodes, and the signature |
| Why is this a parameter? | the two doings, side by side |
| Why did it pick that skill? | the stored `Resolution` beside the reply |
| What did it send? | the run's steps, with `matched_by` per gesture |
| What would it have sent? | a shadow run's withheld write, in full |
| Why can it not run alone? | `ready_for_autonomy`, in the version's own words |
