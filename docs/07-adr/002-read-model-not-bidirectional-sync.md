# ADR 002 — Read model plus explicit write path, never bidirectional sync

**Status:** accepted · applies from Phase A onward

Nothing in v0 writes to a WMS. This ADR is recorded now because the constraint
shapes the schema that v0 establishes, and retrofitting it later is expensive.

## Context

The original design described bidirectional sync: the knowledge graph updates
operational systems automatically, and source-system changes flow back.

Two systems auto-writing to each other is a write-write conflict engine. It
produces sync loops, last-write-wins data loss, and — because this is inventory —
silent corruption that surfaces days later as a physical count discrepancy nobody
can trace.

## Decision

CQRS. The graph is a **read model**. It never writes to a source system.

- **Inbound (sync):** event feeds and polls → read model. One direction.
  Idempotent, replayable, with source-system watermarks.
- **Outbound (writes):** only ever through the executor, as an explicit,
  attributed, idempotency-keyed, verified action. Never a side effect of sync.
- The read model holds *last observed* state with a confidence and staleness
  marker — never *authoritative* state. The source system stays the system of
  record.
- Conflicting values from two systems are **stored as a conflict**, not resolved
  silently. That conflict is the anomaly detector's input.

Two rules that follow, for when writes exist:

**Verify through a different medium than the write.** Same-path verification
proves only that a 200 came back. Cross-path verification proves the system of
record changed.

**Unverified is failed.** A step that succeeded but could not be verified
escalates; it does not pass.

## What v0 establishes

Every record that will ever hold observed state carries `source_system`,
`observed_at` and a staleness marker from the first migration. v0's own tables
follow the same shape.

## Consequences

- A weaker-sounding claim than "bidirectional sync", and a much stronger system.
- It is also the version that survives an enterprise security review.
- Writes are slower to build, because each needs an explicit path and a
  cross-path verification.
