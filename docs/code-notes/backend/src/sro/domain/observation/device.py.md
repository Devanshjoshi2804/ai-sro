# Notes for `backend/src/sro/domain/observation/device.py`

Comments and docstrings moved out of [`backend/src/sro/domain/observation/device.py`](../../../../../../../backend/src/sro/domain/observation/device.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/domain/observation/device.py#L1): Docstring

> One installed extension, in one browser profile, belonging to one operator.

## `AgentDevice`, [line 13](../../../../../../../backend/src/sro/domain/observation/device.py#L13): Docstring

> What a command channel addresses and what a batch was uploaded by.
>
> It holds no policy of its own. Policy is the tenant's, so a device cannot
> grant itself more than the tenant agreed to -- and ``paused`` here is the
> administrator's switch, separate from the operator's own pause, which lives
> in the browser and is theirs to hold.

## `AgentDevice`, [line 27](../../../../../../../backend/src/sro/domain/observation/device.py#L27): Note on the line above

Code: `grants: tuple[HostGrant, ...] = ()`

> Pages this operator said, in this browser, may be watched after all.
>
> Held on the device rather than on the tenant because that is what a grant
> is: one person's decision about one of their own tabs, not a change to what
> the tenant agreed to. It also costs nothing to check -- ingest reads this
> device already.

## `AgentDevice`, [line 29](../../../../../../../backend/src/sro/domain/observation/device.py#L29): Note on the line above

Code: `secret: str | None = None`

> What this browser proves it is itself with, minted at registration.
>
> The tenant credential says which tenant is asking and cannot say which
> browser: every device-scoped path is ``/v1/agents/{device_id}/...``, so
> without this a device id is a namespace rather than a credential and any
> colleague's extension could fire another operator's watch in a live
> warehouse. Same instinct as a trigger's ``inbound_token`` -- a caller with
> no principal behind it carries a per-thing secret -- and the same rule
> about what a wrong one is allowed to reveal.
>
> ``None`` only for a device registered before this existed. Such a device
> proves nothing and is refused everywhere; its browser re-registers on its
> next heartbeat, which is idempotent on the label and hands it one.

## `AgentDevice`, [line 31](../../../../../../../backend/src/sro/domain/observation/device.py#L31): Note on the line above

Code: `revoked_at: str | None = None`

> When this browser's authority was taken away, ISO, or ``None``.
>
> Separate from ``secret`` rather than clearing it: an administrator revoking
> a browser is answering "this one stops acting", and a device whose secret
> was blanked cannot be told from one registered before secrets existed. It
> is also the record of *when*, which an audit of what a browser was allowed
> to do needs and a missing secret cannot give.
>
> Nothing a browser does moves it. `save` deliberately never writes this
> column, so a heartbeat that loaded the device before the revocation and
> saved it after cannot undo one; and registration is idempotent and returns
> the same secret, so re-registering leaves the revocation standing. A browser
> cut off stays cut off -- every device-scoped path refuses it at
> `refuse_unless_itself`.
>
> The way back is an administrator, not the browser: `DeviceRepository.restore`
> and `POST /v1/devices/{device}/restore`. It has to be its own repository
> call precisely because `save` does not write this column -- clearing it
> through the record would mean letting every heartbeat write it too.

## `AgentDevice.proves_itself`, [line 49](../../../../../../../backend/src/sro/domain/observation/device.py#L49): Docstring

> Is this the browser that registered?
>
> On bytes, in constant time, for `ReceiveInbound`'s reasons: the caller
> is guessing or it is not, and a comparison that returns early tells it
> how close it got. ``hmac.compare_digest`` raises ``TypeError`` for a
> non-ASCII ``str`` and Starlette decodes header values through latin-1,
> so a header byte >= 0x80 arrives as one -- encoding both sides first is
> what keeps a 404 from becoming a 500 an unauthenticated caller can read.
>
> A device with no secret answers no. It cannot be told from one that
> never existed, which is the point.

## `AgentDevice.granted_hosts`, [line 54](../../../../../../../backend/src/sro/domain/observation/device.py#L54): Docstring

> The hosts this browser may watch beyond the tenant's default.
>
> Expiry is applied on read rather than by a sweep: a grant that has run
> out must stop admitting the moment it does, and a job that has not run
> yet is not a thing to base that on.

## `AgentDevice.grant`, [line 57](../../../../../../../backend/src/sro/domain/observation/device.py#L57): Docstring

> Watch this host too, until it expires or the tab closes.
>
> Re-granting replaces rather than adds: the operator pressing the button
> again means "keep watching", and a device that accumulated one row per
> press would expire on the oldest.

## `AgentDevice.seen`, [line 67](../../../../../../../backend/src/sro/domain/observation/device.py#L67): Docstring

> A heartbeat. Backlog is recorded because a device whose queue only
> grows is a device that cannot reach us, and that is worth seeing on a
> screen before an operator's day of work is lost to a retention window.

## `AgentDevice.pause`, [line 78](../../../../../../../backend/src/sro/domain/observation/device.py#L78): Docstring

> The administrator's kill switch, delivered on the next heartbeat.
