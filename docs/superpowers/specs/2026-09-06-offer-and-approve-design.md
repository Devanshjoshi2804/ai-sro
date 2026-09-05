# Offer the job as it starts, approve each write until it is earned — Design

**Status:** approved in conversation · 2026-09-06
**Builds on:** `docs/superpowers/specs/2026-09-03-model-first-workflow-mining-design.md`
(the rig, its runner), `docs/superpowers/specs/2026-08-31-offering-to-do-the-work-design.md`
(the nudge, its three endings), `docs/superpowers/specs/2026-09-03-autonomous-workflows-design.md`
(D2: autonomy is earned by verified effect).
**Plan:** written next, in the house format.

## The problem

The rig can mine a job and run it. Nothing recognises that an operator is
doing that job right now, so nothing offers. The one door is a form on the
rig's page, which nobody working in a warehouse tab has open. And a run,
once started, writes without a person seeing each write first.

The owner's words: once we have the context of the task being performed, we
offer to do it; the person approves and watches; where we can call the API we
do, otherwise the browser does the clicking. Latency matters: the offer has to
land while the person is still on step two, not a minute later.

## Decisions taken before design

- **Recognition runs in the extension, not on the rig.** The extension flushes
  gestures to the rig once a minute. Anything that recognises on the rig is a
  minute late. A proven workflow's `shape_key` is arithmetic -- `(system,
  target_identity, kind)` per cited gesture -- so matching a live tail against
  it is a set lookup, no model. Flash's per-gesture reading stays where it is
  and does what it does: the intent, the mining. It is not on this path.
- **Both triggers.** The arrival nudge that exists ("you have done this here
  before") starts asking the rig for candidates too. A matched prefix upgrades
  the same nudge to a concrete offer carrying the values typed so far.
- **Per write until earned, then unattended.** Every write pauses for a tap in
  the panel until the workflow has three live runs whose writes all verified
  by state (status or read-back). Then writes go unasked; the person still
  watches and can stop. A failed write resets the count.
- **`target_identity` lives once.** One Python definition in `rig/shape.py`,
  one generated JavaScript twin under `make gen-recorder`, one shared fixture
  both are tested against. The rule that must not drift is the rule that lives
  once.

## Design

### Shape

```
gesture in tab
  │ content script computes target_identity (generated twin of shape.py)
  ▼
service worker: live tail per tab, last K_TAIL = 12 gestures, scrolls dropped
  ├─ arrival: host has a cached shape           → nudge pill (exists)
  └─ prefix: tail ends with shape[0..k), k ≥ 2  → concrete offer, values from the tail
        │
        ▼
panel card  "You're creating a work area — NEWTESTS, so far. Want me to finish it?"
        │ missing parameters asked inline; Yes disabled until all present
        ▼
POST /v1/runs {workflow_id, values, device_id, live: true, from_step: k, started_by: "offer"}
        │
        ▼
runner performs from step k+1
  before each write: awaiting → panel shows [Approve] [Stop] → POST /v1/runs/{id}/approve
  unless earned(workflow): three live runs, every write verified by state
        │
        ▼
panel polls GET /v1/runs/{id} each second; one row per step as it lands
        │
        ▼
rig, when the flush lands: POST /v1/offers has already told it what was offered
and how it ended; the rig stores it beside the run
```

### The rig serves shapes

`GET /v1/shapes` (bearer), per tenant. One entry per workflow with an empty
`unproven` list that has either never been run or has at least one run
recorded `held`:

```
{ "id": "wfl_…", "title": "Create Work Area", "starts_on": "https://host/…",
  "hosts": ["bf56-kms-wms-web-np2.jdadelivers.com"],
  "shape": [["https://host", "wm.workAreas.code", "type"], …],
  "parameters": [{"name": "workArea", "at": 3}, …] }
```

`shape` is the workflow's `shape_key` as stored. `parameters[].at` is the shape
index of the gesture that typed that parameter's value, derived from the
parameter's `seen_values` matching a cited gesture's value at mining time; a
parameter with no such index is asked inline every time. `hosts` are the
systems the evidence names, the same set `allowlist()` computes; a workflow
whose `starts_on` host is not among them is not served.

The extension caches the answer per host for `CANDIDATES_FRESH_MS`, the same
five minutes and the same `knownHere` map the backend candidates use.

### The extension matches

`background/recognise.js`, pure, no `chrome` at import:

- `tailFor(tabId)` -- the last `K_TAIL = 12` gestures on that tab as triples,
  `anon|scroll` dropped, kept in `state` so a service-worker eviction loses at
  most what is being typed now.
- `match(tail, shapes) -> {workflow, k, values} | null` -- for each shape whose
  first triple's system is the tab's origin: the longest `k ≥ K_OFFER_AFTER = 2`
  such that the tail ends with `shape[0..k)` in order. Ties: longest `k`, then
  most held runs. `values` is `{name: typed text}` for every parameter with
  `at < k`, read off the matching tail gesture; a gesture whose control is
  flagged secret contributes nothing and the parameter is missing.
- `diverged(tail, offer) -> bool` -- the tail no longer ends with the offer's
  prefix: the person went another way.

Wired in the service worker on every gesture: `considerOffer(tabId)`. One offer
per tab. A new match replaces an open offer only with a longer `k`. The nudge's
guards hold: not on an unwatched tab, not while `performing()`, not while the
operator is `busy`, not while muted.

### An offer ends

The three endings the nudge has -- left the page, did the write themselves
(`didItThemselves` on the workflow's recorded mutation method and path),
`NUDGE_TTL_MS` elapsed -- plus `diverged`, plus `accepted`. Every ending is
reported: `POST /v1/offers {workflow_id, k, fate, run_id?, at}` with `fate ∈
{accepted, dismissed, did_it, expired, diverged}`. The rig stores them in
`offers`. They are the labelled record of whether recognition was right, and
they are what moves `K_OFFER_AFTER` later; nothing reads them in this plan.

### The offer card

In the nudge slot the panel already draws. Arrival keeps its words. A prefix
match upgrades the card:

```
You're creating a work area — NEWTESTS, so far.
Want me to finish it?
   description   [                    ]     ← one field per missing parameter
   [ Yes, finish it ]   [ No thanks ]
```

Yes is disabled until every declared parameter has a value; the route refuses a
blank one regardless. Yes posts `POST /v1/runs` with `from_step: k`, `live:
true`, `started_by: "offer"`, and reports `accepted` with the `run_id`. The
pill becomes the driving band the runner already shows. No thanks reports
`dismissed`.

The arrival nudge's Yes has no prefix: `from_step: 0`, every parameter asked
inline. It is the rig page's form, on the panel.

### The runner starts mid-job

`POST /v1/runs` gains `from_step: int = 0`. Steps `order < from_step` are
recorded with verdict `done_by_operator`, `verdict_by = "none"`, no command,
and their cited gestures named in `reason`. The runner begins at `from_step`.
The budget is `len(steps) - from_step + K_STEP_SLACK`. Everything else --
allowlist, dry-first, one rescue, the write-rescue gate, the `finally` -- is
unchanged. A `from_step` beyond the last step is a 400.

### Approval

Two new step verdicts, `awaiting` and `done_by_operator`, join `VERDICTS`. No
new run outcome: an awaiting run is `running`.

Before the runner sends a step that `writes()`, on a live run, when the
workflow is not earned: it records the step `awaiting` with `sent` set to the
planned command, saves, and waits on an `asyncio.Event` held in `Approvals`
(the `Aborts` shape: in-process, keyed by run id, forgotten in the `finally`).
`K_APPROVAL_WAIT_S = 300`. Approved: the event is set, the write goes out,
verify runs, the loop continues. Deadline: the run stops, outcome `stopped`,
reason "nobody approved the write within five minutes". Stop while awaiting:
`aborted`, as today. Dry runs never pause; they withhold.

`POST /v1/runs/{id}/approve` (bearer) sets the event and answers `{"approved":
true}`. It refuses `409` a run whose in-flight step is not `awaiting`, and is
idempotent for the one that is.

### Earned autonomy

Table `workflow_effects (workflow_id, run_id, ord, verified_by, at)`, one row
per write step of a live run whose verdict was `held` by `status` or `read`.
Never `screen`: a picture is not an effect. Written by the runner beside
`mark_stale`.

```
earned(store, workflow_id) =
    count of distinct live runs where every write step has a row here  ≥  K_EARNED_RUNS = 3
```

A live run in which any write step ends `failed` deletes every row for that
workflow: it starts earning again. Earned workflows do not pause; the panel
still shows every step and Stop still works.

### The live run in the panel

While `activeRun.source === "rig"` and the run is `running`, the service worker
polls `GET /v1/runs/{id}` every `K_RUN_POLL_MS = 1000` and puts the answer on
`status.performing.run`. `runCard` draws one row per step as it lands -- order,
says, verdict glyph, `matched_by`, cost -- which is the branch Task 11 of the
runner plan left unreachable. An `awaiting` row shows the planned command in
words ("press Save on Work Areas") with `[Approve]` and `[Stop]`; Approve posts
to the approve route through the worker, so the rig bearer never enters the
panel. Details still opens the rig page.

### What this must refuse

- An offer on a tab that is not watched, or while a run is performing, or
  while the operator is typing, or while muted.
- A shape whose starting host the evidence does not name.
- A blank declared parameter, at the card and at the route.
- An approve for a step that is not awaiting.
- Counting a screen-only verification as an effect.
- A rig that is down produces no shapes, no offer, no error shown. Silence is
  the safe answer, as the nudge code already says.

## Verification

1. **The matcher on real shapes.** Against the eight workflows in `rig.db`:
   a tail of one matching gesture fires nothing; two fire the right workflow;
   a tail that then goes elsewhere ends the offer `diverged`. Two workflows
   sharing a first step resolve to the longer prefix once it exists.
2. **One identity, two languages.** The Python and generated JavaScript
   `target_identity` agree on every gesture in the shared fixture, including a
   secret-flagged control and a scroll.
3. **A run that starts at step k.** `from_step: 2` records two steps
   `done_by_operator`, performs from the third, and the budget is
   `len - 2 + 3`.
4. **Approval.** A live write pauses `awaiting`; approve lets it out; the
   deadline stops the run; Stop aborts it; a dry run never pauses; an earned
   workflow never pauses; a `failed` write un-earns it.
5. **The panel.** The card's Yes is disabled with a parameter missing; an
   awaiting row draws Approve and Stop; a held row draws neither; a rig run
   shows steps while running, not only after.
6. **Live, by a person.** Start the work area job by hand in the WMS tab. The
   offer appears on the second gesture. Yes. Watch the panel. Approve the save.
   Record: how many gestures before the offer, how long from the last gesture
   to the card, whether the offer named the right job, and what the run did.
   Repeat three times; the fourth run should not ask.
7. **The fates.** After a day, `offers` holds a row per offer with a fate. The
   share of `diverged` is the number that decides whether `K_OFFER_AFTER`
   becomes 3.

## Out of scope

- Fuzzy or model-assisted matching of control identity. A changed page stops
  matching; the run's stale-locator signal is what notices a changed page.
- Offering chains of jobs, or a job the tenant has never demonstrated.
- The rig acting on `offers` (moving the threshold, retiring a shape). Stored
  now, read later.
- Computer-use fallback when the locator ladder and the rescue both fail.
- A per-principal role for who may approve. One bearer, one tenant, as the rig
  is today.
