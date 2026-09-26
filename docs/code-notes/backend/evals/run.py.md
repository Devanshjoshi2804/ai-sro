# Notes for `backend/evals/run.py`

The three commands behind `make eval`, `make eval-ci` and `make eval-redact`.

## `run_suite`, [line 35](../../../../backend/evals/run.py#L35): Design

> LIVE: reads the local database and spends model money. Every case is saved
> under `cases/` (gitignored) before it is run and again with the model's
> answer after, so a later `eval-redact` has the recorded answer to replay.
> The report is compared with `results/baseline-<suite>.json` if one exists;
> `--baseline` replaces it only when the gate passed. `--limit` takes the
> first N cases, for a bounded run; a baseline written from a limited run is
> only comparable with runs of the same limit. The calls run under
> `about(tenant=...)`: the meter refuses a call named for no tenant, and the
> eval's spend is billed and capped like any other. `run_ci --live` bills
> the tenant `eval`.

## `run_ci`, [line 60](../../../../backend/evals/run.py#L60): Design

> Offline: each committed case's recorded answer must conform to its prompt's
> schema, and the production entry point, fed that answer through
> `Replayed`, must still score it a pass. `--live` asks the real model
> instead. An empty `ci/` passes.

## `write_candidates`, [line 78](../../../../backend/evals/run.py#L78): Design

> Writes redacted copies to `candidates/` (gitignored). Nothing moves to
> `ci/` without a person reading the file.
