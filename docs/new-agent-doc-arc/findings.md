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
- **The ubiquity filter is unexercised.** Max ratio 0.037 against a threshold
  of 0.25, and no value is ever named twice in one reading.
- **Redaction is unexercised by this data.** Zero credential-named fields in
  the whole capture.
- **One window, one tenant, one day.** Nothing here says anything about the
  carryover pool across users, which is the mechanism for the U1→U2→U3 case.

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

**Window headroom.** 268 estimated tokens per gesture, so a 150K window holds
roughly **561 gestures** — near the 620 estimated during Task 1. A real
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

## Reproducing this

```
new_agent_arch/scripts/measure.py      the instrument
new_agent_arch/evidence/constructed/   the seven constructed TMS gestures
```

The captured acme store is a scratch database rebuilt from captured batches and
is not in the repository.
