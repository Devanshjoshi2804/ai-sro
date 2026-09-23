# Notes for `backend/src/sro/interface/http/v1/routers/watch.py`

Comments and docstrings moved out of [`backend/src/sro/interface/http/v1/routers/watch.py`](../../../../../../../../../backend/src/sro/interface/http/v1/routers/watch.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## `watch_session`, [line 48](../../../../../../../../../backend/src/sro/interface/http/v1/routers/watch.py#L48): Comment

Code: `ctx = RequestContext(tenant_id=caller.tenant_id, principal_id=caller.principal_id)`

> Signed by this deployment is not the same as yours. Session ids are
> handed out by another endpoint, so proving only the credential let
> anybody list a browser and then watch it -- somebody else's warehouse,
> live, for the price of one request.

## `watch_session`, [line 51](../../../../../../../../../backend/src/sro/interface/http/v1/routers/watch.py#L51): Comment

Code: `await websocket.close(code=status.WS_1008_POLICY_VIOLATION)`

> Closed rather than refused with a status: the handshake has not been
> accepted, so there is no response body a browser would ever show. A
> browser that is not yours closes exactly like one that is not there.

## `watch_session`, [line 65](../../../../../../../../../backend/src/sro/interface/http/v1/routers/watch.py#L65): Comment

Code: `await websocket.close()`

> The socket is already closed when the viewer left first, and closing a
> closed socket raises rather than being the no-op it reads as.
