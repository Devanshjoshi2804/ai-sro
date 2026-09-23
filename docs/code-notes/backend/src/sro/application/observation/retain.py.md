# Notes for `backend/src/sro/application/observation/retain.py`

Comments and docstrings moved out of [`backend/src/sro/application/observation/retain.py`](../../../../../../../backend/src/sro/application/observation/retain.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/observation/retain.py#L1): Docstring

> Evidence outliving its own tenant's retention window.
>
> `ObservationPolicy.retention_days` has been a declared number since B1, read by
> nobody but the operator who set it. This is what makes it a promise: the same
> rows-then-blobs deletion `ForgetObservations` gives an operator purging their
> own hour, run instead per tenant against its own configured window, with
> nobody behind it -- the same reason `FireTrigger` and `MineEverything` take no
> `RequestContext` either.

## module, [line 13](../../../../../../../backend/src/sro/application/observation/retain.py#L13): Note on the line above

Code: `_BEFORE_THIS_SYSTEM_EXISTED = datetime(2000, 1, 1, tzinfo=UTC)`

> ``between()`` wants a floor. Any batch this system ever stored is after it.

## `SweepRetention._sweep_one`, [line 34](../../../../../../../backend/src/sro/application/observation/retain.py#L34): Comment

Code: `policy = await uow.observation_policies.get(tenant_id) or ObservationPolicy()`

> Absence is not consent to capture, but a declared window is
> still safer to assume than none: the default keeps something,
> never everything.

## `SweepRetention._sweep_one`, [line 36](../../../../../../../backend/src/sro/application/observation/retain.py#L36): Comment

Code: `doomed = await uow.observations.received_before(tenant_id, cutoff)`

> By when it ARRIVED, not by when the browser says it happened.
> The cutoff is this server's clock and `started_at` is the
> device's, and on this store the two run up to 23 hours apart --
> an extension flushing a queue it held while offline, or a
> machine whose clock is simply wrong. Counted on the browser's,
> a batch that lands already older than the window is swept the
> day it arrives, and a device whose clock reads early is never
> swept at all, with the tenant's declared window quietly not
> honoured either way.
