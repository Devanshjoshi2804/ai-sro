# ADR 009 — The extension is a capture source and a driver, not a second system

**Status:** accepted · v0

## Context

Once observation and execution move into the operator's own browser, there is an
obvious and wrong way to build it: let the extension talk to its own endpoints,
keep its own model of a workflow, and run what it recorded.

That would produce a second execution path with none of what the first one grew:
the promotion ladder, the circuit breaker, blast-radius limits, step
dispositions, withheld writes, self-heal, verdicts, and the audit trail that says
who authorised a write. Every one of those was built because of something that
went wrong, and a second path around them is a second warehouse to corrupt.

## Decision

The extension implements **existing ports** and feeds the **existing capture
seam**. It introduces no new execution concept.

- **Capture.** The extension emits the same JSON `recorder.js` already emits and
  the same network/page/AX shapes `cdp_mapping` already parses. It reaches
  `IngestCaptureEvents` through a new HTTP door
  (`POST /v1/observations`), and from there everything is the code that already
  ran.
- **Execution.** `RemoteUiDriver` implements `UiDriver`; `RemoteHttpCaller`
  implements `HttpCaller`. Each puts one command on the device's websocket and
  awaits one reply. `ExecuteStep` cannot tell which driver it has, so the ladder,
  the breaker, the dispositions and the verdicts apply unchanged.

**Rejected: an extension-side workflow runtime.** Faster to demo, and it puts an
unverified recording on a live WMS with nothing between it and the data.

**Rejected: replacing Steel.** The extension only runs when the operator's laptop
is open. Scheduled and unattended work still needs a browser that is always
there. Steel stays; the extension is a second driver, chosen per run.

**Rejected: bending `Recording` to hold the passive stream.** `seal()` requires
an objective key and at least one frame, and the whole recording is one JSONB
column. A day of continuous capture is neither one task nor one row. Observation
gets its own thin context, and a `Recording` is materialised only when a
candidate is taught — which keeps every downstream consumer untouched.

## Consequences

New surface is small: two adapters, one ingest use case, one websocket router,
and a mining context that is pure functions over evidence. Nothing in `domain/`
changes.

The costs:

- **A driver on the far side of a network is a driver that can vanish.** A closed
  laptop mid-run is a failed step. It surfaces as the existing `UiUnavailable` /
  `TargetUnreachable`, which the run already knows how to record, but it will
  happen more often than a local Playwright call failing.
- **A command deadline is now part of correctness.** A late reply is discarded,
  so the extension must answer every command exactly once, including with an
  error.
- **Writes happen in the operator's real session.** That is the feature — no
  delegated credentials — and it means a run's blast radius is the operator's own
  authority. The existing limits still apply, and a write still needs a named
  authoriser.
