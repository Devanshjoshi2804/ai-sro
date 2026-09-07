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

import json
import logging
from datetime import datetime

from sro.application.intent.spend import over_cap
from sro.application.ports.model import Asker
from sro.application.ports.repositories import UnitOfWork
from sro.application.shared.locks import one_at_a_time
from sro.domain.observation.gesture import Gesture, Intent
from sro.domain.observation.reading import (
    INSTRUCTIONS,
    INTENT_SCHEMA,
    TAIL,
    intent_from,
    one_line,
)
from sro.domain.observation.trim import thin, trim
from sro.domain.shared.identifiers import TenantId

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
    recent = [one_line(intent) for intent in tail[-TAIL:]]
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
    for gesture in rows:
        intent = await read_gesture(
            gesture,
            tail=_tail_for(ordered, intents, gesture),
            asker=asker,
            model=model,
        )
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
