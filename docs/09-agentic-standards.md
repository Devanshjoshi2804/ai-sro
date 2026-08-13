# Agentic standards

v0 makes **zero LLM calls**. This document exists so that the modules that will
— the objective resolver, the heal step, model escalation, document extraction —
land against a written standard rather than inventing one under deadline.

Read this before writing any code that calls a model.

## The deterministic boundary

The failure mode of production agents is a single model handling reasoning,
routing and execution: easy to prototype, brittle to operate.

So:

```
Temporal workflow   = deterministic plan.       No LLM call. Ever.
Temporal activity   = one LLM call or tool call. Retryable, timed, logged.
domain/             = rules.                     No LLM call. Ever.
```

A workflow body that calls a model cannot be replayed, which forfeits the entire
reason Temporal is in the stack. If a decision needs a model, the workflow calls
an activity and *branches on the returned value*.

Corollary: model output is **data crossing a trust boundary**. It is validated
against a schema before anything acts on it, exactly like an HTTP request body.

## Escalation, not omniscience

The ladder from the solution design, cheapest first:

| Tier | Trigger | Cost |
|---|---|---|
| Deterministic replay | Recipe matched above the confidence floor | ~$0 |
| Rule-based heal | Locator miss, endpoint shape change | ~$0 |
| Small model + a11y tree | Heal failed. Text, not pixels. | cents |
| Vision model | Text failed, and only then | expensive |
| Human queue | Model failed, or step is `requires_human` | human time |

Two rules:

- **Never start at the top.** Escalation is measured: log which tier resolved
  each step. Replay hit-rate is a headline product metric — if it plateaus low,
  the economics do not work and we need to know early.
- **Structured matching before semantic matching.** Skills are found by
  `ObjectiveKey`, with embedding similarity only as a tiebreaker among
  structurally-compatible candidates. A wrong match does the wrong thing
  confidently and fast, with no reasoning left in the cached path to catch it.

## Tools

Tool definitions are the agent's real API surface. In production agentic systems
the majority of input tokens are system prompts and tool schemas, so treat a tool
definition with the care of a public endpoint.

- One tool, one capability. No `do_thing(action="...")` dispatchers.
- Parameters are typed and validated. The model does not get to send free-form
  JSON into a WMS.
- Descriptions state **when not to use it**, not only when to.
- Tools that write are separated from tools that read, and write tools carry an
  idempotency key derived from `hash(workflow_id, step_id, params)`.
- A tool result is truncated and shaped for a model to read. Dumping a 200 KB
  response into context is a cost and a correctness problem.

## Context engineering

- Context is a budget, not a bucket. Every prompt has a stated token ceiling.
- Retrieve, do not stuff. The Knowledge Base entry for one system, not all of
  them.
- Cache the **decision**, not the prose: a semantic cache keyed on
  `(system, page fingerprint, step intent, a11y hash)`.
- Prefer the accessibility tree over screenshots. It is exact, cheap, and
  diffable; pixels are none of those.

## Guardrails

- **Writes are gated by the promotion ladder**, never by model confidence. A
  model saying it is sure is not evidence.
- **Verify through a different medium than the write.** Same-path verification
  proves a 200 came back, not that the system of record changed.
- **Unverified is failed.** Escalate, do not pass.
- Every write is attributed, idempotency-keyed and recorded in an immutable audit
  trail: actor, intent, before, after, verification result.
- Circuit breaker per `(tenant, system)`. Fail open to the human queue rather
  than retrying into a degraded WMS.
- Never auto-retry a validation failure. It means the payload is wrong, and
  retrying repeats the error at speed.

## Observability

Traces follow the OpenTelemetry **GenAI semantic conventions** — `gen_ai.*`
spans for `invoke_agent`, `execute_tool`, `invoke_workflow`, plus latency and
token-usage metrics.

These conventions are **pre-stable** (extracted to their own repository at
v1.42.0, no 1.0 release). Pin the version, isolate the mapping in
`infrastructure/telemetry/`, and expect churn. That isolation is the whole reason
to adopt them now rather than inventing private attribute names.

One trace spans the whole workflow: objective → match → step → tier → verify.

## Evals

Traces tell you what happened, not whether it was any good. Quality needs evals
in the same pipeline.

Minimum bar before any model-driven step is promoted past `shadow`:

- A fixture set of real recordings with known-correct expected outcomes.
- A regression run on every prompt or model change, not only on code changes.
- Scored on outcome, not on output text similarity.
- Shadow-mode results compared against what the human then did — that comparison
  is the ladder's exit criterion, and it is free once shadow mode exists.

A prompt change with no eval run is an untested deploy.

## Model routing

| Job | Model class |
|---|---|
| Objective resolution, clarify loop | Small, structured output |
| Skill matching | Embeddings + rules — not a model decision |
| Deterministic replay | **None.** That is the point. |
| Step adaptation on drift | Small model + a11y tree |
| Document extraction (BOL, packing slip) | Small vision model — genuinely well-matched |
| GUI grounding after heal fails | Dedicated computer-use model. Rare by design. |
| Demo → recipe induction | v0 uses **no model at all** — see ADR 004 |

Model identifiers live in configuration, never inline. Routing is a table, not a
chain of `if`s.
