# Notes for `backend/src/sro/application/trigger/receive_inbound.py`

Comments and docstrings moved out of [`backend/src/sro/application/trigger/receive_inbound.py`](../../../../../../../backend/src/sro/application/trigger/receive_inbound.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/trigger/receive_inbound.py#L1): Docstring

> A mail relay or a chat webhook, asking for its trigger to fire.
>
> There is no principal on the other end of an email -- no bearer token, no
> tenant to prove by reading a row the caller's own credential unlocked. The
> per-trigger token is the only thing standing in for that, so it is checked in
> constant time and a wrong trigger id and a wrong token look identical from the
> outside: neither should tell an unauthenticated caller which one it got wrong
> -- which is also why the comparison is on bytes. `hmac.compare_digest` raises
> `TypeError` for a non-ASCII `str`, and Starlette decodes every header value
> through latin-1, so a header byte >= 0x80 always becomes a non-ASCII `str`
> that would otherwise turn a 404 into an unhandled 500 -- itself a signal an
> unauthenticated caller could read.

## `InboundRefused`, [line 13](../../../../../../../backend/src/sro/application/trigger/receive_inbound.py#L13): Docstring

> No such reachable inbound trigger. Deliberately the same error whether
> the id is wrong, the kind is wrong, or the token is wrong.

## `ReceiveInbound.execute`, [line 22](../../../../../../../backend/src/sro/application/trigger/receive_inbound.py#L22): Docstring

> `message` is the relay's payload. A trigger reads from it only the
> parameters it declared it would take, so a relay -- which nobody in
> this tenant wrote and which anybody who learns a token can post to --
> cannot name the facility a warehouse read runs against.
