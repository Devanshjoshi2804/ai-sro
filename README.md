# AI-SRO

An operator does a task in a warehouse system, in their own browser. AI-SRO
watches, works out what the task was, and offers to do the next one — driving
that same browser, step by step, in front of them.

**It writes to the WMS.** That is the product, and it is the thing to be careful
about. What protects a customer's data is not that nothing is sent; it is the
gates in front of each write, and you should read them before running this
anywhere that matters:

- A write waits for a person to approve it, in the panel, with the command drawn
  in words first — until the job has earned the right to write unasked
  (`domain/execution/belts.py`: three runs whose every write was verified by
  state, never by a screenshot).
- A job asked for several things at once does the first one, shows what it made,
  and stops until somebody says to do the rest.
- A write whose effect the system can already see is not made again, and one
  job, one step and one set of values writes once inside half an hour.
- When the reading of a sentence is not sure which job was meant, it asks rather
  than picking.
- Nothing here can take a warehouse record back. A run says what it made; if the
  tenant's own evidence shows somebody deleting that kind of record, the run
  names that job — and still does not press it.

`knowledge-base/DAMAGE.md` records the state this project changed on a live
system during development and could not restore. Read it before you point this
at anything real.

## What it actually does

Two pipelines exist in the tree and only one of them is the product now:

- **The rig** — passive capture → a mining pass reads the day → a **job** with
  cited steps → a run the panel drives. This is what the extension offers and
  what a customer would see.
- **Skills** — the older path: deliberate demonstrations, induction from two
  runs, versions and promotion. Still reachable from the console and the API;
  the panel no longer offers it.

They have separate executors, separate routes, and different thresholds for
writing unattended. If you are reading this to decide what to build on, build on
the rig.

## Five minutes

```bash
make up        # postgres, minio, temporal, steel, otel  (no redis, whatever the docs say)
make install
make migrate
make api       # :8000  — http://localhost:8000/docs
make web       # :3000
```

| Service | URL |
|---|---|
| API docs | http://localhost:8000/docs |
| Web | http://localhost:3000 |
| Steel debug UI | http://localhost:3010/ui |
| Temporal UI | http://localhost:8080 |
| MinIO console | http://localhost:9001 |

Copy `backend/.env.example` to `backend/.env` and `frontend/.env.example` to
`frontend/.env.local`. The defaults match `infra/docker-compose.yml`.

The Chrome extension in `new-chrome-extension/` is loaded unpacked; there is no
packaging or distribution story yet, and its id is pinned in `manifest.json` and
referenced by `SRO_CORS_ORIGINS`.

## What it costs

Every mining pass and every step of every run is a model call. One tenant's
heaviest day in this repo's own store was **$66.95 across 214 mining passes**,
under the `SRO_DAILY_USD_CAP=100.0` that `backend/.env` carries (the code's own
default is $5).

The cap is a gate in front of the *next* ask, not a meter that stops one
mid-pass: a pass that starts under the cap runs to the end whatever it costs,
and the mining loop, the chat door and a new run answer 429 after that. There
is no global cap, only per-tenant-per-day. A model absent from
`domain/shared/prices.py` bills $0.00 and sets `unpriced`, which stops the day
as hard as the dollars do — 65 of this store's 303 passes are unpriced — and
the API logs a warning at boot naming any configured model it cannot price.

## Layout

```
backend/     Python, FastAPI. Ports and adapters, enforced by import-linter.
frontend/    Next.js App Router, TypeScript, Tailwind, shadcn/ui.
new-chrome-extension/  MV3 extension: the recorder, the driver, the side panel.
infra/       docker-compose: the local stack, and the deployed one.
docs/        Architecture, standards, walkthroughs, ADRs, deployment.
knowledge-base/  Recorded description of a live Blue Yonder SCE instance (evidence, not spec).
AGENTS.md    Agent-facing instructions (the open standard; CLAUDE.md points here).
```

## Quality gates

```bash
make lint    # ruff, ruff format, mypy --strict, import-linter, eslint, tsc
make test    # unit + integration
make check   # both
```

A deliberate `domain → infrastructure` import must fail `make lint`. That check
is itself a test of the foundation.

`tests/browser` is excluded from CI and runs only against a local `make up`.

## Where to read next

[CONTEXT.md](CONTEXT.md) — the whole picture in one file: the idea, what exists,
every decision and its consequence, what is next, and what is knowingly
unfinished. Parts of it describe an earlier, smaller system; the code is the
authority.

[docs/00-overview.md](docs/00-overview.md) — what this is and what it
deliberately does not cover.

[docs/18-deployment.md](docs/18-deployment.md) — running it on a VM: the two
images, the compose stack, and the five things that are quiet when wrong. It is
honest about what is missing; read it before promising a deployment date.
