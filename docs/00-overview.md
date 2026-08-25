# AI-SRO v0 — overview

## What this is

An operator demonstrates a warehouse task in a browser. The system watches,
records what happened, and turns two demonstrations of the same task into a
parameterised, reviewable **skill**.

That is skill-based learning — §2 (Workflow Builder) of
[`ai-first-sro-solution-design.md`](../ai-first-sro-solution-design.md).

```
demonstrate ──▶ capture ──▶ seal ──▶ induce (two runs) ──▶ review ──▶ shadow
```

## What v0 does

1. Starts a browser session an operator drives from a live-view URL.
2. Captures network calls, the accessibility tree, input events and a screencast.
   Narration audio is optional.
3. Normalises the stream into ordered **action frames** and seals the recording.
4. Diffs two sealed recordings of the same objective to produce a skill: steps,
   parameters with evidence, assertions, and two independent execution plans per
   step.
5. Shows it in a review UI where a supervisor promotes it to `shadow`.

## What v0 deliberately does not do

No execution or replay. No writes to any WMS. No graph read model, no sync layer,
no anomaly detection, no email intake, no objective resolver. No promotion past
`shadow`. No real identity provider.

No LLM calls at all. The only optional one is narration transcription, and its
default binding is a no-op.

The seams for those exist — ports, the `promotion_stage` enum, `tenant_id` on
every row. Nothing else is pre-built.

## Start here

```bash
make up        # postgres, redis, minio, temporal, steel, otel
make install
make migrate
make api       # :8000
make web       # :3000
```

| Service | URL |
|---|---|
| API | http://localhost:8000/docs |
| Web | http://localhost:3000 |
| Steel debug UI | http://localhost:3010/ui |
| Temporal UI | http://localhost:8080 |
| MinIO console | http://localhost:9001 |

## Reading order

| | |
|---|---|
| [01-architecture.md](01-architecture.md) | Layers, the dependency rule, aggregates, tenancy |
| [02-code-standards.md](02-code-standards.md) | Conventions tooling cannot enforce |
| [03-backend-walkthrough.md](03-backend-walkthrough.md) | Add a use case end to end |
| [04-frontend-walkthrough.md](04-frontend-walkthrough.md) | Add a feature slice end to end |
| [05-testing.md](05-testing.md) | What to test where, and what never to mock |
| [06-glossary.md](06-glossary.md) | One name per concept |
| [07-adr/](07-adr/) | Why the load-bearing decisions were made |
| [08-contributing.md](08-contributing.md) | Branching, commits, PR checklist |
| [09-agentic-standards.md](09-agentic-standards.md) | Rules for the LLM-driven modules of later phases |
| [10-security-and-data.md](10-security-and-data.md) | Tenancy, credentials, what a recording contains, retention |
| [11-capture-completeness.md](11-capture-completeness.md) | What is captured, and why nothing is dropped |
| [12-execution-and-agents.md](12-execution-and-agents.md) | The medium ladder, verification, and the execution agents |
| [13-blue-yonder-knowledge-base.md](13-blue-yonder-knowledge-base.md) | What we recorded about the target WMS, and what it corrects |
| [14-extension-protocol.md](14-extension-protocol.md) | The frozen contract between the extension and the backend |
| [15-observation-to-tasks.md](15-observation-to-tasks.md) | A day of tabs to a named task, and what a model may decide about it |
| [16-what-others-have-solved.md](16-what-others-have-solved.md) | Published work and open source that solves problems this one has, mapped to our files |

Agents read [../AGENTS.md](../AGENTS.md) instead of this file.
