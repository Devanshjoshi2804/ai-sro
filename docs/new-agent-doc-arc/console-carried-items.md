# What phase 6 did not carry across

The rig's console was one 1155-line HTML file with four views and two strips.
Phase 6 rebuilt five of those surfaces as pages in the Next.js console. This is
the list of what did not come with them, so phase 7 deletes
`new_agent_arch/src/rig/web/index.html` knowing what goes with it rather than
finding out afterwards.

Nothing here is a bug report. Every item is either a decision that was made, or
a gap that is real and unowned. They are written plainly on purpose: a carried
item that reads like a nice-to-have gets treated like one.

## 1. The gestures view is gone, and it was the landing page

The rig opened on `#rows` — every captured gesture and what a model read out of
it, one row each, with a stream picker above it. It read `GET /v1/streams` and
`GET /v1/gestures?stream=`. **Neither route was ported.**

What goes with it is not the table. It is the argument the table encoded, which
that file spent more comment lines on than anything else: a gesture has **three**
states, not two.

- `not read yet` — no reading was made.
- `read, nothing usable` — a reading was made, **was billed**, and came back
  with no act a mining pass could use.
- `unread — <error>` — the call failed.

Rendering the middle one as "not read yet" is the console telling an operator a
lie it was paid for. The same three-state rule governed the money column, where
the original bug is recorded in the source: `intent?.cost_usd ? … : ""` drew an
unpriced reading and a genuinely-free one with an identical empty cell.

The backend keeps this distinction — `Answer.cost_usd` beside its unpriced flag,
and the intents table records a cost it could not establish. Nothing reads it
over the wire. Reinstating the view means porting two routes first; the rule it
enforced is worth more than the table it drew.

## 2. The models / bake-off view is gone

`GET /v1/bakeoff?limit=200` and `GET /v1/bakeoff/readings?limit=20000`, written
by `make bakeoff` and read by nothing else. Neither route was ported.

Three tables — `read`, `mine`, `burst` — comparing models on cost, latency,
jitter, thought-token share and how much of a day each one kept; plus an
agreement matrix showing, gesture by gesture, whether two models read the same
day the same way, and a "where they parted" table of the gestures they gave
different verbs to.

**This is the only screen in the product that says which model to buy.** It is
also the only place the per-gesture agreement between models is visible at all,
and its own note is the reason that matters: the verb is what a mining pass
inherits, so two models that agree on prose and disagree on verbs produce
different workflows from the same day.

## 3. `/v1/spend` serves three of the nineteen fields the header line rendered

The rig's header read `gestures_read`, `gestures`, `cost_usd`,
`per_gesture_usd`, `unusable`, `unpriced`, `thought_tokens`, `passes`,
`mining_usd`, `mining_unpriced`, `runs`, `runs_usd`, `runs_unpriced`, `chats`,
`chat_usd`, `chat_unpriced`, `cap_usd`, `today_usd` and `today_unpriced`.

`SpendResponse` is `{cost_usd, unpriced, cap_usd}`, and the narrowing is not in
the HTTP layer: the domain's `DaySpend` is `{cost_usd, blind}` and nothing else.
**There is no source for the other sixteen anywhere in the backend.**

What is lost is the breakdown — which of mining, runs and chat spent the day —
and the per-reading unit cost, which is the number that says whether a cheaper
model would pay for itself. The console renders the three that exist and says
what they are. Restoring the rest is backend work: `DaySpend` would have to
carry the split, which means the four tables a model call bills to would have to
be summed separately rather than together.

One thing from that line survived and must not be collapsed later: `unpriced` is
a **count**, not a flag, and it is reported beside the total and never folded
into it. `docs/new-agent-doc-arc/findings.md` records the incident that settled
it — `mining_usd 0.0` with `mining_unpriced 1`, while $1.12 had actually been
billed.

## 4. `became()` lost `last`, `offers` and `counsel`

`WorkflowHistoryModel` is `{total, held, stale, earned}`. The rig's card line
also read `runs.last`, `runs.offers` and `runs.counsel`, so it could say:

- `last completed (dry) by form` — what the most recent attempt actually did
- `offers: 2 accepted, 1 timed out` — how a job fared when it was offered
- `offered after 40 gestures` — the counsel's threshold

A card now says how many runs there have been, how many were held, how many
steps matched weakly, and whether the job has earned the right to write unasked.
That is enough to judge a job's health and not enough to judge its *offering*.

The offer data exists — `/v1/audit` serves offers with their fates — but not per
workflow and not without a `since`. Closing this means widening
`WorkflowHistoryModel`, which is a read model the workflows route already
builds.

## 5. `POST /v1/mine` still has no button

In the rig it appeared in exactly one place: the empty-state string
`nothing mined yet — POST /v1/mine`. There was never a control.

The console can now read mined jobs, run them, approve them, audit them and
watch what they cost. It cannot ask for a mining pass. That is a console with a
terminal beside it, which is the thing this phase existed to stop being true.

The route is tenant-only and a pass costs real money against a real model — so
the missing piece is not the button, it is the decision about who may press it
and what it says before it spends.

## 6. A console approval records no approver

`approved_by` holds the **browser** that tapped. A tap from this console names
no browser, deliberately: the console holds the tenant's credential and has no
extension of its own, and `ApproveWorkflowStep` documents the choice at length —
refusing a caller that names no browser "would delete the supervisor's queue".

So the row is honest. It says a write was let out, when, and that no browser
answered for it. The audit page renders that as `by the tenant`.

**What it cannot say is which person.** On a deployment where supervisors
approve from the console — which is the deployment this page was built for —
every approval in the audit reads the same way. The credential carries a
principal; the approvals row has nowhere to put it. Closing this is a schema
change plus a decision about whether the principal belongs beside the device or
instead of it.

This is the single most important item on this list. An audit that can name the
minute but not the person is not the thing an audit is for.

## 7. The extension's deep link — closed by this phase

`panel.js` used to withhold "Details in console" for a run whose `source` was
`"rig"`, because no workflow-run screen existed and a link would have landed on
"a 404 dressed up as an answer". Phase 6 built the screen and the link is back,
routed by id space: `/jobs/runs/<id>` for a workflow run, `/runs/<id>` for a
skill run.

The two spaces stay apart for the backend's own stated reason — a string that
round-trips through the wrong repository is looked up, found missing, and read
as a run that does not exist rather than as a type error. Sending a workflow-run
id to `/runs/` would draw "no such run" and look like an answer.

Recorded here because it was open through phases 4 and 5 and the comment that
explained the absence is now gone from the source.

## 8. The audit's section heading is asserted by no test

`audit-walk.tsx` renders the first heading with `toLocaleString()` — the one
place a **local** time is deliberate, matching the picker beside it, while every
row stays in the record's UTC.

The rows are covered. The heading is not, because a `toLocaleString()`
assertion is zone-dependent and the suite runs wherever it runs. So a change
that put UTC into the heading would pass every test. It is exactly the kind of
inconsistency somebody "fixes" while tidying, and nothing would object.

## 9. The audit test's `none` count is global

`expect(await screen.findAllByText("none")).toHaveLength(4)` counts every
occurrence on the page, not one per section. A fifth section added later fails
it — correctly, but for a reason that reads as unrelated to the change that
caused it.

## 10. TanStack Query v5 hands `mutationFn` a second argument

`useMutation({ mutationFn: someApiHelper })` does not do what it looks like: v5
calls the function with `(variables, context)`. A helper declaring one parameter
ignores the extra one and works — until the day it declares two, at which point
it silently receives React Query's context as its second argument.

It cost real time in this phase: an otherwise-correct component failed
`toHaveBeenCalledWith("dev_a")` for this alone. **Every mutation in
`features/workflow/` wraps its helper** — `mutationFn: (id: string) =>
revokeBrowser(id)` — and anyone adding one must too.

## 11. Two artefacts of the generated types

`generated.ts` types `from_step` as **required** on `StartWorkflowRunRequest`,
while the backend declares `from_step: StrictInt = 0`
(`backend/src/sro/interface/http/schemas.py:2924`). Omitting it starts at step
zero, which is correct; the console omits it. A resume-part-way feature will
need to send it, and will find the type already insisting.

`WorkflowModel.parameters` generates as `{[key: string]: unknown}[]` rather than
a named model, so `run-form.tsx` narrows it once through a local `type
Parameter` alias. Delete that alias if the generator ever emits the real shape.

## What is proven, and what is not

Every test in this phase mocks the api module. That is the same limitation the
extension's suites have, and it means **no test here proves a request reaches
the backend correctly.**

What was checked against the running backend: all twelve routes answer, `GET
/v1/audit` refuses a request with no `since`, and the live store holds 7
workflows, 4 browsers and zero runs, offers and chats. Those are read routes.

**The write routes — start, approve, abort, revoke, restore — are proven by
nothing in this phase.** Proving them means driving a real Chrome at a real
warehouse system, which is phase 7's live proof. Until that has been done, the
right thing to say about them is that they are wired, not that they work.
