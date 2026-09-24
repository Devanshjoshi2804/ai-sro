# Notes for `backend/src/sro/interface/http/v1/routers/agent_channel.py`

Comments and docstrings moved out of [`backend/src/sro/interface/http/v1/routers/agent_channel.py`](../../../../../../../../../backend/src/sro/interface/http/v1/routers/agent_channel.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## `commands`, [line 50](../../../../../../../../../backend/src/sro/interface/http/v1/routers/agent_channel.py#L50): Comment

Code: `device = await container.read_device().execute(`

> A valid credential is not ownership. The device has to be this
> tenant's and has to prove it is itself, and one that is neither is
> closed exactly like one that does not exist -- a socket that closed
> differently for a wrong secret would be a way to enumerate devices
> without ever holding one.

## `commands`, [line 60](../../../../../../../../../backend/src/sro/interface/http/v1/routers/agent_channel.py#L60): Comment

Code: `attribute(tenant=ctx.tenant_id.value, principal=ctx.principal_id.value, device=device.id.value)`

> The socket authenticates for itself -- no `ContextDep`, no
> `asking_device` -- so the attribution those two install never reached
> here, and the one door that stays open for a whole session was the one
> door whose lines said nothing about whose session it was. Set after the
> credential and the secret have both been checked, for `asking_device`'s
> reason: an id in a query string is a claim until something proves it.

## `commands`, [line 66](../../../../../../../../../backend/src/sro/interface/http/v1/routers/agent_channel.py#L66): Comment

Code: `sockets.deliver(await websocket.receive_text(), ctx.tenant_id, device.id)`

> Named here, not by the message: a browser that told the registry
> which device it was could tell it that it was another one.

## `commands`, [line 74](../../../../../../../../../backend/src/sro/interface/http/v1/routers/agent_channel.py#L74): Comment

Code: `with contextlib.suppress(Exception):`

> Closing a socket that has already gone is not a failure, and there
> is nothing left to do about it either way.
>
> `RuntimeError` alone was not enough. A browser that goes -- an
> extension reloaded, a laptop shut, a tunnel dropped -- leaves this
> `close()` writing a close frame to nobody, and uvicorn answers that
> with `ClientDisconnected`, which is neither a `RuntimeError` nor
> importable from here without reaching into a server's internals. It
> went uncaught, out of the endpoint, and printed thirty lines of
> `Exception in ASGI application` for the ordinary event this
> `finally` exists to handle. Measured on the deployment 2026-09-21:
> two of them against three reconnections.
>
> Broad on purpose and only here. The detach above has already
> happened, the disconnection is already said, and the one thing this
> line can still do is not shout about a socket nobody is holding.
