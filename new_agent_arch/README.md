# rig

A standalone service that ingests what the browser extension captured and has
a model read each gesture, one at a time, into an intent. It is the model-first
architecture described in
[`docs/new-agent-doc-arc/`](../docs/new-agent-doc-arc/README.md); the pipeline
in [`backend/`](../backend/) is the other one, evidence-first.

## Why standalone

It shares the extension and the wire protocol with `backend/` and nothing
else — no imports, no shared database, no shared deploy. This exists to test
one claim (a model reading everything beats arithmetic reading call shapes)
against the running system, without either pipeline's outcome depending on
the other's code. Never import `sro.*`.

## Run it

```bash
make install   # uv sync
make serve     # :8100
```

`RIG_GEMINI_API_KEY` is required — `make serve` with none set fails
immediately, naming the variable, instead of starting a server that 404s
everything. The rest of the settings (env prefix `RIG_`, see
`src/rig/config.py`) have working defaults:

| Variable | Default | Meaning |
|---|---|---|
| `RIG_GEMINI_API_KEY` | *(none — required)* | the model that reads gestures |
| `RIG_DB_PATH` | `rig.db` | SQLite file |
| `RIG_INGEST_TOKEN` | `dev-only-not-a-secret` | bearer token the extension posts with |
| `RIG_INTENT_MODEL` | `gemini-3.8-flash` | model used for readings |
| `RIG_PLAN_MODEL` | `gemini-3.8-flash` | plans one command per step of a run |
| `RIG_RESCUE_MODEL` | `gemini-3.1-pro-preview` | the one rescue when a step does not hold |
| `RIG_COMMAND_DEADLINE_S` | `20` | how long a command to the browser may take |
| `RIG_TENANT` | `new` | tenant recorded on every row |

## Test it

```bash
make test      # pytest, no network calls
make lint      # ruff check, ruff format --check, mypy --strict
make mutants   # mutation score against the floor in scripts/mutation_floor.py
```

## Prove it

Two scripts measure the runner and the offer on the corpus in `rig.db`,
against a fake browser and no model, on a copy of the file:

```bash
uv run python scripts/dry_run.py      # every job dry, writes withheld and shown
make -C .. offer-replay               # each job's gestures through the real matcher
```

What they print is what `docs/new-agent-doc-arc/findings.md` quotes; nothing
in that section is a number they did not print.
