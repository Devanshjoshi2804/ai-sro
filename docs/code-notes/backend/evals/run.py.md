# Notes for `backend/evals/run.py`

The three commands behind `make eval`, `make eval-ci` and `make eval-redact`.

## `frozen`, [line 86](../../../../backend/evals/run.py#L86): Design

> The case set is built from the database once, to
> `cases/<tenant>/<suite>.json`, and every later run reads that file. On
> the QA box mining keeps adding jobs and seen values, so cases rebuilt per
> run would drift between the baseline and the candidate. A rebuild is
> explicit (`make eval ... rebuild=1`) and is a new case set, so the same
> step retires that tenant's and suite's `baseline-<suite>.json` and its old
> answered cases in `results/<tenant>/<suite>/`, and prints what it retired.
> The next `baseline=1` run writes the new baseline. The first build retires
> the same way, so a hand-deleted case file cannot leave a baseline behind.

## `run_suite`, [line 103](../../../../backend/evals/run.py#L103): Design

> LIVE: reads the database and spends model money, billed to the tenant
> (`about(tenant=...)`): it lands in that tenant's `model_spend` and counts
> toward `daily_usd_cap`, so a large run can make the cap refuse that day's
> live mining or mail. Each suite asks through the asker production uses for
> its prompt (`Suite.asker`: mining's is the patient one). Answered cases go
> to `results/<tenant>/<suite>/` for `eval-redact`. `--baseline` writes
> `results/<tenant>/baseline-<suite>.json` only when the gate passed;
> `--limit` is refused with it.
>
> On the QA box, the image carries no `evals/` (`.dockerignore`); mount it:
>
>     docker compose -f infra/docker-compose.deploy.yml run --rm \
>       -v <box>/backend/evals:/app/evals api \
>       python -m evals run --suite mining --tenant greyorange --baseline
>
> The mount must be writable by the container's user `sro`, and the
> service needs `SRO_INTERPRETATION_ENABLED=true` and the Gemini key (the
> `api` service has both).

## `run_ci`, [line 136](../../../../backend/evals/run.py#L136): Design

> Offline: each committed case's recorded answer must conform to its prompt's
> schema, and the production entry point, fed that answer through
> `Replayed`, must still score it a pass. `--live` asks the real model
> through each suite's production asker, billed to the tenant `eval`. An
> empty set fails: a guard with nothing in it guards nothing.

## `write_candidates`, [line 161](../../../../backend/evals/run.py#L161): Design

> Redacts the answered cases of one tenant into `candidates/<tenant>/<suite>/`
> (gitignored), only those whose id is in the current frozen case set: an
> answer left from an earlier set never becomes a candidate. Nothing moves to `ci/` without a person reading the file.

## `_repair`, [line 37](../../../../backend/evals/run.py#L37): Design

> `SUITES` maps a name to a factory, because the repair suites are built
> from the container's session broker, page driver and vision driver. A
> repair suite has no replayed cases, so without a container (`run_ci`
> offline) it refuses rather than build a suite that could not open a page.
> `run_ci` builds only the suites that have a `ci/<name>` folder; repair has
> none.

## `reachable`, [line 56](../../../../backend/evals/run.py#L56): Design

> A case scored with `latency_s == -1` never reached its page (the repair
> suite's unreachable case). It is left out of the report's rates and
> counted in `Report.unreachable`, so an unreachable page neither passes
> nor fails the lane.
