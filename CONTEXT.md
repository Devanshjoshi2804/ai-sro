# AI-SRO — full context

One document, self-contained: what this is, what exists today, every decision
taken and why, and what happens next. Written to be handed to a person or a tool
that has never seen the repository.

Repository: `bitbucket.org/lab89/ai-sro` · latest commit `a430743`
Deeper reading: [`docs/00-overview.md`](docs/00-overview.md) and the ADRs in
[`docs/07-adr/`](docs/07-adr/). Agent-facing rules: [`AGENTS.md`](AGENTS.md).

---

## 1. The problem

Warehouse operators do the same tasks in a WMS (Blue Yonder, Manhattan, Infor)
hundreds of times a day: adjust inventory, release a wave, confirm a pick. The
work is repetitive, the systems are old, and nobody will rebuild them.

Automating this the usual way means an integration project per customer, per
system, per version. RPA scripts break the first time a page changes. API
integrations require documentation that customers often cannot produce.

## 2. The idea

**An operator demonstrates the task. The system learns it.**

They do it twice. The system records everything — every network call, the
accessibility tree at each click, what was typed, what came back — and *diffs the
two runs*. What changed between them is a parameter. What stayed the same is
structure. That difference is the whole trick: nothing is inferred by a model,
so nothing is invented.

The result is a **skill**: a reviewable, versioned recipe with provenance
pointing back at the two demonstrations it came from.

Later, an operator says "update these six SKUs" and the skill runs — first as a
direct API call, falling back to driving the UI, falling back to a vision model,
with every attempt verified.

**Why this is different from a browser agent:** an agent reasons about the screen
every time, which is slow, expensive and non-deterministic. This reasons once, at
teaching time, from evidence — and then replays deterministically, keeping the
model as a fallback rather than the mechanism.

---

## 3. What exists today (built, running, verified)

The **Workflow Builder** — demonstrations in, reviewable skills out. Nothing
executes; `HIGHEST_PERMITTED_STAGE = SHADOW` and no WMS is written to.

Proven end to end against real infrastructure: start a demonstration from the UI,
drive a real browser, seal it, do it again, induce, review, promote.

```
POST http://…/api/waves/${wave_id}/release
body: {"wave":"${wave_id}","quantity":7}
Authorization:  <blue_yonder/DC07/authorization>   vault reference
X-Trace:        <minted per run>                   fresh each call
X-Warehouse-Id: ${warehouse_id}                    varied → parameter
X-Facility:     DC03                               constant → literal
Referer/Host:   <set by the client>                the client's to set
parameters: wave_id ['W-3001','W-4002'], warehouse_id ['WH-NORTH','WH-SOUTH']
assertions: http_status 200 · response /status == "released"
```

### What is captured

At **every human gesture** (click, type, select, key, upload, scroll):

- The gesture itself, from a script injected into every page. CDP reports what
  the *page* did; only this reports what the *human* did.
- `Accessibility.getFullAXTree` — the whole graph, ignored nodes kept so ancestry
  survives. This gives `dialog "Adjust" > form > button "Confirm"`, which is what
  distinguishes the third Save button on a page.
- A screenshot.

**Continuously**: every request and response with full headers, bodies, cookies
sent and set, **CDP initiator chains** (the JS stack that caused the call — the
"why"), timings, redirects, failures; console output; navigations, dialogs,
downloads, popups; and a screencast encoded to H.264 as frames arrive.

### How it is stored

Three planes, deliberately separated:

| Plane | Holds | Where |
|---|---|---|
| **Evidence** | Everything verbatim | `recordings.frames` JSONB + blobs in object storage |
| **Skill** | Header set and shape; secrets by vault reference only | `skills.versions` JSONB |
| **Telemetry** | Never bodies, never secrets | OTel |

An `ActionFrame` is one thing the human did plus everything the page did in
response. A body too large to inline keeps its blob URI — a `Body` that is
neither inline nor pointing at a blob *raises*. Nothing is silently dropped.

### How it is marked

Two runs are aligned and diffed. A value that **changed** becomes `${parameter}`
with both observed values recorded as evidence for the reviewer. A value that
**held** stays literal. A value appearing in a later response becomes *derived* —
never prompted for.

Every header lands in one of four visible states: vault reference, minted per
run, set by the client, or semantic (literal or parameter). Only replayable
headers are diffed — a session cookie varies per session and a trace id per call,
and parameterising those would ask the operator questions nobody can answer.

Each version cites its provenance: which two recordings, who, when. Promotion
moves one rung at a time: `recorded → shadow → assisted → autonomous`, and today
it stops at `shadow`.

### Stack

Python 3.12 · FastAPI · SQLAlchemy 2 / Postgres+pgvector · Temporal · MinIO ·
Steel (self-hosted browser) · Playwright over CDP · PyAV · OpenTelemetry ·
Next.js 16 + TypeScript + Tailwind + shadcn/ui + TanStack Query.

Ports and adapters across four layers, **enforced by import-linter**, not by
convention — a deliberate `domain → infrastructure` import fails the build, and
that has been verified to fire.

```
interface  ──▶  application  ──▶  domain
                     ▲
              infrastructure          (imported only by container.py)
```

Quality gates, all green: ruff · ruff format · mypy --strict · import-linter 4/4
· 111 backend unit+contract tests · 17 integration tests against real Postgres,
Steel and Temporal · 10 frontend tests.

---

## 4. What we are building next

An operator opens a chat-style thread. A **+** offers "teach a workflow", which
opens a browser session inside the thread. They demonstrate; the system learns.
Later they type what they want, and the skill runs.

### The medium ladder

| Rung | Medium | Comes from | Cost | Determinism |
|---|---|---|---|---|
| **L1** | Network replay | `network_plan` | milliseconds | total |
| **L2** | UI replay | `ui_plan` + AX graph | seconds | high |
| **L3** | Vision | Gemini computer use | tens of seconds | none |

Each rung is slower, less predictable and more expensive than the one above.
That ordering *is* the product.

**The ladder inverts safety, and this is stated plainly rather than hidden:** L1
is the most trustworthy rung and the most likely to break when the WMS is
upgraded; L3 is the most capable and the least predictable. Automatic escalation
means that when things are *most* broken, the least deterministic medium takes
control of a live system. That was accepted deliberately (§5), and it is why
verification is built the way it is.

### Agents

| Agent | Job | Model |
|---|---|---|
| Intent | utterance → objective key + parameters | Gemini Flash, structured output |
| Resolver | objective → skill version, stage, missing parameters | none |
| Executor | run one step at the highest rung that works | none for L1/L2 |
| Vision executor | L3 only | Gemini computer use |
| Verifier | did it hold; did the WMS actually change | none, plus model for ambiguity |
| Escalator | rung failed → next rung, or stop | policy as data |

Orchestrated by Temporal. **A workflow never calls a model** — every LLM call is
an activity. A workflow is replayed after a restart, and a model that answers
differently on replay destroys the audit trail, which is the one thing an
enterprise cannot lose after an incident.

### Verification is the control, not a component

With every rung escalating automatically and skills promoting themselves, nothing
else stands between a model and a live warehouse. Each attempt is verified by:

1. **Assertions** extracted at induction — status, response fields, UI text.
2. **Read-back** — the demonstration almost always contains the `GET` the operator
   did *after* the mutation, to check it worked. That call is already captured and
   already parameterised by the same diff, so it is replayed to ask the WMS what
   it now believes.
3. **Equivalence** — an L2 or L3 outcome is checked against what L1 would have
   produced, never against "the model said it was done".

**Rule: a skill with no verifiable post-condition cannot become autonomous.** It
may run assisted indefinitely. Autonomy is earned by being checkable.

**Every mutating step carries an idempotency key.** A retried `POST /adjust` is
otherwise a double adjustment, and a Temporal activity retry is an ordinary event.

---

## 5. Decisions taken, with the consequence accepted

| Decision | Choice | Consequence |
|---|---|---|
| Scope of v0 | Workflow Builder only | No executor until it is built properly |
| Parameterisation | Diff two runs, never infer | Teaching requires two demonstrations |
| Browser | Steel, self-hosted | Sessions are a scarce resource to manage |
| Capture | Everything, nothing scrapped | Storage holds live customer payloads |
| Secrets | Labelled, never deleted; vault reference in skills | A real vault is required before production |
| Write approval | Autonomous after N clean runs | The verifier is the only gate; it must be right |
| Escalation | All rungs automatic, verifier gates the result | Vision may drive a live WMS unattended |
| Knowledge base | Live sandbox + recorded traffic only | No spec to validate a generated call against |
| First slice | Full ladder on one task | Depth before breadth |
| Target task | Blue Yonder inventory adjust | A write, with a natural read-back |
| Secret storage | Env vars behind a port, real manager later | One adapter swap, not a migration |
| Repository | One repo, not three | The OpenAPI contract stays enforced by the build |

A **clean run**, for promotion counting: every assertion passed, read-back
verified, and **no escalation past L1**. A run that needed vision is evidence the
skill is drifting from the system it was taught on — it resets the counter rather
than advancing it.

---

## 6. Phases

| Phase | Contents | State |
|---|---|---|
| **0** | Secret capture hardening | In progress — blocking |
| **1** | L1 network execution: execution domain, HTTP executor, idempotency, verification, deterministic workflow, audit | Next |
| **2** | L2 UI replay by accessibility ancestry; escalation policy as data | |
| **3** | L3 Gemini computer use; redaction before egress; model-call logging | |
| **4** | Chat and intent; teach entry point; validated intent; batch preview | |
| **5** | Autonomy: counters, circuit breaker, blast-radius limits | |

**Phase 0 is blocking and small.** Password fields are captured verbatim today —
the page recorder sends the value of every `change` event regardless of input
type. Teaching a Blue Yonder login would put the password into the evidence plane
as plain text and into a UI plan as a literal. Nothing may be recorded against a
real WMS login until this is fixed.

---

## 7. Known limits, stated rather than hidden

- **Two runs cannot distinguish noise from meaning.** A header carrying a fresh
  random value on every call is indistinguishable, by diffing alone, from a value
  the task genuinely varies. Classification is extended by *name* (`trace`,
  `nonce`, `idempotency`, …) because naming is a decision the target system
  already made; inspecting values would be the inference this design forbids.
  Residue: a per-call value under an unguessable name becomes a parameter. The
  reviewer sees it, with both observed values, before promotion.
- **A request that starts before its click** — a debounced handler firing late —
  is attributed to the previous frame. The initiator chains needed to fix this are
  captured; assembly does not yet use them.
- **Generated workflows have no provenance.** A skill written from a knowledge
  base cites nothing. Those must be a distinct kind and must not enter the
  promotion ladder by the same door.
- **Egress.** L3 sends screenshots and DOM of a live WMS to Google. Capture stays
  in the customer's infrastructure; egress is a separate conversation, with
  redaction before rather than after.
- **`sec-*` and browser-managed headers** vary on their own and are marked
  client-set rather than replayed.

## 8. Operational notes that cost time to learn

- **Induction runs in the Temporal worker.** An API-only restart silently keeps
  running the old code. Restart the worker on every deploy.
- **Integration fixtures truncate every table** and refuse a database whose name
  does not mark it disposable — after pointing them at the development database
  destroyed demo data once.
- **Two workers on one task queue must share data**, or one will accept work it
  cannot find.
- **Steel**: health is `/v1/health`; it reports URLs as seen from inside its
  container; Chrome strips the port from `webSocketDebuggerUrl`; `startUrl` is
  ignored for an attached browser.
- **The page recorder must install idempotently by construction**, never behind a
  flag: `document.open()` unregisters window listeners while leaving the flag
  standing, and capture goes silent for the rest of the session.
- **Never `Page.startScreencast` on a page a human is watching.** Chrome allows
  one consumer and the newest wins, so it steals Steel's live view and freezes
  the operator's browser while capture carries on regardless.
- **A monitoring surface must poll in the background.** The operator is looking
  at the browser, not at the console tab; a paused interval freezes the step
  count and the completion countdown while capture continues server-side.

## 9. Waiting on someone else

- **Bitbucket Pipelines** cannot be enabled until 2FA is set up on the account;
  the config is committed and inert, and `main` has no branch protection.
- **Blue Yonder sandbox** URL and credentials, to build Phase 1 against reality.
- **Gemini API key** for Phases 3 and 4.

## 10. Getting it running

```bash
make up        # postgres, redis, minio, temporal, steel, otel
make install
make migrate
make api       # :8000  — http://localhost:8000/docs
make worker    # Temporal worker — induction runs here
make web       # :3000
make check     # every gate: lint, types, architecture, tests
```

`frontend/.env.local` sets the tenant; demo data lives under `acme`.
