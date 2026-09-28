# Notes for `backend/src/sro/domain/execution/waiting.py`

Comments and docstrings moved out of [`backend/src/sro/domain/execution/waiting.py`](../../../../../../../backend/src/sro/domain/execution/waiting.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/domain/execution/waiting.py#L1): Docstring

> A run that ended waiting to hear from somebody outside this system.
>
> `asking.py` already says the good half of this: the state is the thread. A run
> that comes up short ends, and what it could not find becomes a question in the
> operator's own conversation, carrying everything established so far -- so
> nothing is held open, no process has to stay up, and the answer arrives days
> later against a row in Postgres. That is a dormant pause and it works.
>
> It has one address. The question is asked in the panel and answered in the
> panel, and the person who knows the answer is very often not the person with
> the panel open: the mail that asked for the job named a description and no
> code, and the only one who can say what the code should be is whoever sent it.
> Asking them means asking outside, and an answer that arrives outside has to be
> able to find its way back to the run that is waiting for it.
>
> So a pause may name the conversation it is waiting on -- a mailbox and a thread
> id -- and that name is what a reply is matched against. Nothing here reaches
> the mailbox; this is the arithmetic around the name.
>
> **A pause without a deadline is not a pause, it is an abandonment.** Somebody
> is asked, somebody does not answer, and a run waits with a row that says
> "waiting" until the table is read by an archaeologist. So a wait says when it
> stops being one, and after that instant a reply on that thread is a reply to
> something nobody is holding open any more -- which is a thing to say plainly
> rather than to act on, because acting on it would write a warehouse record
> somebody asked for a week ago and has long since made by hand.

## module, [line 11](../../../../../../../backend/src/sro/domain/execution/waiting.py#L11): Note on the line above

Code: `K_PATIENCE = timedelta(days=7)`

> How long a run waits to hear back before the wait is over.
>
> A week rather than a day, because the person being asked is not sitting in
> front of this: a request that arrived on a Friday is answered on a Monday, and
> a wait that expired over a weekend would turn the one case this exists for --
> the colleague who has the answer -- into the one case it fails.
>
> And a week rather than a month, because what is waiting is a write. A warehouse
> record asked for in early September and created in October is not the record
> anybody wanted, and by then whoever asked has made it by hand.

## `Awaiting`, [line 19](../../../../../../../backend/src/sro/domain/execution/waiting.py#L19): Docstring

> The outside conversation a run is waiting to hear back on.

## `Awaiting`, [line 20](../../../../../../../backend/src/sro/domain/execution/waiting.py#L20): Note on the line above

Code: `server: str`

> The connector the conversation lives in -- `gmail` today. Named rather
> than assumed: a deployment with two mailboxes has two threads that can
> perfectly well share an id.

## `Awaiting`, [line 23](../../../../../../../backend/src/sro/domain/execution/waiting.py#L23): Note on the line above

Code: `until: str`

> The ISO instant this stops being a wait. See the module docstring.

## `waiting_on`, [line 26](../../../../../../../backend/src/sro/domain/execution/waiting.py#L26): Docstring

> A wait on that conversation, or None where there is no conversation.
>
> None rather than a wait on `""`: a run that names no thread is not waiting
> on one, and a blank would match the next blank and resume a run on a reply
> to something else entirely.

## `still_waiting`, [line 38](../../../../../../../backend/src/sro/domain/execution/waiting.py#L38): Docstring

> Whether anything is still holding this question open.
>
> An unreadable deadline counts as over. A run whose `until` cannot be parsed
> is one nothing can say the age of, and treating an unknown age as young is
> how a row from last year answers a mail that arrived this morning.

## `as_said`, [line 69](../../../../../../../backend/src/sro/domain/execution/waiting.py#L69): Docstring

> The wait as it is stored on a run row.

## `read_wait`, [line 75](../../../../../../../backend/src/sro/domain/execution/waiting.py#L75): Docstring

> The wait a stored row holds, or None where it holds nothing usable.
>
> Given `object` and not a typed shape, because this is JSON off a column and
> anything that pretends otherwise is pretending. A row half-written by an
> older deployment is not a wait.

## `asks_a_person`, [line 48](../../../../../../../backend/src/sro/domain/execution/waiting.py#L48): Note

> Whether a run's wait on a mail thread is live: the run stopped short with
> `needs` (the extension's ask), or it is running and parked on a question
> (a Steel run's `progress.asking`). A run working its steps or finished is
> asking nobody, whatever `awaiting` still holds. The SQL `waiting_on`
> keeps the same rule in its WHERE clause.

## module, [line 13](../../../../../../../backend/src/sro/domain/execution/waiting.py#L13): Note on the line above

Code: `STUCK = "the run stopped responding and was closed after its time ran out"`

> The reason a stuck run is closed with (D10). It lands on the run's last step,
> as every other close's reason does, and in the one line said to the operator.

## module, [line 15](../../../../../../../backend/src/sro/domain/execution/waiting.py#L15): Note on the line above

Code: `Durably = Literal["open", "closed", "unknown"]`

> What the durable side says of a run's workflow. `unknown` is a workflow it
> never heard of -- a run whose handoff was lost, or an extension run, which has
> none -- and leaves the decision to the clock.

## `stuck`, [line 57](../../../../../../../backend/src/sro/domain/execution/waiting.py#L57): Note

> Whether a `running` row is stuck: its workflow ended without running `finish`
> (timed out, lost with its worker, terminated) and nothing will ever close it.
>
> - The durable side is the authority where it answers. `open` is never stuck,
>   however late: Temporal's own `execution_timeout` is the same
>   `budget + K_BUDGET_MARGIN_S` and will end it. `closed` is stuck at once,
>   even while it asks a question: the answer is signalled to the workflow, and
>   a closed workflow can take no answer.
> - Otherwise the clock decides: `started_at + budget + K_BUDGET_MARGIN_S`,
>   the budget counted once per thing of a list run, since `run_budget` prices
>   one pass of the job and a list runs it once per line.
> - A run waiting on a person -- `asks_a_person`, or a step parked `awaiting`
>   an approval -- is waiting, not stuck, and the clock never closes it.
>
> Ceiling: the budget is recomputed from the pinned job and its evidence. If
> retention has removed that evidence since the start, the recomputed budget is
> smaller than the one the workflow was given, which only matters where the
> durable side cannot answer.
