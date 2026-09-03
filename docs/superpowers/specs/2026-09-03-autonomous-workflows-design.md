# Autonomous workflows in the operator's own browser — Design

**Status:** proposed · 2026-09-03
**Supersedes the scope of:** `docs/superpowers/plans/2026-09-02-an-agent-roster.md`
(that plan becomes sub-plan 1 of the roadmap this spec produces)
**Origin:** the functional map (`~/Desktop/sro-shots/Screenshot 2026-09-03 at
12.25.08 PM.png`), the session history Aug 13 to Sep 3, the backend audit of
Sep 2, and the prior-art and competitor surveys of the same day.

## The vision, in one paragraph

An operator's day is mail, a WMS, an ERP, a document, and mail again. A request
arrives ("what is the status of order X, update the tracker, reply"), the person
searches Blue Yonder, switches to SAP, edits a sheet, sends the answer. Nobody
teaches the system any of it. The system watches, in the operator's own Chrome,
across every tab. It registers work the first time it sees it. It offers to do
the work once it can do it safely. Asked to do something it has never seen, it
does it anyway: from skills it has, from connectors it has, and where those run
out, by driving the operator's own tab with vision. When a way fails it tries
the next. What worked becomes a skill. Over months the human does less and the
system does more, and every write it made can be shown to have happened.

## Three decisions this spec makes

The code and the map disagreed in three places. Each is decided here, with the
reason, so nobody re-argues it in a pull request.

### D1. Observation covers every tab, always, under a tenant policy

**Decision.** The extension observes all tabs in the browser profile it is
installed in. The gate is a tenant policy set by an admin, not a per-tab press
by the operator. The operator keeps three controls: a visible indicator, pause,
and purge. The admin keeps an exclusion list of hosts never observed. Defaults
for that list: password managers, banking, health, the vendor's own consent
pages.

**Why.** A workflow that spans mail, WMS, ERP and a document cannot be observed
by a tab picker. The map says "monitor all tabs at all times". The instruction
of Aug 26 ("ask which tab to monitor") was given to stop a hard-coded origin
list, and the picker was the smallest fix at the time. It is now the thing in
the way.

**Consent.** The published guidance is consistent: employee consent is not a
valid basis under GDPR because it cannot be freely refused, so the basis is
legitimate interest, which requires a documented, proportionate purpose, prior
notice, a retention limit, and a works-council process where one exists. The
tenant policy is that document. Proportionality is met by what is *not*
captured: no keystroke logging beyond values that reach a request, sensitive
fields redacted at the edge (`sensitivity.module.js`), screenshots only around
episodes, purge on demand (`Delete the last hour`), retention sweep already
running. `docs/10-security-and-data.md` §consent is rewritten to say this.

### D2. Autonomy is earned by verified effect, not by counting runs

**Decision.** Three constants change meaning.

| Today | After |
|---|---|
| `WORTH_OFFERING = 3` doings before a candidate exists in the panel | A candidate is **registered at the first doing**. It is **offered** at the third. |
| `REQUIRED_CLEAN_RUNS = 10` consecutive clean system runs before `AUTONOMOUS` | A write step may run unattended after **3 verified effects**. A verified effect is a write whose result was confirmed by a read-back through a second path. **A human doing the task under observation counts as one**, because the read-back is evidence about the system of record, not about who pressed the button. |
| Reads climb the same ladder as writes | Reads are autonomous from the first run. The design doc's rule, "reads free, writes gated", becomes code. |

`DEMOTE_AFTER_FAILURES = 3`, the circuit breaker, and the blast-radius limits
are unchanged. The audit's four gate defects (H1 to H4) are fixed first;
lowering the bar on a ladder that gates nothing would be the worst of both.

**Why.** Ten consecutive clean runs, where any gesture at all makes a run
`DEGRADED`, means a `needs_a_person` skill can never climb and a network skill
climbs only after a fortnight of somebody pressing yes. The map says "after 3
successful captures, potential workflow; after one successful execution,
workflow, auto and scheduled execution". What makes that safe is not the count
but the check: OpenAdapt measured a screen-only check accepting 75% of wrong
effects and a system-of-record read-back cutting that to 12.5%. With the
Verifier in place, three confirmed effects is stronger evidence than ten
unconfirmed runs. Without it, no number is.

**What the map's "1" means.** Registered as a candidate. Not offered, not run.

### D3. Identity stays deterministic; models decide boundaries and chains

**Decision.** Three jobs, three mechanisms.

1. **What a step is** stays `(principal_id, signature)` and exact-equality
   clustering. No model ever answers "are these two the same call".
2. **Where an episode starts and ends, what it was for, and which doings are
   variants of one task** become a Flash call per episode. Today an episode is
   a three-minute idle gap (`segment.py:IDLE`) and a host change. A person who
   reads one mail, searches one order and replies is three episodes to the
   segmenter and one job to the person. Flash reads the episode's own evidence
   (hosts, calls in order, field names, the mail subject if a mail step is in
   it) and answers with a boundary, a sentence, and, for a set of episodes that
   share a signature, which fields varied. Its answer is validated the way
   every model answer here is: a boundary must fall on an event that exists, a
   variant grouping must agree with the signature, and a sentence is never
   identity.
3. **Which candidates form a workflow** is found by co-occurrence and data
   flow, not by asking. Candidates A, B, C, D that occur in that order within
   `LONGEST` of each other on three or more days, with a value produced by A
   appearing in B's request (the existing `_find_produced` and transformation
   discovery in `induction/diff.py` and `domain/skill/transform.py`), are one
   chain. A Pro call then writes the chain's story and proposes the parameter
   flow between its members. The proposal is validated against every observed
   instance of the chain; a flow that explains only one instance is discarded.

**Why.** The map wants Flash on every gesture and Pro on umbrellas. Per-gesture
calls are the cost profile of a screen recorder, and a model that decides
identity is the misevolution risk the prior-art survey documented. But the
code's exact-signature identity misses what the operator asked for on Aug 31:
"the same task done a thousand times, with different fields". Boundaries and
variants are judgement. Identity is arithmetic. The split gives each to the
mechanism that can be checked.

## The loop

```
observe (all tabs) ─▶ segment (Flash boundaries) ─▶ cluster (signature)
      │                                                    │
      │                                     candidate at 1 ─┤─ chain by co-occurrence + data flow
      │                                                    ▼
      │                                          offer at 3 (panel)
      ▼
request (chat | mail watch | schedule)
      │
      ▼
plan ── skills ─▶ connectors ─▶ pursuit in the operator's tab ─▶ ask the person
      │            (network/tool)     (vision, extension device)     (panel)
      ▼
do, durably (Temporal), one step at a time, verify each write by read-back
      │
      ├── step fails ─▶ next medium (escalation table) ─▶ pursuit ─▶ ask
      ▼
learn: a pursuit that verified becomes a skill version;
       a composed run that verified becomes a workflow skill;
       three verified effects and a write step runs unattended
```

Every arrow that lands on a model produces a proposal checked against
evidence. Every arrow that lands on a system of record is followed by a read.
Every step is a Temporal activity with its own checkpoint, so a workflow that
takes an hour, or pauses for a person overnight, resumes where it stopped.

## Components, by whether they exist

### Exists and stays

- Capture: gestures, network, page state, AX tree, bounded screenshots
  (`new-chrome-extension/src/content`, `background/shots.js`, `trees.js`).
- Identity, diff, parameters, lookups, transformation discovery
  (`application/induction`, `domain/skill`).
- Three media and the escalation table (`domain/execution/run.py:Medium`,
  `diagnosis.py`, `escalation.py`).
- Verdicts, track record, breaker, blast radius, `UNREACHABLE`
  (`domain/execution/verdict.py`, `domain/skill/track_record.py`,
  `domain/execution/safety.py`).
- Durable execution (`infrastructure/temporal/workflows.py:ExecutionWorkflow`).
- Connectors as a medium (`Medium.TOOL`, `application/skill/map_step_to_tool.py`,
  the Gmail connector).
- Mail watch to trigger (`domain/trigger/watch.py`, `content/watch.js`).
- The extension as driver (`infrastructure/agent/drivers.py:RemoteUiDriver`,
  `RemoteHttpCaller`, command channel in `background/commands.js`).
- Open questions to a person (`application/knowledge/open_questions.py:AskAbout`).
- Self-heal with a budget (`application/execution/self_heal.py`).

### Exists and changes

- `domain/skill/track_record.py`: `REQUIRED_CLEAN_RUNS` becomes
  `REQUIRED_VERIFIED_EFFECTS = 3`, counted from a new `verified_effects`
  column that only a confirmed read-back increments. `earned_stage` reads it.
- `domain/execution/verdict.py:_CLEAN_MEDIA`: a UI step whose effect was
  confirmed counts as clean. ADR.
- `domain/observation/candidate.py`: `WORTH_OFFERING` stays 3 and gates the
  offer only; registration happens at 1.
- `application/observation/segment.py`: boundaries proposed by Flash, validated
  against events; the three-minute rule stays as the fallback when no model is
  configured.
- `application/execution/pursue_goal.py`: takes a `BrowserProvider` chosen per
  run: the operator's device when one is online for the tenant, Steel otherwise.
  Commits what "done" will look like before the first gesture; `reached` is
  that string on screen, not `proposed.done`.
- `application/intent/resolve.py:_nothing_taught`: a request that matches no
  skill goes to the planner, not to a refusal.
- `new-chrome-extension/src/background/state.js`, `commands.js`: watching is
  policy-driven; screenshots of a background tab go through `chrome.debugger`
  `Page.captureScreenshot` (the tree code already uses the debugger), since
  `captureVisibleTab` photographs only the active tab.

### New

- **Verifier** (`application/execution/confirm_effect.py`,
  `AssertionKind.EFFECT_CONFIRMED`). Sub-plan 1. Most of it is pure induction
  off the two-run diff; the model half commits an expectation before the write
  and never sees the response.
- **Device browser provider** (`infrastructure/agent/browser_provider.py`).
  `BrowserProvider` over the online device: navigate, screenshot, perform_at,
  current URL, over the existing command channel. Sub-plan 2.
- **Planner** (`application/execution/plan_request.py`). One Pro call turns a
  request plus what is known (skills, chains, connectors, knowledge catalogue,
  the mail that triggered it) into a list of steps, each naming a skill, a
  connector call, or a pursuit goal with a start URL and a done-condition. The
  list is validated: every skill named must exist and be runnable for this
  principal, every connector must be configured, every pursuit must name a
  host the tenant has connected. Sub-plan 3.
- **Composed run** (`infrastructure/temporal/workflows.py:ComposedWorkflow`).
  Steps as activities, a checkpoint per step, a pause activity that waits on an
  `AskAbout` answer, outputs (a mail sent, a document updated) as connector
  steps. Sub-plan 3.
- **Chain miner** (`application/observation/chain.py`). Co-occurrence over
  candidates plus data-flow linking. Sub-plan 4.
- **Episode judge** (`application/observation/boundaries.py`, port
  `application/ports/boundaries.py`, null adapter). Sub-plan 4.
- **Observation policy** (`domain/observation/policy.py` grows a tenant
  policy: purpose, retention, exclusions; extension reads it at handshake).
  Sub-plan 6.
- **Roles** (`domain/identity/scope.py`: `READ_ONLY`, `WRITE_WITH_PERSON`,
  `WRITE_UNATTENDED` per principal; `_check_runnable` consults it). Sub-plan 7.

## What Steel is for now

Two jobs, both real, neither the front door.

1. **Verification reads.** A read-back sent from a browser the operator is not
   in cannot be confused with the operator's own activity, and it works when
   their Chrome is closed.
2. **The night shift.** A scheduled workflow at 02:00 has no operator tab to
   drive. Steel runs it, with the tenant's stored session. This is the one
   place the extension cannot go, and it is the place "long hours of work"
   ends up. Keep it, size it small, say so in `docs/07-adr/003-steel.md`.

Chrome's limits, stated once: an extension drives only tabs its host permission
covers, cannot see or act below the browser, and cannot run when Chrome is not
running. Everything above those limits is Steel's, and nothing else.

## What the panel is

The product. A conversation. Offers with Yes and Not now. A run as a card with
each step and its verdict as it happens. A question from a paused run inline,
answered inline. One status line: watching, signed in where, connectors
attached. Totals for the day. The watch gate becomes a chip when policy covers
the tab. The console is the supervisor's view and says so.
(`docs/superpowers/specs/2026-09-02-the-panel-is-a-conversation-design.md` is
the base; this spec adds the run card, the inline question, the status line
and the totals.)

## What no model touches

- Identity: `(principal_id, signature)`, exact-equality clustering.
- The two-run diff and which values vary.
- The escalation table.
- The breaker, blast radius, batch caps.
- The ladder's arithmetic once `verified_effects` is a column.
- L1 and L2 step execution.

## Roadmap

Two tracks, so the work splits between two people without collision. Track A
is extension and panel. Track B is backend. Sub-plans are written one at a time,
in the house format, when their predecessor is green.

| # | Sub-plan | Track | Depends on |
|---|---|---|---|
| 1 | Ladder gates and the Verifier (existing roster plan, Tasks 1 to 8) | B | none |
| 2 | Do it in the operator's tab: device browser provider, pursuit picks the device, chat with no match starts a pursuit, background-tab screenshots | A + B | 1 |
| 3 | Request to composed run: planner, `ComposedWorkflow`, pause and resume on a question, mail watch to planner, connector output steps | B | 1, 2 |
| 4 | Learn at one and chain: candidate at first doing, episode judge, variants, chain miner, chain offers | B | 1 |
| 5 | Panel as the product: offers, run card, inline question, status line, totals, watch chip | A | 2 for the run card |
| 6 | Observation policy: tenant policy, exclusions, indicator, `docs/10` rewrite, ADR 016 | A + B | none |
| 7 | Roles and metrics: per-principal scope, `_check_runnable` consults it, a metrics page off the analytics summary | B + console | 1 |

Deferred, from the roster plan: Repairer, Diagnostician, Curator. Revisit when
the library passes twenty skills or drift is the top failure in the run log.

## Verification of the whole

One scenario, run live, after sub-plans 1 to 5:

1. A mail arrives in the watched Gmail tab: "status of order 4471?"
2. Nobody teaches anything. The chat is asked, or the mail watch fires.
3. The planner names: read order in Blue Yonder (skill), read the shipment in
   the second system (pursuit, since nothing was taught there), append a row to
   the tracker (connector or pursuit), reply by Gmail (connector).
4. Each step lands as a card in the panel as it runs. The pursuit drives the
   operator's tab; they can watch it.
5. The reply goes out. The tracker row is read back and matches.
6. The pursuit that worked is now a skill. The four steps are now a chain
   candidate. The next such mail is offered as one job.

Then the same scenario with the second system's page changed, so the pursuit
fails once, escalates, and asks the person one question in the panel before
finishing.

## Open questions, deliberately left

- Which second system is real for the pilot. The scenario above needs one
  besides Blue Yonder. SAP QA access decides sub-plan 3's live test.
- Whether a chain of five skills is offered as one job or as five. Proposed:
  one, with the members visible.
- Where the tenant policy is edited. Console, admin page, until an admin portal
  exists.
