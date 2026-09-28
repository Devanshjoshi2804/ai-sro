# Notes for `backend/src/sro/application/execution/stuck_runs.py`

Comments and docstrings for [`backend/src/sro/application/execution/stuck_runs.py`](../../../../../../../backend/src/sro/application/execution/stuck_runs.py). Each note names the code it explains (function or class, then the line in the current file).

## `CloseStuckRuns`, [line 23](../../../../../../../backend/src/sro/application/execution/stuck_runs.py#L23): Note

> D10. A run's workflow can end without running `finish` -- it timed out, the
> worker died, it was terminated, or the handoff failed -- and then its row
> stays `running` for ever: it keeps its tab and any parked lease, blocks the
> one-running-run-per-device index, and the panel shows it running. The worker
> runs this on each pass of the session keeper, before the keeper expires
> leases, so what a closed run lets go of is expired in the same pass.
>
> Each row is decided by `waiting.stuck` and closed by the repository's
> compare-and-set; one row failing is logged and does not stop the rest.

## `CloseStuckRuns._close`, [line 51](../../../../../../../backend/src/sro/application/execution/stuck_runs.py#L51): Note

> Only the sweep that won the compare-and-set releases anything or says
> anything, so a run is released and announced once. A Steel run is released
> through `RunSteps.release`, the same activity the workflow runs last: it
> closes the run's tab and ends a lease parked on a person for this run. The
> lease itself is the account's and expires through the keeper when nothing
> beats it; `Browsers.release` is for a claimed recording session, which a run
> never holds. The operator hears one line in their current thread through
> `SayWhatHappened`, the path a run's other notes take.

## `CloseStuckRuns._budget`, [line 77](../../../../../../../backend/src/sro/application/execution/stuck_runs.py#L77): Note

> The budget the run was started with, from its pinned job (or the job, for a
> row older than pinning) and the evidence it cites -- `start_on_steel`'s own
> arithmetic. A job that can no longer be found (retired, or never this
> tenant's) budgets at the floor rather than raising: a row whose job is gone
> is exactly the row nothing else will ever close.
