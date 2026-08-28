# Architecture

## The layers

```
interface  ──▶  application  ──▶  domain
                     ▲
              infrastructure
```

Dependencies point inward only. `infrastructure` implements ports declared by
`application`, and is imported by exactly one module: `sro.container`.

| Layer | Contains | May import |
|---|---|---|
| `domain` | Entities, value objects, invariants | stdlib only |
| `application` | Use cases, port Protocols, pure algorithms | `domain` |
| `infrastructure` | SQLAlchemy, Steel, MinIO, Redis, Temporal, OTel | `application`, `domain` |
| `interface` | FastAPI routers, request/response schemas | `application`, `domain` |

This is not a convention. It is four `import-linter` contracts in
`backend/pyproject.toml`, run by `make lint` and by CI. Adding
`from sro.infrastructure...` to a domain module fails the build.

**Verify the guard is alive** — this should fail:

```bash
echo "import sro.infrastructure" >> backend/src/sro/domain/shared/errors.py
make lint-backend    # expect: contract "Domain is pure" BROKEN
git checkout backend/src/sro/domain/shared/errors.py
```

## Why ports and adapters here

The systems this platform automates are not knowable in advance. Blue Yonder is
MOCA on-prem at one site and Luminate REST at another; Infor is an ION gateway
with per-endpoint throttling nobody has documented; some steps have no API at
all. Each of those is an adapter swap, and each will happen after the domain
logic is written.

Ports also buy the thing that keeps development fast: the entire application
layer runs against in-memory fakes. `make test-unit` needs no Docker and
finishes in well under a second.

What ports are **not** for: a single implementation with no second use in sight.
See [02-code-standards.md#ports](02-code-standards.md#ports).

## Aggregates

Two, and only two in v0.

**Recording** — evidence of one person doing one task once. Mutable while
capturing, immutable after `seal()`. Skill provenance cites recordings, and a
citation is worthless if the cited evidence can still change.

**Skill** — what was learned from two recordings. Versions are append-only:
re-inducing produces v2 and never edits v1, so nothing a supervisor already
approved can change underneath them.

## Tenancy

Every persisted row carries `tenant_id`, and every repository method takes a
`TenantId` as its **first positional parameter with no default**. Scoping is
therefore a mypy question, not a code-review question.

`NotFound` is raised identically whether a row is missing or belongs to another
tenant. Distinguishing the two would confirm that an id exists somewhere else.

Ids are distinct types (`SkillId`, `RecordingId`, …) rather than bare `str`, so
passing one where another belongs is a type error, and two ids of different
kinds never compare equal at runtime.

## Promotion ladder

```
recorded  ──▶  shadow  ──▶  assisted  ──▶  autonomous
```

| Stage | Behaviour |
|---|---|
| `recorded` | Exists, never runs. Awaits supervisor review. |
| `shadow` | Proposes an action, executes nothing. |
| `assisted` | Executes, human confirms each commit. |
| `autonomous` | Executes and verifies unattended. |

Two rules, enforced in `domain/skill/promotion.py` rather than in a service, so
they hold on every path — HTTP, Temporal, or a future auto-promotion job:

1. **No skipping.** A promotion moves exactly one rung. "Recorded straight to
   autonomous" is the failure the ladder exists to prevent.
2. **Evidence, not a ceiling.** `HIGHEST_PERMITTED_STAGE` is `AUTONOMOUS`, and
   what holds the line is `SkillVersion.promote`: the last rung is refused
   unless the version is checkable (some step has an assertion) and has ten
   consecutive clean runs. A constant could always have been edited; a clean-run
   streak cannot be. Three consecutive failures demote automatically — failures
   of the skill, not of the network: a run that never reached the system it was
   aiming at counts towards neither. See `docs/12-execution-and-agents.md`.

Demotion is not reachable through promotion. Auto-demotion on a failure spike is
a separate, monitored action — deliberately not wired to a review-UI button.

## Writes and the read model

Writes go out only through a run of a reviewed skill, at `assisted` or above,
carrying an idempotency key and the name of the human who authorised them. The
constraint from the solution design holds: the platform is a **read model plus an
explicit write path**, never bidirectional sync. See
[07-adr/002-read-model-not-bidirectional-sync.md](07-adr/002-read-model-not-bidirectional-sync.md).

## Durability

Temporal owns anything that outlives a request:

| Workflow | Responsibility |
|---|---|
| `RecordingWorkflow` | Session lifecycle, stop signal, reaper timer for abandoned browsers |
| `InductionWorkflow` | Pair → diff → emit → assert, retried per activity |

Task queues split by resource: `browser` (stateful, scarce, crash-prone) and
`default`. A browser worker crash must not stall induction.

## Where things are

```
backend/src/sro/
  domain/
    shared/        ids, errors, ObjectiveKey
    recording/     Recording, ActionFrame, ElementFingerprint, artifacts
    skill/         Skill, SkillVersion, plans, parameters, assertions, promotion
  application/
    ports/         Protocols — the seams
    capture/       raw events → ActionFrames
    recording/     start, ingest, attach artifact, finish
    induction/     align, diff, name, assert, emit, induce
    skill/         promote
  infrastructure/  adapters (db, steel, blob, cache, temporal, telemetry)
  interface/http/  routers, schemas, error mapping
  container.py     composition root — the only importer of infrastructure
```
