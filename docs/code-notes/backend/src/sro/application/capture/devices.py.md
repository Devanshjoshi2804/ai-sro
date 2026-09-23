# Notes for `backend/src/sro/application/capture/devices.py`

Comments and docstrings moved out of [`backend/src/sro/application/capture/devices.py`](../../../../../../../backend/src/sro/application/capture/devices.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/capture/devices.py#L1): Docstring

> Cutting a browser off, and reading which ones are connected.
>
> A revocation is two facts, not one: a row that says when this browser's
> authority ended, and a socket forgotten so it is offline from that instant
> rather than from whenever its connection happens to drop. The rig did both
> inside its ``POST /v1/devices/{device_id}/revoke`` route; here they are a use
> case, because either half alone is a lie an audit is read against -- a row
> saying revoked beside a channel still taking commands, or a browser cut off
> with no record of when it was.
>
> Registration is deliberately not here. ``sro.application.observation.register``
> already mints what the rig's ``issue`` minted and answers what its ``holder``
> answered, under the tenant-and-secret rule this codebase had before the rig
> arrived; there is nothing of the rig's ``devices.py`` left for this module but
> the revoke.
>
> What is here and was not in the rig is `RestoreDevice`. The rig un-revoked as a
> side effect of `issue` handing out a fresh token; registration here is
> idempotent and hands back the same secret, so letting a browser back in had to
> become its own act once revocation began to enforce.

## `RevokeDevice`, [line 13](../../../../../../../backend/src/sro/application/capture/devices.py#L13): Docstring

> This browser stops acting, now.
>
> Answers whether there was a live browser to revoke: ``False`` when it was
> already revoked, because the first revocation's instant is what an audit of
> what this browser was allowed to do is read against and a second press must
> not move it. ``NotFound`` for a browser this tenant does not have, which the
> repository raises and this does not soften into a quiet ``False`` -- "no
> such browser" and "nothing live to revoke" are different answers and phase
> 4 gives them different status codes.

## `RestoreDevice`, [line 28](../../../../../../../backend/src/sro/application/capture/devices.py#L28): Docstring

> A revoked browser may act again.
>
> No rig ancestor: there, `issue` un-revoked as a side effect of minting a
> fresh token. This port chose idempotent registration instead -- a second
> register hands back the SAME secret -- so nothing here undid a revoke at
> all, and once plan 3b made `refuse_unless_itself` enforce on all seven
> device-scoped paths, an administrator who pressed revoke on the wrong row
> had no way back short of a hand-edited row.
>
> No socket is opened, and no `AgentDrivers` is taken to open one with: the
> extension dials on its own next heartbeat, and a backend that dialled a
> laptop nobody is sitting at would be a channel nobody asked for. That is
> the asymmetry with `RevokeDevice`, which drops one -- cutting off is
> urgent, letting back in is not.
>
> The cost, named because nothing else names it: this ERASES the instant the
> revocation recorded. `RevokeDevice` is emphatic that the first press's
> instant is what an audit of what a browser was allowed to do is read
> against, and a restore deletes it outright -- so `DeviceRepository.since`
> afterwards has no record the browser was ever cut off, and a day that
> contained a revocation and a restore reads as a day that contained neither.
> The rig did the same and this port keeps it, but a system that has to answer
> "who could act, and from when to when" will want the pair kept somewhere.
>
> ``NotFound`` for a browser this tenant does not have, as the revoke gives:
> the repository raises it and this does not soften it into a quiet
> ``False``, so a tenant cannot confirm another tenant's device ids by
> pressing at them.

## `DeviceLine`, [line 42](../../../../../../../backend/src/sro/application/capture/devices.py#L42): Note on the line above

Code: `online: bool`

> A command channel open right now.
>
> Never true of a revoked browser. ``RevokeDevice`` drops its socket, so
> normally there is nothing to report -- but this is the list an administrator
> reads to answer "who can act", and a browser whose drop was missed reading
> as connected is exactly the audit line ``AgentDrivers.drop`` exists to
> prevent. The row is the authority; the socket is only a fact about a wire.

## `ReadRoster`, [line 45](../../../../../../../backend/src/sro/application/capture/devices.py#L45): Docstring

> Every browser this tenant registered, most recently seen first, and
> whether each is connected.
>
> A revoked browser stays on it, carrying the instant its authority ended,
> rather than disappearing: this is the list read before cutting one off and
> after, and a revocation that erased its own subject would leave an
> administrator unable to confirm the thing they just did.
>
> Ordered most recently *seen* first, where the rig's `registered` was
> ordered by issue. Inherited rather than chosen: `list_for_tenant` is plan
> 2's and already sorts that way, and it is the better order for this
> question anyway -- an administrator asking who can act cares which browser
> was here this morning, not which was installed first.

## `RevokeDevice.execute`, [line 24](../../../../../../../backend/src/sro/application/capture/devices.py#L24): Comment

Code: `self._drivers.drop(ctx.tenant_id, device_id)`

> After the commit, so a revocation that rolled back cannot leave an
> operator's browser cut off; and unconditionally, whatever the row
> said, because "there was a live token" and "there is still a socket"
> are different questions. A browser revoked a minute ago by somebody
> else can still be holding one, and this is the one caller that closes
> it. The rig dropped it on every press for the same reason.
