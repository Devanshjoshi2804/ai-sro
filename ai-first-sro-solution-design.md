# AI-First SRO — Solution Design

Combining the stated requirements (three execution cases, self-healing WMS brain, email interface, concurrency, cheap-Gemini constraint) with the deck architecture (Unified System of Records, Workflow Builder, Workflow Executor, 5-level execution medium, 4 storage mechanisms).

---

## 0. Three corrections that change the design

### 0.1 Your Level 5 is much smaller than the deck assumes

The deck puts Blue Yonder, mFolio/Infor, and E2 in "UI last resort." That is wrong for at least three of them, and it changes where the engineering effort should go.

| System | Deck level | Actual level | Access surface | Key constraints |
|---|---|---|---|---|
| **Infor WMS** | L5 | **L2/L3** | ION API Gateway — REST over OAuth 2.0, plus **BOD event bus** (push, not poll) | Gateway timeout 1 min default / 5 min max; 10 MB buffered payload cap; per-endpoint throttling policies (no global limit — must be discovered per suite); app must be registered with Swagger 2.0 / OpenAPI 3 |
| **Blue Yonder WMS** | L5 | **L2/L3** | **MOCA** is the native command layer — queryable, schema-discoverable. Community MOCA MCP servers already exist (read-only default, writes gated behind explicit approval). Luminate REST where the Connect/API entitlement is present | MOCA is proprietary and version-variable; on-prem vs cloud differ; auth via session key or basic |
| **SAP** | L2 | L2/L3 | OData V2/V4; MCP Gateway on Integration Suite | EWM V4 services often not active by default — must be published |
| **OpenDock** | L2 | L2/L3 | Neutron REST + **Subspace streaming** (create/update/delete events) | JWT auth |
| **Gmail** | L2 | L2 | Gmail API | — |
| **E2 / JobBOSS²** | L5 | **L5 (genuine)** | No public API | Not in POC scope — deprioritize |

**Implication:** browser automation is not the backbone. It is the *last mile* — specific screens and actions not exposed through MOCA/ION/OData. Build the ladder and the sync layer first; browser automation second. This inverts the effort allocation implied by the deck and substantially de-risks the Gemini Flash-Lite constraint, because most steps never reach a vision model at all.

**Infor's BOD event bus and OpenDock's Subspace are the two most under-used assets in the deck.** Both are push. They give the Unified System of Records a change feed instead of a polling loop — which is the difference between a sync layer that scales and one that hammers throttled endpoints.

### 0.2 "Bi-directional Sync" as written is the most dangerous slide in the deck

> *"Graph RAG updates operational systems automatically, and source system changes flow back into the Graph RAG."*

Two systems auto-writing to each other is a write-write conflict engine. It produces sync loops, last-write-wins data loss, and — because this is inventory — silent corruption that surfaces days later as a physical count discrepancy nobody can trace.

**Fix: CQRS. The Graph RAG is a read model. It never writes to a source system.**

- **Inbound (sync):** BODs, Subspace events, MOCA polls, OData deltas, email → Graph RAG. One direction. Idempotent, replayable, with source-system watermarks.
- **Outbound (writes):** only ever through the Workflow Executor, as an explicit, attributed, idempotency-keyed, verified action. Never as a side effect of the sync layer.
- The Graph RAG holds the *last observed* state and a confidence/staleness marker, never the *authoritative* state. Source system stays system of record.

Reframe the slide as **"Unified Read Model + Explicit Write Path."** It's a weaker-sounding claim and a much stronger system. It is also the thing that will get you through an enterprise security review.

### 0.3 The Anomaly Detection Agent is your best wedge, and it needs no writes at all

"Crawl index → cross-check sources → anomaly found → escalate to human → one-click fix" is read-only until the last step. It is deployable in weeks, it is the fastest path to a customer saying "this found something we missed," and it carries near-zero blast radius. Lead the POC with it.

---

## 1. Reference architecture

```
                            ┌─────────────────────────────┐
   INGRESS                  │  Gmail  ·  Web UI  ·  Slack │
                            └──────────────┬──────────────┘
                                           │
                            ┌──────────────▼──────────────┐
                            │  Objective Resolver         │
                            │  vague task → structured     │
                            │  objective (clarify loop)    │
                            └──────────────┬──────────────┘
                                           │
                            ┌──────────────▼──────────────┐
                            │  ORCHESTRATOR (Temporal)     │
                            │  durable, resumable,         │
                            │  signal-based human waits    │
                            └──────┬───────────────┬───────┘
                                   │               │
                    ┌──────────────▼───┐     ┌─────▼──────────────┐
                    │ MATCH WORKFLOW?  │     │  NOT FOUND path    │
                    │ structured match │     │  pull similar ctx  │
                    │ + confidence gate│     │  → plan from KB    │
                    └──────────────┬───┘     └─────┬──────────────┘
                                   └───────┬───────┘
                                           │  per step
                            ┌──────────────▼──────────────────────┐
                            │  EXECUTION MEDIUM LADDER            │
                            │  L1 Graph RAG (read)                │
                            │  L2 MCP (SAP, OpenDock, Gmail, MOCA)│
                            │  L3 Direct API (ION, Neutron, OData)│
                            │  L4 Network interception            │
                            │  L5 UI (a11y-first, vision last)    │
                            └──────────────┬──────────────────────┘
                                           │
                            ┌──────────────▼──────────────┐
                            │  VERIFY (read-back on a     │
                            │  DIFFERENT path than write) │
                            └──┬────────────┬─────────────┘
                        pass   │            │  fail
                               │            ▼
                               │   ┌────────────────────┐
                               │   │ HEAL (locator/API) │
                               │   │  ↓ fail            │
                               │   │ ESCALATE MODEL     │
                               │   │  ↓ fail            │
                               │   │ HUMAN TAKEOVER     │
                               │   │  (Steel live view) │
                               │   └────────┬───────────┘
                               │            │ capture demo
                               ▼            ▼
                    ┌──────────────────────────────────────┐
                    │ STORAGE                              │
                    │ Graph RAG · Workflow Repo ·          │
                    │ Knowledge Base · LLM Cache           │
                    └──────────────────────────────────────┘
                                    │
                            PROMOTION LADDER
                    recorded → shadow → assisted → autonomous
```

---

## 2. Workflow Builder — concrete implementation

The deck's four inputs are correct. Their value ranking is not equal:

**network calls > accessibility tree > narration > video.**

### 2.1 Capture harness

Run demos inside an instrumented Steel/CDP session (or a Chrome extension for on-prem-only apps). Per user action, capture:

| Channel | Source | Use |
|---|---|---|
| Network | CDP `Network.*` — request, headers, body, response, timing | **Primary.** Becomes the L4 recipe |
| a11y tree | CDP `Accessibility.getFullAXTree` at action time | Element fingerprint + L5 recipe |
| Input events | click/type/select + target element multi-attribute fingerprint | Step boundaries, L5 recipe |
| Screen | video | Human-reviewable evidence; canvas/iframe fallback only |
| Audio | mic → transcript, timestamp-aligned | **Branch discovery** (see 2.4) |

### 2.2 One demo → two recipes

This is the highest-leverage idea in the whole build. While the clerk clicks, you are recording the network calls their clicks produced. That yields, from a single demonstration:

- **`network_plan`** — the L4 path. Fast, robust, survives UI redesigns, derived from a human who definitionally did it right.
- **`ui_plan`** — the L5 fallback, for when a call cannot be replayed (CSRF tokens, client-minted signatures, WebSocket-only flows, or a step that has no network call at all).

The executor always prefers `network_plan`, falls back to `ui_plan`. **Your demo pipeline is an API discovery pipeline.** Build it explicitly for that, not as a side effect.

For Blue Yonder this is even better: the "network calls" are MOCA commands. A recording of a clerk doing a wave release hands you the exact MOCA command sequence — which is a *documented, schema-discoverable, replayable* artifact, not a reverse-engineered guess.

### 2.3 Parameterisation by two-run diff

The demo contains literals: order `12345`, dock door `7`. Turning `type "12345"` into `type {order_number}` is where naive systems break, and an LLM guessing slots will get it wrong in ways you won't notice until production.

**Don't infer. Diff.** Record the same task twice with different values:

- Fields that changed → parameters
- Fields that stayed constant → structure
- Values appearing in both input and later response → derived/correlated (session IDs, generated LPNs)

Cheap, deterministic, far more reliable. Make "record it twice" a mandatory part of the capture protocol, not an optimisation.

### 2.4 Branches come from narration, not video

One demo gives a happy path. It cannot tell you what happens when the PO doesn't match, the shipment is short, or an unexpected modal appears.

The audio input in your diagram is the answer, and it's the most under-specified box in the deck. **Make the recorder actively prompt:**

- "Say what you're checking on this screen."
- "What would you do if that number didn't match?"
- "Is there another way this usually goes?"

A narrated demo is worth roughly ten silent ones. Remaining branches are discovered at runtime and written back — which is exactly what the SAVE arrow in your Workflow Execution diagram already does.

### 2.5 Assertions are free — capture them

During the demo, the clerk verifies their own work. They look at a field, a count, a status badge. That gaze/scroll/final-screen behaviour is your post-condition. Extract it:

- What was the last screen state before they moved on?
- Which response field confirmed success?
- What number did they compare against what?

That becomes the VERIFY step. You get it at zero marginal cost, and it is far better than an LLM inventing a plausible-sounding assertion.

### 2.6 Output split (matches the deck)

- **Workflow Repository — "what to do":** ordered steps, decision points, parameters, assertions, system-agnostic.
- **Knowledge Base — "how to do it":** system-specific. MOCA command signatures, ION endpoint + auth profile, element fingerprints, known modals, quirks ("Blue Yonder session drops after 20 min idle"), discovered throttling limits.

Keep them separate exactly as the deck has it. It's what lets one workflow ("resolve a short-ship") execute against Blue Yonder at one site and Infor at another.

---

## 3. Workflow Executor

### 3.1 The MATCH WORKFLOW gate is the highest-risk box in the diagram

A wrong match means doing the wrong thing **confidently and fast** — the cached path has no reasoning left in it to catch the error. This is the failure mode that corrupts inventory.

Do not match on embedding similarity of request text alone. Match on a structured key:

```
{ objective_type, target_system, entity_type, facility, direction(in/out) }
```

with embedding similarity only as a tiebreaker among structurally-compatible candidates. Apply a confidence floor. Below it, route to the NOT FOUND path **with the near-match supplied as context** — which your diagram already supports. Log every match decision with its score; a drop in match confidence over time is your earliest signal that a system's UI or API changed.

### 3.2 Verification must cross paths

For anything that writes:

> **Verify through a different medium than the write.**

Wrote via L4 network interception → verify via L1 Graph RAG (once the BOD/Subspace event lands) or an L3 API read. Wrote via L5 UI → verify via L3 API.

Same-path verification proves only that you got a 200 back. Cross-path verification proves the system of record actually changed. For inventory, that distinction is the entire safety argument.

Treat **unverified as failed.** A step that succeeded but could not be verified escalates; it does not pass.

### 3.3 Escalation ladder (your three cases, made concrete)

| | Trigger | Action | Cost |
|---|---|---|---|
| **Case 1 — Fast path** | Recipe matched, confidence above floor | Deterministic replay of `network_plan`; assertions checked; **zero or near-zero LLM calls** | ~$0 |
| **Case 2a — Heal** | Locator miss / endpoint 404 / shape change | Rule-based candidate scoring on a11y fingerprint; if API shape changed, re-derive from a fresh interception | ~$0.001 |
| **Case 2b — Model escalate** | Heal fails | Flash-Lite with a11y tree + step intent + KB context; retry once; then vision model with screenshot | $0.01–$0.25 |
| **Case 3 — Human** | Model escalate fails, or step is flagged `requires_human` (MFA, approval, ambiguous business call) | Temporal signal → notify → Steel live-view takeover → **capture as new demo** → resume | human time |

Case 3 is a product surface, not a safety net. Build the operator queue properly: task, context, what was tried, live browser, one-click resume.

### 3.4 Promotion ladder — the missing governance layer

The deck's "capture human → learn" loop assumes the human was right. Clerks have workarounds, personal shortcuts, and occasionally wrong procedure. Without a gate you will faithfully scale one person's idiosyncrasy across every facility.

| Stage | Behaviour | Exit criterion |
|---|---|---|
| **Recorded** | Exists, never auto-runs | Reviewed by a supervisor |
| **Shadow** | Runs, produces a proposed action, does not execute | N runs matching what the human then did |
| **Assisted** | Executes, human confirms before commit | N verified successes, zero cross-path verification failures |
| **Autonomous** | Executes and verifies unattended | — (continuous monitoring; auto-demote on failure spike) |

Separate, stricter thresholds for **writes** than for **reads**. Nothing goes from recording straight to autonomous.

---

## 4. Four storage mechanisms — concrete shape

### 4.1 Graph RAG Database (read model)
- Postgres + pgvector to start; entities as first-class rows, embeddings for semantic lookup, graph edges as a join table. Move to a dedicated graph/vector store only when a query pattern demands it.
- Core entities: `order`, `sku`, `shipment`, `trailer`, `appointment`, `document`, `customer`, `location`, `task`.
- **Every record carries:** `source_system`, `source_watermark`, `observed_at`, `staleness`, `confidence`. Never a bare value.
- Conflicting values from two systems are **stored as a conflict**, not resolved silently. That conflict *is* the anomaly detector's input.
- Strict per-tenant isolation (`tenant_id` enforced at the query layer, separate namespaces for embeddings).

### 4.2 Workflow Repository
```
workflow_recipe
  id, tenant_id, objective_key{...}, version
  steps[]: { intent, network_plan, ui_plan, params[], assertions[], requires_human }
  branches[]: { condition, goto_step }
  promotion_stage, success_count, last_verified_at
  site_fingerprint          # invalidation trigger
  provenance                # which demo, which human, when
```

### 4.3 Knowledge Base
Per system, per tenant: auth profile refs (never secrets), endpoint catalogue with **discovered throttling limits**, MOCA command signatures, element fingerprints with last-validated timestamps, known modals and quirks, business rules.

### 4.4 LLM Cache
Semantic cache keyed on `(system, page/response fingerprint, step intent, a11y hash)`. This is what makes the Flash-Lite constraint survive. Cache the *decision*, not the prose. Layer Gemini context caching underneath for the KB prefix — but only cache content that is genuinely reused, since cache storage bills per token-hour.

---

## 5. The five keywords, answered in this architecture

### TIMEOUTS
Three tiers, and one hard external constraint:
- **Step timeout** (seconds): per medium. Note **Infor's ION gateway times out at 1 minute by default, 5 max** — long Infor operations must go async (submit + poll/BOD) rather than blocking.
- **Job timeout** (minutes–hours): Temporal workflow budget.
- **Human wait** (hours–days): Temporal signal with a long timer. Never a blocked thread, never a held HTTP connection.
- Every write carries an **idempotency key** = `hash(workflow_id, step_id, params)` so crash-replay cannot double-write. This is non-negotiable for inventory.
- Retries: exponential backoff + jitter on transient/gateway failures only. **Never auto-retry a validation failure** — that means the payload is wrong, and retrying just repeats the error.

### CACHE
Five layers, each with its own invalidation:
1. **Workflow recipes** — invalidate on `site_fingerprint` drift → route to heal + re-induce.
2. **Element fingerprints / endpoint catalogue** — invalidate on heal-rate spike (a *spike* means the system changed; patch the recipe, don't heal per-run).
3. **Auth/session state** (cookies, localStorage, MOCA session keys, OAuth tokens) — encrypted at rest, max-age enforced, refreshed ahead of expiry.
4. **LLM cache** — as §4.4.
5. **Graph RAG** — is itself a cache of source systems; staleness marker drives whether a read is trusted or refreshed.

### BIDIRECTIONAL
Two separate concerns, deliberately kept apart:
- **UI ↔ platform:** SSE for job progress (resumable via `Last-Event-ID`, pairs cleanly with Temporal checkpoints); WebSocket only where the user steers mid-run; GraphQL subscriptions over the same stream.
- **Human ↔ live browser:** CDP screencast / Steel live view, brokered through a relay with short-lived signed tokens so the viewer doesn't need to reach the same worker instance (a real constraint once workers autoscale).
- **Platform ↔ WMS:** deliberately *not* bidirectional. Inbound = event feeds (BOD, Subspace). Outbound = explicit workflow writes. See §0.2.

### QUADRANTS
Only relevant at L5 with vision, which should be rare in this design. When you do get there:
- Prefer **a11y coordinates** (exact, free) over model-predicted pixels — always.
- When vision is unavoidable, use **set-of-mark overlays** (numbered marks on candidate elements, model picks an ID) rather than free-hand coordinates. Grid/quadrant scaffolding helps as a secondary cue.
- **Always verify the click landed** before trusting it. Never let a cheap vision model free-hand coordinates on a write.

### GRAPHQL
- **Your platform's API:** GraphQL + subscriptions for the operator UI and job state.
- **The WMS's own internal calls:** the L4 interception layer. This is the point — the frontend still needs its endpoints after a redesign, so the intercepted call outlives the button that triggered it.

---

## 6. Concurrency and reliability

- **Temporal task queues** per medium: `browser`, `api`, `llm`. Browser workers are the scarce, stateful, crash-prone resource — isolate them.
- **Per-tenant concurrency caps** and fair scheduling so one facility's batch job can't starve another.
- **Per-system rate limiting is mandatory and must be discovered, not assumed.** Infor uses per-endpoint throttling policies with no published global limit; you must probe and record limits per API suite into the KB. Blue Yonder MOCA has no meaningful protection against you hammering it — you are responsible for not taking down a customer's WMS.
- **Circuit breaker per (tenant, system).** Trip on error-rate or latency; fail open to the human queue rather than retrying into a degraded system.
- **Browser workers:** one browser per worker, semaphore-capped pages, `--disable-dev-shm-usage`, bounded disk cache, scheduled restarts, handle `disconnected` and retry on a fresh instance. Budget ~200–500 MB per session; KEDA-scale on queue depth.
- **Observability:** OpenTelemetry traces spanning the whole workflow; rrweb session recordings for every L5 run (this doubles as your demo capture); an immutable audit trail of every write — actor, intent, before, after, verification result.

---

## 7. Model routing under the Gemini constraint

| Job | Model | Notes |
|---|---|---|
| Objective resolution / clarify loop | Flash-Lite | Structured output, cheap |
| Workflow matching | Embeddings + rules | Not an LLM decision |
| Deterministic replay | **none** | The whole point |
| Step adaptation on drift | Flash-Lite + a11y tree | Text, not pixels |
| Document extraction (BOL, packing slip) | Flash-Lite vision | Well-suited; this is OCR+structure, not GUI grounding |
| GUI grounding after heal fails | Dedicated computer-use model | Rare by design; the expensive tail |
| Demo → recipe induction | Larger model, offline | Batch, not latency-sensitive, worth the spend |

The economics only work if replay hit-rate climbs high (80–90%+) as each tenant's library matures. **Track hit-rate as a headline product metric** — if it plateaus low, the model constraint stops being viable and you'll know early.

Document extraction is worth calling out separately: it's the one place a cheap vision model is genuinely well-matched, and it maps directly to the deck's Cognitive ERP Agent.

---

## 8. Build order

**Phase A — Read-only, no writes (weeks 1–6)**
1. Sync layer: Infor BOD subscription + OpenDock Subspace + Blue Yonder MOCA read queries + SAP OData reads → Graph RAG.
2. Anomaly Detection Agent (cross-check sources → flag → escalate). **No writes.**
3. Natural-language chat over the Graph RAG.
4. Email intake + objective resolver + clarify loop.
5. The four deck reports (past-due, trailer-vs-SLA, 4-hour pick/put-away) — all reads.

This ships real value, proves the sync spine, and touches nothing. It is also the fastest path to "this found something we missed."

**Phase B — Workflow Builder (weeks 4–10, overlapping)**
6. Capture harness (network + a11y + input + audio + video).
7. Two-run diff parameterisation.
8. Dual-recipe emission (`network_plan` + `ui_plan`).
9. Recipe review UI for supervisors — the promotion ladder's entry gate.

**Phase C — Writes, narrowly (weeks 8–14)**
10. Executor with cross-path verification, on **one** write workflow — document processing into SAP (API-backed, reversible, well-understood).
11. Human takeover queue + Steel live view + demo capture on takeover.
12. Promotion ladder in shadow mode.

**Phase D — Coverage**
13. L4 interception where no API exists; L5 UI last.
14. Additional systems, additional workflows.

**Sequencing principle to hold throughout:**

> **Reads on the browser-automated systems. Writes on the API-backed ones.**

A wrong read is a bad report someone catches. A wrong write is corrupted inventory nobody catches for a week. Your deck's DEPTH/COVERAGE split already mostly obeys this — three of the four Blue Yonder items are reads. Make it an explicit rule rather than an accident.

---

## 9. Open decisions

1. **Deliberate demos vs passive capture.** Deliberate ("teach the system this task") is far cleaner on consent, PII, and — given the GreyOrange deck flags union requirements — on optics. Passive capture reads as monitoring. Decide before you build the harness; it's hard to retrofit.
2. **Blue Yonder deployment shape per site.** Cloud with Luminate REST entitlement, or on-prem MOCA? This determines whether L2/L3 is available or you're doing MOCA-direct. Ask before scoping.
3. **Who owns credentials.** Customer-held with delegated sessions is the defensible position; system-held credentials make you a much bigger security review target.
4. **ToS posture.** L4 interception and L5 automation of a vendor's UI needs explicit written customer authorisation. Get it in the pilot agreement, not later.
5. **What "one-click fix" writes to.** The anomaly agent's one-click fix is a write. It should go through the same executor, verification, and promotion ladder as everything else — not a shortcut path.
