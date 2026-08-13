# AGENTS.md

Instructions for coding agents working in this repository. Humans should read
[`docs/00-overview.md`](docs/00-overview.md) instead.

`CLAUDE.md` points here. Keep both in sync by editing only this file.

## What this project is

An operator demonstrates a warehouse task in a browser. The system records it and
turns two demonstrations of the same task into a parameterised, reviewable
**skill**. Nothing executes skills yet — v0 captures and induces only.

Vocabulary is fixed in [`docs/06-glossary.md`](docs/06-glossary.md). Use those
words; do not invent synonyms (`demo`, `session`, `macro` are all wrong for
"recording").

## Commands

```bash
make up            # local stack: postgres, redis, minio, temporal, steel, otel
make install
make migrate
make api           # :8000
make web           # :3000
make lint          # ruff + mypy --strict + import-linter + eslint  <- must pass
make test          # unit + integration
make types         # regenerate frontend API types from backend OpenAPI
```

Backend commands run through `uv` from `backend/`. Never invoke `pip` or a bare
`python`.

## The one rule that is not negotiable

Dependencies point inward:

```
interface  ──▶  application  ──▶  domain
                     ▲
              infrastructure
```

- `domain/` imports stdlib only. No FastAPI, SQLAlchemy, Temporal, httpx.
- `application/` imports `domain` and its own `ports/`. Never an adapter.
- `infrastructure/` is imported by `sro/container.py` and nothing else.

This is enforced by four `import-linter` contracts in `backend/pyproject.toml`.
If a change needs one relaxed, stop and ask — that is an architecture decision,
not a lint fix.

## Directory responsibilities

| Path | Holds |
|---|---|
| `backend/src/sro/domain/` | Entities, value objects, invariants. Pure. |
| `backend/src/sro/application/ports/` | `Protocol` definitions — the seams |
| `backend/src/sro/application/*/` | Use cases and pure algorithms, grouped by capability |
| `backend/src/sro/infrastructure/` | Adapters: db, steel, blob, cache, temporal, telemetry |
| `backend/src/sro/interface/http/` | Routers and wire schemas |
| `backend/src/sro/container.py` | Composition root |
| `frontend/src/features/` | One folder per feature slice |
| `docs/` | Design rationale. Lives here, never restated in code. |

## Conventions

Full detail: [`docs/02-code-standards.md`](docs/02-code-standards.md). The parts
agents get wrong most often:

- **Comments say why, code says what, `docs/` says why-it-was-designed-so.**
  Module docstrings are one or two lines. Do not write design essays in source
  files. Prose should stay under ~25% of lines in `src/`.
- **Business rules live on entities**, not in use cases. A rule in a use case
  holds only on the paths that call it.
- `tenant_id` is the first parameter of every repository method, never defaulted.
- Every timestamp is timezone-aware.
- Use cases take `RequestContext` first, dependencies injected in `__init__`.
- New effect (I/O, time, randomness) → a port + a fake in
  `tests/unit/fakes.py`. New pure calculation → just a function, no port.
- Domain objects never cross the HTTP boundary; use `interface/http/schemas/`.

## Testing

- `tests/unit` — fakes only, no Docker, no network, no real clock.
- `tests/integration` — testcontainers. The only place SQL and transactions are
  proved.
- Never mock the domain or a pure function.
- Test names are sentences.

## Do not change casually

| Path | Why |
|---|---|
| `backend/pyproject.toml` `[tool.importlinter]` | The architecture guard |
| `domain/skill/promotion.py` | Governance ladder. `HIGHEST_PERMITTED_STAGE` must not rise without an executor and cross-path verification. |
| `infra/docker-compose.yml` | Port map is deliberate; Steel is on 3010 so Next keeps 3000 |
| `docs/06-glossary.md` | Renaming a concept is a repo-wide change |

## Data handling

Recordings capture **live customer payloads** from a WMS. Before adding a field,
a log line or an artifact, read
[`docs/10-security-and-data.md`](docs/10-security-and-data.md). Never log request
or response bodies. Never emit captured headers into a skill.

## Future agentic modules

The executor phase will run LLM calls. Before writing any of it, read
[`docs/09-agentic-standards.md`](docs/09-agentic-standards.md). No LLM call
belongs in `domain/` or in a Temporal workflow body.

## Pull requests

- Conventional commits (`feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`).
- `make lint && make test` green before opening.
- Behaviour change → a test. Architecture decision → an ADR in `docs/07-adr/`.
- Say what you did **not** do and why.
