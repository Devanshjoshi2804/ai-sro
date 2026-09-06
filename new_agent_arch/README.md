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
| `RIG_INGEST_TOKEN` | `dev-only-not-a-secret` | the tenant's bearer: registers browsers, revokes them, opens every door |
| `RIG_INTENT_MODEL` | `gemini-3.8-flash` | model used for readings |
| `RIG_PLAN_MODEL` | `gemini-3.8-flash` | plans one command per step of a run |
| `RIG_RESCUE_MODEL` | `gemini-3.1-pro-preview` | the one rescue when a step does not hold |
| `RIG_COMMAND_DEADLINE_S` | `20` | how long a command to the browser may take |
| `RIG_TENANT` | `new` | tenant recorded on every row |
| `RIG_DAILY_USD_CAP` | `5.0` | what one day's model calls may cost, summed over readings, passes, runs and chat; over it the three doors answer 429, and one unpriced billed call stops the day too; `-1` is no cap |

Constants that are not settings, because changing one is changing what the
evidence means, live beside the code that reads them: `K_EARNED_RUNS = 3`
(`effects.py`, live runs verified by state before a job writes unasked),
`K_OFFER_AFTER = 2`, `K_WINDOW = 10`, `K_ENOUGH = 3`, `K_QUIET_HOURS = 24`
(`offers.py`, how a job's offers move when it is offered and rest it), and
`K_TEXT_IDENTITY_MAX = 40` (`shape.py`, the longest text a control may be
known by).

## One token per browser

The tenant's bearer is typed once, into the extension's options page. On
save the extension calls `POST /v1/devices/register` with it and keeps the
answer: a token of that browser's own, held on the rig as a hash, which opens
its own command socket and no other, approves only the run that browser is
driving, and names the browser on every call it makes. It does not open the
tenant's purse (`/v1/mine`, `/v1/chat`) or the other browsers' days
(`/v1/audit`, `/v1/gestures`, `/v1/streams`, `/v1/spend`, evidence): those
answer 403 to a device token. The tenant's bearer keeps working for
everything, so an older extension that never registered loses nothing. To
cut a browser off, which also drops its socket at once:

```bash
curl -X POST -H "Authorization: Bearer $RIG_INGEST_TOKEN" \
  http://localhost:8100/v1/devices/<device_id>/revoke
```

To rotate the tenant's bearer, set a new `RIG_INGEST_TOKEN` and restart the
rig. Every registered browser keeps working: what it holds is its own token,
compared against a hash in `device_tokens`, and the tenant's bearer is not
part of that. Only a browser that never registered -- one pointed at a rig
older than the registry, or one saved before it had a device id and not yet
signed in -- holds the tenant's bearer and needs the new one typed. The old
bearer stops opening every door the moment the rig comes back up; there is
no grace period, by design: two valid tenant bearers is one more than an
audit can name.

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
