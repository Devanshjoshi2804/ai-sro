# Notes for `backend/src/sro/interface/http/v1/routers/agents.py`

Comments and docstrings moved out of [`backend/src/sro/interface/http/v1/routers/agents.py`](../../../../../../../../../backend/src/sro/interface/http/v1/routers/agents.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## `heartbeat`, [line 88](../../../../../../../../../backend/src/sro/interface/http/v1/routers/agents.py#L88): Comment

Code: `for line in body.said:`

> What the browser decided since the last beat, straight into the same log
> the ladder narrates into. Trimmed here rather than trusted: a device is
> not a trusted writer, and a line long enough to bury a log is a line
> somebody would have to grep around.
>
> AFTER the beat, which is where the browser proves it is itself. These
> used to be written first, so anything holding a device id -- a namespace,
> not a credential -- could put lines of its choosing into this tenant's
> log without ever answering for them. The id is no longer interpolated
> either: `refuse_unless_itself` attributes the request to the browser, so
> every one of these carries it the way every other line does.

## `arrival_fire`, [line 227](../../../../../../../../../backend/src/sro/interface/http/v1/routers/agents.py#L227): Comment

Code: `raise NotFound("no such arrival")`

> Not `Conflict`: from the browser's side this is "that rule is not
> about this page", which is the same answer as a rule that does not
> exist -- and telling the two apart tells a caller which pages this
> operator has rules for.

## `arrival_fire`, [line 229](../../../../../../../../../backend/src/sro/interface/http/v1/routers/agents.py#L229): Comment

Code: `await container.record_attempt().execute(`

> What the operator asked for and what came of it -- including the case
> that used to leave nothing at all behind. `FireTrigger` skips rather
> than starting a run whose required inputs are empty, and a skip answers
> 202 with a `run_id` of null: from the browser it is a press that did
> nothing, and until this there was no record anywhere that it had
> happened.

## `watch_matched`, [line 305](../../../../../../../../../backend/src/sro/interface/http/v1/routers/agents.py#L305): Comment

Code: `if watch.workflow_id is not None:`

> A skill or a mined job. Both answer the same two questions -- what is this
> called, and what did the mail not say -- out of different places: a
> skill's runnable version declares its inputs, a job declares its
> parameters. `_watch_of` has already refused a watch that names neither.

## `watch_matched`, [line 318](../../../../../../../../../backend/src/sro/interface/http/v1/routers/agents.py#L318): Comment

Code: `missing = [] if version is None else blank_inputs(version, running_with)`

> A skill with no runnable version is not a shortage of values, and
> saying "nothing said shipment_id" about one would send somebody
> looking in the mail for a value that was never the problem. The press
> answers that one, with the trigger's own words.

## `watch_matched`, [line 320](../../../../../../../../../backend/src/sro/interface/http/v1/routers/agents.py#L320): Comment

Code: `thread = await container.read_threads().current(ctx)`

> Said into the conversation as well as answered here, so the operator
> sees it somewhere that survives the panel closing. Names only: the
> values were read out of somebody's mail and stay in the browser that
> read them, which is what `ValueAt` is for. Once per offer -- a browser
> reports a match per frame it sees the mail in, and without an id to
> recognise the second report by there is nothing to say it once, which
> is why an older extension that sends none has nothing written.

## `watch_matched`, [line 341](../../../../../../../../../backend/src/sro/interface/http/v1/routers/agents.py#L341): Comment

Code: `can_find=container.tools.available and container.asker is not None,`

> Whether what the mail did not say stops the press. A deployment that
> can read the operator's mailbox answers a missing value by going and
> looking for it, and a card that refused to start would be the panel
> asking for what the run already knows how to find.

## `_watch_of`, [line 397](../../../../../../../../../backend/src/sro/interface/http/v1/routers/agents.py#L397): Comment

Code: `raise NotFound("no such watch")`

> A watch that asks a question runs nothing, and the two calls below
> would reach it with nothing to describe. The same `NotFound`
> everything else here answers, rather than a 500 about a field.

## `list_devices`, [line 406](../../../../../../../../../backend/src/sro/interface/http/v1/routers/agents.py#L406): Comment

Code: `return [`

> `ReadRoster` rather than the `ReadDevices` that used to be here: a strict
> superset over the identical repository call, and two use cases over one
> `list_for_tenant` in two packages is how they drift apart. `online` is
> the thing it adds, and it is the question this list is actually read to
> answer.
