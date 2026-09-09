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

**The one thing it structurally cannot catch, measured.** `validate` checks that
every step cites evidence, that the evidence exists in the window, that a step
naming a system cites a gesture on it, and that the workflow claims no system
its citations never touched. What it cannot check is whether the step's PROSE
matches the evidence it points at: "type the code" citing only clicks is
internally valid and still fiction.

Measured over all 66 steps of the eight real workflows, comparing the verbs in
each step against the kinds of the gestures it cites: **zero mismatches.** The
model's prose agrees with what the gestures actually were.

The obvious way to close the gap should not be built, and the same measurement
says why. A verb check flagged two of the 66 immediately, and both were the
check being wrong:

```
'Navigate to the Warehouse Equipment Type tab.'   cites ['click']
'Save the new equipment type record.'             cites ['click', 'click']
```

`Type` is the verb the model uses AND a noun in this warehouse's vocabulary.
Whole-word matching does not help, because the noun IS the word. This is the
third time this project has met the same trap -- `pin` inside `shippingPhone`,
`test` inside `Test Drive LLC` -- and the first two each cost real evidence
before anybody measured. A check with a 3% false-rejection rate on a corpus
where the true rate is zero would discard real workflows to catch nothing.

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

## A run performs

Verification 6 and 7 need two things this work could not supply: the operator's
own Chrome with the extension pointed at the rig, and a WMS session. So the
part that can be measured unattended was measured, and the part that needs a
person is written down below as the measurement it is, with the commands.

### The chain, against a fake browser (measured)

`new_agent_arch/scripts/dry_run.py` starts every workflow in the store dry, over
`POST /v1/runs`, against a `FakeChannel` that answers every look and every
perform as a success and an asker that is not a model: it plans `ui.perform`
with the primary gesture's own kind and holds every verification. It works on a
copy of `rig.db` in a temp directory — the live file is opened read-only and
still holds zero runs afterwards, which the script's last line checks.

```
cd new_agent_arch && uv run python scripts/dry_run.py
```

| workflow | steps | withheld | outcome | cost | verdicts |
|---|---|---|---|---|---|
| Login and Start Recording | 5 | 2 | held | not asked | held:3 withheld:2 |
| Create a Warehouse Equipment Type | 7 | 1 | held | not asked | held:6 withheld:1 |
| Create Work Area NEWTESTS | 8 | 2 | held | not asked | held:6 withheld:2 |
| Create Work Area TWOTEST | 8 | 1 | held | not asked | held:7 withheld:1 |
| Search and Filter Work Areas | 2 | 0 | stopped | not asked | held:1 skipped:1 |
| Create Work Area Operation NEWTEST4 | 1 | 0 | stopped | not asked | skipped:1 |
| Create Carrier Cross Reference for Test Drive LLC | 10 | 2 | held | not asked | held:8 withheld:2 |
| Create Work Activity TEST1 | 7 | 2 | held | not asked | held:5 withheld:2 |

8 workflows / 48 steps / 10 withheld / held:6 stopped:2. Both stops are the
runner refusing to walk past a step nobody watched succeed: *Search and Filter
Work Areas* stopped at step 2 of 11 and *Create Work Area Operation NEWTEST4* at
step 1 of 10, both `skipped` — "no cited gesture can be acted on" — and a run
does not continue past one. Nine steps of each were never reached. Cost is not `$0.0000`: **no model was asked**, so these records carry
no tokens at all, which is the absence of a bill rather than a cheap run.

The ten withheld writes are printed in full by the script — planned kind, the
locator list the payload carries, and the recorded `method`, `url` and `body`.
Five are real WMS mutations — `POST …/wm/workAreas` twice
(`{"workArea":"NEWTESTS"…}` and `{"workArea":"TWOTEST"…}`), `…/wm/equipmentTypes`,
`…/wm/carrierCrossReferences`, `…/wm/activityCodes` — and five are the incidental
POSTs the pages make: two `sessionKeepAlive` calls, a performance-entry batch, an
analytics beacon, and the recorder's own `finish` call. Exactly one `«redacted»` marker survives into
them — a Google analytics cookie inside a query string — and it is printed as it
stands rather than re-redacted; a withheld record carries no headers at all, and
what a plan does send goes through `wire.headers_without_markers` first.

**What that proves:** the chain from the door to the record. `POST /v1/runs`
claims the run and answers 202; the runner reads the row back, builds the
allowlist and the locators from the cited evidence, asks a planner, sends over
the channel, verifies, bills, and saves after every step;
`GET /v1/runs/{id}` reads the whole thing back, withheld writes included. The
dry-first rule holds over the steps these runs reached: every one of those whose
evidence carries a mutation was withheld and shown. It says nothing about the
steps a stopped run never got to. The script names those: of the nine *Search
and Filter Work Areas* never reached, one carries
`POST bf56-kms-wms-web-np2.jdadelivers.com/refs/data/api/v1/rp/admin/sessionKeepAlive`
— never withheld, never shown — and *Create Work Area Operation NEWTEST4*'s nine
carry no mutation at all. The origin allowlist is built and checked on every plan, but no step of
these eight was refused, so that path is proven by the suite rather than here.

**What it does not prove**, and nothing below should be read as if it did:

- **No real browser.** Nothing matched a locator against a DOM. `matched_by:
  "component"` was asserted by the fake, so the health signal that says a step
  is about to break is untested against a real page.
- **No WMS.** No session, no server; no write left the process and no read came
  back. `verify`'s strongest rung — a confirming read of hidden state — never
  ran: none of the eight workflows declares a parameter, so every run's `values`
  was `{}`, and that rung needs a value to look for.
- **No model.** Both the plan and the verdict were fixed answers. Whether Flash
  picks the right command for a step, whether it navigates when it is on the
  wrong page, whether Pro rescues a step Flash lost, and whether the verifier can
  tell a failure from a green toast are all unmeasured.
- **No parameters fired live.** With no declared parameters there was nothing to
  substitute, so the form's prefill and the value-into-control path are exercised
  by tests only.

### The real one, for whoever has the browser (not yet performed)

1. **Start the rig.** `cd new_agent_arch && make serve` — `uvicorn rig.api:app`
   on `:8100`, reading `new_agent_arch/.env`. With no `RIG_GEMINI_API_KEY` it
   refuses at startup and names the variable; a run needs a real key, since the
   planner and the verifier are the model.
2. **Point the extension at it.** `chrome://extensions` → this extension →
   *Extension options* → the **Rig** section: **Rig URL** `http://localhost:8100`,
   **Rig token** the value of `RIG_INGEST_TOKEN` from `new_agent_arch/.env`.
   Save. The extension dials `ws://localhost:8100/v1/agents/<device>/commands`
   on its own; nothing on the rig can reach into a browser that has not dialled.
3. **Confirm the rig sees the browser.** Put the token in the shell first —
   `set -a; . new_agent_arch/.env; set +a` — or paste its value into the header
   by hand; then
   `curl -s -H "Authorization: Bearer $RIG_INGEST_TOKEN" http://localhost:8100/v1/devices`
   must list one device id. That id is what the run form's picker offers; an
   empty list means the socket is not up, and no run can be started (`409`).
4. **Sign in to the WMS in that same Chrome** —
   `https://bf56-kms-wms-web-np2.jdadelivers.com` — and leave the tab open. The
   run drives that session; there is no server-side login.
5. **Dry run.** Open `http://localhost:8100/`, find **Create Work Area
   NEWTESTS**, press **run**, pick the device, leave **live** unticked, start.
   The page polls the run and, under *what a live run would have sent*, prints
   the withheld `POST …/wm/workAreas`. Read it before going further: it is the
   whole point of the first execution being dry.
6. **Record what happened.** Per step: `verdict`, `verdict_by`, `matched_by`,
   `before_url`/`after_url`, and whether `stale` was set (a step that only ever
   matched on `css_path` is a step about to break). Then the withheld POST, the
   run's `cost_usd` (and `unpriced`), and the extension's own `sro.lastError`,
   which the panel shows as a *Last error* card.
   `curl -s -H "Authorization: Bearer $RIG_INGEST_TOKEN" http://localhost:8100/v1/runs/<run_id>`
   is the same record the page is drawing.
7. **Then live.** Same form, **live** ticked. Watch four things while it runs:
   the **band across the page** that says a run is driving it (it takes itself
   away if nothing refreshes it); the panel's run card, one row per step, where
   `✓` is held, `⏸` withheld, `✗` failed or refused, `○` not reached — and the
   **Stop this run** button, which is the only stop there is; the rig holding
   commands while you type (the extension sends `busy`, and the rig waits out
   part of the deadline rather than fighting for the keyboard); and whether the
   supplier of the value — here the work area — actually exists in the WMS
   afterwards. A second press against the same browser is refused with `409`
   while the first run is still going: one browser, one hand.
   Then the ask, which is the part with a known gap. A step the verifier will
   not pass is planned once more by Pro — one rescue, and a `navigate` does not
   spend it — and if it still does not hold the run's outcome is `stopped` and
   the record says which step and why. **Nothing notifies anybody.** The page
   showing `stopped` is the whole of "stop and ask", so whoever presses run is
   the person who has to still be looking. Record which rung the failing step
   reached (`planned_by`), what the rescue cost, and how long the run sat
   `stopped` before it was noticed.
8. **The boundary.** A step whose plan names an origin the job's own evidence
   does not is `refused` before anything is sent, and the record says
   `<origin> is not a system this job's evidence names`. Note what the allowlists
   actually are, because it changes the measurement the plan expected: *Create
   Work Area NEWTESTS* and *Create Work Area TWOTEST* are the **same origin**
   (`https://bf56-kms-wms-web-np2.jdadelivers.com`), so pointing one job at the
   other's write is not a cross-origin refusal and will not produce a `refused`
   step. **Five** of the eight workflows allow that one host and nothing else;
   **three** allow more. *Login and Start Recording* names six
   (`workspace.google.com`, `b2clogin.com`, the Keycloak host, `localhost:3000`,
   `localhost:8000`, `analytics.google.com`), and *Create Work Area NEWTESTS* and
   *Search and Filter Work Areas* each allow a second host their evidence names,
   `https://zmpa6jmjcthsg-hgatahc3adfqe7cq.z01.azurefd.net`. So the job the
   recipe above starts has two permitted origins, not one — and both are its own,
   so a plan naming either is allowed and neither is a refusal. A live `refused`
   cannot be provoked from the form at all: the planner chooses the origin, and
   every origin it can read out of this evidence is on the list. What can be recorded is the negative: **no** step of a live run
   ever sent to an origin outside the job's list. The positive is held by
   `tests/test_runner.py::test_an_origin_outside_the_evidence_is_refused_before_it_is_sent`,
   and would be measurable live only against evidence that spans two hosts —
   which is the same two-system capture verification 1 is still waiting for.

Until this section is rewritten with those numbers in it, **verification 6 and 7
are not done.** The dry run above proves the chain; only the real one proves the
claim.

## An offer lands

The rig serves the shape of every job it can prove; the extension keeps the last
few gestures on the tab, matches them against those shapes, and — on the second
gesture — offers to finish what the operator has started. Yes starts the run
from that step, the panel draws it live, and a write on a job that has not
earned its autonomy waits as `awaiting` until somebody presses **Approve**.

What can be measured without a browser is measured below: what the rig actually
serves, and whether two gestures are enough to tell this corpus's jobs apart.
What cannot is the offer itself — a card landing on a real gesture stream — which
needs a person, a Chrome with the extension in it, and a WMS session. Its
commands are at the end of this section, with the fields to fill in and the
query that settles the constant.

### What the rig serves (measured)

`scripts/dry_run.py` asks `GET /v1/shapes` on the same in-process app, before it
starts a single run, so the per-workflow held gate reads a store with no runs in
it — which is what a rig looks like the first time an extension dials it.

```
cd new_agent_arch && uv run python scripts/dry_run.py
```

```
SHAPES -- what the extension matches a live tail against

shapes served: 8 of 8 workflows

Login and Start Recording: 13 triples; parameters: none declared
    distinct at two

Create a Warehouse Equipment Type: 12 triples; parameters: none declared
    shares its first two steps with: Create Work Area TWOTEST, Create Carrier Cross Reference for Test Drive LLC

Create Work Area NEWTESTS: 20 triples; parameters: none declared
    distinct at two

Create Work Area TWOTEST: 14 triples; parameters: none declared
    shares its first two steps with: Create a Warehouse Equipment Type, Create Carrier Cross Reference for Test Drive LLC

Search and Filter Work Areas: 20 triples; parameters: none declared
    distinct at two

Create Work Area Operation NEWTEST4: 16 triples; parameters: none declared
    distinct at two

Create Carrier Cross Reference for Test Drive LLC: 22 triples; parameters: none declared
    shares its first two steps with: Create a Warehouse Equipment Type, Create Work Area TWOTEST

Create Work Activity TEST1: 15 triples; parameters: none declared
    distinct at two
```

**Shapes served: 8 of 8 workflows.** Four gates stand between a workflow and
being served, and all eight pass every one: not unproven; not a workflow that
has run and never held; citing gestures that still exist; and starting on a host
its own allowlist holds. A shape is (system, control identity, kind) per cited
gesture, in step order: the same triple `identity.py` resolves on, generated
into the extension so the two cannot drift. One count per shape, because
`shapes.py` drops the scrolls before it serves one — for the reason
`recognise.js`'s `tailWith` drops them before it writes the tail: a triple that
can never appear in a tail is a triple no shape can be matched on. The shapes as
served run from 12 triples (*Create a Warehouse Equipment Type*) to 22 (*Create
Carrier Cross Reference for Test Drive LLC*).
Nothing in a shape is a typed value — control identities, hosts and parameter
*names* only — which is why the block above can be printed at all.

**Every one reads `parameters: none declared`.** The same gap *A run performs*
records: no workflow in this corpus declares a parameter, so the card has no box
to draw, `valuesFrom` has nothing to lift out of the tail, and the whole
value-into-control path — prefill, the blank-is-not-a-value rule, the missing
list, **Yes** disabled until the boxes are filled — is exercised by tests and by
nothing else. An offer on this corpus is a bare "shall I finish this".

**Three of the eight share their first two triples**: *Create a Warehouse
Equipment Type*, *Create Work Area TWOTEST* and *Create Carrier Cross Reference
for Test Drive LLC* — three jobs that begin with the same two gestures on the
same host. The other five are distinct at two. The rig serves scroll-free
shapes, so that comparison is made on the very triples the extension walks;
*Create Work Area Operation NEWTEST4*, whose first triple used to be a scroll
and which therefore could not be offered at any `k` at all, is now distinct at
two like the rest. Dropping the scrolls does not dissolve the collision: the
same three jobs share their first two walkable triples. That is the number that
says what `K_OFFER_AFTER = 2` is worth on this corpus. `match()` offers only on a
prefix that is unique — two shapes matching at the same `k` end the tail with
the same `k` triples, so the tail holds nothing that says which job it is —
which means a tail two gestures long into any of those three names none of
them. **Those three of the eight are first offered at `k = 3`, not `k = 2`,
and no offer a fresh rig makes on this corpus names the wrong job.** That
sentence is now measured rather than argued. `make offer-replay` has the rig
write each job's demonstrated gestures beside the shapes it serves, and feeds
them one at a time through the same `tailWith` and `match` the service worker
runs -- no browser, no model, the corpus against itself:

```
job                                                gestures  offered at  k  named
Login and Start Recording                                14           2  2  itself
Create a Warehouse Equipment Type                        13           3  3  itself
Create Work Area NEWTESTS                                22           2  2  itself
Create Work Area TWOTEST                                 18           4  3  itself
Search and Filter Work Areas                             35           2  2  itself
Create Work Area Operation NEWTEST4                      21           3  2  itself
Create Carrier Cross Reference for Test Drive LLC        26           3  3  itself
Create Work Activity TEST1                               16           2  2  itself
8 jobs replayed against 8 served shapes at K_OFFER_AFTER = 2: 8 offered as themselves, 0 offered as another job, 0 never offered
```

Four jobs are offered on their second gesture and NEWTEST4 -- unofferable
before the shapes went scroll-free, its first gesture being a scroll -- on its
third; that is five at `k = 2`. The three that collide need a third walkable
gesture, `k = 3`: two are offered on their third and TWOTEST on its fourth,
because its third gesture is a scroll the tail drops. What this does not measure is a real gesture stream: the recorder's
live triples on a page that has been through a reload or a frame are the
recipe's question, not this table's. The constant was not moved on this evidence. Whether an operator would rather see a wrong title early
or a right one later is not settled by a collision count; it is settled by what
becomes of the offers, which is the `offers` table's own column and the last
thing the recipe below asks for.

### What the suites prove

- **The matcher.** `recognise.test.mjs`: nothing offered on one gesture; two
  gestures offer the job whose prefix they are; a shared first step resolves on
  the second; a shape on another origin is never matched; scrolls do not break a
  prefix; the tail is bounded at `K_TAIL`; a job already finished is not offered
  back; a prefix two jobs share offers neither and the gesture that separates
  them is the gesture that offers; a secret control and a blank field
  each leave the parameter missing; going another way ends the offer.
- **One identity, two languages.** `shape.generated.test.mjs` — the extension's
  triple is generated from the rig's own identity source and agrees with the
  shared fixture, so a shape the rig serves means the same thing on both sides.
- **Starting mid-job.** `test_a_run_started_mid_job_starts_on_the_page_of_the_step_it_starts_at`
  and `test_a_from_step_past_the_job_is_refused`.
- **Approval.** `test_a_live_write_waits_for_approval_and_goes_out_when_it_comes`,
  `test_a_write_nobody_approves_stops_the_run` (`K_APPROVAL_WAIT_S`, then the
  run stops), `test_approve_releases_a_waiting_write`,
  `test_approve_with_nothing_waiting_is_refused`.
- **Earning.** `test_effects.py`: `K_EARNED_RUNS` live runs whose every write
  verified **by state** earn autonomy; a screen-only verification is not an
  effect; one unverified write does not count; a failed write starts the earning
  again; a dry run earns nothing.
- **The card.** `src/panel/ledger.test.mjs`: a rig offer asks for what is
  missing and cannot start until it has it (**Yes** disabled while a parameter is
  blank); an arrival nudge offers to do the job from the start; the press is
  handed the values that were typed in; one press ends the card, so a refused
  offer cannot then be started; a title or a value that looks like markup is
  shown as the string it is.
- **The offer's life and the live panel.** `offering.test.mjs` and
  `offering-worker.test.mjs`: two gestures become one offer; an open offer is
  replaced only by a longer prefix; a tail that goes elsewhere ends it as
  diverged; nothing is offered while this browser is performing a run; **Yes**
  starts the run; a dropped offer cannot then be started; the run is drawn while
  it runs, including one parked on an approval; **Approve** is refused for a run
  this browser is not driving.

### What is not proven

- **No offer has ever landed on a real gesture stream.** Every test above feeds
  the matcher a tail built by hand. Whether the recorder's live gestures produce
  the triples the shapes were built from — on a page that has been through a
  reload, a frame, a slow render — is untested outside the fixtures.
- **The panel has never polled a live rig.** The run card's poll, its rows, its
  glyphs and its **Approve** button are driven by a fake worker in the suite.
  The rig's own page has, once (2026-09-06, Playwright against a rig on a
  scratch database with one batch and two registered browsers): the three
  views cycle, the spend line and the browsers strip draw, the two-press
  revoke lands and the strip redraws the browser as revoked on the next
  tick, the audit view lists both browsers. Two warts found and fixed: the
  since heading in UTC beside a local picker, and a favicon 404 on every
  load. Nothing that needs a model -- a parked run, an offer, a job card --
  was on that page, because the rig had a fake key.
- **The value of `K_OFFER_AFTER` against a live stream is unmeasured.** Replayed
  against its own evidence every job is offered as itself; whether a person
  minds waiting for a third gesture on three of the eight is what the offers'
  fates will say, not the replay.
- **No parameter has ever been lifted from a live tail.** Four of the eight
  jobs declare eleven between them now (see *A real key, one afternoon*
  below); replayed, ten of the eleven are lifted by the end of a doing and one
  at the moment of the offer. A live tail is still untested.
- **Nothing here proves earning end to end.** `K_EARNED_RUNS` live runs whose
  writes verified by state have never happened against a real WMS; the counter
  has only ever been fed by tests.
- **Nothing here says one job follows another, and the query that said so
  was wrong about why.** Asked of the corpus on 2026-09-06 by placing each
  job's *cited* gestures on its stream, the eight jobs appeared once each,
  hours to days apart. The same afternoon a real mining pass proposed
  thirteen doings from the same 387 gestures and learned seven values of
  `operationCode` and four of `activityCode`: the corpus holds repeated
  doings, and the citations name one of them. A chain needs the doings
  stored as occurrences, which the resolver does not do (it learns the
  parameters and discards the proposal); the evidence exists, the record of
  it does not.
- **The sight rung has never looked at a real screen.** Every picture it has
  answered on is the fixture's eight bytes; whether Pro returns a usable
  centre for a moved control on a real WMS page, and how often, is unmeasured.
  The run record will say: `matched_by: sight` on the step, and the job's
  stale mark.

Say the last one plainly, because it is a design decision and not a defect: **a
job whose writes can only be verified by screenshot never earns and asks every
time.** The belt that counts towards autonomy is a confirming read of state. A
job the rig can only watch succeed on a screen will pause on every live write,
for as long as it exists, on purpose.

### A real key, one afternoon (measured, 2026-09-06)

A rig on a copy of the corpus database, a real Gemini key, and the page in a
real browser. Every number below is on record in that copy
(`new_agent_arch/rig.learned-2026-09-06.db`, untracked); the repository's
`rig.db` is as it was.

| what | result | cost |
|---|---|---|
| chat door, first sentence | 400: `additionalProperties` refused by the Developer API; the door had never met it | $0.00, unpriced |
| chat door, after the schema fix, 3 sentences | every job null: titles carry one demonstration's values | $0.01 |
| chat door, after the instruction says a job is a kind of work, 5 sentences | 5 of 5 name the right job, incl. null for a flight to Paris | $0.01 |
| mining pass, default output ceiling | cut mid-string at 17,313 chars, filed "not json" | $1.16 |
| mining pass, 65,536-token ceiling | 13 proposed, 0 kept: all resolved into the 8 known; 11 parameters learned on 4 jobs | $1.14 |
| served shapes after the pass | every learned parameter `at: None` -- placed by no step | -- |
| after placing by control name | 10 of 11 indexed | -- |
| offer replay, tail of 12 | 8 of 8 named; values lifted by end 0 of 11 | -- |
| offer replay, tail of 40 | 8 of 8 named; 1 of 11 at the offer, 10 of 11 by the end | -- |
| the page: jobs, run form | 8 cards; TWOTEST's form draws 5 fields prefilled from the last doing | -- |

What it changed: the chat door's schema and instructions; a 65,536
output-token ceiling on every call and a cut-off answer named as such;
learned parameters placed in the shape by the control that typed them; a
tail of 40; the replay counting values. What it did not reach: a live tail,
a run (no browser was connected to that rig), an offer landing, the sight
rung on a real screen.

### The measurement, for whoever has the browser (not yet performed)

1. **Start the rig.** From `new_agent_arch/`: `make serve`. Without
   `RIG_GEMINI_API_KEY` it refuses at startup and names the variable; the
   planner and the verifier are the model, so a run needs a real key. Stay in
   `new_agent_arch/` for the shell commands below.
2. **Connect the extension to the backend first.** `chrome://extensions` → this
   extension → *Extension options* → **Connection**: **Backend**
   `http://localhost:8000`, **Credential** the token
   `make token tenant=acme principal=you` issued → **Connect**. This is not
   optional decoration for the rig: registering with the backend is the only
   thing that sets this browser's device id, and the rig socket dials
   `/v1/agents/<device>/commands` with that id. With no device id the rig
   channel is not dialled at all, silently.
3. **Then point it at the rig.** Same options page, the **Rig** section:
   **Rig URL** `http://localhost:8100`, **Rig token** the value of
   `RIG_INGEST_TOKEN` from `.env` → **Save**. The extension dials the rig;
   nothing on the rig reaches into a browser that has not dialled.
4. **Confirm the rig sees the browser.** Put the token in the shell first —
   `set -a; . .env; set +a` — then
   `curl -s -H "Authorization: Bearer $RIG_INGEST_TOKEN" http://localhost:8100/v1/devices`
   must list one device id. An empty list means the rig socket is not up, and
   the two ordinary reasons are the two above: the browser never registered with
   the backend, so it has no device id to dial with, or the rig fields are empty.
   Until that list has an entry, no offer can start anything.
5. **Sign in to the WMS in that same Chrome, and watch the tab.** Open the side
   panel beside the WMS tab and press **Watch this tab** (if the site was
   excluded the same button reads `Watch <host> anyway`). Nothing is offered on
   a tab that is not watched — `considerOffer` returns before it looks at
   anything else — so an unwatched tab produces silence, not a wrong offer. The
   run drives this session; there is no server-side login.
6. **Start the work area job by hand.** Do the first gestures of *Create Work
   Area NEWTESTS* yourself, as if the rig were not there. **Expect the card on
   the second gesture.**
7. **Press Yes, finish it.** Watch the panel's run card fill in, one row per
   step, while the run walks the rest of the job from the step you had reached.
8. **Approve the save.** The first live write parks as `awaiting` and the row
   offers **Approve**; press it and watch the write go out.
9. **Do it twice more** — three live runs whose writes verify by state — and
   then a fourth. **The fourth should not ask.**
10. **Then do the same over *Create Work Area TWOTEST*.** *NEWTESTS* is
    `distinct at two` and cannot show the collision at all: whatever it does,
    the offer on it is the only candidate. *TWOTEST* is one of the three that
    share their first two walkable triples, so it is the run where a wrong
    title can actually appear — and on a rig where none of the three has held
    yet the tie goes by served order to *Create a Warehouse Equipment Type*.
    Whether the card says that or says *TWOTEST* is the whole measurement.

Record, for each of the runs:

- how many gestures went in before the offer appeared;
- how many seconds from the last gesture to the card;
- whether the offer named the right job — on the *TWOTEST* passes this is where
  the three-way collision above shows, or does not;
- how the run ended — held, stopped, or diverged out from under itself;
- and for the fourth: whether it asked for approval at all.

Then, after a day of ordinary work with the extension connected, read each
job's card on the rig page: its history line ends `offers: 2 accepted, 1
diverged` -- the five fates, counted, only the ones that happened. The same
numbers for the whole tenant, if a query is nearer to hand:

```
sqlite3 rig.db "select fate, count(*) from offers group by fate"
```

Every offer the extension made is in that table under one of five fates
(`rig/offers.py`): **accepted** — Yes was pressed and a run started;
**dismissed** — No thanks; **did_it** — the operator made the job's write
themselves while the card was still asking; **expired** — the card's lifetime
passed unanswered; **diverged** — the tail stopped matching the prefix, so the
offer was for a job they were not doing. **The share of `diverged` is the number
that decides whether `K_OFFER_AFTER` moves.** A collision count says two
gestures *can* be ambiguous; the `diverged` share says how often being offered
after two actually guessed wrong in front of somebody. That is verification 7,
and nothing short of a day of real gestures produces it.

Until those runs and that table are written down here, **the offer is proven in
tests and in nothing else.**

## Verification of the whole

| # | claim | result |
|---|---|---|
| 1 | suite green, three gates clean | 381 passed; `ruff check`, `ruff format --check`, `mypy src` clean |
| 2 | a workflow spans two systems, every step citing gestures that exist | **not shown on captured evidence — it has one system.** 6/6 on constructed two-system evidence, every citation valid |
| 3 | re-mining adds no workflow | yes, on real output: second pass kept 0 |
| 4 | two occurrences of one job resolve `same_job` | 33 of 57 proposals folded onto an existing workflow, mostly by shape |
| 5 | nothing stranded | 0 on every pass |
| 6 | an invented citation is rejected and named | yes, plus four other tampers each under its own reason |
| 7 | an over-long window reports its skew | exercised now, by constraining the budget: `scripts/rotate.py` drives `left_out` to 318–362 and the pool covers 387/387 in ten passes. At the full budget the corpus still fits in one window, so this remains unexercised on unconstrained real evidence |
| 8 | cost is known, beside plan 1's $1.36 | $2.9419 for this whole corpus — $0.9459 to read 387 gestures and $1.9960 for three mining passes. Scaled to a 2,000-gesture day: $4.88 of reading plus a mining bill of the same order. See the cost section; the earlier per-day figures here predated both the thinking-token accounting and any measurement of mining |

## Reproducing this

Every number above comes from one of these. A measurement whose instrument is
not committed is an anecdote -- the pool rotation table in this document was
published without its harness, and when a reviewer rebuilt it from the prose
they got a different answer with nothing to arbitrate between the two.

```
new_agent_arch/scripts/dry_run.py     the whole run loop against a fake browser, no model
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

## The backend runs the whole chain — 2026-09-09, and what is still open

The rig had done all of the above. **The backend had never done any of it.**
Four passes over the ported miner, against the real Postgres and the real
Gemini, are the first end-to-end evidence on this side. What follows is the
measurement and, more usefully, the list of what it did not settle.

Three things were unbuildable or unwired when the day started, each found by
running the system rather than by a test:

- **`container.asker` did not exist.** `mining_pass.mine` and `run_workflow`
  both take an `Asker`, the port and `GeminiAsker` were ported by plan 2, and
  the composition root was never told about either. Neither could be
  constructed at all — `AttributeError` before a single call. Fixed, `e32e478`.
- **Ingest never reached the evidence plane.** `correlate` and `add_gestures`
  had no caller anywhere in `src/`; uploads stopped at `observation_batches`.
  397 batches and 4,661 events were in the blob store and 0 gestures in the
  table. Fixed, `f8b218f`; `backend/scripts/backfill_gestures.py` replayed 266
  `acme` batches into **507 gestures, 0 failures, 0 unreadable events**.
- **`add_orphan_request` and `add_orphan_page` had no caller either** — the
  same defect, one layer over, wired in the fix round. A click whose XHR landed
  in the next batch had been losing its call permanently.

### The four passes

| # | proposed | kept | rejected | learnt | cost | note |
|---|---|---|---|---|---|---|
| 1 | 0 | 0 | 0 | 0 | $0.0090 | empty store |
| 2 | 0 | 0 | 0 | 0 | $1.9984 | **truncated at `K_EFFORT="high"`** |
| 3 | 3 | 2 | 0 | 0 | $0.9277 | first workflows; `lopsided=True` |
| 4 | 4 | 2 | 0 | **3** | $0.4406 | coverage 0.90, `lopsided=False` |
| 5 | 1 | 0 | **1** | 0 | $0.3574 | hallucinated citation; coverage 0.0 |

**`K_EFFORT = "high"` truncated the Pro model on the first real day**: 204,747
in, 65,522 out, the answer cut after 2,610 tokens, $2.00 and nothing kept. The
constant's own docstring had recorded that trap for `gemini-3.8-flash` and it
was never applied to the model actually configured. At `"medium"` the same
evidence answered in 6,041 output tokens for $0.93 and kept 2 of 3.

**`K_WINDOW_TOKENS` did not guard the boundary it exists for.** `tokens()`
counts four characters to a token; the measured ratio on this evidence is
**2.36** — 481,566 characters estimated at 120,438 and counted by Gemini at
204,333, a 1.697× under-count. A window filled to 150,000 shipped 204,747 and
crossed the 200,000 line where Pro's input price doubles. At 100,000 the same
day packs 405 of 507 and ships **164,028 measured**.

**Parameter learning ran for the first time**, on pass 4, and needs two doings:

```
Create a Work Operation   operationCode     ['NEWTEST4', 'AITESTNE9']
                          longDescription   ['test4', '9 test']
Create a Work Area        description       ['testing zone', 'test 7']
```

### Against the acceptance criterion, quoted as it is written

The spec asks for **"8 of 8 named as themselves, 10 of 11 values by the end."**
The state is **4 of 8 workflows and 3 of 11 values**. The replay names 2 of 2
of the jobs it has, which is a shrinking denominator and not a pass — it was
reported as one once, and that is why this line is here.

## Open, and what would settle each

1. **Does `seen_values` widen on a third doing?** Pass 5 was meant to answer it
   and could not: its single proposal was rejected, so `resolve()` never ran.
   Unsettled. *Settled by:* a pass that reaches `same_job` on a job that already
   has parameters.
2. **How often does the model invent a citation?** One in eight proposals so
   far — `ges_a1ac645771bdd705ea5ba4648f3f8247c`, 37 characters where real ids
   are 36, sharing nothing with any real id. `validate` caught it and the whole
   workflow was refused, which is the guard working; the rate is what nobody
   knows. *Settled by:* the rejection count over a run of passes, which
   `mining_passes.rejected` now carries.
3. **How wide is pass-to-pass variance?** Pass 4 read coverage 0.90 and
   `lopsided=False`; pass 5 read 0.0 and `True`. Same evidence, same model,
   same settings. Three passes cannot tell a lucky one from an unlucky one.
4. **Would network-first parameter learning be better?** ADR 005 ranks
   `network calls > accessibility tree > narration > video` and execution obeys
   it — `network_from_rig.py` reads request bodies twenty times. **Learning does
   not:** `domain/skill/learned.py` never reads `gesture.requests`, taking
   parameters only from what was typed into a UI control plus the model's echo.
   The first measurement says it is not a straight win, which is why it is open
   rather than done:

   | workflow | UI fields | body fields |
   |---|---|---|
   | Create a Warehouse Equipment Type | 4 | 7 |
   | Create a Work Operation | 3 | **0** |
   | Create a Carrier Cross Reference | 2 | **58** |
   | Create a Work Area | 8 | 9 |

   One workflow has no usable body at all — ADR 005's own named exception — and
   one has 58 fields, most of them constants a variance filter would drop. So
   the answer is a **union**, not a replacement. *Settled by:* implementing both
   channels behind the existing across-doings diff and comparing
   `learned_parameters` before and after, which is now recordable.
5. **Is a body-derived parameter safe?** Bodies pass `redact_body`, which
   reports *shapes*; typed values report *field names*. `typed_values` refuses
   the **whole gesture** when `is_secret()`. A body path must ask the same
   question or a password field that was never typed returns through the JSON.
   *Settled by:* a test, not an argument.
6. **Two miners, no reconciliation.** `MineObservations` reads `observations`
   and writes `task_candidates` (53 rows); `mining_pass.mine` reads `gestures`
   and the pool and writes `workflows` (4 rows). Neither reads the other's
   tables. Phase 7 deletes the first. *Settled by:* the shared-day run now
   written into the spec's *Verification* as a precondition on *Deletions*.
7. **Steel's remaining job.** The extension carries the operator's own session,
   so it needs no stored credential — which Steel does. ADR 009 keeps Steel for
   unattended work and live view, and that still holds. What is now doubtful is
   Steel's **capture** half: passive capture comes from the extension, and
   `test_steel_capture.py` is excluded from every gate. *Settled by:* the same
   shared-day discipline before anything is removed.
8. **The extension cannot call two of the doors that were built for it.**
   `/v1/shapes` and `/v1/offers` go through `rigHeaders()`, documented as
   sending *"none of the backend's headers"* — and `X-Device-Secret` is one.
   `shapes()` gets a 404 and returns `[]`; `reportOffer()` gets a 403 **and has
   no status check at all**, so every offer fate would be lost silently. Phase 5.
9. **`run_workflow` still has no production caller.** The whole right half of
   the loop — perform, verify, earn autonomy — is built, reviewed, and reachable
   by nothing. Phase 4b.

## Those nine, re-checked against the running system — 2026-09-09, later

Every line below was read off the live store or the source, not off the section
above. **Nothing is fully closed. Two moved, one of them decisively.**

### The route exists now, and it works

`POST /v1/mine` reached the model path over HTTP for the first time —
`backend/scripts/probe_mine_route.py`, through the real ASGI app and the
container the application builds for itself, against real Postgres and a real
Gemini call. 200, a `mining_passes` row written, and the wire body matching that
row on both `learned_parameters` and `cost_usd`. Before today every mining
figure this document quotes came from a script calling `mine()` directly.

### Seven passes over the same 507 gestures

| started | proposed | kept | rejected | learnt | cost | coverage | lopsided |
|---|---|---|---|---|---|---|---|
| 09-08 18:21 | 0 | 0 | 0 | 0 | $0.0090 | 0.0 | yes |
| 09-08 18:34 | 0 | 0 | 0 | 0 | $1.9984 | 0.0 | no — **truncated** |
| 09-08 18:43 | 3 | 2 | 0 | 0 | $0.9277 | 0.4 | yes |
| 09-09 07:30 | 4 | 2 | 0 | 0 | $0.4406 | 0.9 | no |
| 09-09 07:57 | 1 | 0 | **1** | 0 | $0.3574 | 0.0 | yes |
| 09-09 10:37 | 1 | 0 | 0 | 0 | $0.3421 | 0.2 | yes |
| 09-09 10:38 | 2 | 1 | 0 | 0 | $0.4464 | 0.6 | yes |
| **total** | **11** | **5** | **1** | **0** | **$4.52** | — | 5 of 7 |

**Item 3 is settled and the answer is bad.** Coverage on identical input:
0.0, 0.0, 0.4, 0.9, 0.0, 0.2, 0.6 — and five passes of seven are `lopsided`.
One pass tells you almost nothing about this system.

**Item 2 has a number, and it is not the one quoted above.** We wrote "one in
eight". `mining_passes.rejected` — the instrument that item named — totals
**1 rejection in 11 proposals, ~9%**. The rejection is the 07:57 pass: $0.36 for
one hallucinated citation, caught by `validate`, nothing kept. Still a small n.

**Item 1 got worse, not better.** `learned_parameters` reads **0 on all seven
rows**. The column, its migration, its mapper and its contract test all exist
and the figure has never once survived a real pass — learning fires only on
`resolve() == same_job`, and no pass has reached it since the one that predates
the column.

**The unit economics, measured rather than estimated.** $2.71 across the four
passes that kept nothing; $1.81 across the three that kept five workflows.
**$4.52 for 5 workflows kept.**

**Against the criterion, quoted as written:** 8 of 8 workflows and 10 of 11
values is what the spec asks. The store now holds **5 of 8 workflows and 3 of
11 values** — workflows moved by one (`Create a Work Activity`, mined today
with zero parameters), values have not moved at all since they first appeared.

### Item 8, confirmed in the code and half fixed

`api.js:275` read `await fetch(...)` with **no assignment and no status check**,
so a 4xx and a success were the same nothing. Its own docstring calls this "the
one measurement that says whether recognising a job early was worth doing";
three lines below, the `catch` called the record "a nicety". Two comments in one
function disagreeing about whether the data matters.

**Fixed here: it returns whether the fate landed, and still never throws.** The
single caller uses `void`, so nothing downstream changes.

**What is NOT fixed, and item 8 stays open for it:** `rigHeaders()` omits
`X-Device-Secret`. Today these calls reach the rig, which has no device registry
and accepts the bare bearer, so they work. Phase 5 points them at the backend
and every one becomes a 403. The swallow was fixed first *because* of that — the
403 will be visible on the day it starts, rather than silently eating every
offer fate until somebody wonders why counsel never rests a job.

### Items unchanged, with today's evidence

- **4, 5** — untouched. Network-first parameter learning is still an accepted-ADR
  violation with no work started, and no test yet asks whether a body-derived
  parameter can carry a redacted value.
- **6** — confirmed in the live store: `task_candidates` **53** rows,
  `workflows` **5**. Two miners over one day, neither reading the other's tables.
- **7** — unchanged.
- **9** — `run_workflow` still has no caller; `grep` finds one docstring mention
  in `approvals.py` and nothing else. Phase 4b's Task 5 owns it.

### Fixed today, and none of it was on the list above

The contract suite had been red since 2026-09-06 and is green (109 passed);
`make lint-backend` had been broken by two unformatted files and is clean;
`make check` runs `tests/browser` (86 passed) despite a `pyproject.toml` comment
that said for years it did not — which is why one fixture defect failed two
suites while only one was ever looked at.

### The instruments

```
backend/scripts/backfill_gestures.py  replays stored batches into the evidence plane
backend/scripts/dry_run.py            the offer replay against the backend's own store
```

Both committed, because a measurement whose instrument is not committed is an
anecdote — the rule this document already states, broken once today: the
backfill ran from `/tmp` and every number above rested on a database state
nothing could recreate until it was committed.
