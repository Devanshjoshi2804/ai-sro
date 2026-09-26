# Notes for `backend/scripts/record_workflow_history.py`

Notes on [`backend/scripts/record_workflow_history.py`](../../../../backend/scripts/record_workflow_history.py). Each note names the code it explains (function or class, then the line in the current file) and says what the code does and why.

## `Recording`, [line 22](../../../../backend/scripts/record_workflow_history.py#L22): Class

> The real-Temporal tests in `tests/integration/test_run_workflow.py` connect
> through this client interceptor, which keeps the id of every workflow they
> start. With `SRO_RECORD_HISTORIES` set (`make record-histories`), each
> test's histories are saved to `tests/replay/histories`, which
> `tests/replay` replays on the current `RunWorkflow`. The tests' client
> identity is `runs-test`, so no host name reaches a history; every run id,
> tenant and value in them is the tests' own synthetic data.

## module, [line 19](../../../../backend/scripts/record_workflow_history.py#L19): Note

Code: `VERSION = hashlib.sha256(Path(workflows.__file__).read_bytes()).hexdigest()[:8]`

> Histories are named by a hash of `workflows.py`, so recording after a
> workflow change adds the new shape's histories and never overwrites the
> old ones: those are what prove a `workflow.patched()` branch still
> replays the runs in flight from before the change.

## `_without_stack_traces`, [line 47](../../../../backend/scripts/record_workflow_history.py#L47): Note

Code: `def _without_stack_traces(node: dict[str, Any]) -> dict[str, Any]:`

> A failure's stack trace carries the recording machine's absolute paths
> (a user name) and plays no part in replay, which compares commands only.
