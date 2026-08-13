# AI-SRO

An operator demonstrates a warehouse task in a browser. AI-SRO records
everything that happened and why, diffs two runs of the same task, and emits a
parameterised **skill** a supervisor can review.

v0 is the Workflow Builder only: demonstrations in, reviewable skills out.
Nothing executes, and nothing is written to any WMS.

## Five minutes

```bash
make up        # postgres, redis, minio, temporal, steel, otel
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
`frontend/.env.local` if you need to change any of it. The defaults match
`infra/docker-compose.yml`.

## Layout

```
backend/     Python, FastAPI. Ports and adapters, enforced by import-linter.
frontend/    Next.js App Router, TypeScript, Tailwind, shadcn/ui.
infra/       docker-compose for the local stack.
docs/        Architecture, standards, walkthroughs, ADRs.
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

## Where to read next

[docs/00-overview.md](docs/00-overview.md) — what this is, what v0 covers, and
what it deliberately does not.
