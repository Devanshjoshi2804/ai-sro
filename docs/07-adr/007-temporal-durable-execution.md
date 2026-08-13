# ADR 007 — Temporal for anything that outlives a request

**Status:** accepted · v0

## Context

Three things in this product outlive an HTTP request:

- A demonstration lasts minutes and holds an expensive browser session that must
  be reaped if the operator walks away.
- Induction is a multi-stage pipeline where a mid-stage failure must not lose the
  recordings.
- Later phases add human waits measured in hours or days — an approval, an MFA
  prompt, a takeover queue.

The alternatives were a job queue (Celery, RQ, Arq) plus hand-written state
machines, or durable execution.

## Decision

Temporal, from v0, with two workflows:

| Workflow | Responsibility |
|---|---|
| `RecordingWorkflow` | Session lifecycle, stop signal, reaper timer for abandoned browsers |
| `InductionWorkflow` | Pair → diff → emit → assert, retried per activity |

Task queues split by resource: `browser` and `default`. Browser workers are the
scarce, stateful, crash-prone resource; a browser crash must not stall induction.

Adopted now rather than later because the human-wait pattern is the one a job
queue models worst. A wait measured in days is a Temporal timer plus a signal —
never a blocked thread and never a held HTTP connection. Retrofitting that onto a
queue means rewriting the state machine.

### The determinism boundary

```
workflow   = deterministic orchestration. No I/O, no clock, no randomness, no LLM.
activity   = one effectful call. Retryable, timed, logged.
```

This boundary is also the agentic boundary: when the executor arrives, an LLM
call is an activity and the workflow branches on its validated result. A model
call inside a workflow body forfeits replay, which is the entire reason Temporal
is here. See [../09-agentic-standards.md](../09-agentic-standards.md).

### Timeouts

Three tiers, plus one external constraint worth recording now: Infor's ION
gateway times out at 1 minute by default and 5 maximum, so long Infor operations
must go async — submit, then poll or wait for an event — rather than blocking.

| Tier | Scale |
|---|---|
| Step | seconds, per medium |
| Job | minutes to hours, the workflow budget |
| Human wait | hours to days, a timer plus a signal |

Every write carries an idempotency key `hash(workflow_id, step_id, params)` so
crash-replay cannot double-write. Non-negotiable for inventory.

## Consequences

- One more service in the local stack, and Temporal's own Postgres databases.
- Workflow code has real constraints: no `datetime.now()`, no `random`, no direct
  I/O. Enforced by the SDK's sandbox, and it is the same discipline the `Clock`
  port already imposes.
- Crash recovery, retries, timers and human waits stop being application code.
- Temporal's Python SDK emits OTel traces that follow the GenAI semantic
  conventions, so agent spans arrive on the same pipeline as everything else.

## How it is wired (v0)

The interface layer talks to `application/ports/durable.py`, never to Temporal.
`TemporalDurableExecution` is the only adapter, and the composition root is the
only place that knows it exists.

- **Induction** goes through `InductionWorkflow` and the caller waits for the
  result. Waiting is not a workaround: induction takes milliseconds and the
  supervisor wants the skill back. What the workflow buys is a retryable history
  when it fails, starting from the sealed recordings rather than from a browser
  session nobody can reproduce. A bad pair is marked non-retryable, and the
  adapter unwraps Temporal's nesting so the caller sees *why* — "a skill needs
  two different recordings", not "Activity task failed".
- **The session deadline** is started when a recording starts and signalled when
  it finishes. It is explicitly best effort: the recording is already durable by
  then, so a scheduler outage costs a deadline, never a demonstration. That
  asymmetry is the whole reason `watch_recording` returns a bool instead of
  raising.

Task queues split by scarcity rather than by feature: `browser` holds work tied
to a scarce browser slot, so a slow induction can never starve session reaping.
They live in `queues.py` because both the worker and the client need them, and
the worker imports the composition root.
