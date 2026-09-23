# Notes for `backend/src/sro/application/execution/approvals.py`

Comments and docstrings moved out of [`backend/src/sro/application/execution/approvals.py`](../../../../../../../backend/src/sro/application/execution/approvals.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/execution/approvals.py#L1): Docstring

> Runs parked in front of a person, waiting to be told the write may go out.
>
> A live write is shown before it is sent, and the run stops until somebody taps
> approve. This is the register of those parked runs: one `asyncio.Event` per
> run, set by the tap.
>
> An `asyncio.Event` holding a person's authorisation is a deliberate choice, not
> an oversight. Phase one of this port keeps the rig's process model: one asyncio
> task per run, on the worker that holds that browser's socket, with this
> register in the same process, and the approve and abort routes forwarded to
> that worker. A deployment therefore runs one API worker until phase two -- two
> workers and half the taps land in a process where nothing is waiting. The
> in-process device sockets beside this and the busy check both assume the same
> thing.
>
> Phase two makes the run a Temporal workflow: this wait becomes a signal with
> the same five-minute timeout, and abort becomes a signal too. That is the
> change that lets the API scale out, and it is the first item after this port
> rather than part of it.
>
> The other half of the rig's pair, `Aborts`, is already here as `Stops` next
> door in `stops.py`: a person stopping a run is a separate register from a
> person authorising one step, and one stop register is enough.
>
> Both halves of that seam are built, and this module's safety argument depends
> on the pair. In the rig, the abort route sets the flag and then releases the
> wait, so a parked run wakes at once instead of sitting out the full five
> minutes -- and because a release says only that the wait ended, the loop asks
> `Aborts` on the way out before it treats one as a person's yes. The loop's
> half: `run_workflow` asks `Stops` after `wait_for` returns and before the write
> goes out, so a release that was a stop aborts the run rather than writing. The
> route's half is `AbortWorkflowRun`, which sets `Stops` and then calls `approve`
> here, in that order. Not `StopRun`, which resolves a skill run through
> `uow.runs` and so cannot reach a run parked on this register at all.

## module, [line 5](../../../../../../../backend/src/sro/application/execution/approvals.py#L5): Note on the line above

Code: `K_APPROVAL_WAIT_S = 300.0`

> How long a live write waits for a tap before the run stops and asks. Five
> minutes is a person reading the panel, not a person who has gone home.

## `Approvals`, [line 8](../../../../../../../backend/src/sro/application/execution/approvals.py#L8): Docstring

> Which runs are parked on a person, and the event each one waits on.
>
> Keyed by `WorkflowRun.id`, which is a plain `str` -- the same id the run
> repository's `approve` and `awaiting` are keyed on, and not the skill run's
> `RunId`.

## `Approvals.register`, [line 12](../../../../../../../backend/src/sro/application/execution/approvals.py#L12): Docstring

> This run is about to park. Called before the step is saved, so a tap
> that lands before the wait starts finds an event to set rather than a
> 409 from a route that can see no one waiting.

## `Approvals.wait_for`, [line 15](../../../../../../../backend/src/sro/application/execution/approvals.py#L15): Docstring

> Whether the wait was released rather than timing out.
>
> Released, not authorised: an abort releases it too, and the caller asks
> `Stops` before it lets the write out.

## `Approvals.approve`, [line 30](../../../../../../../backend/src/sro/application/execution/approvals.py#L30): Docstring

> Whether anything was waiting on this run to be released.
>
> Not whether this tap was the one that authorised the step -- that is
> the run repository's `approve`, which is keyed by step and where the
> first tap wins.

## `Approvals.waiting`, [line 37](../../../../../../../backend/src/sro/application/execution/approvals.py#L37): Docstring

> The runs parked right now, for the panel's `awaiting` list.

## `Approvals.forget`, [line 40](../../../../../../../backend/src/sro/application/execution/approvals.py#L40): Docstring

> Once the run has ended. Drops the wait without releasing it: a run
> being cleaned up is not a run somebody approved.

## `Approvals.__init__`, [line 10](../../../../../../../backend/src/sro/application/execution/approvals.py#L10): Comment

Code: `self._waiting: dict[str, asyncio.Event] = {}`

> An instance, where the rig used a `ClassVar`. Nothing in production
> can tell the difference -- one container per process, one register --
> but class-level state is shared by every `Approvals` a test process
> ever builds, and a register of who may write is the last place to
> want one test's leftovers visible to the next.

## `Approvals.wait_for`, [line 18](../../../../../../../backend/src/sro/application/execution/approvals.py#L18): Comment

Code: `timeout: float = K_APPROVAL_WAIT_S,  # noqa: ASYNC109`

> The wait IS the timeout here, so ASYNC109's advice to let the caller
> wrap it does not apply: a second deadline on the same person is not
> the five minutes this module writes down.

## `Approvals.wait_for`, [line 28](../../../../../../../backend/src/sro/application/execution/approvals.py#L28): Comment

Code: `self._waiting.pop(run_id, None)`

> Popped on the way out, so a tap arriving after the run gave up
> finds nothing waiting and is told so, rather than authorising a
> write nobody is holding open any more.
