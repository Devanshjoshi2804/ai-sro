# Notes for `backend/src/sro/application/observation/register.py`

Comments and docstrings moved out of [`backend/src/sro/application/observation/register.py`](../../../../../../../backend/src/sro/application/observation/register.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/observation/register.py#L1): Docstring

> An extension announcing itself, and saying it is still there.

## `Registered`, [line 24](../../../../../../../backend/src/sro/application/observation/register.py#L24): Note on the line above

Code: `secret: str`

> Said once, to the browser that asked, and never listed anywhere.
>
> Handed back on every registration rather than only the first, because
> registration is idempotent on (tenant, principal, label): a caller who can
> reach this answer is holding the credential of the operator whose device it
> is, and a reinstall that could not get its secret back would be a device
> that had to be deleted by hand to work again.

## `Beat`, [line 30](../../../../../../../backend/src/sro/application/observation/register.py#L30): Note on the line above

Code: `policy: ObservationPolicy | None`

> Only when the version the device holds is behind. A heartbeat that
> re-sent the whole policy every minute would be the largest thing this
> system says to a browser, and it says it once.

## `refuse_unless_itself`, [line 35](../../../../../../../backend/src/sro/application/observation/register.py#L35): Docstring

> Raise the answer a stranger gets, unless this browser proved it is itself.
>
> Word for word the message `DeviceRepository.get` raises for a device that
> does not exist, and deliberately: another operator's device, another
> tenant's, one whose secret is wrong, one that was revoked and one that was
> never registered are one answer, so a browser holding an id it should not
> have learns nothing from the difference. The same rule `ReceiveInbound`
> follows.
>
> A revoked browser is refused before its secret is even compared. Revoking
> leaves the secret alone -- it has to, because a device with no secret cannot
> be told from one registered before secrets existed -- so a gate that asked
> only "is this the browser that registered" would answer yes forever, and
> the extension would resume on its next heartbeat. This is the one place
> that turns `revoked_at` into a refusal, for all seven device-scoped callers
> at once. The rig's `holder` did it in its `WHERE revoked_at IS NULL`.

## `_mint`, [line 41](../../../../../../../backend/src/sro/application/observation/register.py#L41): Docstring

> A trigger's ``inbound_token`` is minted the same way, at the same width.

## `RegisterDevice`, [line 45](../../../../../../../backend/src/sro/application/observation/register.py#L45): Docstring

> Idempotent on (tenant, principal, label).
>
> A reinstalled extension registers again, and must come back as the device it
> was rather than as a second one -- an administrator reading the device list
> is answering "whose browsers are being observed", and one operator appearing
> four times is not an answer.

## `RecordHeartbeat`, [line 89](../../../../../../../backend/src/sro/application/observation/register.py#L89): Docstring

> Sixty seconds of "still here", and the two numbers worth having.
>
> The backlog a device reports is the only warning that an operator's day of
> work is sitting in a browser that cannot reach us.

## `ReadDevice`, [line 121](../../../../../../../backend/src/sro/application/observation/register.py#L121): Docstring

> One device, and only if it is this tenant's and proved it is itself.
>
> The ownership check every device-scoped path makes: a tenant credential
> proves who is asking, never which browser they may ask about, so it says
> which tenant and the device's own secret says which browser. Neither is
> dropped -- without the credential a leaked secret would reach across
> tenants, and without the secret a device id is a namespace rather than a
> credential.

## `GrantHost`, [line 134](../../../../../../../backend/src/sro/application/observation/register.py#L134): Docstring

> The operator saying this page may be watched after all.
>
> Behind the device's own secret like every device-scoped path: the tenant
> credential says who is asking and can never say which browser, and the
> whole justification for a grant is that the person whose browser it is
> chose it. A grant somebody else could add for you is not consent.

## `RevokeHost`, [line 165](../../../../../../../backend/src/sro/application/observation/register.py#L165): Docstring

> Stop watching it. The operator closing the tab, or pressing the button.
>
> Revoking something never granted is success: a tab closing twice, a browser
> catching up after being offline, and a grant that expired on its own all
> end in the same place, and none of them is an error worth showing anybody.

## `_hostname`, [line 181](../../../../../../../backend/src/sro/application/observation/register.py#L181): Docstring

> The host a grant is for, as `ObservationPolicy.allows` will compare it.
>
> A URL is accepted as well as a bare host because the panel has one and not
> the other, and a grant stored as `https://mail.google.com/mail/u/0` would
> match nothing while looking exactly like it should.

## `refuse_unless_itself`, [line 38](../../../../../../../backend/src/sro/application/observation/register.py#L38): Comment

Code: `attribute(device=device.id.value)`

> And from here every line this request writes says which browser it was.
>
> After it has proved itself, never before -- `asking_device`'s rule, for
> its reason: a line attributing work to a browser that FAILED to prove it
> is worse than one attributing it to nobody. Here rather than at the seven
> callers, because this is already the one place that decides, and a
> `/v1/agents/{device_id}/...` route carries the device in its PATH and so
> never went near `asking_device` at all -- six routes whose whole subject
> is one browser, and not one of their lines said which.

## `RegisterDevice.execute`, [line 60](../../../../../../../backend/src/sro/application/observation/register.py#L60): Comment

Code: `secret = known.secret or _mint()`

> A device registered before secrets existed adopts one here.
> This is the whole of the migration: the browser is refused on
> its next device-scoped call, re-registers under the label it
> always used, and comes back as itself holding a secret.

## `RegisterDevice.execute`, [line 82](../../../../../../../backend/src/sro/application/observation/register.py#L82): Comment

Code: `won = await uow.devices.registered_as(ctx.tenant_id, ctx.principal_id, label)`

> Two registrations for the same (tenant, principal, label)
> raced. Idempotent means the loser comes back as the winner,
> not as a 409 an extension that only ever registers once has
> no reason to expect or retry. The winner is a row another
> registration just wrote, so it holds a secret; a row that
> somehow does not is one this cannot answer for, and a
> conflict is more honest than a secret nobody stored.

## `GrantHost.execute`, [line 153](../../../../../../../backend/src/sro/application/observation/register.py#L153): Comment

Code: `raise NotFound(f"device {device_id} was not found")`

> The device proved it is itself, so this is that browser --
> but a browser is not a person, and the panel's button is
> only consent when the person pressing it is the one being
> observed. Refused as not-found for the same reason as
> everything else on this path.
