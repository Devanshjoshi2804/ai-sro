# Notes for `backend/src/sro/application/ports/tools.py`

Comments and docstrings moved out of [`backend/src/sro/application/ports/tools.py`](../../../../../../../backend/src/sro/application/ports/tools.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/ports/tools.py#L1): Docstring

> Connectors a tenant has connected, and the tools they offer.
>
> The other half of `infrastructure/mcp/server.py`. That one hands this system's
> skills to somebody else's agent; this one calls somebody else's tools from a
> skill's own step -- which is what makes a mail step a call rather than a click,
> and a click is the one thing that can never be clean.

## `ToolOffered`, [line 11](../../../../../../../backend/src/sro/application/ports/tools.py#L11): Docstring

> One tool a connector says it has.
>
> Read when somebody maps a step onto it, so a person choosing is choosing
> from what the server actually offers rather than typing a name and finding
> out at run time.

## `ToolResult`, [line 18](../../../../../../../backend/src/sro/application/ports/tools.py#L18): Docstring

> What a tool answered.
>
> ``text`` is the body an assertion is checked against, exactly as a network
> step's response body is. ``failed`` is the tool saying no, which is
> different from this system failing to ask -- the first is an answer and
> goes in the run record as one.

## `ToolsUnavailable`, [line 24](../../../../../../../backend/src/sro/application/ports/tools.py#L24): Docstring

> No connector by that name, or it will not answer.
>
> Its own exception rather than an empty result, because "the tool said no"
> and "there was nothing to ask" are different facts and the escalation table
> answers them differently.

## `NotConnected`, [line 28](../../../../../../../backend/src/sro/application/ports/tools.py#L28): Docstring

> This operator has not connected this server.
>
> A subclass rather than a bare `ToolsUnavailable` so a console can tell "you
> have not connected Gmail yet" -- which a person can fix in one click --
> from "the connector is down", which they cannot. Both are still "there was
> nothing to ask", which is why the escalation table needs no new entry.

## `ToolCaller`, [line 32](../../../../../../../backend/src/sro/application/ports/tools.py#L32): Docstring

> Somebody else's tools, called with THIS tenant's credential.
>
> Every method takes the tenant AND the operator, and that is the whole of
> the security property: a connector is reached with a bearer read from the
> vault under `connector_key`, so an operator with no grant cannot reach one
> and an operator with a grant reaches only their own mailbox.
>
> Per operator rather than per tenant because each reads their own mail. A
> key without the person in it would have one operator's inbox answering for
> everybody in the tenant -- the same bug one scope smaller, and worth saying
> because the first version of this change had exactly that.
>
> It was not always so. Until 2026-09-16 neither the port nor the adapter had
> a tenant on it and the bearer was one string in deployment config, so a
> skill run for any tenant reached the same connector holding the same
> person's Google grant. Nothing had noticed because nothing had called it:
> MCP was unreachable from a mined-workflow run, and the one path that did
> use it was a single-tenant deployment. This is the door shut before
> anything leaned on it.

## `ToolCaller.available`, [line 34](../../../../../../../backend/src/sro/application/ports/tools.py#L34): Docstring

> Whether this deployment has connectors configured at all.
>
> Asked before a mapping screen offers anything, so an operator is not
> invited to map a step onto a connector nobody set up.

## `ToolCaller.list_tools`, [line 36](../../../../../../../backend/src/sro/application/ports/tools.py#L36): Docstring

> What this connector offers this operator, now. Raises `ToolsUnavailable`.
>
> Who first, and on every method, because a connector is reached with a
> credential and a credential belongs to one person. The port carried
> neither until 2026-09-16 and neither did the adapter, so every step of
> every tenant reached the same mailbox with the same grant.

## `ToolCaller.call`, [line 40](../../../../../../../backend/src/sro/application/ports/tools.py#L40): Docstring

> Call it and return what it said. Raises `ToolsUnavailable`.
>
> No idempotency key here, deliberately. Whether this call may happen at
> all is decided before the port is reached -- a provider that promises
> to deduplicate is a promise this system cannot check, and the one call
> worth protecting is the one whose reply never arrived.
