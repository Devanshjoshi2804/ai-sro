# AGENTS.md

Instructions for coding agents working in this repository. Humans should read
[`docs/00-overview.md`](docs/00-overview.md) instead.

`CLAUDE.md` points here. Keep both in sync by editing only this file.

## What this project is

An operator demonstrates a warehouse task in a browser. The system records it and
turns two demonstrations of the same task into a parameterised, reviewable
**skill**.

Today the system captures, induces, **executes** and **is asked for work in
chat**. All three rungs are built — L1 network replay, L2 UI replay, L3 Gemini
computer use — and `HIGHEST_PERMITTED_STAGE` is `AUTONOMOUS`. The ceiling is not
what holds the line: `SkillVersion.promote` refuses the last rung until a
version is checkable and has ten consecutive clean runs, three consecutive
failures demote it automatically — a run that never reached the system at all is
not one of them — and a circuit breaker stops a run before it starts. The medium ladder and the
agent design are in [`docs/12-execution-and-agents.md`](docs/12-execution-and-agents.md)
— read it before building anything that runs a skill.

A demonstration is started by naming a URL, and **one** is enough: the two-run
diff still proves parameters where two runs exist, but a single sealed recording
becomes a skill through `UnderstandRecording`, with the calls kept as evidence
and the narrative and parameters marked as a model's reading of them. Its objective key is derived from the
evidence at seal (`application/capture/identity.py`); nothing asks the operator
to classify the task up front. See [`docs/06-glossary.md`](docs/06-glossary.md).

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

**A double must not implement the thing under test.** The extension's panel
hands the console a credential and waits for the console to announce itself.
The browser test passed for weeks against a stub console that announced
itself — while the real console never did, so the feature had never once
worked. A test whose double supplies the missing half proves the double. When
a test stands in for the other side of a contract, assert the real side
somewhere too: `frontend/src/features/console/embedded-credential.test.tsx`
exists for exactly that reason.

**A step's credentials come from the system it is calling.** Not from the
skill's objective key. A skill whose steps call two systems -- taught by
`TeachWorkflow` from two candidates a person joined -- would otherwise resolve
the first system's cookie, bearer, minted token and referer for every step, and
post one customer system's live session to another. `session_scope` is derived
per call in `execute_skill._perform`, and `resolve_headers` ignores a credential
reference that names a different system from the calling one. See
`docs/12-execution-and-agents.md`.

**A wire type change is not finished until `make types` has run.** It writes
`frontend/openapi.json` and `frontend/src/lib/api/generated.ts`, and both are
committed. Four fields once shipped without it and the pipeline's contract step
was failing for three commits while every local `make check` passed --
`tests/contract/test_the_committed_schema_is_current.py` now asks the same
question where the code is, so a stale document fails `make test-contract`.

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

- **A Steel session is not a browser.** `POST /v1/sessions` answers 201 whether
  or not Chrome came up, and a session with nothing attached is reported `idle`.
  `open()` waits for `live` and refuses otherwise, because handing that back
  produced a teaching session that said "Recording · run 1 of 2" over a viewer
  reading "the browser session has ended".
- **Steel advertises whatever `DOMAIN` says**, and unset it advertises its own
  inside-the-container address. The session player embeds that in its websocket
  (`ws://0.0.0.0:3000/v1/sessions/cast`), which a browser on the host cannot
  dial, so the live view sits on "Session connecting…" forever. `DOMAIN` and
  `CDP_DOMAIN` are set in `infra/docker-compose.yml` for this reason.
- **Steel does not notice its own dead browser.** When Chrome dies leaving a
  stale `/tmp/steel-chrome/SingletonLock`, the session stays `live` forever and
  holds the only browser a self-hosted Steel has. Releasing it answers **200 and
  changes nothing**, so `close()` checks afterwards and warns. The refusal from
  `open()` names the holder and says to restart the container, because that is
  the only thing that clears it.

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
| `domain/skill/promotion.py` | Governance ladder. The ceiling is open; `SkillVersion.promote` and `domain/skill/track_record.py` are what refuse autonomy. |
| `domain/execution/safety.py` | Circuit breaker and blast radius. Loosening a limit here is a decision about a customer's warehouse. |
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
