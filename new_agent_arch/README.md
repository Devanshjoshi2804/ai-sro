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
| `RIG_TENANT` | `new` | tenant recorded on every row |

## Test it

```bash
make test      # pytest, no network calls
make lint      # ruff check, ruff format --check, mypy --strict
```
