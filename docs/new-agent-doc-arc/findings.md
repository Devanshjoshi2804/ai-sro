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

Eight workflows -- seven of them warehouse work, and the eighth the operator
getting ready, which is the caution below rather than a find:

```
Create Carrier Cross Reference for Test Drive LLC   10 steps, 26 citations
Create Work Area Operation NEWTEST4                 10 steps, 21 citations
Search and Filter Work Areas                        11 steps, 35 citations
Create Work Area NEWTESTS                            8 steps, 22 citations
Create Work Area TWOTEST                             8 steps, 18 citations
Create Work Activity TEST1                           7 steps, 16 citations
Create a Warehouse Equipment Type                    7 steps, 13 citations
Login and Start Recording                            5 steps, 14 citations  NOT THE WORK
```

The production pipeline, on the same operator, held 30 candidates of which 29
were `localhost` -- `Read skills on localhost`, `Create __nextjs_original stack
frames on localhost`. One was on the WMS host.

`coverage 1.0, skew 0.016, gini 0.014` on the first pass: every gesture in the
window cited, and citations spread evenly across 170 hours rather than
clustering at the head. On the 81-gesture corpus skew was +0.37 every time.

**The cross-system one is real, it is a caution, and the caution is worse than
first written.** `Login and Start Recording` was described here as spanning
Google and the WMS. Counting the systems of the gestures it actually cites:

```
workspace.google.com               2
blueyonderalphaus.b2clogin.com     1
keycloak-…-wms-keycloak-prod       4
localhost:3000                     7      <- this system's own console
bf56-kms-wms-web-np2.jdadelivers   0
```

It cites **no WMS gesture at all**, and half its evidence is the SRO console,
which the operator had open in a tab while demonstrating. So the one
multi-system workflow the miner found on captured evidence is the login flow
plus the apparatus watching itself -- not a warehouse job crossing into
another system, which is the claim this architecture exists to support. The
identity providers were not in the default exclusion list, and they still are
not: what changed is **this tenant's stored policy** (version 10), which now
names `b2clogin.com`, the keycloak host and `workspace.google.com`.
`DEFAULT_EXCLUSIONS` in `domain/observation/policy.py` is unchanged, so the
next tenant starts where this one did. `admit` does refuse this deployment's
own API and console outright, and that part is in the code.

That leaves the corpus at **seven warehouse jobs**, not eight. The eighth was
the operator getting ready.

The cross-system mechanism itself is unaffected -- it was measured on
constructed two-system evidence and scored 1.00/1.00/1.00 there. What this
costs is the claim that it has been shown on CAPTURED two-system traffic. It
has not, and the fifteen-minute two-host capture is still what would settle
it.

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
narrowed to an exact parameter name beside an OAuth companion. It earned its
keep twice over: the token in that URL is a five-segment JWE, and the JWT
*shape* rule -- three segments, on both sides -- would have replaced its first
three and left 1,059 characters of ciphertext sitting beside a `«redacted»`
marker. The name-and-companion rule took the whole parameter, so the rig's
number is real. The shape rule has since been widened to two-to-four dots.

**Since closed, and how it went wrong first.** The backend's ingest path now
redacts, and `backend/scripts/redact_stored_evidence.py` rewrote the 396
already-stored objects. An independent review of that work then found two
things the run itself could not see:

- The backend had **no OAuth `code` rule at all** -- the heuristic above lived
  only in the rig. The `&code=` in the store was caught by accident, because
  Okta happens to emit a token starting `eyJ`. An opaque authorization code,
  which is the common case, had nothing to stop it. Ported now, and the
  generated extension JS with it, so all three copies agree.
- The three-segment JWT shape left the JWE tails described above in 14 live
  objects, and the script's own success check greps for `eyJ` -- the very
  prefix a partial redaction removes. Both counters read `0 -> 0` and it
  printed a clean bill over surviving ciphertext. The check now looks for a
  marker with base64 still glued to it, which is the shape of that failure and
  cannot be produced by the rule it verifies.

Verified after the second run, by scanning every object in the bucket rather
than trusting the run's own summary -- the first cleanup's summary was the
thing that lied:

```
                     objects   JWT  code=eyJ  severed  AIza  bearer
live (3 tenants)       1,886     0         0        0     0       0
<key>.pre-redaction      396    14        14        0   109       0
```

The live figure covers all 1,886 objects, not only the 396 tracked in
`observation_batches`: roughly 1,490 of them were never touched by the cleanup
at all, and are clean on their own.

**Still open, and the operator's call:** the 396 `<key>.pre-redaction` backups
sit in the same bucket under the same tenant prefix, and they hold 14 JWTs, 14
OAuth codes and 109 Google API keys between them. The rewrite is proven
lossless -- 396/396 identical event counts and order, idempotent byte-for-byte
-- so the backups have done their job and are now the largest credential store
in the deployment. They should be deleted or moved out of the tenant prefix.

### Cost, measured rather than estimated

```
387 gestures read      $0.9459        $0.00244 each
thinking tokens        168,771 of 211,317 billed output   (80%)
three mining passes    $1.9960        $0.0066 + $1.0649 + $0.9245
                       ------
total on this corpus   $2.9419
```

**Two figures here were wrong and are corrected.** The thinking total was
published as 169,246, and the difference of 475 is exactly the thought tokens of
the first mining pass — a mining pass counted inside the reading total. And the
three mining passes were published as **"~$0.02"**, against a real $1.9960. The
first of the three did cost $0.0066: it proposed nothing, on 416 input tokens.
Reading one pass and writing down the number for all three understated mining by
a hundredfold.

That correction matters more than its size, because mining is not a rounding
error on top of reading — it is roughly two thirds of what this corpus cost.

Plan 1 estimated $1.36 for a 2,000-gesture day. Readings alone scale to $4.88 at
$0.00244 each. Mining is the part that was missing: a full-window pass over this
corpus cost **$0.99 on average**, and one pass does not see a day — the rotation
measurement needed ten passes at a constrained budget to put 387 gestures in
front of the model even once. How many a 2,000-gesture day needs is not measured
and is not guessed here; what is measured is that each one costs about a dollar,
so the day's true figure is the $4.88 of reading plus a mining bill of the same
order, not the $0.02 the earlier line implied.

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

## The pool rotates a real day

The corpus fits one window, so `left_out` was 0 and the carry-over pool never
bit. Constraining the budget to 20,000 tokens makes it bite exactly as a
genuine all-tabs day would -- the window then holds 25 to 70 of 387 gestures,
which is the 6-18% a real day produces against the full budget.

No model calls; this is `pack` and the pool alone. Run it:

```
cd new_agent_arch && uv run python scripts/rotate.py
```

```
pass  1: window  25  new-vs-last  25  left_out 362  seen  25/387   6%
pass  2: window  45  new-vs-last  36  left_out 342  seen  61/387  16%
pass  5: window  69  new-vs-last  69  left_out 318  seen 195/387  50%
pass  7: window  55  new-vs-last  55  left_out 332  seen 320/387  83%
pass 10: window  45  new-vs-last  45  left_out 342  seen 387/387 100%

covered 387/387 of a real day in 10 passes
retired without ever being shown: 0
```

**An earlier version of this table was wrong, and the way it was wrong is the
point of committing the script.** It published 100% at pass 7 and a
`new-vs-last` equal to the window on *every* pass. Neither reproduces: coverage
completes at pass 10, and pass 2 shows 45 items of which 36 are new -- nine
carry over. The harness that produced those figures was never committed, so
when a reviewer rebuilt it from the prose and got pass 10, there was nothing to
arbitrate between the two runs. `scripts/rotate.py` is that arbiter now.

Nine of ten passes are disjoint from the one before. The exception is pass 2,
and the mechanism is visible rather than mysterious: an entry shown on pass 1
keeps `pack`'s flat `K_POOL_BONUS` while its `waited` resets to 0, so a strong
item can outrank a waiting weak one exactly once before the waiting term
overtakes it. Rotation is what the two clocks buy, not disjointness -- and the
two claims that carry weight both hold: **387/387 of a real day reaches the
model, and nothing retired without ever being shown.**

Before the two clocks -- `age` counting readings an entry was shown, `waited`
counting passes it was passed over -- the same measurement gave 19% after ten
passes and the identical 468 gestures every time.

The mechanism that made it wrong is worth remembering: one counter cannot mean
both "how long since you were read" and "how long have you waited", because an
entry read six times would then outrank one never seen at all. The first
attempt at rotation made coverage worse -- 6% against 19% -- for exactly that
reason.

## Shape cannot tell one job done twice from two jobs on one screen

The parameter machinery needs pairs: a parameter is what two doings of one job
disagree about, and `identity.resolve` finds those by matching shapes while the
citations differ. The real corpus contains one such pair -- `Create Work Area
NEWTESTS` and `Create Work Area TWOTEST` are the same job with a different work
area name -- and identity called them two jobs.

That is not a threshold that needs moving. Four signals, measured over the
eight real workflows:

| signal | the same-job pair | best different-job pair |
|---|---|---|
| containment over the shape key | 0.47 | 0.46 |
| the same, weighted by how rare each step is | 0.26 | 0.22 |
| containment over filled FIELDS only | 0.50 | **1.00** |
| containment over SCREENS touched | **1.00** | **1.00** |

Plain containment separates them by one point in a hundred. Weighting by rarity
widens that to four, which is better and still not a line anybody could draw.
Fields-only inverts it -- a job with one field is wholly contained by anything
sharing that field, the "half of two against half of twenty" problem
`K_MIN_SHARED_STEPS` exists for, biting hardest where the counts are smallest.
Screens tie, because creating a work area and searching work areas happen on
the same screen.

The cause is structural. `shape_key` keys on `system`, and `system` is a host.
A WMS with fifty screens behind one host makes every job on it share its
navigation, its `Add` and its `Save`, so the entries that distinguish a job are
outnumbered by the chrome that does not.

A combined signal -- screens to narrow the field, shape to discriminate inside
it -- looks promising in these numbers. It is not implemented, and that is
deliberate: **the corpus holds exactly one true-positive pair.** Tuning a
multi-signal matcher against one example is fitting to noise, and this document
has already recorded two heuristics rejected for less.

What would settle it is more pairs, which is the same fifteen-minute capture
everything else here waits on: do one job twice, with different values.

## A mined workflow, as something this system can run

The rig proposes workflows; the backend runs skills. Three modules now join
them, and what they refuse to do is the interesting half.

**`from_rig`** turns a mined step into `UiPlan`s. Over the eight workflows:
all 66 steps produce at least one action, 62 resolve to at least one locator,
57 reach a component query. Of the 165 actions, 118 have a component query as
their strongest rung, 7 text, 6 css path, 1 role-and-name, and 33 have none at
all -- those are the scrolls, which have no target by design.

**`network_from_rig`** builds the other recipe. 30 of 165 steps carry a call,
and six of the eight workflows carry exactly one write apiece -- one POST per
`create`, which is what those jobs are.

Five of those six, rather. The sixth is `Login and Start Recording`, whose
"write" is a POST to `localhost:8000/v1/recordings` -- the SRO console, which
the operator had open in a tab, asking this system's own API to start
recording. Twelve such requests are in the store. The apparatus was captured as
though it were the work, and a mined workflow reported the act of recording as
the write its job performs.

`admit` now refuses this deployment's own API and console ahead of the tenant's
policy, and no operator grant widens them -- which is the difference between
that rule and `exclude_hosts`, since a grant is exactly what widens the latter,
and pressing "observe this page" while looking at the console would switch the
apparatus back on. Configuration could have excluded it and did not, because a
default nobody sets is a default nobody has.

**`version_from_rig`** assembles a `SkillVersion`. All eight build, 165 steps,
every one at `RECORDED`, because nothing about a mined workflow has been
reviewed by anybody.

**`GET /v1/workflows/{id}/evidence`** is what makes those three reachable from
outside the rig's own process. `/v1/workflows` served the citations and
`/v1/gestures` reduces a target to its NAME for a person reading a listing, so
nothing served the target itself and the bridge had to be pointed at a SQLite
column. Cited gestures only: the largest real workflow cites 35 of 387. It
carries the requests beside the gestures and the distinct capture streams,
which is the one input a caller would otherwise reach into a column for and the
one that mis-states whether a skill's values were ever diffed if it is wrong.
A citation whose evidence the store no longer holds is reported in `missing`
rather than dropped.

Complete rather than trimmed, at a known cost: response bodies are 94% of the
7.2 MB of captured requests and the bridge reads none of them yet. They are
served anyway, because assertions are the next consumer -- post-conditions are
built from responses, `unchecked_writes` is a live concern in the skill domain,
and a route called `evidence` that ships 6% of the evidence is the shape of
defect this project keeps finding. The largest workflow is 1.6 MB, all eight
3.4 MB.

### The thesis, in one body

```
POST /data/WM/wm/workAreas?siteId=SG
{"workArea": "$workArea", "workAreaDescription": "$workAreaDescription",
 "warehouseId": "SG", "deltaPriority": null, ...}
```

`workArea` and `workAreaDescription` were derived from two doings of a UI
gesture -- what the operator typed differently on the screen. They are two keys
of the call the screen made. `warehouseId` did not vary and stays a constant.

Bound by KEY, never by scanning the text: a work area named `SG` would
otherwise have rewritten the site id sitting beside it in the same body.

### What it refuses to invent

- **An `ObjectiveKey`.** A `Skill` needs objective type, target system, entity
  type, facility and direction. The rig knows a title, the systems a job
  touched and a shape key. Deriving "an inbound receipt against BLR1" from
  `Create Work Area NEWTESTS` would be a guess wearing the clothes of a
  finding. The version is built; naming what the job is FOR stays a person's.
- **A `RecordingId`.** `Provenance` requires one and the rig has no
  `Recording`. Its nearest equivalent is the capture stream, so the caller
  passes it and this refuses without it. Minting one would lie to
  `from_one_demonstration`, which decides whether a write skill's values were
  ever diffed.
- **A credential.** Measured over all 291 stored requests: the only
  `authorization` header anywhere is on twelve `localhost` calls -- the rig
  talking to its own ingest. Every business call authenticates by cookie and
  the rig captures no cookies, so no plan carries a credential reference. A
  replay depends on the executor's own session. Inventing a SESSION header to
  hang a vault key on would make an unauthenticated plan look authenticated.
  The 544 CSRF headers ARE handled: minted live, never replayed.

### Which way it errs

Two doings of one job inside a single capture stream report as ONE recording,
so a version whose parameters were genuinely proven can still read as
`from_one_demonstration`. That is the strict answer: `values_are_fixed`
follows it and promotion asks more. Understating the evidence costs a
reviewer's time; overstating it promotes something on a diff that never
happened.

### The ceiling that remains

Every version still reports `needs_a_person`, and it is not a rig defect.
`needs_a_person` reads "no network plan and no tool plan", and typing into a
field causes no call -- only the save posts. That is true of any demonstration,
however captured. It lifts the same way it does for a skill induced from a
recording: `map_step_to_tool`.

### Unexercised, still

The eight stored workflows have no parameters, because identity calls the
NEWTESTS/TWOTEST pair two jobs. So the binding path -- screen value to body key
-- is proven by test and by hand against the real POST, and has never fired on
the live store. The fifteen-minute two-host capture is what would close it.

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

Every number above comes from one of these. A measurement whose instrument is
not committed is an anecdote -- the pool rotation table in this document was
published without its harness, and when a reviewer rebuilt it from the prose
they got a different answer with nothing to arbitrate between the two.

```
new_agent_arch/scripts/measure.py     the mining instrument: A/B over evidence sets
new_agent_arch/scripts/rotate.py      the pool rotation table, pack and the pool alone
new_agent_arch/scripts/compare.py     the rig's workflows against the pipeline's
new_agent_arch/scripts/trial.sh       the week-long capture trial
new_agent_arch/evidence/constructed/  the seven constructed TMS gestures
backend/scripts/mirror_backfill.py    replays stored batches into the rig
backend/scripts/skill_from_rig.py     the bridge, end to end over HTTP, and --adopt
```

Two things they need. `new_agent_arch/rig.db` is a scratch database rebuilt
from captured batches and is not in the repository; `mirror_backfill.py` is
what rebuilds it. And the bridge scripts talk to a running rig, which has to be
one recent enough to serve `/v1/workflows/{id}/evidence` -- an older one
answers 200 on the listing and 404 on the evidence, and `skill_from_rig.py`
says so rather than raising.
