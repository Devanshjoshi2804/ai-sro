"""A3 — one model call per gesture, and never a batch of them.

Batching stream items into a shared call degrades each item through semantic
interference and diluted attention; measured accuracy decays roughly
A(T) = A_max * e^(-b(T-1)) in batch size while throughput only saturates. The
saving is small and the cost is per-item quality. So: one gesture, one call.

Ported from `read_gesture` in `new_agent_arch/src/rig/intents.py` and
`read_new_gestures` / `_read_unread` in `new_agent_arch/src/rig/api.py`. The
words, the schema and the parsing are `sro.domain.observation.reading`; this is
the half that asks and the half that stores.
"""

from __future__ import annotations

import hashlib
import json
import logging
from collections.abc import Mapping
from dataclasses import replace
from datetime import datetime

from sro.application.context import RequestContext
from sro.application.intent.spend import over_cap
from sro.application.observation.evidence import once_each
from sro.application.observation.shots import frame_of, frames_by_instant, stored_shots
from sro.application.ports.blob import BlobStore
from sro.application.ports.model import Asker, asker_or_refuse
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.system import Clock
from sro.application.shared.locks import one_at_a_time
from sro.application.shared.refusals import OverCap
from sro.domain.observation.gesture import Gesture, Intent
from sro.domain.observation.reading import (
    INSTRUCTIONS,
    INTENT_SCHEMA,
    TAIL,
    intent_from,
    one_line,
    with_recent_values,
)
from sro.domain.observation.trim import thin, trim
from sro.domain.shared.identifiers import BatchId, TenantId

logger = logging.getLogger(__name__)

READING_LIMIT = 200
"""How many unread gestures one pass reads. A drain calls this repeatedly.

Bounded because a pass that asks the model thousands of times before returning
is a pass nothing can stop, and because every pass must reduce the unread set:
a pass that returns 0 ends the drain."""


async def read_gesture(
    gesture: Gesture,
    *,
    tail: list[Intent],
    asker: Asker,
    model: str,
    image: bytes | None = None,
) -> Intent:
    """One gesture, one call, one intent -- error, refusal and nonsense alike."""
    # Already bounded by the caller, which is the one that knows how long a
    # tail this deployment asked for. Re-trimming to the constant here made
    # `tail_size` unenforceable from above: a caller asking for none still
    # got eight if it handed eight over.
    recent = [one_line(intent) for intent in tail]
    evidence = json.dumps(
        {"gesture": trim(gesture), "just_before": recent},
        indent=2,
        sort_keys=True,
        # The redaction marker is «redacted», and the default ensure_ascii
        # writes it into the prompt as \u00abredacted\u00bb -- a form
        # nothing else in this system uses. The model was being asked to understand a
        # marker written one way here and another way everywhere else, and a
        # reviewer grepping stored prompts for it found nothing. Every
        # json.dumps on a path to a prompt or to the store says so.
        ensure_ascii=False,
    )

    answer = await asker.ask(
        model=model,
        instructions=INSTRUCTIONS,
        evidence=evidence,
        schema=INTENT_SCHEMA,
        # A picture only where the markup could not name the control. A
        # screenshot on every gesture is the largest avoidable line on the
        # bill, and on a named control it tells the model nothing the
        # field label already did.
        image=image if thin(gesture.action.target) else None,
    )
    intent = intent_from(answer.data, gesture, answer, model=model)
    return with_recent_values(intent, gesture, tail)


async def read_new_gestures(
    uow: UnitOfWork,
    *,
    tenant_id: TenantId,
    asker: Asker,
    model: str,
    now: datetime,
    cap_usd: float,
    limit: int = READING_LIMIT,
    blobs: BlobStore | None = None,
    tail_size: int = TAIL,
) -> int:
    """Every stored gesture of THIS TENANT with no intent gets exactly one reading.

    Scoped, because the reading is what costs money: a second tenant in one
    database had this loop paying for gestures no pass of ours will ever mine,
    and filing intents under their tenant on our bill.

    One reading loop at a time. Two concurrent callers both select the same
    unread gestures before either writes an intent, so every gesture in the
    race window is asked -- and billed -- twice, while the replacing write
    leaves only one cost row. One of these fires per ingest, so two batches
    arriving together is enough to trigger it.

    Keyed by tenant, not by the bare word "reading". What the lock is for is two
    readers racing over the same unread rows, and those rows belong to a
    tenant: a single global name also made two DIFFERENT tenants take turns,
    which is nothing but a queue. The bake-off is the caller that showed it --
    five models, five copies of one day, and a lock that turned an hour of
    parallel work into five hours of serial work.

    ponytail: a process-local lock, because this runs in one process. Claim
    rows in the database if it ever becomes more than one.

    `uow` is already open: this commits per reading and never enters or leaves
    the block, so the caller owns the session.

    `blobs` is optional and, missing, changes nothing: every gesture is read
    exactly as before. Given, it is read from only for a `thin` gesture --
    see `sro.domain.observation.trim.thin` -- the one case a picture can tell
    the model something its markup could not. A deployment with no object
    store wired to this pass is not a broken one; it is one asking the same
    question this always asked, without the one extra source a picture is.
    """
    async with one_at_a_time(f"reading:{tenant_id.value}"):
        return await _read_unread(
            uow,
            tenant_id=tenant_id,
            asker=asker,
            model=model,
            now=now,
            cap_usd=cap_usd,
            limit=limit,
            blobs=blobs,
            tail_size=tail_size,
        )


async def _read_unread(
    uow: UnitOfWork,
    *,
    tenant_id: TenantId,
    asker: Asker,
    model: str,
    now: datetime,
    cap_usd: float,
    limit: int,
    blobs: BlobStore | None,
    tail_size: int,
) -> int:
    # An intent row means a reading happened, whatever came back in it -- an
    # error, or an answer whose `act` was the wrong type and got nulled. None
    # of those is retried: `unread` is "has no intent row", the model was
    # asked, it answered, and it was billed. Re-asking the same evidence with
    # the same prompt bills again for the same likely answer. What a row with
    # no usable `act` gets instead is to be visible: the day's spend counts it
    # as unusable and the gestures route returns an intent rather than null.
    # Not both billed and hidden -- pick one, and this picks visible.
    rows = await uow.gestures.unread(tenant_id, limit=limit)

    why = await over_cap(uow, tenant_id, now=now, cap_usd=cap_usd)
    if why:
        # Reading stops; capture does not. The evidence is still stored, so
        # raising the cap tomorrow reads what today declined -- which is why
        # this stops the asking rather than the mirroring. Read before the
        # loop asks anything: a cap checked per gesture is a cap that has
        # already paid for the gesture it stops on.
        logger.warning("%s for %s, %d gesture(s) unread", why, tenant_id.value, len(rows))
        return 0

    # The tail comes out of one read of the tenant's evidence rather than a
    # query per gesture, and the scan of it is linear per gesture.
    # ponytail: this reads the tenant's WHOLE HISTORY, not a day. Neither
    # `gestures_for` nor `intents_for` takes a time bound, so every pass
    # deserialises every gesture ever captured -- request and response bodies
    # included -- and that set only grows. Defensible while a pass is dominated
    # by up to `limit` model calls, and no longer once it is not. The upgrade is
    # `GestureRepository.tail_for(stream_id, before)`: the rig had that query in
    # SQL, and a port is exactly the seam it belongs on.
    ordered = await uow.gestures.gestures_for(tenant_id)
    intents = {intent.gesture_id: intent for intent in await uow.gestures.intents_for(tenant_id)}

    written = 0
    shots: dict[str, tuple[Mapping[str, int], Mapping[float, int]] | None] = {}
    # One reading per distinct piece of evidence. Two gestures the model would
    # be shown the same bytes for get the same answer, so the second one is
    # arithmetic rather than a call -- 25.6% of a real 164-gesture day.
    #
    # Only reachable with no tail, and that is not a tuning choice but the
    # whole of it: measured on that same day, keyed on the evidence alone the
    # rate is 25.6%, and keyed on the evidence the model is ACTUALLY shown --
    # which ends with the last eight readings -- it is 0.0%. Every gesture has
    # a tail nothing else has, so with one, nothing is ever reusable.
    already: dict[str, Intent] = {}
    for gesture in rows:
        image = None
        if blobs is not None and thin(gesture.action.target):
            image = await _thin_shot(
                gesture, uow=uow, blobs=blobs, tenant_id=tenant_id, cache=shots
            )

        seen = _same_evidence(gesture, image) if not tail_size else None
        if seen is not None and seen in already:
            intent = _reread(already[seen], gesture)
        else:
            intent = await read_gesture(
                gesture,
                tail=_tail_for(ordered, intents, gesture)[-tail_size:] if tail_size else [],
                asker=asker,
                model=model,
                image=image,
            )
            if seen is not None:
                already[seen] = intent
        await uow.gestures.save_intent(intent)
        # Committed one reading at a time, not once at the end: a loop that
        # raises on gesture 50 has already been billed for 49, and a rollback
        # would leave them unread and ask -- and pay -- for them again.
        await uow.commit()
        # So the next gesture of this stream is read against what this one
        # said, exactly as the rig's per-gesture query was.
        intents[gesture.id] = intent
        written += 1
    return written


def _same_evidence(gesture: Gesture, image: bytes | None) -> str:
    """A name for exactly what the model would be shown about this gesture.

    `trim` is what `read_gesture` serialises, so hashing it is hashing the
    question rather than guessing at what makes two questions alike. A key
    built by hand out of the fields that "look like they matter" is the
    version of this that serves a stale answer: keyed on the control and the
    action alone, the same real day reports 65.9% reusable, and the extra
    forty points are gestures whose typed value or request body differed --
    every one of which would have been answered with somebody else's values.

    The picture counts too. A thin gesture asked about with its screenshot and
    the same gesture asked about without one are two different questions, and
    only the first is worth the token it costs.
    """
    payload = json.dumps(trim(gesture), sort_keys=True, default=str)
    if image is not None:
        payload += hashlib.sha256(image).hexdigest()
    return hashlib.sha256(payload.encode()).hexdigest()


def _reread(seen: Intent, gesture: Gesture) -> Intent:
    """The same answer, filed against this gesture, and billed to nobody.

    The tokens are zeroed rather than copied. The first reading paid for them
    and the row that says so is already stored; repeating the figure here
    would make a day of mining cost whatever the duplicates happened to
    total, which is the same arithmetic error `MineResult` fixed by putting
    the bill on the pass instead of on each workflow it found.
    """
    return replace(
        seen,
        gesture_id=gesture.id,
        tenant=gesture.tenant,
        in_tokens=0,
        out_tokens=0,
        thought_tokens=0,
        cost_usd=0.0,
        unpriced=False,
    )


async def _thin_shot(
    gesture: Gesture,
    *,
    uow: UnitOfWork,
    blobs: BlobStore,
    tenant_id: TenantId,
    cache: dict[str, tuple[Mapping[str, int], Mapping[float, int]] | None],
) -> bytes | None:
    """The picture behind one thin gesture, or `None` when there is not one.

    A `thin` gesture is the one case `read_gesture` can use a picture for at
    all, and this is that picture -- the same join `ReadShots` reads back for
    a mined job's evidence tab: the recorder numbers every gesture in a batch,
    a screenshot is filed under that number, and the two sides are matched on
    the browser's clock because a gesture row carries an id the recording's
    own payload never saw.

    `cache` holds the listing and the frame numbering per batch, keyed once
    per reading pass rather than once per gesture: a pass over hundreds of
    gestures from a handful of batches would otherwise re-list the object
    store and re-parse the same NDJSON payload for every thin gesture in it.
    """
    if gesture.batch_id not in cache:
        batch = await uow.observations.get(tenant_id, BatchId(gesture.batch_id))
        found = await stored_shots(blobs, batch) if batch is not None else {}
        if batch is None or not found:
            cache[gesture.batch_id] = None
        else:
            try:
                frames = frames_by_instant(once_each(await blobs.read(batch.uri)))
            except (KeyError, OSError):
                # The evidence aged out from under the gesture that cites it.
                cache[gesture.batch_id] = None
            else:
                cache[gesture.batch_id] = (found, frames)

    entry = cache[gesture.batch_id]
    if entry is None:
        return None
    found, frames = entry
    ordinal = frames.get(gesture.at)
    if ordinal is None:
        return None
    shot = frame_of(found, ordinal)
    if shot is None:
        return None
    try:
        return await blobs.read(shot.uri)
    except (KeyError, OSError):
        return None


def _tail_for(
    ordered: tuple[Gesture, ...], intents: dict[str, Intent], gesture: Gesture
) -> list[Intent]:
    """The readings of this stream that came before this gesture, oldest first.

    Scoped to the stream rather than the tenant: `continues` asks whether this
    gesture carries on the last doing, and one operator's other tab is not it.

    Unbounded on purpose. `read_gesture` takes the last TAIL of whatever it is
    handed, and one function knowing that number is one place for it to be
    wrong.
    """
    return [
        intents[other.id]
        for other in ordered
        if other.stream_id == gesture.stream_id and other.at < gesture.at and other.id in intents
    ]


class ReadGestures:
    """Read this tenant's unread gestures, once, and bill it.

    The same shape as `sro.application.observation.mine_pass.MinePass`, and for
    the same reasons: both refusals happen here, before `read_new_gestures`
    itself. That function's own cap check returns a bare `int` -- no reason a
    reader can tell apart from "nothing was unread" -- which is right for a
    loop that fires on every ingest and wrong for a request that asked to be
    told. Raised here, the door answers 503 and 429, which is what those two
    facts are.
    """

    def __init__(
        self,
        uow: UnitOfWork,
        *,
        asker: Asker | None,
        model: str,
        clock: Clock,
        cap_usd: float,
        blobs: BlobStore | None = None,
        tail_size: int = TAIL,
    ) -> None:
        self._uow = uow
        self._asker = asker
        self._model = model
        self._clock = clock
        self._cap_usd = cap_usd
        self._blobs = blobs
        self._tail_size = tail_size

    async def execute(self, ctx: RequestContext) -> int:
        # Before the session is opened: neither refusal needs a database, and
        # a 503 that first took a connection is a 503 that made the outage
        # slightly worse.
        asker = asker_or_refuse(self._asker)
        now = self._clock.now()
        async with self._uow as uow:
            why = await over_cap(uow, ctx.tenant_id, now=now, cap_usd=self._cap_usd)
            if why is not None:
                raise OverCap(why)
            return await read_new_gestures(
                uow,
                tenant_id=ctx.tenant_id,
                asker=asker,
                model=self._model,
                now=now,
                cap_usd=self._cap_usd,
                blobs=self._blobs,
                tail_size=self._tail_size,
            )
