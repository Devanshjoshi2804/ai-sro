# Execution and agents

How a taught skill becomes work performed against a live WMS, and what stops it
doing the wrong thing. This is §3 of the solution design; the Workflow Builder
(§2) is what produced the skills it runs.

## The loop

```
utterance ──▶ intent ──▶ resolve ──▶ per item: execute ──▶ verify ──▶ record
                                          │                  │
                                          └── escalate ◀─────┘
```

An operator says what they want. Intent turns it into an objective key and
parameter values. Resolution finds the skill version and checks its stage.
Each item then runs through the medium ladder, and every attempt is verified
the same way regardless of which rung produced it.

## The medium ladder

| Rung | Medium | Comes from | Cost | Determinism |
|---|---|---|---|---|
| L1 | Network replay | `network_plan` | milliseconds | total |
| L2 | UI replay | `ui_plan` + AX graph | seconds | high |
| L3 | Vision | Gemini computer use | tens of seconds | none |

Each rung is slower, less predictable and more expensive than the one above.
That ordering *is* the product: a system that only had L3 would be a browser
agent, and a system that only had L1 would break on the first UI change.

**The ladder inverts safety, and that is worth saying plainly.** L1 is the most
trustworthy rung and the most likely to break when the WMS is upgraded. L3 is
the most capable and the least predictable. Auto-escalation means that when
things are *most* broken, the least deterministic medium takes control of a live
system. The decision to allow that was taken deliberately (see Decisions), and
it is the reason verification is built the way it is.

## Verification is the control, not a component

With all rungs escalating automatically and skills promoting themselves after N
clean runs, nothing else stands between a model and a live warehouse. Every
attempt is verified by:

1. **Assertions** extracted at induction — status, response fields, UI text.
2. **Read-back** — the demonstration almost always contains the `GET` the
   operator did *after* the mutation, to confirm it worked. That call is
   captured, parameterised by the same diff, and replayed to ask the WMS what it
   believes the state now is.
3. **Equivalence** — the outcome of an L2 or L3 attempt is checked against what
   L1 would have produced, not against "the model said it was done".

**Rule: a skill with no verifiable post-condition cannot become autonomous.** It
can run assisted indefinitely. Autonomy is earned by being checkable, not by
succeeding quietly.

### The post-condition is not always the state change

Measured on the target task. Every inventory adjustment demonstrated on the Blue
Yonder QA instance — including a change of one case — came back with *"The
Adjustment requested is greater than permitted limit - An Approval is Required.
The Location has been Locked."* The `PUT /data/WM/wm/inventory/adjust` returns
200, the LPN's on-hand quantity does **not** change, and a row appears in
Inventory ▸ Adjustments ▸ Approvals for a supervisor to approve or reject.

So a read-back asserting "on-hand is now the requested quantity" fails on a
successful run, and a verifier written to that assumption would classify every
correct execution as a failure. The post-condition for this task is *an
adjustment exists, pending approval, with these values*, and reaching the real
quantity needs a second human step this system does not perform.

Read as a rule rather than a Blue Yonder quirk: **the post-condition belongs to
the demonstration, not to the writer's intent.** What the operator's read-back
looked at after the write is the only honest source for it.

## Writes

Every mutating step carries an idempotency key derived from the run and the
step. A retried `POST /adjust` is otherwise a double adjustment, and a Temporal
activity retry is a completely ordinary event.

Mutation is already a domain property (`CapturedRequest.is_mutation`), so this
is enforced where the plan is built rather than remembered at the call site.

## L1 as built

A **run** (`domain/execution/run.py`) is the audit record: the skill version, the
stage it was at, the parameters it was given, the values it read out of the
system as it went, and one outcome per step. It is written after every step and
nothing in it is ever rewritten.

**What the stage means, concretely.** This is the difference the ladder makes,
and it lives in one property:

| Stage | Reads | Writes |
|---|---|---|
| `recorded` | refused | refused — nobody has reviewed it |
| `shadow` | sent for real | produced in full, **withheld** |
| `assisted` | sent for real | sent, and the run names the human who authorised it |
| `autonomous` | not available | — |

A withheld write is recorded with its URL and its idempotency key, so a
supervisor reviews the exact request before allowing the rung above.

**One step per activity.** `ExecutionWorkflow` calls `start_run`, then
`execute_step` per index, then `finish_run`. The step is the unit of durability
because it is the unit of damage: a worker that dies after step 7 resumes at
step 8, and an activity asked to repeat a step the run already records returns
what happened rather than doing it again. Retries are capped at one attempt for
every step, not only the writing ones — whether a step writes is knowable only
after it has been built, and a read losing a retry costs less than a write
gaining one.

**Where the credentials come from.** A skill's header plan holds references, not
values: `<blue_yonder/SG/cookie>` for the session, `<minted per run>` for CSRF.
The executor prefixes the tenant and resolves both out of the vault, so one
skill is usable by any tenant holding a login to that system and by no other.
A header that cannot be resolved stops the step; the call never goes out
degraded, because a request missing its session is a request as somebody else.

The honest gap: "minted" is aspirational. Blue Yonder issues
`CSRF-ENCRYPT-TOKEN` at login and no page, cookie or storage key exposes it, so
it is supplied through `POST /v1/connections/{id}/session-headers` by whoever can
read one — an operator, or the capture adapter, which sees every request header
of the session it is attached to. It expires with the session, and a run whose
header has expired fails at its first write rather than doing half a task.

## L2 as built

The measured problem first, because it decides the design: on this WMS the
accessibility tree carries no `button` role on three of four screens and never
carries a field's payload key, while the DOM ids are handed out in render order
— `ext-gen4443` is a different control after a reload. Replaying a demonstration
by CSS path or by role would find the wrong control or none.

So capture now also records **what the application calls the control**. The
recorder walks from the clicked element to its ExtJS component and stores the
`xtype`, the `itemId` and a two-segment `Ext.ComponentQuery` — the selector
language the application's own code uses. Induction turns that into an ordered
list of `ControlLocator`s: component query, test id, role and name, text, CSS
path. A signal that differs between the two demonstrations describes the record
rather than the control, so it becomes the parameter the diff already created
(the row for *this* LPN) or is dropped.

The driver resolves a component query by asking ExtJS, filtering to the visible
instance — this SPA keeps every screen it has ever shown — and then acts on the
resulting element through Playwright, so the gesture is a real click with real
actionability checks rather than a synthetic event the application may ignore.
Each step records which strategy matched: a step that only ever matches on the
last fallback is a skill about to break.

### The task is the unit that changes rung

A run that swapped medium half way through would leave the browser without the
screen state the earlier steps never produced, and a lone UI step would not find
its control. So the medium is a property of the **run**: `network` replays the
calls, `ui` performs the whole task in a browser. The escalation table in
`domain/execution/escalation.py` says which failures make the second choice
sensible; choosing it automatically belongs with Phase 5, because it is the same
decision as the circuit breaker.

Two refusals in that table are worth naming. A missing credential never
escalates — a browser cannot invent a session either. A system that did not
answer never escalates — pointing a browser at it turns an outage into a heavier
one. And a shadow run never drives the interface at all: a click is
indistinguishable from a call once it has happened.

## Teaching entry: the task names itself

An operator starts a demonstration by naming a URL. Nothing else is asked.

What the task *is* — its objective key — is read off the evidence when the run is
sealed. The call the demonstration ended on names the entity and the verb
(`PUT /data/WM/wm/inventory/adjust` is `inventory` / `adjust`), the query
parameter every call carried names the facility (`siteId=SG`), and the connection
that owns the host names the system (`blue_yonder`, which is what the vault scope
and the knowledge base call it — `bf56-kms-wms-web-np2.jdadelivers.com` is not).

This replaces a five-field form, and the reason is measured rather than
aesthetic: there were two such forms, they disagreed on the default direction,
and two people describe one task two ways. Induction pairs on **exact** equality,
so every disagreement produced two objectives that could never pair. Deriving
makes the key a property of what was done. Run 2 is started under run 1's derived
key, so a pair pairs by construction.

Same rule as parameter naming: no model is asked. Record ids are skipped when
naming (`/waves/W-8817/release` is about `wave`, not about `W-8817`), routing
segments (`data`, `api`, `v1`, `wm`) are skipped as facts about how the server is
wired, and background traffic never names anything because the frame excludes it
already.

A demonstration that asked the server nothing cannot be named this way. Sealing
it raises `unnamed_demonstration` and asks the operator for one line — the
exception, not the entry point.

## Agents

| Agent | Job | Model |
|---|---|---|
| Intent | utterance → objective key + parameters | Gemini Flash, structured output |
| Resolver | objective → skill version, stage, missing parameters | none |
| Executor | run one step at the highest rung that works | none for L1/L2 |
| Vision executor | L3 only | Gemini computer use |
| Verifier | did it hold, did the WMS actually change | none, plus model for ambiguity |
| Escalator | rung failed → next rung, or stop | policy as data |

**A Temporal workflow never calls a model.** Every LLM call is an activity.
A workflow is replayed after a restart, and a model that answers differently on
replay produces a different history — which destroys the audit trail, the one
thing an enterprise cannot lose here. This is not a style preference; it is what
makes the system explainable after an incident.

**Intent output is validated, never trusted.** The model returns a structure
that must resolve to an objective key we already know and parameters the skill
already declares. An utterance that resolves to nothing is a question back to
the operator, not an improvised call.

## Generated workflows

A skill induced from two demonstrations cites them: which recordings, who
performed them, when. A skill generated from a knowledge base cites nothing —
there is no evidence it was ever performed successfully.

Generated skills are therefore a distinct kind, visible as such, and they do not
enter the promotion ladder by the same door. The first time a generated skill
runs successfully against the live system *with verification passing*, it has
earned its first piece of provenance, and only then does it start counting.

## Egress

L3 sends screenshots and DOM of a customer's live WMS to Google; intent parsing
sends the operator's words. The enterprise agreed to *capture* everything — that
is storage, and it stays in their infrastructure. Egress is a different
conversation and is treated as one:

- Redaction before egress, not after: secrets, password fields, and the fields
  marked secret at capture time never leave.
- Every model call is logged with what was sent, what came back, and which run
  it belonged to.
- The set of destinations is configuration, so a deployment that may not use a
  hosted model can run L1 and L2 with L3 disabled.

## Decisions taken

| Decision | Choice | Consequence accepted |
|---|---|---|
| Write approval | Autonomous after N clean runs | The verifier is the only gate; it must be right |
| Escalation | All rungs automatic, verifier gates the result | Vision can drive a live WMS unattended |
| Knowledge base | Live sandbox + recorded traffic only | No spec to validate a generated call against |
| First slice | Full ladder on one task | Depth before breadth; one task proves the machinery |
| Target task | Blue Yonder inventory adjust | A write, with a natural read-back |
| Secrets | Env vars behind a port, real manager later | One adapter swap, not a migration |

A **clean run**, for promotion counting: every assertion passed, read-back
verified, and no escalation past L1. A run that needed vision is evidence the
skill is drifting from the system it was taught on — it resets the counter
rather than advancing it.

## Phases

0. **Secret capture hardening.** Blocking: passwords are captured verbatim today.
1. **L1 execution.** Execution domain, HTTP executor, idempotency, verification,
   deterministic workflow, audit.
2. **L2 UI replay.** Ancestry-based control finding, escalation policy as data.
3. **L3 vision.** Gemini computer use, redaction, egress logging.
4. **Chat and intent.** Thread, teach entry point, validated intent, batch preview.
5. **Autonomy.** Counters, circuit breaker, blast-radius limits.
