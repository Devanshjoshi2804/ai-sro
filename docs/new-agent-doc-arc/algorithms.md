# Algorithms

Every algorithm this architecture needs, written to be implemented. Each one says
where it came from: **[paper]** means adapted from published work, with what was
measured; **[ours]** means it is our own and nothing published backs it, which is
a thing to know before trusting it.

Rationale and evidence live in [`README.md`](README.md). This file is the
mechanics.

Notation: `‖x‖` is a token count. Tunables are named `K_`, with the starting
value given and the verification step that measures it.

---

## A1 · Correlate requests to a gesture

**[ours, from the existing capture invariants]**

The extension uploads gestures and requests as separate events in one batch. A
gesture owns the calls its own action caused.

```
def correlate(batch):
    gestures = sorted(batch.gestures, key=at)
    requests = sorted(batch.requests, key=started_at)

    for r in requests:
        owner = last gesture g where
                    g.tab_id == r.tab_id
                and g.at <= r.started_at
                and r.started_at - g.at <= K_ATTRIBUTION
        if owner: owner.requests.append(r)
        else:     orphan(r)          # kept, never dropped
```

`K_ATTRIBUTION = 10s`. The existing pipeline's rule holds and is the reason for
the `else`: *a request arriving after a drain belongs to the previous action, not
to nobody* — only traffic with no owning tab at all is an orphan, and orphans
stay in the store because a background poll is evidence that a background poll
happened.

Page events attach to the gesture preceding them by the same rule.

---

## A2 · Trim a gesture for the intent call

**[ours]** — token discipline, because A3 runs once per gesture.

```
def trim(g):
    return {
      "kind": g.gesture.kind,
      "target": pick(g.gesture.target,
                     [role, name, text, testId,
                      component.itemId, component.fieldLabel,
                      component.xtype, component.query]),   # never cssPath/xpath
      "value": None if g.gesture.secret else g.gesture.value,
      "url": strip_query_except(g.url, K_KEEP_PARAMS),
      "calls": [ {method, path_shape(url), status,
                  body_keys(request_body),        # keys + short values only
                  response_shape(response_body)}  # keys, and ids, not prose
                 for r in g.requests ],
      "page": [e.page_kind for e in g.page_events],
    }
```

`cssPath` and `xpath` are excluded deliberately: they are long, they carry no
meaning a model can use, and they are the two locators that break. The runner
still gets them from the stored gesture — this trim is for the model, not for
execution.

`body_keys` truncates each value to `K_VALUE_CHARS = 80`. A body over
`K_BODY_KEYS = 40` keys is summarised to its keys alone.

---

## A3 · The per-gesture intent call

**[paper]** — one call per gesture, never a batch. Batching stream items into a
shared call degrades each item through semantic interference and diluted
attention, with accuracy decaying roughly `A(T) = A_max · e^(−β(T−1))` in batch
size `T` while throughput only saturates as `y(T) = T/(aT+b)`. The saving is
small and the cost is per-item quality.

```
def intent(g, stream):
    tail = last K_TAIL intents on stream, one line each
    shot = g.shot_ref if thin(g.gesture.target) else None
    return model(K_INTENT_MODEL,
                 prompt   = INTENT_PROMPT,
                 evidence = trim(g),
                 context  = tail,
                 image    = shot,
                 schema   = Intent)

def thin(target):
    return not (target.name or target.text
                or target.component.fieldLabel or target.component.itemId)
```

`K_TAIL = 8`. `K_INTENT_MODEL` starts at Gemini 3.8 Flash and moves to Flash-Lite
if that reads a gesture as well (verification 3c).

A failed or malformed call leaves `Intent = None` on the gesture. The gesture
still enters the window; the umbrella pass reads raw evidence and does not
require every gesture to carry an intent.

---

## A4 · Pack a window

**[paper]** — the ordering is not incidental. Prompt ordering alone moved
accuracy from **0.28 to 0.44** on a two-supporting-fact task at 64K tokens, with
question-first strongest at long context; and *Long-Context LLMs Meet RAG*
(ICLR 2025) found RAG quality **non-monotonic** in retrieved passages — improving,
then declining as hard negatives accumulate — and offers a training-free
reordering that puts the strongest evidence at both ends and the weakest in the
middle, with gains that appear specifically once the evidence set is large.

```
def pack(new_gestures, pool, known, kb):
    budget = K_WINDOW_TOKENS - ‖INSTRUCTION‖*2 - ‖known‖ - ‖kb‖

    items = [ (g, strength(g)) for g in new_gestures ]
          + [ (p, strength(p) + K_POOL_BONUS) for p in pool ]

    chosen, spent = [], 0
    for item, _ in sorted(items, key=strength, desc=True):
        if spent + ‖item‖ > budget:
            if len(chosen) < K_MIN_GESTURES: item = trim(item)   # shrink, keep
            else: break
        chosen.append(item); spent += ‖item‖

    chosen.sort(key=at)                      # temporal order is never lost
    return INSTRUCTION + arrange(chosen) + known + kb + INSTRUCTION_RESTATED

def arrange(xs):
    """Strongest at both ends, weakest in the middle. [paper]"""
    by_strength = sorted(xs, key=strength, desc=True)
    head, tail, mid = [], [], []
    for i, x in enumerate(by_strength):
        (head if i % 2 == 0 else tail).append(x) if i < K_ENDS else mid.append(x)
    return head + sorted(mid, key=at) + reversed(tail)

def strength(g):
    s  = 1.0
    s += 1.0 if any(call.method != "GET" for call in g.requests) else 0
    s += 0.5 if g.intent and g.intent.confidence == "high" else 0
    s += 0.5 if g.gesture.kind in ("type", "select", "upload") else 0
    s += 1.0 if g.id in shared_value_gestures(window) else 0     # A6
    return s
```

`K_WINDOW_TOKENS = 150_000` — below the 200K boundary where Gemini 3.1 Pro's
input price doubles from $2 to $4 per million. `K_MIN_GESTURES = 25`, so a quiet
morning is still read. `K_ENDS = 12`, `K_POOL_BONUS = 0.5`.

**The window is built from trimmed evidence, not full bodies, and that is a
measurement rather than a preference.** Across 81 real gestures from the acme
tenant:

| | median | mean | max |
|---|---|---|---|
| full requests inline | 72 tok | **8,388 tok** | **203,644 tok** |
| `trim()` | 88 tok | 204 tok | 1,916 tok |

Two single gestures each carried more than the entire window, and **three of the
eighty-one held 71% of all request bytes**. "Bodies inline until the budget is
spent" therefore does not degrade gracefully — it lets one click starve the day,
and which click wins is an accident of iteration order.

Trimmed, a whole day fits: ~700 gestures by mean and more by median, against a
real day of roughly 1,500. So `K_MAX_GESTURE_TOKENS = 2_000` caps any single
gesture's contribution, full bodies stay in the store reachable by id, and the
coarse-to-fine pass in A7 becomes the rare case it was meant to be rather than
the normal one.

**`arrange` keeps `chosen.sort(key=at)` upstream of it for a reason.** Order-
invariant representations were measured to specifically degrade cross-application
reconstruction, so the *middle* stays in temporal order and only the ends are
promoted. A workflow is a sequence; scrambling it to chase a position effect
would trade the thing we are trying to read for a few points on a benchmark that
is not ours.

**What is deliberately absent:** no marking of which evidence is most relevant.
Explicitly telling a model *"the most relevant context is marked as 1"* was
measured to **reduce** accuracy in all five languages tested. `strength` orders
the prompt; it is never stated inside it.

Verification 3a measures whether any of this moves our numbers.

---

## A5 · The shape key

**[ours]** — the replacement for `(principal_id, ordered call shape)`.

```
def shape_key(workflow):
    return [ (g.system, target_identity(g), g.gesture.kind)
             for g in cited_gestures(workflow) ]        # evidence order

def target_identity(g):
    t = g.gesture.target
    return first_present(
        t.component.itemId,                 # "clientCode"  — ExtJS, stable
        t.component.query,                  # "panel#clients textfield#clientCode"
        f"{t.role}|{t.name}"      if t.role and t.name else None,
        t.testId,
        f"text|{t.text}"          if t.text else None,
    ) or f"anon|{g.gesture.kind}"
```

Never `cssPath` or `xpath`: both encode document position, both change when the
page is restyled, and a key built on them is the brittleness we are removing.

---

## A6 · Values that crossed a system boundary

**[paper]** — cross-organisational process mining reconstructs one process from
logs with **no shared case identifier** — our exact problem — at **over 98.4%
precision and 94.2% recall**, by detecting connections between adjacent event
pairs and linking on **shared data items across the separate logs**. No model
anywhere in it.

```
def shared_values(window):
    seen = defaultdict(list)                     # value -> [(gesture, system)]

    for g in window:
        for v in typed_values(g) + response_ids(g):
            if trivial(v): continue
            seen[normalise(v)].append((g, g.system))

    return { v: occurrences
             for v, occurrences in seen.items()
             if distinct_systems(occurrences) >= 2 }

def trivial(v):
    return (len(str(v)) < K_MIN_VALUE_LEN
            or tenant_frequency(v) > K_UBIQUITY
            or v in {"true","false","null","0","1",""})
```

`K_MIN_VALUE_LEN = 4`. `K_UBIQUITY = 0.25` — a value appearing in more than a
quarter of the tenant's gestures is furniture, not a link. A facility code every
call carries links nothing; a supplier name typed once in Blue Yonder and
returned by an SAP call links a great deal.

`tenant_frequency` is a count over stored evidence, refreshed per pass. It is
arithmetic, not a pattern, and it is the only thing in A6 that needs history.

**This is a hint, not a gate.** The shared values are handed to the umbrella pass
as a labelled section — *these values appear in more than one system* — and the
model decides what they mean. Nothing is joined or rejected on this score alone.

---

## A7 · The umbrella call, coarse then fine

**[paper, adapted]** — LongCite's coarse-to-fine structure (chunk-level citations
first, then sentence-level citations *within* the cited chunks) is a
training-data construction method, not an inference technique, and the
verification votes killed the claim that it was one. The **structure** is still
worth borrowing at inference time, and this is our adaptation of it rather than
a published result. Use it only when a single pass is over budget.

```
def umbrella(window, pool, known, kb):
    if ‖window‖ <= K_SINGLE_PASS:
        return model(K_UMBRELLA_MODEL, pack(...), schema=[ProvenWorkflow],
                     reasoning_effort=K_EFFORT, samples=K_SAMPLES)

    # coarse: which spans of the day hold a job at all
    spans = model(K_UMBRELLA_MODEL, pack(summarise_each(window), ...),
                  schema=[Span])                        # cites gesture ids

    # fine: one pass per span, full evidence for that span only
    return flatten(
        model(K_UMBRELLA_MODEL, pack(full(window, s), pool, known, kb),
              schema=[ProvenWorkflow])
        for s in merge_overlapping(spans)
    )
```

`K_SINGLE_PASS = 150_000`. `K_EFFORT` starts high — reasoning effort has a
significant positive linear relationship with accuracy, and is the first knob to
turn. `K_SAMPLES = 1`; see A8.

**Output schema orders `cites` before `says`.** An explicit step identifying the
relevant evidence *before* composing the answer measurably beats composing first.
That is a schema-ordering decision with a measured basis, not tidiness.

---

## A8 · Sample count

**[paper, contested]**

```
def propose(window):
    runs = [ umbrella(window) for _ in range(K_SAMPLES) ]
    if K_SAMPLES == 1: return runs[0]
    return plurality_by(runs, key=shape_key)      # A5 makes them comparable
```

`K_SAMPLES = 1`. Published: 0.4% gain from 1→20 samples at ~20× cost, and no
significant gain from 1→7 in a second study. But that headline was measured on
Gemini-2.5-Flash-Lite, and the backfire result (voting hurting 56.6% / 65.7% of
problems) is from 7–8B open models and **does not transfer to a frontier model**.

The direction that does bear on us: the diminishing-returns paper's thesis is
that voting helps *less* as models get stronger, so a newer model argues for
expecting less, not more. That is still someone else's benchmark on someone
else's task. Verification 3b measures it here; turn the default up only if it
says to.

Note that `plurality_by` is only possible because A5 gives two proposals a
comparable key. Voting over free-text workflows would be voting over prose.

---

## A9 · Validate citations

**[paper]** — grounding is worth an order of magnitude: free-generated workflow
JSON hallucinated **up to 21% of steps**; forced to select from real components,
that fell to **under 7.5% at every model size and 1.9% at 7B**. And models omit
citations wherever the output shape permits, so absence is a rejection.

```
def validate(w, window, pool):
    known = { g.id for g in window } | { p.gesture_id for p in pool }

    for step in w.steps:
        if not step.cites:                    reject(w, "uncited step", step)
        bad = set(step.cites) - known
        if bad:                               reject(w, "unknown gesture", bad)

    if not w.steps:                           reject(w, "no steps")
    if systems(w) != systems(cited(w)):       reject(w, "system not in evidence")
    return w
```

The third check is not decoration: it is what stops a workflow claiming to touch
SAP when nothing it cited ever spoke to SAP, which is the failure that would put
an invented origin in front of the runner.

Rejections are stored with the model's full response. A rising rejection rate is
a signal about the prompt, and it is invisible if rejections are only logged.

---

## A10 · Coverage and positional skew

**[paper]** — position bias is real but **model-specific and direction-
specific**: some models favour late context, and one SIGIR 2026 reproduction
found no positional effect at all. So this measures rather than assumes.

```
def coverage(w_list, window):
    cited = { id for w in w_list for s in w.steps for id in s.cites }
    n = len(window)
    deciles = [ 0.0 ] * 10
    for i, g in enumerate(window):
        if g.id in cited: deciles[min(9, i * 10 // n)] += 1

    mass = normalise(deciles)
    return {
      "coverage": count(d > 0 for d in deciles) / 10,
      "skew":     sum(mass[:3]) - sum(mass[-3:]),   # + early, − late, 0 even
      "gini":     gini(mass),
    }
```

Acted on, not merely recorded:

```
if coverage < K_MIN_COVERAGE:      K_WINDOW_TOKENS *= 0.8      # shrink and retry
if abs(skew)  > K_MAX_SKEW:        flag("positional skew", direction=sign(skew))
```

`K_MIN_COVERAGE = 0.5`, `K_MAX_SKEW = 0.4`.

**Do not use model confidence as a substitute.** Accuracy drops most when
evidence sits mid-context **without any rise in output entropy** — the model
stays confident while using the wrong span — and token entropy was shown to
mostly measure prose fluency. A confidence signal will not find this; a count
will.

---

## A11 · Identity

**[ours]**, two questions with two answers. Gesture ids are per-occurrence, so
raw overlap answers only the first.

```
def resolve(proposal, known):
    # 1. is this a re-read of evidence already processed?
    for w in known:
        if jaccard(cited(proposal), cited(w)) >= K_SAME_EVIDENCE:
            return SameOccurrence(w)

    # 2. is this the same job, on different evidence?
    a = shape_key(proposal)
    best, score = None, 0
    for w in known:
        c = containment(set(a), set(shape_key(w)))
        if c > score: best, score = w, c

    if score >= K_SAME_JOB:
        return SameJob(best, contains = len(a) > len(shape_key(best)))
    return NewJob()

def containment(a, b):   return len(a & b) / min(len(a), len(b))
def jaccard(a, b):       return len(a & b) / len(a | b)
```

`K_SAME_EVIDENCE = 0.5`, `K_SAME_JOB = 0.5` — the only tunable constants that
decide anything, measured by verification 2 and 2a.

**Containment, not Jaccard, for the second question.** Jaccard would call a
3-step *create supplier* and a 12-step *create supplier, add item, set status in
SAP* two different jobs, because the small set drowns in the union. Containment
says the first sits inside the second — true, and the variant relation the panel
should surface. `contains` carries which way round.

The model's own `same_as` is stored and **decides neither**. A model asked to
re-judge its earlier verdict disagrees with itself at roughly 90%, and that is
exactly what `same_as` asks it to do.

---

## A12 · The pool

**[ours]**, motivated by measurement: model abstraction over raw event streams
was measured at roughly **74% recall** against ground truth (12,741 correct of
17,165 events), with spurious aggregation of repeats and worst performance on
the do-nothing class. A quarter of every window needs a second reading.

```
def after_pass(window, proven, pool):
    claimed = { id for w in proven for s in w.steps for id in s.cites }

    for g in window:
        if g.id not in claimed:
            pool.add(PoolEntry(g.id, g.intent, age=0, tenant=g.tenant))

    for e in pool:
        e.age += 1
        if e.age > K_POOL_AGE or older_than(e, K_POOL_DAYS):
            pool.retire(e)              # out of the prompt, still in the store
```

`K_POOL_AGE = 6`, `K_POOL_DAYS = 7`. **The pool is keyed by tenant, not by
stream** — that is the whole mechanism by which one operator's Blue Yonder half
meets another's SAP half.

Retirement removes an entry from prompts, never from evidence. A retired gesture
is still citable if a later pass reaches it another way.

---

## A13 · Build a step's locators

**[ours]**, from the frozen protocol. No model involved.

```
def locators(step):
    g = primary_cited_gesture(step)      # first cited gesture that is a gesture
    t = g.gesture.target
    ls = []
    if t.component.query:  ls.append(("component",     t.component.query))
    if t.role and t.name:  ls.append(("role_and_name", f"{t.role}|{t.name}"))
    if t.text:             ls.append(("text",          t.text))
    if t.testId:           ls.append(("test_id",       t.testId))
    if t.cssPath:          ls.append(("css_path",      t.cssPath))
    return ls                            # tried in order; first to resolve wins

def origin(step):
    g = primary_cited_gesture(step)
    r = first(c for c in g.requests if names_a_system(c))
    return scheme_and_host(r.url if r else g.url)
```

**`origin` is per step, from that step's own evidence.** In a job spanning two
systems the Blue Yonder steps carry Blue Yonder's origin and the SAP step carries
SAP's. A documented cross-application agent failure is losing window focus during
a hand-off so data meant for the second application is typed into the first;
this is what stops it, and A9's system check is what stops a fabricated origin
reaching here.

---

## A14 · Verify a step

**[paper]** — a propose-then-verify evaluator grounded in **environment state**
rather than a model reading a screenshot scored **86.9% against 78.8%**, human
agreement 94.0% (κ 0.84). Its taxonomy is the load-bearing part: evidence is
visible-state, hidden-state, or artifact, and **artifact verification was the
largest category — 192 of 321 tasks**. Most completions leave their proof
somewhere other than the visible screen.

```
def verify(step, sent, answer):
    # 1. artifact: what the command itself returned
    if sent.kind == "http.send":
        if answer.status in expected_status(step):  return Held("status")
        if answer.status >= 400:                    return Failed(answer.status)

    # 2. hidden state: a read the cited evidence shows this page performs
    probe = confirming_read(step)          # a GET seen in the demonstration
    if probe:
        got = send(probe)
        if contains_expected(got, step.parameters): return Held("read")
        else:                                       return Failed("read")

    # 3. visible state: last, and least
    shot = screenshot(inline=True)
    return model(K_VERIFY_MODEL, step, before=step.before, after=shot,
                 schema=Verdict)
```

Screenshots are the fallback, not the method. A supplier that was created is
proved by a `201` and an identifier in the body, or by a read that returns it;
a green toast is the weakest of the three and the easiest to be wrong about.

---

## A15 · Escalate, and notice staleness

**[ours]**, one rung of the existing ladder's logic applied lower down.

```
def run_step(step):
    for attempt, planner in [(1, K_PLAN_MODEL), (2, K_RESCUE_MODEL)]:
        sent   = plan(planner, step, look(), locators(step), origin(step))
        if sent.origin not in run.allowlist:  return Refused("origin")
        answer = perform(sent)
        v      = verify(step, sent, answer)
        if v.held:
            if answer.matched_by in K_WEAK_LOCATORS:
                flag_stale(step, answer.matched_by)     # succeeded AND stale
            return v
    return Stopped(v, ask_operator=True)
```

`K_WEAK_LOCATORS = {"css_path", None}`. The protocol says it plainly: a step that
only ever matches on the last fallback is a step about to break. So a run whose
`component` and `role_and_name` locators both missed **succeeds and reports the
recipe stale** — the same instinct as a vision rung finding a button somewhere
new, one rung down.

`run.allowlist` is the set of origins the workflow's own cited evidence names.
Checked before the command leaves the process, not after.

---

## The tunables, in one place

| | Start | Decided by |
|---|---|---|
| `K_ATTRIBUTION` | 10 s | A1, existing capture behaviour |
| `K_TAIL` | 8 intents | — |
| `K_WINDOW_TOKENS` | 150,000 | the 200K price boundary; A10 shrinks it |
| `K_MIN_GESTURES` | 25 | — |
| `K_ENDS` | 12 | verification 3a |
| `K_MIN_VALUE_LEN` / `K_UBIQUITY` | 4 chars / 0.25 | verification 5 |
| `K_SAMPLES` | 1 | verification 3b |
| `K_EFFORT` | high | — |
| `K_SAME_EVIDENCE` / `K_SAME_JOB` | 0.5 / 0.5 | verification 2, 2a |
| `K_MIN_COVERAGE` / `K_MAX_SKEW` | 0.5 / 0.4 | A10, continuously |
| `K_POOL_AGE` / `K_POOL_DAYS` | 6 passes / 7 days | verification 5 |
| `K_UMBRELLA_MODEL` | 3.1 Pro vs 3.8 Flash | verification 3c |
| `K_INTENT_MODEL` | 3.8 Flash vs Flash-Lite | verification 3c |

Fourteen numbers. The pipeline this replaces has five — 3 minutes, 30 minutes,
0.60, 5 minutes, 20 pairs — and the difference is that **every one of these is
attached to a measurement that moves it**, rather than tuned once against one WMS.
Two of them (`K_SAME_EVIDENCE`, `K_SAME_JOB`) decide anything at all; the rest
shape a prompt or bound a cost.

---

## What no algorithm here does

- **Segment by time or by host.** There is no idle bound and no span bound. A4
  packs by tokens, A7 lets the model find the boundaries, A12 catches what it
  missed.
- **Compare URLs, call shapes, or bodies for identity.** A5 is UI-level, A6 is
  value-level, and neither reads a URL. The one place a URL is read is A13's
  `origin`, which is execution, not identity.
- **Ask a model whether two things are the same.** A11 decides; the model's
  opinion is stored beside the verdict and overrules nothing.
- **Trust a model's confidence.** A10 counts citations because entropy was
  measured not to track correctness here.
- **Gate which gestures are read.** A3 runs on every gesture. The standard advice
  is to filter first; this design declines it, and A2 is how it stays affordable.
