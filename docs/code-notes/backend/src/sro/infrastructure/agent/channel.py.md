# Notes for `backend/src/sro/infrastructure/agent/channel.py`

Comments and docstrings moved out of [`backend/src/sro/infrastructure/agent/channel.py`](../../../../../../../backend/src/sro/infrastructure/agent/channel.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/infrastructure/agent/channel.py#L1): Docstring

> The ``Channel`` port over the sockets the API worker already holds.
>
> Nothing here is a second channel. ``DeviceSockets`` mints the ids, correlates
> the answers and waits out the operator; this only names those in the vocabulary
> a run holds, and adds the one deadline rule a typed driver never needed because
> it never let a caller say zero.

## `SocketChannel`, [line 10](../../../../../../../backend/src/sro/infrastructure/agent/channel.py#L10): Docstring

> The ``Channel`` port over the sockets the API worker already holds.

## `SocketChannel.send`, [line 25](../../../../../../../backend/src/sro/infrastructure/agent/channel.py#L25): Comment

Code: `return Reply(ok=False, error_kind="timeout", error_detail="a non-positive deadline")`

> Not folded into `timeout_s or default`: that could not express a
> short deadline near zero and let a negative one reach the wire.

## `SocketChannel.send`, [line 26](../../../../../../../backend/src/sro/infrastructure/agent/channel.py#L26): Comment

Code: `answer = await self._sockets.send(`

> "rig", unconditionally: this port has exactly one caller, the
> workflow-run engine, and the extension's one socket has no other
> way to tell a rig command from a skill command it should not offer
> Approve for.
