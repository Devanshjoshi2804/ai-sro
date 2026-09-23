# Notes for `backend/src/sro/infrastructure/agent/drivers.py`

Comments and docstrings moved out of [`backend/src/sro/infrastructure/agent/drivers.py`](../../../../../../../backend/src/sro/infrastructure/agent/drivers.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/infrastructure/agent/drivers.py#L1): Docstring

> The two ports execution already has, performed in somebody else's browser.
>
> Nothing here decides anything. A gesture is proposed by the same code that
> proposes it for a browser on the server, and what comes back is the same
> ``UiOutcome`` or ``HttpResponse``. The only new fact is that this browser can
> close, and that arrives as the unavailability execution already records.

## module, [line 15](../../../../../../../backend/src/sro/infrastructure/agent/drivers.py#L15): Note on the line above

Code: `_NO_BROWSER = (`

> Failures that mean there was no browser to act in, rather than facts about
> the page. A page whose control moved is a skill that has drifted; a laptop that
> closed is not, and counting the second as the first would demote a skill for
> somebody going to lunch.

## `RemoteHttpCaller`, [line 166](../../../../../../../backend/src/sro/infrastructure/agent/drivers.py#L166): Docstring

> Sends from the operator's own page context, so the call carries their
> session. It is why a skill can be replayed against a system this deployment
> holds no credentials for at all.

## `_locator`, [line 220](../../../../../../../backend/src/sro/infrastructure/agent/drivers.py#L220): Docstring

> Which of the five known strategies matched, or none.
>
> An operator's extension is a different build than this deployment's own
> code, unlike the local Playwright driver which only ever produces a
> strategy it constructed itself -- version drift here is a fact about the
> reply, not a reason a whole run's outcome should raise instead of just
> losing this one diagnostic field.

## `_int`, [line 229](../../../../../../../backend/src/sro/infrastructure/agent/drivers.py#L229): Docstring

> JSON from a browser, so a number may arrive as one, as a float, or as
> the string somebody's template produced.

## `RemoteUiDriver.capture`, [line 125](../../../../../../../backend/src/sro/infrastructure/agent/drivers.py#L125): Docstring

> Inline, not an artifact: this picture is being looked at now, and a
> round trip through object storage to read back what we just asked for
> would be two more places for it to be delayed or lost.

## `RemoteUiDriver.for_session`, [line 140](../../../../../../../backend/src/sro/infrastructure/agent/drivers.py#L140): Docstring

> Itself. A device is one browser and there is no other to point at;
> the deployment does not own it and cannot open a second.

## `RemoteUiDriver._ask`, [line 146](../../../../../../../backend/src/sro/infrastructure/agent/drivers.py#L146): Comment

Code: `if self._origin:`

> Named on every command rather than once at connect: a device holds one
> channel and may be asked to act for several runs against different
> systems, so which page a command belongs to is a fact about the
> command.

## `RemoteUiDriver._ask`, [line 148](../../../../../../../backend/src/sro/infrastructure/agent/drivers.py#L148): Comment

Code: `if self._may_take_focus:`

> Sent only when it is true. A payload carrying `allow_focus: false`
> says the same thing as one that omits it, and the omission is the
> safer default to have in a protocol: a browser reading a field it
> does not understand takes nobody's screen.

## `RemoteUiDriver._ask`, [line 150](../../../../../../../backend/src/sro/infrastructure/agent/drivers.py#L150): Comment

Code: `if self._starts_on:`

> The screen the task was demonstrated on. Without it a run could only
> be performed by an operator who had already navigated there, and one
> who had not got a page of `control_not_found` that said nothing about
> being on the wrong screen.

## `RemoteUiDriver._ask`, [line 152](../../../../../../../backend/src/sro/infrastructure/agent/drivers.py#L152): Comment

Code: `if self._doing:`

> What the page says about itself while this is happening. The operator
> whose browser is being driven is watching the page, not the panel,
> and "AI-SRO is doing X, step 4 of 13" is the difference between an
> application behaving oddly and a task somebody can see and stop.

## `RemoteUiDriver._ask`, [line 163](../../../../../../../backend/src/sro/infrastructure/agent/drivers.py#L163): Comment

Code: `raise UiUnavailable(str(gone)) from gone`

> Never a fall back to a browser on the server: that one is signed
> in as somebody else, on a screen nobody demonstrated.

## `RemoteHttpCaller.send`, [line 193](../../../../../../../backend/src/sro/infrastructure/agent/drivers.py#L193): Comment

Code: `raise TargetUnreachable(answer.detail or "the browser did not send the request")`

> Including the timeout: a mutation whose answer never came back is
> in an unknown state, and TargetUnreachable is how the executor is
> told not to retry it without looking.
