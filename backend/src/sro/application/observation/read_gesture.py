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


async def read_gesture(
    gesture: Gesture,
    *,
    tail: list[Intent],
    asker: Asker,
    model: str,
    image: bytes | None = None,
) -> Intent:
    recent = [one_line(intent) for intent in tail]
    evidence = json.dumps(
        {"gesture": trim(gesture), "just_before": recent},
        indent=2,
        sort_keys=True,
        ensure_ascii=False,
    )

    answer = await asker.ask(
        model=model,
        instructions=INSTRUCTIONS,
        evidence=evidence,
        schema=INTENT_SCHEMA,
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
    rows = await uow.gestures.unread(tenant_id, limit=limit)
    rows = await _not_our_own_driving(uow, tenant_id, rows)

    why = await over_cap(uow, tenant_id, now=now, cap_usd=cap_usd)
    if why:
        logger.warning("%s for %s, %d gesture(s) unread", why, tenant_id.value, len(rows))
        return 0

    ordered = await uow.gestures.gestures_for(tenant_id)
    intents = {intent.gesture_id: intent for intent in await uow.gestures.intents_for(tenant_id)}

    written = 0
    shots: dict[str, tuple[Mapping[str, int], Mapping[float, int]] | None] = {}
    already: dict[str, Intent] = {}

    for group in _groups(rows, at_once if not tail_size else 1):
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
                continue
            intent = with_recent_values(intent, gesture, _gestures_before(ordered, gesture))
            await uow.gestures.save_intent(intent)
            intents[gesture.id] = intent
            written += 1
            saved += 1
        if saved:
            await uow.commit()

        if failure is not None:
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
    questions: dict[str | None, tuple[Gesture, bytes | None]] = {}
    for gesture, image, key in asked:
        if key is None:
            questions[gesture.id] = (gesture, image)
        elif key not in already:
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
            continue
        if key is not None:
            already.setdefault(key, answered)
        if answered.gesture_id != gesture.id:
            answered = _reread(answered, gesture)
        answers[gesture.id] = answered
    return answers, failure


def _same_evidence(gesture: Gesture, image: bytes | None) -> str:
    payload = json.dumps(trim(gesture), sort_keys=True, default=str)
    if image is not None:
        payload += hashlib.sha256(image).hexdigest()
    return hashlib.sha256(payload.encode()).hexdigest()


def _reread(seen: Intent, gesture: Gesture) -> Intent:
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
    if gesture.batch_id not in cache:
        batch = await uow.observations.get(tenant_id, BatchId(gesture.batch_id))
        found = await stored_shots(blobs, batch) if batch is not None else {}
        if batch is None or not found:
            cache[gesture.batch_id] = None
        else:
            try:
                frames = frames_by_instant(once_each(await blobs.read(batch.uri)))
            except (KeyError, OSError):
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
    return [
        other for other in ordered if other.stream_id == gesture.stream_id and other.at < gesture.at
    ]


def _tail_for(
    ordered: tuple[Gesture, ...], intents: dict[str, Intent], gesture: Gesture
) -> list[Intent]:
    return [
        intents[other.id]
        for other in ordered
        if other.stream_id == gesture.stream_id and other.at < gesture.at and other.id in intents
    ]


class ReadGestures:
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
