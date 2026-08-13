# AGENTS.md

Instructions for coding agents working in this repository. Humans should read
[`docs/00-overview.md`](docs/00-overview.md) instead.

`CLAUDE.md` points here. Keep both in sync by editing only this file.

## What this project is

An operator demonstrates a warehouse task in a browser. The system records it and
turns two demonstrations of the same task into a parameterised, reviewable
**skill**.

Today the system captures and induces. It does not execute: `HIGHEST_PERMITTED_STAGE`
is `SHADOW` and nothing is written to any WMS. The executor, the medium ladder
and the agent design are planned in
[`docs/12-execution-and-agents.md`](docs/12-execution-and-agents.md) — read it
before building anything that runs a skill.

Vocabulary is fixed in [`docs/06-glossary.md`](docs/06-glossary.md). Use those
words; do not invent synonyms (`demo`, `session`, `macro` are all wrong for
"recording").

## Commands

```bash
make up            # local stack: postgres, redis, minio, temporal, steel, otel
make install
make migrate
make api           # :8000
make worker        # Temporal worker — induction runs HERE, not in the API
make web           # :3000
make lint          # ruff + ruff format + mypy --strict + import-linter + eslint
make test          # unit + integration
make types         # regenerate frontend API types from backend OpenAPI
```

Backend commands run through `uv` from `backend/`. Never invoke `pip` or a bare
`python`.

Narrower loops:

```bash
cd backend
uv run pytest tests/unit -q                                  # fast, no Docker
uv run pytest tests/unit/domain/test_skill.py -q             # one file
uv run pytest -k "promotion" -q                              # one behaviour
uv run lint-imports                                          # the architecture guard alone
SRO_INTEGRATION_DATABASE_URL="postgresql+asyncpg://sro:sro@localhost:5432/sro_test" \
  uv run pytest tests/integration -q                         # against an existing Postgres

cd frontend
npm test                                                     # vitest
npx vitest run src/features/skill/components/skill-detail.test.tsx
```

**A code change is not live until the worker restarts.** Induction executes as a
Temporal activity in the worker process, so an API-only restart silently keeps
running the old induction. This has already cost debugging time twice.

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

Enforced by four `import-linter` contracts in `backend/pyproject.toml`. A
deliberate `domain → infrastructure` import must fail `make lint`; that check has
been verified to fire. If a change needs a contract relaxed, stop and ask — that
is an architecture decision, not a lint fix.

**A router never touches `container.unit_of_work()`.** Reads go through a use
case like everything else; a read that looks too small to deserve one is exactly
how the application layer gets bypassed. Mechanical check:

```bash
grep -rn "unit_of_work()" backend/src/sro/interface/    # must return nothing
```

## Directory responsibilities

| Path | Holds |
|---|---|
| `backend/src/sro/domain/` | Entities, value objects, invariants. Pure. |
| `backend/src/sro/application/ports/` | `Protocol` definitions — the seams |
| `backend/src/sro/application/*/` | Use cases and pure algorithms, grouped by capability |
| `backend/src/sro/infrastructure/` | Adapters: db, steel, blob, temporal, telemetry |
| `backend/src/sro/interface/http/` | Routers and wire schemas (`schemas.py`) |
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
- Domain objects never cross the HTTP boundary; use `interface/http/schemas.py`.

## Capture invariants

These were learned against a real browser and are easy to undo by accident.
Background in [`docs/03-backend-walkthrough.md`](docs/03-backend-walkthrough.md).

- **The page recorder installs idempotently by construction** (remove-then-add on
  `window`), never behind a boolean flag. `document.open()` unregisters every
  window listener while leaving both the window and document objects intact, so a
  flag on either reports "installed" after the listeners are gone — and capture
  goes silent for the rest of the session.
- **The adapter re-injects on `domcontentloaded`**, because init scripts do not
  re-run for a document rewrite.
- **Video is sampled with `Page.captureScreenshot`, never `Page.startScreencast`.**
  Chrome allows one screencast consumer per page and the newest one wins, so
  subscribing steals the stream from Steel's live view and silently freezes the
  browser the operator is driving. Proved by attaching two clients and watching
  the first receive zero frames; guarded by an integration test.
- **Nothing in flight is stranded**: `flush_incomplete()` emits exchanges that
  never reached `loadingFinished` rather than leaving them in the pending map.
- **A request arriving after a drain belongs to the previous action**, not to
  nobody. Only traffic with no frame at all is orphaned.
- `sro.observability.configure_logging` exists because uvicorn configures only
  its own loggers. Without it every capture diagnostic goes nowhere.
- **Credential values never reach storage.** The single exception to keeping
  everything: the page recorder drops the value of a credential field, and
  credential-named body fields are replaced before the body is written. Matched
  by field name on whole words, never by inspecting values. Watch the indirect
  routes — the accessible-name fallback reads `el.value`, and a blanked
  attribute can arrive as the string `"None"`. See
  [`docs/11-capture-completeness.md`](docs/11-capture-completeness.md).

Steel quirks, all worked around in `infrastructure/steel/client.py`: health is at
`/v1/health`; session URLs are reported as seen from inside its container; Chrome
strips the port from `webSocketDebuggerUrl`; `startUrl` is ignored for an
attached browser, so the adapter navigates itself.

## Testing

- `tests/unit` — fakes only, no Docker, no network, no real clock.
- `tests/integration` — real Postgres, Steel and Temporal. The only place SQL,
  transactions and CDP behaviour are proved. Skips itself when they are absent.
- `tests/contract` — the OpenAPI document, including that the committed copy
  matches the code.
- Never mock the domain or a pure function.
- Test names are sentences.

Integration fixtures **truncate every table** and refuse a database whose name
does not mark it disposable. Never point `SRO_INTEGRATION_DATABASE_URL` at the
development database; that has already destroyed demo data once.

Two workers on one task queue must be looking at the same data. The suite uses
its own queues because a developer's `make worker` is pointed at the development
database and will otherwise accept the suite's work and fail to find it.

## Do not change casually

| Path | Why |
|---|---|
| `backend/pyproject.toml` `[tool.importlinter]` | The architecture guard |
| `domain/skill/promotion.py` | Governance ladder. `HIGHEST_PERMITTED_STAGE` must not rise without an executor and cross-path verification. |
| `domain/recording/sensitivity.py` | Decides what may leave the evidence plane. Name-based by design; classifying by inspecting values is the inference ADR 004 forbids. |
| `infrastructure/steel/recorder.js` | See capture invariants above |
| `infra/docker-compose.yml` | Port map is deliberate; Steel is on 3010 so Next keeps 3000 |
| `frontend/next.config.ts` | `agentRules: false` stops Next generating competing agent files |
| `docs/06-glossary.md` | Renaming a concept is a repo-wide change |

## Data handling

Recordings capture **live customer payloads** from a WMS. Before adding a field,
a log line or an artifact, read
[`docs/10-security-and-data.md`](docs/10-security-and-data.md) and
[`docs/11-capture-completeness.md`](docs/11-capture-completeness.md).

Three planes: evidence keeps everything verbatim; a skill keeps the header set
and shape with secrets by vault reference; telemetry keeps neither bodies nor
secrets. Never log request or response bodies. Never emit a captured credential
into a skill.

## Future agentic modules

Read [`docs/09-agentic-standards.md`](docs/09-agentic-standards.md) and
[`docs/12-execution-and-agents.md`](docs/12-execution-and-agents.md) first.

- No LLM call belongs in `domain/` or in a Temporal workflow body. A workflow is
  replayed after a restart; a model that answers differently on replay destroys
  the audit trail.
- Model output is validated against what already exists — a known objective, a
  declared parameter — never trusted as free-form.
- Verification is the control, not a component: with automatic escalation and
  self-promoting skills, nothing else stands between a model and a live system.

## Pull requests

- Conventional commits (`feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`).
- `make lint && make test` green before opening.
- Behaviour change → a test. Architecture decision → an ADR in `docs/07-adr/`.
- Say what you did **not** do and why.
