# From a day of tabs to a named task

How continuous observation becomes a task somebody can be offered, and exactly
which parts of that a model is allowed to decide.

Read [`docs/12-execution-and-agents.md`](12-execution-and-agents.md) for the
other half — what happens once a task is taught. This file is everything before
that: the pipeline that turns an operator's ordinary day into candidates, and
the three places a model is asked for an opinion about them.

---

## The one rule

**Evidence decides identity. The model writes the sentence and proposes the
joins. Nothing a model says is ever the key.**

Every stage below is deterministic unless it is marked **M**, and every **M**
output is stored marked as a model's reading, next to the derived fact it did
not replace.

---

## The pipeline

| # | Stage | Where | Model |
|---|---|---|---|
| 0 | Capture — gestures, calls, page events, uploaded in batches | the extension | — |
| 1 | Admit and store verbatim as NDJSON | `observation/ingest.py` | — |
| 2 | Segment a day into episodes | `observation/segment.py` | — |
| 3 | Cluster episodes into candidates | `observation/mine.py` | — |
| 4 | **Name the candidate** | `observation/propose.py` | **M** |
| 5 | **Propose variant merges** | `observation/propose.py` | **M** |
| 6 | **Propose cross-system workflows** | `observation/propose.py` | **M** |
| 7 | Teach: candidate → recording → skill | `observation/teach.py` → `induction/` | M for words only |

### 2. What an episode is

A run of activity breaks on a **host change**, a **gap over three minutes**, or
a **span over thirty minutes**, and is kept only if it contains at least one
non-background call *and* at least one gesture — reading a screen is not a task.

The signature of an episode is the ordered shape of its calls,
`"POST /data/WM/wm/inventory/adjust → GET /data/WM/wm/inventory/*"`, with
immediate repeats collapsed. `url_shape` comes from `induction/diff.py` on
purpose: clustering and two-run alignment must ask the same question about a URL
or a task will cluster one way and pair another.

### 3. What makes two doings "the same task"

`(principal_id, signature)`. A string, compared for equality.

Not a model, not an embedding, and not a similarity threshold — because mining
re-runs over evidence it has already read, and induction pairs two
demonstrations on **exact** objective-key equality. Anything that answers
slightly differently on a second pass produces a second candidate, a second
skill, and a pair that can never pair. That failure is silent, which is what
makes it the one worth designing against.

The cost of that strictness is real and is paid at stages 5 and 6: the same task
done with one extra page is two candidates, and a task spanning two systems is
two candidates. Those are the two places a model earns its keep.

---

## The three model slots

Each one is a **proposal about** a candidate, never a change to what a candidate
*is*. All three are gated on `interpretation_enabled` and a configured key, and
all three degrade to nothing when the interpreter is unavailable — a deployment
that may not call a hosted model still mines, still offers candidates, and still
teaches.

### Slot 1 — the sentence on the front

`Adjust inventory on bf56-kms-wms-web-np2.jdadelivers.com` is what deriving a
title from a URL can honestly produce. It is correct and nobody reads it.

The model is given the candidate's evidence — its host, how often it happens,
how long it takes, and its call shapes — and asked for one line a warehouse
person would recognise. The result goes through `TaskCandidate.rename(title,
by_model=True)`, and `named_by_model` travels with it to the screen, so a
sentence is never mistaken for a fact.

**It cannot touch `signature`, `host`, or the objective key** derived later at
seal. Renaming is cosmetic by construction: two candidates with the same
signature are the same candidate whatever they are called.

### Slot 2 — variants of one task

Deterministic first: same operator, same host, and one signature's steps a near
subset of the other's. Only a pair that passes that is worth a model call.

The model is asked one question — *are these the same piece of work?* — and
answers with a reason. What is stored is a **join suggestion** on both
candidates: the other's id, why, and that a model said so. Nothing is merged.
The two candidates still count separately, still show separately, and a person
teaching one is not silently teaching the other.

### Slot 3 — a workflow across systems

An episode breaks on host change, so "check the WMS, then update the ERP" can
never be one candidate. The deterministic filter is adjacency: the same
operator, different hosts, one episode ending as the other begins, on more than
one occasion.

Same shape as slot 2 — a suggestion with a reason, stored on both, merging
nothing. This is the one place the system can see a workflow that no single
system's traffic contains, and it is the one place a model is genuinely better
than a rule.

---

## Why not let one large reasoning model do all of it

The tempting design is to hand a day of evidence to a reasoning model nightly
and ask what the operator kept doing. It was tried, and the reasons it is not
what this system does are specific:

- **Identity has to be stable across runs.** Mining is re-runnable by design.
  A model asked the same question twice does not have to answer the same way,
  and every difference is a duplicate candidate whose demonstrations never pair.
- **The audit has to survive a restart.** A Temporal workflow never calls a
  model (`docs/12`), because a replayed workflow that answers differently has a
  different history — and the history is what an incident review reads.
- **Egress is a second consent.** Keeping a customer's WMS traffic in their own
  infrastructure is what they agreed to. Sending a full day of it to a hosted
  model is a different conversation, and the volume grows per operator per day.
- **Out-of-the-box models are measurably weak at exactly this.** Benchmarks on
  semantics-aware process mining find frontier models struggle without
  fine-tuning; a computer-use model at ~72% on OSWorld is a good fallback rung
  under verification and a bad mechanism in front of a warehouse write.

What the industry does is the same split. UiPath's unassisted task mining finds
"the most frequently occurring and consistent sequence of steps" with an
algorithm and lets a human edit the label; its LLM functions summarise text
inside transformations. Celonis discovers from the event log and uses ML to
group and explain on top of it. The vendors selling against task mining attack
it on precisely the ground this design avoids: non-deterministic computer vision
that "can produce different outcomes" run twice on identical data, and
screenshots full of confidential content.

So the model is here, and it is used where evidence genuinely underdetermines
the answer: what to call something, whether two things are the same, and what a
screen means when replay has already failed.

---

## What a candidate carries

| Field | Derived | Model |
|---|---|---|
| `signature`, `host`, `principal_id` | yes | never |
| `episodes`, counts, durations | yes | never |
| `title` | yes, from verb + entity + host | **replaced when slot 1 runs, marked `named_by_model`** |
| `joins` | the pair is filtered deterministically | **the judgement and its reason** |
| `status` (`new`/`dismissed`/`taught`) | a person | never |

---

## Where this stops

Slots 2 and 3 suggest; they do not merge, and nothing downstream reads a
suggestion. Acting on one is a person's decision, and the shape that decision
should take — teach both as one skill, dismiss one as a duplicate, or stitch two
recordings into one demonstration — is not built. That is deliberate: a
suggestion nobody has acted on is a sentence on a screen, and a suggestion the
system acts on is a task identity a model decided after all.
