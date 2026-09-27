# Notes for `backend/src/sro/infrastructure/db/evidence.py`

Comments and docstrings moved out of [`backend/src/sro/infrastructure/db/evidence.py`](../../../../../../../backend/src/sro/infrastructure/db/evidence.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/infrastructure/db/evidence.py#L1): Docstring

> The evidence plane on Postgres: gestures, their readings, and the pool.
>
> The rules here are the rig's, and they were SQLite there. Three of them had to
> be translated rather than copied, and each translation is marked where it
> happens:
>
> * ``INSERT OR IGNORE`` and ``INSERT OR REPLACE`` become ``ON CONFLICT DO
>   NOTHING`` and ``ON CONFLICT DO UPDATE`` on a named conflict target. SQLite's
>   forms swallow *every* constraint; naming the target means a different
>   constraint failing is still an error rather than a silent no-op.
> * ``orphan_pages`` keyed on SQLite's ``rowid`` alias becomes a bigserial
>   identity. It is a surrogate either way, and the reason it is one is that two
>   distinct page events can share a batch, an instant and a payload.
> * The empty-``shown`` branch of ``age`` stays spelled out. ``gesture_id NOT IN
>   ()`` is not a predicate that matches everything -- under three-valued logic
>   it matches nothing -- so a pass that packed no evidence would leave every
>   entry's waiting frozen, which is the failure the second clock exists to
>   prevent.
>
> The row-to-record mapping lives here rather than in ``mappers.py``: a
> repository's mapping belongs with the repository, and there are four shapes
> here that nothing else reads.

## `_when`, [line 128](../../../../../../../backend/src/sro/infrastructure/db/evidence.py#L128): Docstring

> A device's own timestamp, as it sent it, or nothing.
>
> Empty for uploads from before the protocol carried both clocks, and
> `fromisoformat` is strict: what it cannot read is a clock this cannot
> reason about, which is not an error -- it is one gesture left alone.

## `SqlPoolRepository`, [line 340](../../../../../../../backend/src/sro/infrastructure/db/evidence.py#L340): Docstring

> The rig's ``pool`` module, one storage layer down.
>
> Live and retired are two reads because a retired entry is still a row. It
> is the record that the gesture has been mined (read K_POOL_AGE + 1 times,
> read and gone stale, or this browser's own driving), so no pass packs it
> again, and nothing here ever deletes one. The only entry that leaves is one
> a pass cited, and it leaves because it was placed.

## `SqlGestureRepository.add_batch`, [line 155](../../../../../../../backend/src/sro/infrastructure/db/evidence.py#L155): Comment

Code: `await self._session.flush()`

> Flushed here rather than at commit, and before the gestures are
> added: whether this upload is a retry has to be settled before
> anything it carries is written, and a claim the rest of the block
> then fails to follow rolls back with it. An id claimed but never
> followed by its gestures can never be retried -- the events it
> named are gone, and the id says they were handled.

## `SqlGestureRepository.add_gestures`, [line 163](../../../../../../../backend/src/sro/infrastructure/db/evidence.py#L163): Comment

Code: `await self._session.flush()`

> Flushed and translated here for ``add_batch``'s reason and one
> more: a gesture id already stored is a retried upload the batch
> claim did not catch, and doubling a tenant's evidence is exactly
> what that claim exists to stop. The caller has to hear it as a
> ``Conflict`` rather than as whatever the driver raises at commit
> -- and that is the only shape a fake can be held to.

## `SqlGestureRepository.gestures_for`, [line 186](../../../../../../../backend/src/sro/infrastructure/db/evidence.py#L186): Comment

Code: `rows = (`

> The id breaks a tie the rig left open: `at` is the browser's clock in
> milliseconds and two gestures of one burst share it, so `at` alone is
> not a total order -- and in `unread` below, where the order decides
> which 200 are read, that is a different set rather than a different
> order.

## `SqlGestureRepository.uploads_for`, [line 213](../../../../../../../backend/src/sro/infrastructure/db/evidence.py#L213): Comment

Code: `ended_at=_when(row.ended_at),`

> Kept as the device sent it, which is a string and may be
> empty: uploads predating the two clocks carry neither, and a
> batch that cannot say what its clock was doing is one nothing
> here will guess about.

## `SqlGestureRepository.unread`, [line 220](../../../../../../../backend/src/sro/infrastructure/db/evidence.py#L220): Comment

Code: `query = (`

> A gesture that was read is never offered again, error or not: the
> model was asked, it answered, and it was billed. Re-asking the same
> evidence with the same prompt bills again for the same likely answer.

## `SqlGestureRepository.newest_arrival`, [line 231](../../../../../../../backend/src/sro/infrastructure/db/evidence.py#L231): Comment

Code: `carried = (`

> The same `received_at` and the same "carried something" rule as
> `tenants_since` below, so the two agree about what an arrival is: a
> watching extension uploads on its timer whether or not anybody did
> anything, and counting an empty heartbeat would keep a tenant
> looking busy while nobody worked.

## `SqlGestureRepository.tenants_since`, [line 242](../../../../../../../backend/src/sro/infrastructure/db/evidence.py#L242): Comment

Code: `carried = (`

> ``received_at`` and not ``ended_at``: the first is when this process
> took the upload and the second is the device's own clock, kept as a
> string exactly as it was sent. A browser with a wrong clock would
> otherwise take its tenant out of every sweep or put it in every one.
>
> **Batches that carried something.** A watching extension uploads on
> its timer whether or not anybody did anything, so an idle browser
> posts an empty batch a minute, forever. `MineLately` reads this to
> ask "is this tenant mid-task", and an empty heartbeat answered yes --
> so a tenant was `still working; leaving this one to settle` for as
> long as the browser stayed connected, and mining never ran at all
> while the product was in use. Seen on the QA deployment: fifty-four
> gestures captured, five empty batches after them, and nothing mined
> five minutes later.
>
> An `exists` rather than a join: one row per tenant is wanted, and a
> join would multiply by the gestures before the `distinct` took them
> away again.

## `SqlGestureRepository.save_intent`, [line 253](../../../../../../../backend/src/sro/infrastructure/db/evidence.py#L253): Comment

Code: `values = _intent_values(intent, created_at=datetime.now(tz=UTC))`

> ``created_at`` is the server's, taken here rather than carried on the
> record: it is when the reading was stored, and the spend window is
> summed over it.

## `SqlGestureRepository.save_intent`, [line 260](../../../../../../../backend/src/sro/infrastructure/db/evidence.py#L260): Comment

Code: `for attribute in IntentRow.__mapper__.column_attrs`

> Only the columns the insert supplied are replaced. `intents.continues`
> stays in the schema with nothing mapping it (GC 17); replacing every
> column wrote NULL over what it held. By mapped attribute, because
> `object_` is the attribute and `object` the column.

## `SqlGestureRepository.save_intent`, [line 258](../../../../../../../backend/src/sro/infrastructure/db/evidence.py#L258): Comment

Code: `set_={`

> Every column but the key takes the new reading's value, which
> is what INSERT OR REPLACE did: a second reading of one
> gesture supersedes the first rather than sitting beside it.

## `SqlGestureRepository.intents_for`, [line 271](../../../../../../../backend/src/sro/infrastructure/db/evidence.py#L271): Comment

Code: `.execution_options(populate_existing=True)`

> The upsert above is a Core statement, so a row this session had
> already loaded would otherwise come back at its old reading.

## `SqlGestureRepository.intents_since`, [line 280](../../../../../../../backend/src/sro/infrastructure/db/evidence.py#L280): Comment

Code: `.order_by(IntentRow.created_at.desc(), IntentRow.gesture_id.desc())`

> The gesture id breaks the tie: ``created_at`` is the server
> clock inside ``save_intent`` and a batch of readings saved in one
> call routinely shares it, so the clock alone is not a total order
> -- and an order that is not total is one that changes between
> reads of the same rows.

## `SqlGestureRepository.intents_since`, [line 281](../../../../../../../backend/src/sro/infrastructure/db/evidence.py#L281): Comment

Code: `.execution_options(populate_existing=True)`

> The reading a caller has just saved is the one it is most likely
> to be reading back, and ``save_intent`` upserts with a Core
> statement -- so, as in ``intents_for``, the identity map must not
> hand back the reading this session superseded.

## `SqlGestureRepository.add_orphan_page`, [line 308](../../../../../../../backend/src/sro/infrastructure/db/evidence.py#L308): Comment

Code: `self._session.add(`

> No dedup key, unlike its sibling above: two distinct page events can
> share a batch, an instant and a payload, and the batch's own primary
> key already makes re-ingesting a batch a no-op.

## `SqlGestureRepository.streams`, [line 334](../../../../../../../backend/src/sro/infrastructure/db/evidence.py#L334): Comment

Code: `.order_by(last.desc(), GestureRow.stream_id)`

> The stream id breaks the tie: two streams whose last gesture
> shares an instant would otherwise swap places between reads.

## `SqlPoolRepository.add_unclaimed`, [line 348](../../../../../../../backend/src/sro/infrastructure/db/evidence.py#L348): Comment

Code: `await self._session.execute(`

> In full, not only where it intersects the window. A pooled
> gesture is packed beside the fresh ones, so a pass can cite
> evidence that is already in the pool -- and clearing only the
> intersection would leave that citation to age out and retire
> despite having been placed.

## `SqlPoolRepository.add_unclaimed`, [line 351](../../../../../../../backend/src/sro/infrastructure/db/evidence.py#L351): Comment

Code: `.execution_options(synchronize_session=False)`

> ``synchronize_session=False`` for the same reason ``_bump``
> gives: no PoolRow is ever loaded as an ORM object here, so
> there is no session state to keep in step and asking for one
> only buys a SELECT of the rows about to go.

## `SqlPoolRepository.add_unclaimed`, [line 373](../../../../../../../backend/src/sro/infrastructure/db/evidence.py#L373): Comment

Code: `added = await self._session.execute(`

> DO NOTHING, the rig's OR IGNORE: a gesture that has sat unplaced
> through three passes keeps the age those passes gave it. Re-entering
> must not reset the clock, or nothing in a recurring window ever
> retires -- and it leaves a retired row retired, which is a decision.
> RETURNING rather than rowcount, because how many actually entered is
> the answer, and it is what the caller reports.

## `SqlPoolRepository.age`, [line 388](../../../../../../../backend/src/sro/infrastructure/db/evidence.py#L388): Comment

Code: `await self._session.execute(`

> No window named is not the same as an empty one: a caller with no
> window is not claiming nothing was read.

## `SqlPoolRepository.age`, [line 394](../../../../../../../backend/src/sro/infrastructure/db/evidence.py#L394): Comment

Code: `await self._session.execute(self._bump(*live, waited=PoolRow.waited + 1))`

> Spelled out rather than folded into the general case.
> ``gesture_id NOT IN ()`` matches nothing under three-valued
> logic, so a pass that packed no evidence would have frozen
> every entry's waiting -- the "the day did not rotate" failure
> the second clock exists to prevent, behind a branch nobody
> reads. A pass that packs nothing is exactly when the pool
> most needs to record that nobody was seen.

## `SqlPoolRepository.age`, [line 396](../../../../../../../backend/src/sro/infrastructure/db/evidence.py#L396): Comment

Code: `await self._session.execute(`

> Shown: one reading older, and its waiting starts again.

## `SqlPoolRepository.age`, [line 408](../../../../../../../backend/src/sro/infrastructure/db/evidence.py#L408): Comment

Code: `await self._session.execute(`

> Passed over: one pass of waiting, which is what raises it next
> time. Ageing was doing both jobs, so an entry read six times
> outranked one never seen at all and the day did not rotate.

## `SqlPoolRepository.age`, [line 412](../../../../../../../backend/src/sro/infrastructure/db/evidence.py#L412): Comment

Code: `passes = await self._session.execute(`

> Two caps, because a pool that only counts passes keeps an entry
> forever in a tenant nobody is mining, and one that only counts days
> retires an entry a busy tenant has already reconsidered fifty times.
> Whichever comes first, and the row says which -- both filtered on
> `retired = 0`, so nothing is retired twice or re-reported by the
> other cap. A failed reading (`failed=True`) moves nothing but `failed`:
> `waited` is untouched, so the next pass packs the same window and
> K_MINE_ATTEMPTS counts per window rather than over whichever entries the
> waiting bonus rotates in (M1 round 3).
> The stale cap takes only what has been read (`age > 0`):
> retired is never mined again, and an unread entry is backlog.
> RETURNING rather than ``rowcount``, as in ``add_unclaimed``: which
> rows actually retired is the answer, and it is one shape everywhere
> rather than the driver's own count.

## `SqlPoolRepository._bump`, [line 461](../../../../../../../backend/src/sro/infrastructure/db/evidence.py#L461): Comment

Code: `return (`

> ``synchronize_session=False`` because nothing in this repository ever
> loads a PoolRow as an ORM object -- the reads below select columns --
> so there is no in-session state for the UPDATE to keep in step with,
> and asking for one would have SQLAlchemy fetch the affected rows
> first to do it.
