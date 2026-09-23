# Notes for `backend/scripts/status.py`

Comments and docstrings moved out of [`backend/scripts/status.py`](../../../../backend/scripts/status.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../backend/scripts/status.py#L1): Docstring

> What each running process says it is running, beside what the tree says.
>
> ``make status``. Written after an API that had been up for two days kept serving
> a rule that had been fixed an hour earlier: the message named a real rule and
> quoted real parameter names, so every step of the diagnosis pointed at the code,
> and the answer was in the process table.
>
> Reports, never enforces. Two revisions at once is what a rolling deploy looks
> like, and a check that refused to run on a mismatch would stop one dead.

## module, [line 20](../../../../backend/scripts/status.py#L20): Note on the line above

Code: `UNMARKED = "unmarked"`

> What a process started before this change reports: nothing.
>
> Shown rather than hidden. A process that is genuinely running and cannot say
> which code it is running is the oldest thing on the machine, and that line is
> the one this tool exists to print.

## module, [line 22](../../../../backend/scripts/status.py#L22): Note on the line above

Code: `POLLED_WITHIN = timedelta(seconds=120)`

> How recently a poller must have been seen for its revision to be reported.
>
> Temporal keeps poller history for around five minutes, so ``described.pollers``
> is largely a record of the recently dead. Reporting all of it had this tool
> naming two phantom stale workers on a machine running exactly one -- and a
> status line that cries wolf gets ignored, which is the failure this whole thing
> exists to prevent.
>
> A worker long-polls on a 60s timeout and the server stamps ``last_access_time``
> as each poll arrives, so a live worker refreshes at least once a minute. Two of
> those cycles: one missed refresh is forgiven, and a killed worker is off the
> line inside two minutes instead of five. Much tighter and a worker between polls
> would vanish, which is its own kind of lie.

## `tree`, [line 25](../../../../backend/scripts/status.py#L25): Docstring

> What the checkout is on right now -- the thing everything else is compared to.

## `worker_revisions`, [line 46](../../../../backend/scripts/status.py#L46): Docstring

> Asked of Temporal, which already knows every process polling its queues.
>
> The worker puts its revision in the identity it polls with, so this needs no
> table and no log file, and -- unlike a row written at startup -- it is empty
> when the worker has died rather than stale. Counted rather than listed: two
> workers on one revision is a normal Tuesday, two on different revisions is a
> deploy in flight, and the difference is worth seeing.

## `reported`, [line 72](../../../../backend/scripts/status.py#L72): Docstring

> The revision out of a ``pid@host@revision`` Temporal identity.
>
> Two fields is Temporal's own default, which is what a worker from before
> this change polls with.

## `api_revision`, [line 42](../../../../backend/scripts/status.py#L42): Comment

Code: `except Exception as why:`

> Any failure at all means the same thing here: nobody answered.

## `worker_revisions`, [line 58](../../../../backend/scripts/status.py#L58): Comment

Code: `except Exception as why:`

> Same again -- no answer is the answer.

## `worker_revisions`, [line 68](../../../../backend/scripts/status.py#L68): Comment

Code: `order = sorted(alive.items(), key=lambda seen: (seen[0] != here, seen[0]))`

> The working tree's own revision first, so anything that is not it reads as
> the exception rather than being hunted for in an alphabetical list.
