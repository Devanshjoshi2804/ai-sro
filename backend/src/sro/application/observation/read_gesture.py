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

import asyncio
import hashlib
import json
import logging
from collections.abc import Callable, Iterator, Mapping, Sequence
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
from sro.domain.observation.driving import WAS_OUR_OWN_DRIVING, our_own_driving
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
    """One gesture, one call, one intent -- error, refusal and nonsense alike.

    The reading as it came back, and nothing folded into it. `with_recent_values`
    used to run here and now runs in the loop, because the two have different
    inputs: this is handed one gesture and the readings before it, and the fold
    needs the recorded GESTURES before it -- which only the loop holds. Keeping
    it here also made the cascade unsound, since the answer cached under a piece
    of evidence would carry the first gesture's fold into the second's reading.
    """
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
    return intent_from(answer.data, gesture, answer, model=model)


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
    at_once: int = 1,
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
            at_once=at_once,
        )


async def _not_our_own_driving(
    uow: UnitOfWork, tenant_id: TenantId, rows: tuple[Gesture, ...]
) -> tuple[Gesture, ...]:
    """The ones an operator made, with this system's own replays taken out.

    The second check. The extension drops what it is driving before it is ever
    uploaded, and that was the only thing standing between a run and the
    evidence plane -- one check too few for a rule whose cost is a task mined
    from a robot imitating a person and then offered back as worth automating.
    Every other capture rule in this system is enforced twice, for the reason
    `ObservationPolicy.allows` gives: an extension that is wrong, old or lying
    does not get to write into the evidence plane.

    **Marked, not hidden.** Each one gets an intent saying what it is, which
    is what makes this safe to do here: `unread` is "has no intent row", so a
    gesture merely skipped would come back on every pass forever and the
    reading loop would stall on a window of them. An intent with no `act` is
    already what every later reader treats as nothing to learn from, the day's
    spend counts it at nothing because nothing was asked, and the record says
    which run it was -- so somebody reading the evidence can tell a replay
    from a gap.
    """
    if not rows:
        return rows
    ours = our_own_driving(
        [(row.id, row.batch_id, row.at) for row in rows],
        await uow.gestures.uploads_for(tenant_id, tuple(sorted({row.batch_id for row in rows}))),
        await uow.workflow_runs.driving_windows(tenant_id),
    )
    if not ours:
        return rows
    for row in rows:
        if row.id in ours:
            await uow.gestures.save_intent(
                Intent(gesture_id=row.id, tenant=tenant_id.value, why=WAS_OUR_OWN_DRIVING)
            )
    logger.info(
        "%s: %d gesture(s) were this browser's own driving, not read",
        tenant_id.value,
        len(ours),
    )
    return tuple(row for row in rows if row.id not in ours)


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
    at_once: int,
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
    rows = await _not_our_own_driving(uow, tenant_id, rows)

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
    # arithmetic rather than a call -- 17.1% of a real 164-gesture day.
    #
    # Only reachable with no tail, and that is not a tuning choice but the
    # whole of it: measured on that same day, keyed on the evidence alone the
    # rate is 17.1%, and keyed on the evidence the model is ACTUALLY shown --
    # which ends with the last eight readings -- it is 0.0%. Every gesture has
    # a tail nothing else has, so with one, nothing is ever reusable.
    already: dict[str, Intent] = {}

    for group in _groups(rows, at_once if not tail_size else 1):
        # The pictures first, and one at a time, because they come off the
        # unit of work: `_thin_shot` reads the batch row and the object store
        # through the same session every other query here uses, and a session
        # is not a thing two coroutines may hold at once.
        asked: list[tuple[Gesture, bytes | None, str | None]] = []
        for gesture in group:
            image = None
            if blobs is not None and thin(gesture.action.target):
                image = await _thin_shot(
                    gesture, uow=uow, blobs=blobs, tenant_id=tenant_id, cache=shots
                )
            key = _same_evidence(gesture, image) if not tail_size else None
            asked.append((gesture, image, key))

        answers, failure = await _ask_group(
            asked,
            already=already,
            asker=asker,
            model=model,
            tail=lambda gesture: (
                _tail_for(ordered, intents, gesture)[-tail_size:] if tail_size else []
            ),
        )

        saved = 0
        for gesture, _, _key in asked:
            intent = answers.get(gesture.id)
            if intent is None:
                # Its own call raised. The rest of the group answered and was
                # paid for, so they are saved below and this one stays unread
                # -- which is what `unread` means and what the next pass will
                # pick up.
                continue
            # Folded here and not inside `read_gesture`, and after the cascade
            # and not before it. The fold reads the recorded gestures of this
            # stream, which is a thing only this loop holds; and `already`
            # therefore caches the unfolded answer, so a reading reused under a
            # piece of evidence gets THIS gesture's fold rather than inheriting
            # the first one's.
            intent = with_recent_values(intent, gesture, _gestures_before(ordered, gesture))
            await uow.gestures.save_intent(intent)
            # Committed a group at a time, not once at the end: a pass that
            # dies later has already been billed for these, and a rollback
            # would leave them unread and ask -- and pay -- for them again.
            # So the next gesture of this stream is read against what this one
            # said, exactly as the rig's per-gesture query was.
            intents[gesture.id] = intent
            written += 1
            saved += 1
        if saved:
            # Only when there is something to make durable. A group whose every
            # call raised has staged nothing, and committing it anyway is a
            # round trip to Postgres that says nothing -- visible, because
            # `FakeUnitOfWork.commits` is a number a test can read and the
            # per-reading commit rule is worth keeping legible.
            await uow.commit()

        if failure is not None:
            # Loudly, and only after the group's paid-for readings are durable.
            # Swallowing it would turn a broken deployment into a pass that
            # quietly reads nothing every night.
            raise failure
    return written


def _groups(rows: Sequence[Gesture], size: int) -> Iterator[Sequence[Gesture]]:
    for start in range(0, len(rows), size):
        yield rows[start : start + size]


async def _ask_group(
    asked: list[tuple[Gesture, bytes | None, str | None]],
    *,
    already: dict[str, Intent],
    asker: Asker,
    model: str,
    tail: Callable[[Gesture], list[Intent]],
) -> tuple[dict[str, Intent], BaseException | None]:
    """Every distinct question in this group, asked once and all at once.

    Nothing in here touches the unit of work, which is the whole reason the
    group may go out together: `read_gesture` takes a gesture, an image and a
    port, and the port is an HTTP client. The session work -- the pictures
    before, the saves after -- stays one at a time around it.

    Distinct is the operative word, and it is why this deduplicates WITHIN the
    group as well as against `already`. Two gestures carrying the same evidence
    that happened to land in the same batch would otherwise both be asked, and
    the cascade's rate would become a function of where the batch boundaries
    fell -- which is not a property of the evidence and not a number anybody
    could act on.

    Returns what came back and the first exception if there was one. Not
    raised here: the answers that did come back have been paid for, and a
    raise on the way out of this function would discard them unsaved.
    """
    questions: dict[str | None, tuple[Gesture, bytes | None]] = {}
    for gesture, image, key in asked:
        if key is None:
            # With a tail there is no shared question -- every gesture trails
            # a different one -- so it is keyed by itself and the group is one.
            questions[gesture.id] = (gesture, image)
        elif key not in already:
            # Keyed by the evidence, so two gestures carrying the same bytes
            # collapse to one entry here and are asked once. WHICH of them is
            # the one asked does not matter -- the key covers the image too, so
            # it is the same question either way -- but the reading that comes
            # back is stamped with that gesture's id, and every other sharer
            # needs it re-stamped with its own. See below.
            questions[key] = (gesture, image)

    async def one(
        key: str | None, gesture: Gesture, image: bytes | None
    ) -> tuple[str | None, Intent]:
        return key, await read_gesture(
            gesture, tail=tail(gesture), asker=asker, model=model, image=image
        )

    done = await asyncio.gather(
        *(one(key, gesture, image) for key, (gesture, image) in questions.items()),
        return_exceptions=True,
    )

    failure: BaseException | None = None
    fresh: dict[str | None, Intent] = {}
    for result in done:
        if isinstance(result, BaseException):
            failure = failure or result
            continue
        key, intent = result
        fresh[key] = intent

    answers: dict[str, Intent] = {}
    for gesture, _, key in asked:
        answered = (
            already.get(key) if key in already else fresh.get(gesture.id if key is None else key)
        )
        if answered is None:
            # This one's own call raised. Every other member of the group is
            # unaffected, and this gesture stays unread.
            continue
        if key is not None:
            already.setdefault(key, answered)
        # Re-stamped unless this IS the gesture that was asked, and the test is
        # the id rather than the order it was met in. Ordering was what stood
        # in for this, and it held only while the asked gesture happened to be
        # the first sharer the loop reached; it stopped holding the moment the
        # dict kept the last. What went wrong was not subtle and was invisible
        # in every unit test: the answer carried the asked gesture's id, so it
        # was SAVED under that id for all of them -- one gesture written twice,
        # the other never written, and the never-written one read and billed
        # again on the next pass. A real 164-gesture pass reported 169 readings
        # for 164 rows, which is how it was found.
        if answered.gesture_id != gesture.id:
            answered = _reread(answered, gesture)
        answers[gesture.id] = answered
    return answers, failure


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


def _gestures_before(ordered: tuple[Gesture, ...], gesture: Gesture) -> list[Gesture]:
    """The recorded gestures of this stream that came before this one, oldest first.

    `_tail_for`'s twin, and deliberately not merged with it: that one answers
    what the MODEL should be shown about the doing so far, and this one answers
    what the OPERATOR demonstrably typed. The first is capped by
    `gemini_read_tail` because every line of it is paid for in prompt tokens;
    this one is not capped at all, because it costs nothing and a form filled
    across twenty gestures is a form whose first field still belongs in the
    save.

    Same stream, same reason: a value typed in the operator's other tab was
    never on this form.
    """
    return [
        other for other in ordered if other.stream_id == gesture.stream_id and other.at < gesture.at
    ]


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
        at_once: int = 1,
    ) -> None:
        self._uow = uow
        self._asker = asker
        self._model = model
        self._clock = clock
        self._cap_usd = cap_usd
        self._blobs = blobs
        self._tail_size = tail_size
        self._at_once = at_once

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
                at_once=self._at_once,
            )
