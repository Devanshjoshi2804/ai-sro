# Notes for `backend/src/sro/infrastructure/agent/sockets.py`

Comments and docstrings moved out of [`backend/src/sro/infrastructure/agent/sockets.py`](../../../../../../../backend/src/sro/infrastructure/agent/sockets.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/infrastructure/agent/sockets.py#L1): Docstring

> The open channels to operators' browsers, and the commands sent down them.
>
> One command, one answer, correlated by an id this side mints. The extension
> must answer every command exactly once, including with an error, and a late
> answer is discarded rather than applied -- a run that has already recorded the
> step as failed must not have it succeed underneath it.
>
> Held in memory on purpose. A socket does not survive a restart either, so a
> durable record of which browser was connected would only ever be a record of
> which browser used to be connected.

## module, [line 21](../../../../../../../backend/src/sro/infrastructure/agent/sockets.py#L21): Note on the line above

Code: `_DEFAULT_BUSY = 5.0`

> What a `busy` with no window of its own asks for.

## module, [line 23](../../../../../../../backend/src/sro/infrastructure/agent/sockets.py#L23): Note on the line above

Code: `K_REDIAL = 8.0`

> How long a command waits for a browser that is dialling back in.
>
> Chrome stops an extension's service worker after 30 seconds without an event
> and takes the socket with it; the extension dials again as soon as anything
> wakes it. Measured on the deployment, 2026-09-16, over half an hour of an
> operator's ordinary day:
>
>     20:28:27 disconnected  20:28:28 connected   (1s)
>     20:36:59 disconnected  20:37:00 connected   (1s)
>     20:39:43 disconnected  20:39:45 connected   (2s)
>     20:29:08 disconnected  20:33:48 connected   (4m40s -- nothing woke it
>                                                  until the minute alarm)
>
> So the ordinary gap is a second or two, and a command that landed in one of
> them failed its step for a browser that was about to be there. Eight seconds
> covers every short gap with room to spare and gives up long before a run could
> be said to have hung; the long gaps still fail, because waiting five minutes at
> a step is not waiting, it is hanging.
>
> This is a wait for a browser to COME BACK, not a wait for it to answer -- that
> is `DEFAULT_TIMEOUT`, and it starts once the command has gone out.

## module, [line 25](../../../../../../../backend/src/sro/infrastructure/agent/sockets.py#L25): Note on the line above (debt)

Code: `K_LOOK_AGAIN = 0.25`

> How often the wait above checks. ponytail: a poll, where an event per device
> would be exact -- at eight seconds and a quarter-second tick this is at most
> thirty-two wake-ups on the one path where a browser is missing, and the
> alternative is a dict of events to keep in step with `attach` and `drop`.

## module, [line 27](../../../../../../../backend/src/sro/infrastructure/agent/sockets.py#L27): Note on the line above

Code: `MAX_BUSY_WAIT = 0.5`

> How much of a command's own deadline may be spent waiting for the operator
> to stop typing, as a fraction of it. A device that says it is busy is asking for
> politeness, not for a veto: a run that waited out every keystroke would be a run
> that never happened on a busy morning.

## `Socket`, [line 30](../../../../../../../backend/src/sro/infrastructure/agent/sockets.py#L30): Docstring

> What the router hands over. Narrow so this file never imports a web
> framework, and so a test can be a list.

## `DeviceSockets`, [line 48](../../../../../../../backend/src/sro/infrastructure/agent/sockets.py#L48): Docstring

> Which browsers are connected here, and what they owe an answer to.

## `_busy_seconds`, [line 199](../../../../../../../backend/src/sro/infrastructure/agent/sockets.py#L199): Docstring

> How long a device is asking to be left alone, or `None` for a message
> that does not say anything usable.
>
> Absent is the documented default. Present and not a real number of
> milliseconds is ignored outright rather than rounded into a default: a
> browser that sends nonsense has not asked for anything in particular.
>
> `json.loads` accepts a bare `NaN`, which passes an `isinstance` check and
> survives `min()` -- and `asyncio.sleep(nan)` raises. Stored, that made every
> later command to the device raise the same way, so one malformed frame from
> one browser took that device offline until the process restarted.

## `Answer.detail`, [line 42](../../../../../../../backend/src/sro/infrastructure/agent/sockets.py#L42): Docstring

> What went wrong, keeping the kind the extension named.
>
> The detail alone used to win whenever both were sent, which threw away
> the only machine-readable half. `focus_not_permitted` with a sentence
> beside it arrived as the sentence, so a run that politely declined to
> steal the operator's screen was indistinguishable from one that could
> not find a control. Every device failure passes through here, so naming
> the kind once covers all of them.

## `DeviceSockets.attach`, [line 56](../../../../../../../backend/src/sro/infrastructure/agent/sockets.py#L56): Docstring

> A device is connected. A second connection for the same device
> replaces the first: a browser that reconnected after a network drop is
> the same browser, and the stale socket will never answer anything.

## `DeviceSockets.drop`, [line 59](../../../../../../../backend/src/sro/infrastructure/agent/sockets.py#L59): Docstring

> Forget whatever socket this device holds: it is offline from here
> on, whether or not the browser has noticed.
>
> The one caller is a tenant revoking a browser, and a revoked browser
> that still read as connected would be an audit line nobody could
> trust.

## `DeviceSockets.detach`, [line 64](../../../../../../../backend/src/sro/infrastructure/agent/sockets.py#L64): Docstring

> Only if it is still the socket we hold. A slow close arriving after
> a reconnect must not unregister the live one.

## `DeviceSockets.deliver`, [line 70](../../../../../../../backend/src/sro/infrastructure/agent/sockets.py#L70): Docstring

> An answer arrived. Unknown ids are dropped, not raised: a reply to a
> command that already timed out is late, not wrong.
>
> The device is named by the router rather than by the message, because a
> browser saying which device it is would be a browser that could say it
> was another one. It is only needed for the unsolicited messages -- an
> answer carries its own command id and needs nothing else.

## `DeviceSockets.send`, [line 108](../../../../../../../backend/src/sro/infrastructure/agent/sockets.py#L108): Docstring

> ``source`` rides in the envelope because the extension has one socket
> and cannot otherwise tell a workflow run's command from a skill run's --
> both arrive on the same channel it dialled as "backend". `SocketChannel`
> is the rig's only door onto this method and passes "rig" on every call;
> `AgentDrivers`, the skill executor's, never passes it and gets the
> default. Without this the panel can show Approve only for a run it
> started itself, never one a console or another caller began.

## `DeviceSockets.held_for`, [line 163](../../../../../../../backend/src/sro/infrastructure/agent/sockets.py#L163): Docstring

> How much longer this browser has asked to be left alone.
>
> Clamped to what `_wait_out_the_operator` will actually honour, so a
> console counting down from this never promises longer than the backend
> intends to wait. The expired entry is dropped here as well as there:
> two readers of one dict disagreeing about whether a pause is over is a
> bug waiting for a quiet morning.

## `DeviceSockets._dialling_back`, [line 174](../../../../../../../backend/src/sro/infrastructure/agent/sockets.py#L174): Docstring

> This device's socket, waiting a few seconds for one that is coming.
>
> A browser whose extension worker Chrome has just stopped has no socket
> for a second or two and then has one again. Without this wait, a
> command that landed in that second failed the step -- `not_actionable`,
> `no_tab_for_origin` -- against a browser that was there before and
> after it, and an operator read a run that stopped for no reason they
> could see.
>
> The device is not woken by this and cannot be: nothing this side can
> reach a stopped service worker. What it does is stop treating "not this
> instant" as "not at all".

## `DeviceSockets._wait_out_the_operator`, [line 188](../../../../../../../backend/src/sro/infrastructure/agent/sockets.py#L188): Docstring

> Hold a command back while the operator is using their own browser.
>
> Typing into a field a moment before a replay clicks it is how a run and
> a person fight over the same form. Bounded by a fraction of the
> command's own deadline: politeness that could stall a run indefinitely
> would be a browser deciding whether work happens.

## `DeviceSockets.__init__`, [line 51](../../../../../../../backend/src/sro/infrastructure/agent/sockets.py#L51): Comment

Code: `self._redial = redial_s`

> How long to wait for a browser that is dialling back in. A knob for
> the same reason `timeout_s` is one: a suite proving what happens when
> a device is NOT there should not spend eight seconds per case finding
> out, and one test sets it deliberately to prove the wait itself.

## `DeviceSockets.attach`, [line 56](../../../../../../../backend/src/sro/infrastructure/agent/sockets.py#L56): Comment

Code: `def attach(self, tenant_id: TenantId, device_id: DeviceId, socket: Socket) -> None:`

> -- the router's side ---------------------------------------------------

## `DeviceSockets.detach`, [line 68](../../../../../../../backend/src/sro/infrastructure/agent/sockets.py#L68): Comment

Code: `self._busy.pop(key, None)`

> A browser that said it was busy and then closed the lid is not
> busy any more, and its entry would otherwise sit here for the
> life of the process waiting for a send that never comes.

## `DeviceSockets.deliver`, [line 82](../../../../../../../backend/src/sro/infrastructure/agent/sockets.py#L82): Comment

Code: `seconds = _busy_seconds(message.get("for_ms"))`

> Self-expiring, and short. A browser that says it is busy and then
> closes its laptop must not leave a device nothing can be sent to
> until the process restarts, so the pause carries its own end
> rather than waiting for an "idle" that may never come.

## `DeviceSockets.online`, [line 103](../../../../../../../backend/src/sro/infrastructure/agent/sockets.py#L103): Comment

Code: `def online(self, tenant_id: TenantId) -> tuple[DeviceId, ...]:`

> -- the driver's side ---------------------------------------------------

## `DeviceSockets.send`, [line 120](../../../../../../../backend/src/sro/infrastructure/agent/sockets.py#L120): Comment

Code: `if await self._dialling_back(key) is None:`

> Keyed by tenant as well as device, so another tenant's id is not a
> device that exists and refuses -- it is a device that is not there,
> which is the same answer as one that never existed.

## `DeviceSockets.send`, [line 127](../../../../../../../backend/src/sro/infrastructure/agent/sockets.py#L127): Comment

Code: `socket = await self._dialling_back(key)`

> Read *after* the wait, not before it. That wait can be seconds long,
> and a laptop lid or a wifi hop in the middle of it has the extension
> re-dial: `attach` replaces the registry entry, and a command sent
> down the socket this call was holding fails as an unreachable device
> against a browser that is in fact connected.

## `DeviceSockets.send`, [line 151](../../../../../../../backend/src/sro/infrastructure/agent/sockets.py#L151): Comment

Code: `with about(command=command_id), doing("browser.command", command=command_id) as span:`

> Every line written while this command is in flight says which
> command it was -- and the browser's half of it says the same id
> back, so the two halves of a step join without guessing which of
> the three `ui.perform`s in that second is the one that failed.
>
> And a span around the wait, because this is where a run's time
> actually goes: a browser on a slow page, an operator who has been
> asked to approve, a tab that stopped answering. A trace that
> measured only the request could say a run took four minutes and
> nothing about which command it spent them in.
