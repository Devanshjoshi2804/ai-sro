# Notes for `backend/src/sro/application/observation/read_shots.py`

Comments and docstrings moved out of [`backend/src/sro/application/observation/read_shots.py`](../../../../../../../backend/src/sro/application/observation/read_shots.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/observation/read_shots.py#L1): Docstring

> The screenshots behind the gestures one workflow cites.
>
> The recorder photographed an operator's screen as it watched, and every one of
> those pictures is in the object store keyed by
> ``tenant/principal/day/batch/screenshot/NNNNN.png`` -- and until this, nothing
> read a single one of them back. A mined job's evidence was prose about clicks
> nobody could see.
>
> The join is `shots`': the number on a picture is the gesture's position in its
> batch as the recorder counted it. What is different here is the side we start
> from. `teach` walks a batch's stored lines and is holding the very events the
> numbers were assigned to; this is holding `Gesture` rows, which carry ids
> `correlate` minted and the payload never saw. So the batch is read back and
> its gestures numbered again, and the two sides are matched on the browser's
> clock -- the one value both carry. `frames_by_instant` drops an instant two
> gestures share rather than guessing between them.
>
> Tenant scoping is the whole of the security here, because a presigned URL is a
> capability: whoever holds it reads that object without proving anything again.
> Both reads are by `ctx.tenant_id` -- the workflow, then the batch -- and the
> key a URL is minted for is built from the *batch's* tenant and principal by
> `artifact_prefixes`. A batch belonging to somebody else is `None` and its
> pictures are never reached.

## `PlayableShot`, [line 18](../../../../../../../backend/src/sro/application/observation/read_shots.py#L18): Docstring

> A picture of one gesture, addressed for a browser to fetch once.

## `ReadShots`, [line 23](../../../../../../../backend/src/sro/application/observation/read_shots.py#L23): Docstring

> What a workflow's cited gestures looked like on the screen.
>
> Keyed by gesture id, and a gesture nobody photographed simply has no
> entry: the per-minute cap, a background tab, a batch the server filtered.
> An entry carrying nothing would make the console draw a broken picture
> where there was never one to draw.

## `ReadShots.execute`, [line 30](../../../../../../../backend/src/sro/application/observation/read_shots.py#L30): Comment

Code: `workflow = await uow.workflows.get(ctx.tenant_id, workflow_id)`

> Tenant-scoped, and this is the whole of the 404: a workflow of
> somebody else's is not found rather than read. `ReadEvidence`
> beside it answers the same way, so the route this rides on says
> one thing about an unknown job rather than two.

## `ReadShots.execute`, [line 32](../../../../../../../backend/src/sro/application/observation/read_shots.py#L32): Comment

Code: `gestures = await uow.gestures.gestures_for(ctx.tenant_id, ids=cited) if cited else ()`

> Not a null check: `gestures_for` with no ids is `IN ()` against
> Postgres, and a workflow that cites nothing is a real row.

## `ReadShots.execute`, [line 39](../../../../../../../backend/src/sro/application/observation/read_shots.py#L39): Comment

Code: `shots: dict[str, PlayableShot] = {}`

> Outside the transaction: what is left is object storage, and a
> database connection held open across it is held for nothing.

## `ReadShots.execute`, [line 43](../../../../../../../backend/src/sro/application/observation/read_shots.py#L43): Comment

Code: `continue`

> The evidence aged out from under the job that cites it. The
> other gestures still have their pictures.

## `ReadShots.execute`, [line 57](../../../../../../../backend/src/sro/application/observation/read_shots.py#L57): Comment

Code: `url = await self._blobs.presigned_url_for_uri(shot.uri, expires_in=PLAYBACK_TTL)`

> Short-lived, and the same window playback uses: a link that
> outlives the page it was drawn on is a copy of somebody's
> screen that nobody is tracking.
