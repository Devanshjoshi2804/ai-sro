# What the miner actually found

The question this architecture was built to answer: **does one model pass over
a window of captured evidence find a job that spans two systems** — the thing
the production pipeline is structurally unable to represent, because
`observation/segment.py` partitions candidates by host and a two-system job is
therefore two candidates forever?

Answer, in one line: **yes, on two-system evidence; and it does not invent one
when the evidence has only a single system.** The second half is what makes the
first half worth anything.

## The evidence problem, stated first because it bounds everything below

Every gesture in the captured acme store — 81 of them, after two non-acme
batches are dropped — happened on **one host**,
`bf56-kms-wms-web-np2.jdadelivers.com` (Blue Yonder). The recorded knowledge
base is the same system: 296 exchange files whose URLs are all relative paths
with no host at all.

So the captured evidence **cannot** demonstrate a cross-system job, however
well the miner performs. A clean run on it proves the pipeline executes and
proves nothing about the bet.

That is why the second system below is **constructed**, and it is labelled as
constructed everywhere it appears. It was built from the real captured shapes —
a real carrier name (`Test Drive LLC`) that genuinely appears in the WMS
capture, real field names, real request bodies — and ingested through the real
protocol, read by the real model, mined by the real loop. What is synthetic is
the second host and the seven gestures on it. Nothing else.

## What was run

Four configurations, three passes each, then re-run against shipped `HEAD`
after the redaction and splitter work landed:

| | evidence | model | cross-system workflows |
|---|---|---|---|
| A | 81 captured, one host | 3.1 Pro | **0 / 3** |
| B | 88 = captured + 7 constructed, two hosts | 3.1 Pro | **3 / 3** |
| C | same as B | 3.8 Flash | **3 / 3** |
| D | 81 captured, one host | 3.8 Flash | **0 / 3** |

Every pass on single-system evidence found zero. Every pass on two-system
evidence found exactly one, and it was the same job each time: the carrier
cross-reference that starts in the WMS and finishes in the TMS.

The workflow it keeps, from the shipped-code run:

```
Configure parcel cross reference for carrier Test Drive LLC
  steps 7, cites 32
  claims     ['https://tms.enveyo.example', 'https://bf56-kms-wms-web-np2…']
  stands on  ['https://bf56-kms-wms-web-np2…', 'https://tms.enveyo.example']
```

`claims` is what the model said. `stands on` is what its cited evidence
actually touches, computed independently. They agree.

## The part that makes it credible

A model that finds a cross-system job is not interesting on its own — a model
will happily assert one. What matters is whether the checks refuse a
fabricated version of the same claim. Taking the **real** answer above and
tampering with it five ways:

```
cite a gesture that does not exist   -> unknown gesture: ges_invented
TMS step citing only WMS evidence    -> step system not in evidence
an invented third system             -> system not in evidence: sap.acme.example
a step with no words                 -> wordless step
a step citing nothing                -> uncited step
```

Every one refused, each with its own reason. The second is the one worth
noting: that check was rewritten during Task 5 because the original compared
the model's claimed systems against the model's own step list — it was reading
the model to validate the model. It now checks a step's claimed system against
the systems its cited gestures actually happened on, and here it catches a
fabricated cross-system claim on real model output.

The arithmetic agrees with the model independently. `shared_values` reports
`{}` on the captured store and `{'Test Drive LLC': 2}` once the TMS half is
present — the same join, found without a model.

## What this does not prove

- **It has not been shown on captured two-system traffic.** The mechanism
  works; the demonstration uses a constructed second system. Anyone repeating
  this should treat B and C as a proof of mechanism, not a field result.
- **The ubiquity filter is unexercised.** Max ratio 0.136–0.148 against a
  threshold of 0.25 — closer than the 0.037 measured before `frequencies_over`
  moved to counting gestures, and still never firing.
- **The window budget is unexercised, and so is pool retirement.** `left_out`
  was 0 on all thirteen passes and `retired_entries` empty on every one:
  `K_POOL_AGE` counts six passes and no store here saw more than two.
- **Redaction is unexercised by this data.** Zero credential-named fields in
  the whole capture.
- **One window, one tenant, one day.** Nothing here says anything about the
  carryover pool across users, which is the mechanism for the U1→U2→U3 case.

## arrange() has no measurable effect at this scale

`window.arrange` puts the strongest evidence at both ends of the prompt and the
weakest in the middle, against the long-context finding that attention sags in
the middle. It was found to be dead code during the whole-branch review — three
documents described it and nothing called it — and wired in.

Then measured, because a mechanism that only looks like it is working is worse
than none. Six real passes on the 81 captured gestures, three with it and three
without, same model, same evidence:

```
arrange=ON    coverage 0.80   skew +0.367   proposed [4, 4, 4]
arrange=OFF   coverage 0.80   skew +0.367   proposed [4, 4, 4]
```

Identical to three decimal places. The control holds: the two prompts differ,
74 of the 81 items change position, and the lengths match exactly.

**This does not say the idea is wrong. It says the conditions are not present
here.** The window is 81 items at 16% of budget; the attention findings it
argues from are about prompts near their limit. The honest reading is that
`arrange` is unproven at this scale rather than useless, and the experiment
worth repeating is the same A/B on a window near the 555-gesture ceiling.

It is kept, because it costs one sort and the hypothesis has not been tested
under the conditions it was designed for. What is not kept is the claim: no
document should say it improves anything until a window large enough to answer
that has been mined.

## A day that does not fit one window

Everything above was measured on 81 captured gestures on one host. The product
watches every tab -- mail, WMS, TMS, ERP -- so a real day is thousands, and
three mechanisms this document called unexercised become the ones the system
rests on. Measured on a synthetic all-tabs day of 3,240 gestures across five
hosts, built from the real captured shapes:

**The window holds about 200 of them, 6% of the day.** That is the number every
other figure here follows from.

**The furniture filter, unexercised at 0.037 against a 0.25 threshold, works
the moment it sees a real day.** The operator's own address appears on every
gesture and is filtered at ratio 1.000; a supplier code at 0.007 is kept as a
link. It also exposed a gap: `test` is exactly `K_MIN_VALUE_LEN`, scored 0.025,
and was published as a cross-system link across five hosts. Blocklisting the
word is what that looks like it needs, and the corpus refuses it -- `Test Drive
LLC` is a real carrier here and a real crossing. Shape, not vocabulary: a lone
short word collides across five applications, two words or one long one do not.

**The pool retired 81% of the day unread.** `age_pool` counted passes rather
than showings, so 2,630 of 3,240 gestures retired having never once been in
front of the model -- the mechanism built to stop the same tail losing forever
was guaranteeing it. It now ages only what the window showed.

**And the day did not rotate.** A flat carry-over bonus reorders nothing, so
passes two through ten packed the identical 468 gestures and ten passes had
shown 19% of the day. More passes would never have helped.

Two clocks fixed it, because showing and waiting are opposites: `age` counts
readings an entry was shown and not cited and runs out at `K_POOL_AGE`;
`waited` counts passes it was passed over, resets when shown, and earns
priority. Measured after:

```
pass  1: window 200  new 200   waited in pool [0, 1]
pass  2: window 569  new 569   waited in pool [0, 1, 2]
pass  3: window 572  new 572   waited in pool [0, 1, 2, 3]
...
ever in a window after 10 passes: 3240 of 3240  (100%)
retired without ever being shown: 0
```

`new` equals the window size on every pass -- each pass shows a set disjoint
from the one before. About 1.4 showings per gesture to cover the day, so
rotation is efficient rather than thrashing, and nothing retires because no
gesture accumulates six readings before the day is covered.

The honest caveat: this is a synthetic day. It is built from real captured
gestures, real values and real request shapes, but the host assignment and the
volume are constructed. What it establishes is that the mechanisms behave
correctly at that scale, not what a real all-tabs day contains.

## The rig on real evidence

Everything above was measured on 81 gestures from one afternoon, or on a
synthetic day. This section is 387 real gestures across 170 hours of one
operator's genuine work, replayed out of the backend's own blob store by
`backend/scripts/mirror_backfill.py`.

### What it found

Eight workflows, all of them warehouse work:

```
Create Carrier Cross Reference for Test Drive LLC   10 steps, 26 citations
Create Work Area Operation NEWTEST4                 10 steps, 21 citations
Search and Filter Work Areas                        11 steps, 35 citations
Create Work Area NEWTESTS                            8 steps, 22 citations
Create Work Area TWOTEST                             8 steps, 18 citations
Create Work Activity TEST1                           7 steps, 16 citations
Create a Warehouse Equipment Type                    7 steps, 13 citations
Login and Start Recording                            5 steps, 14 citations  CROSS-SYSTEM
```

The production pipeline, on the same operator, held 30 candidates of which 29
were `localhost` -- `Read skills on localhost`, `Create __nextjs_original stack
frames on localhost`. One was on the WMS host.

`coverage 1.0, skew 0.016, gini 0.014` on the first pass: every gesture in the
window cited, and citations spread evenly across 170 hours rather than
clustering at the head. On the 81-gesture corpus skew was +0.37 every time.

**The cross-system one is real and it is also a caution.** `Login and Start
Recording` spans Google and the WMS, which is the architecture's central claim
demonstrated on captured evidence rather than a constructed second host -- and
it is the login flow, which is not a job anyone wants automated. It exists in
the corpus because the tenant's own identity providers were not in the default
exclusion list. They are now.

### Identity, on the second pass

The same 387 gestures again:

```
proposed 14   kept 0   rejected 0
same_occurrence 1,  same_job 13
```

Zero duplicates. Thirteen of fourteen matched by **shape containment**, one by
citation overlap -- because the model re-reading byte-identical evidence cites
different gestures almost every time. A design keyed on citation overlap alone
would have produced thirteen duplicate workflows from this pass and more from
every pass after it. Scores ran 0.64 to 1.00, spread rather than clustered at
the threshold, and `Create Work Area NEWTESTS` and `Create Work Area TWOTEST`
stayed distinct despite sharing most of their shape.

### Redaction, finally tested against credentials

Every earlier measurement could only say the capture held none. This one did.
Comparing what the browser uploaded against what the rig stored:

```
as the browser sent it:   974,397 chars, 0 «redacted» markers, 1 JWT, 1 &code=
after the parse boundary: 518 markers, 0 JWTs, 0 &code=
```

The client-side rules did not fire at all on this traffic. The server-side ones
caught a live JWT and a real OAuth authorization code. That is the argument
this work rested on -- *a rule that runs only in the browser is one a browser
can be made not to run* -- and it is no longer an argument.

The `&code=` catch is the OAuth heuristic that was nearly not implemented,
because `code` matches seven real warehouse field names and only shipped once
narrowed to an exact parameter name beside an OAuth companion.

**Still open, and it is a live exposure:** the backend's blob store holds those
same two credentials unredacted. The rig strips them at ingest; the backend
keeps what the browser sent.

### Cost, measured rather than estimated

```
387 gestures read      $0.9459        $0.00244 each
thinking tokens        169,246 of 211,317 billed output   (80%)
three mining passes    ~$0.02
```

Plan 1 estimated $1.36 for a 2,000-gesture day. The real figure is about $4.90,
and the difference is almost entirely thinking tokens, which every cost figure
before commit `a0ddd04` excluded.

`unusable` fired zero times across 387 real calls -- the billed-but-unusable
reading Task 8 added a third state for is rare rather than routine.

### What is still unexercised

`validate` has now seen 92 real proposals and rejected none. Under
citation-forcing the model does not appear to fabricate, which is the
21%-to-7.5% finding holding on real data -- but the rejection paths remain
proven only by deliberate tampering.

387 gestures still fit one window, so `left_out` was 0 and the pool rotation
work is still untested on real evidence. That needs a day past the ~555-gesture
ceiling.

## What evidence would settle it

One operator, one session, two hosts, with a value carried between them by
hand. Concretely: create a carrier in the WMS, copy its code, open the TMS or
ERP in a second tab, and use that code there. Seven gestures on the second
system was enough for the miner to find the join; the capture needs the
extension running with both hosts granted, and it needs to be one operator's
continuous session so the timestamps interleave.

That is a fifteen-minute capture and it converts every "constructed" label in
this document into a measured one.

## Numbers worth carrying forward

**Window headroom.** 270 estimated tokens per gesture, so a 150K window holds
roughly **555 gestures** — near the 620 estimated during Task 1. The 88-gesture
window spends 23,840 of 150,000, so the pass runs at 16% of budget. A real
operator day exceeding that is why evidence the budget leaves out now enters
the carryover pool.

**Reproducibility.** Citation Jaccard across three passes on shipped code:
1.00 / 1.00 / 1.00 on two-system evidence, 0.88–0.98 on single-system. The same
runs against a pre-redaction snapshot gave 0.50–0.51 for Pro, so the
convergence work made the pass materially more stable, not just cleaner.

**Cost, and a caveat that mattered.** Thinking tokens are billed at the output
rate and `candidates_token_count` does not include them, so every figure this
project quoted before `a0ddd04` is a lower bound. On a Flash pass, thinking ran
to ~27,000 tokens against ~5,000 written — about 84% of billed output. `high`
is already Gemini 3.1 Pro's default, so the effort setting changes nothing
about the bill; turning it *down* is the only lever, and whether `low` changes
the result is unmeasured.

A preview model name is not in `PRICES`, so the entire measurement run recorded
`cost_usd 0.0, unpriced=True` while actually billing $1.12. The preview names
are priced now.

## Every pass, in numbers

Thirteen passes on shipped `HEAD`, three per arm plus one identity re-run.
`resolved` counts proposals that passed every check and were then folded onto a
workflow already stored. Nothing was rejected and nothing was stranded on any
pass — every gesture in every window was either cited by a kept workflow or in
the pool.

| arm | run | proposed | kept | resolved | coverage | skew | gini | pooled | in | written | thought | $ |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A captured, Pro | 1 | 6 | 3 | 3 | 0.70 | +0.20 | 0.47 | 40 | 40,274 | 6,084 | 3,884 | 0.200 |
| | 2 | 5 | 2 | 3 | 0.60 | +0.34 | 0.53 | 43 | 40,274 | 4,850 | 6,028 | 0.211 |
| | 3 | 6 | 3 | 3 | 0.70 | +0.21 | 0.46 | 39 | 40,274 | 5,372 | 9,770 | 0.262 |
| | re-run | 3 | **0** | 3 | — | — | — | 81 | 42,334 | 4,474 | 14,264 | 0.310 |
| B constructed, Pro | 1 | 5 | 2 | 3 | 0.70 | +0.31 | 0.47 | 43 | 43,192 | 5,346 | 6,846 | 0.233 |
| | 2 | 5 | 2 | 3 | 0.70 | +0.31 | 0.47 | 43 | 43,192 | 4,664 | 12,391 | 0.291 |
| | 3 | 5 | 2 | 3 | 0.70 | +0.31 | 0.47 | 43 | 43,192 | 5,226 | 21,656 | 0.409 |
| C constructed, Flash | 1 | 4 | 2 | 2 | 0.70 | +0.31 | 0.47 | 43 | 43,157 | 4,441 | 39,968 | 0.199 |
| | 2 | 4 | 2 | 2 | 0.70 | +0.31 | 0.47 | 43 | 43,157 | 4,542 | 36,398 | 0.186 |
| | 3 | 4 | 2 | 2 | 0.70 | +0.31 | 0.47 | 43 | 43,157 | 4,868 | 35,039 | 0.182 |
| D captured, Flash | 1 | 4 | 2 | 2 | 0.60 | +0.34 | 0.53 | 43 | 40,274 | 5,018 | 38,136 | 0.192 |
| | 2 | 4 | 2 | 2 | 0.60 | +0.34 | 0.53 | 43 | 40,274 | 4,049 | 26,100 | 0.143 |
| | 3 | 4 | 2 | 2 | 0.60 | +0.34 | 0.53 | 43 | 40,274 | 5,473 | 37,003 | 0.189 |

Two jobs are found on every pass of every arm — the work operation `AITEST9`
and the cross reference for `Test Drive LLC` — and two captured/Pro runs also
kept a one-step "review the Suppliers tab" fragment. Skew is positive on every
single pass: citations cluster toward the head of the window, but never past
`K_MAX_SKEW = 0.4`. The third of the window never cited is scrolls, mis-clicks
and stray navigation, and it goes to the pool rather than being lost.

**Duplicate absorption is load-bearing.** Across the thirteen passes, 33 of 57
proposals were folded onto an existing workflow rather than stored. Roughly
three per pass are the same two jobs re-described at a different granularity;
without `resolve` the store would fill with re-descriptions of one day.

## Identity, on real model output

Mining the same store twice: the second pass proposed 3 and kept **0**. All
three matched by **shape containment**, not by citation overlap — the model
re-reading byte-identical evidence did not re-cite the same gestures closely
enough to clear `K_SAME_EVIDENCE = 0.5`. An earlier run of the same experiment
did clear it twice (`same_occurrence` at 1.00) and matched the rest by shape.

So both mechanisms carry weight in practice, and on at least one real re-run the
shape key was the only thing that recognised a duplicate. `identity.py`'s two
questions are not belt-and-braces; A11's argument that cited ids alone cannot
answer "is this the same job" is confirmed on live output.

One artefact of that pass: it reports `lopsided = True`. It kept nothing —
correctly — so `coverage()` over an empty kept-list returned 0.0, which reads as
a lopsided window. A pass that found nothing *new* is not a lopsided reading;
`lopsided` is only meaningful when `kept > 0`.

A second artefact: because that pass claimed nothing, `add_unclaimed` re-pooled
all 81 gestures, the 38 cited by pass 1's kept workflows included. Defensible —
that pass placed nothing — but it means the pool refills to the whole window
whenever a pass is a duplicate.

## Does repetition buy anything, and is Pro needed

**Repetition: no.** Citation Jaccard between independent passes over an
identical window:

| arm | distinct shapes | held by a plurality | Jaccard |
|---|---|---|---|
| A captured, Pro | 4 | 3 | 0.88 / 0.98 / 0.90 |
| B constructed, Pro | 2 | 2 | 1.00 / 1.00 / 1.00 |
| C constructed, Flash | 3 | 2 | 1.00 / 0.98 / 0.98 |
| D captured, Flash | 3 | 2 | 1.00 / 0.97 / 0.97 |

Across every pass run for this document, plurality voting would have changed
exactly one outcome: a pre-redaction constructed/Pro pass split the cross-system
job into "Check carrier details in TMS" and "Create parcel cross reference",
losing the crossing. Its two siblings kept it whole. That is one case in
fifteen, for three times the money. **`K_SAMPLES` stays at 1** — the published
0.4%-for-20× result holds up here.

**Pro: not needed on this evidence.** Flash found the same jobs, kept the
cross-system workflow 3/3, produced no invalid citation, and was slightly the
more stable of the two. It costs 20–30% less per pass — not the 3× the input
price implies, because Flash spends 26,000–40,000 thinking tokens against Pro's
4,000–22,000 on the same window, and thinking is billed as output. On input
alone Flash would be $0.03 a pass against Pro's $0.086.

The recommendation is to move `config.mine_model` to `gemini-3.8-flash`, on a
sample of thirteen passes over one day. Note that the setting currently reads
`gemini-3.1-pro`, **which the API rejects with a 404** — `models.list()` offers
only `gemini-3.1-pro-preview`. Every Pro figure here is from the preview name;
the configured default has never completed a pass.

## The bill

One operator-day of 81 gestures, end to end:

| | Flash | Pro (preview) |
|---|---|---|
| reading 81 gestures (A3 is always Flash; $0.00243/gesture with thinking counted) | $0.20 | $0.20 |
| one mining pass | $0.14–$0.19 | $0.20–$0.26 |
| **a day** | **≈ $0.37** | **≈ $0.43** |

Beside plan 1's $1.36. Extrapolated to a 2,000-gesture day: roughly $4.90 of
reading plus four windows of mining, order $5–6 — extrapolated, not measured.

`/v1/spend` on a mined store reads
`{'passes': 1, 'mining_usd': 0.0, 'mining_unpriced': 1}` for a Pro pass made
before the preview names were priced. The flag was doing its job; the table was
missing a row.

## Verification of the whole

| # | claim | result |
|---|---|---|
| 1 | suite green, three gates clean | 314 passed; `ruff check`, `ruff format --check`, `mypy src` clean |
| 2 | a workflow spans two systems, every step citing gestures that exist | **not shown on captured evidence — it has one system.** 6/6 on constructed two-system evidence, every citation valid |
| 3 | re-mining adds no workflow | yes, on real output: second pass kept 0 |
| 4 | two occurrences of one job resolve `same_job` | 33 of 57 proposals folded onto an existing workflow, mostly by shape |
| 5 | nothing stranded | 0 on every pass |
| 6 | an invented citation is rejected and named | yes, plus four other tampers each under its own reason |
| 7 | an over-long window reports its skew | **not exercised** — `left_out` 0 everywhere, window at 16% of budget |
| 8 | cost is known, beside plan 1's $1.36 | ≈ $0.37 Flash / $0.43 Pro per operator-day, after `a0ddd04` |

## Reproducing this

```
new_agent_arch/scripts/measure.py      the instrument
new_agent_arch/evidence/constructed/   the seven constructed TMS gestures
```

The captured acme store is a scratch database rebuilt from captured batches and
is not in the repository.
