# Notes for `backend/src/sro/application/observation/artifacts.py`

Comments and docstrings moved out of [`backend/src/sro/application/observation/artifacts.py`](../../../../../../../backend/src/sro/application/observation/artifacts.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/observation/artifacts.py#L1): Docstring

> Screenshots and oversized bodies, stored beside the batch they belong to.

## module, [line 19](../../../../../../../backend/src/sro/application/observation/artifacts.py#L19): Note on the line above

Code: `_ALLOWED = (ArtifactKind.SCREENSHOT, ArtifactKind.PAYLOAD, ArtifactKind.VIDEO)`

> A recording's other kinds -- raw events, audio, transcript -- belong to a
> demonstration somebody started. An observation stream has no narration.

## `artifact_prefixes`, [line 28](../../../../../../../backend/src/sro/application/observation/artifacts.py#L28): Docstring

> Every key prefix a purge of this batch's artifacts has to sweep.
>
> Usually one: an artifact is filed under the day of the batch it
> illustrates, which `execute()` below reads off the batch for exactly this
> reason. A batch spanning midnight gets both days rather than risk leaving
> one behind -- the same key shape `execute()` writes, read back rather than
> re-derived a second way.
>
> `received_at` is in the set as well, and it is the belt. An artifact whose
> batch row had not landed yet is filed under the day this server was having
> when it arrived, and that is the closest day to it anything here knows.
> Without it, a screenshot filed on one day and a batch stamped on another
> -- the browser's clock runs up to 23 hours from this one on the real store
> -- leaves a prefix nobody ever sweeps: `forget_prefix` returns 0, the
> operator is told "0 artifacts", and the pictures stay.

## `StoreObservationArtifact`, [line 35](../../../../../../../backend/src/sro/application/observation/artifacts.py#L35): Docstring

> No row. The key says which batch and which frame it belongs to, so a
> miner reading a batch finds its screenshots by prefix, and a retention rule
> expires them with the evidence they illustrate.

## `StoreObservationArtifact.execute`, [line 61](../../../../../../../backend/src/sro/application/observation/artifacts.py#L61): Comment

Code: `device = await uow.devices.get(ctx.tenant_id, device_id)`

> The same two questions ingest asks, for the same reason: the
> credential says which tenant, the secret says which browser, and
> a screenshot is a picture of somebody's screen filed under their
> name.

## `StoreObservationArtifact.execute`, [line 74](../../../../../../../backend/src/sro/application/observation/artifacts.py#L74): Comment

Code: `day = (at or (batch.started_at if batch else self._clock.now())).date().isoformat()`

> The batch's own day, because the purge reads the batch and this
> writes the key: two clocks here means a prefix nobody sweeps. This
> server's day only when there is no batch to ask -- a picture that
> arrived before the evidence it illustrates -- and
> `artifact_prefixes` carries `received_at` to cover that case.

## `StoreObservationArtifact.execute`, [line 72](../../../../../../../backend/src/sro/application/observation/artifacts.py#L72): Comment

Code: `raise InvariantViolation("a picture of a sign-in page is never stored")`

> Spec §5.6: no screenshot of a sign-in page is stored, whatever the browser
> sent. The batch the picture illustrates was stored first (the extension stages
> pictures only once their batch is accepted), with its sign-in events marked by
> `redact_events`, so the picture's gesture is read back from it the way
> `read_shots` does. Refused as an invariant, which the extension treats as
> permanent and drops.

## `_pictures_a_sign_in`, [line 84](../../../../../../../backend/src/sro/application/observation/artifacts.py#L84): Docstring

> Whether the picture numbered `frame_index` in this stored batch is of a
> sign-in gesture. When the batch had events refused, stored ordinals no longer
> line up with the browser's frame numbers (`stored_shots` gives up on such a
> batch for the same reason), so any sign-in event in it refuses every picture.
