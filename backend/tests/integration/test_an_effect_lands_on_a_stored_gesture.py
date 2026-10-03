from __future__ import annotations

import asyncio
from dataclasses import replace

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from sro.domain.observation.gesture import Action, Effect, FrameHop, Gesture, GestureBatch, Seen
from sro.domain.shared.identifiers import TenantId
from sro.infrastructure.db.repositories import SqlUnitOfWork

TENANT = TenantId("acme")
AT = 1_790_000_000.25
SAID = Effect(appeared=(Seen("status", "Saved"),), ended="quiet")


def _gesture(
    gesture_id: str,
    at: float = AT,
    frame: tuple[FrameHop, ...] | None = None,
    ref: str | None = "r.1",
) -> Gesture:
    return Gesture(
        id=gesture_id,
        tenant=TENANT.value,
        stream_id="dev-1",
        batch_id="b1",
        at=at,
        url="https://wms.example/a",
        system="wms.example",
        tab_id=1,
        frame_url=None,
        action=Action(
            kind="click",
            value=None,
            secret=False,
            at=at,
            url="https://wms.example/a",
            frame_path=frame,
            ref=ref,
        ),
    )


async def _attach(
    session_factory: async_sessionmaker[AsyncSession], effect: Effect = SAID, of: str = "r.1"
) -> bool:
    async with SqlUnitOfWork(session_factory) as uow:
        ok = await uow.gestures.attach_effect(
            TENANT, stream_id="dev-1", tab_id=1, frame_path=None, at=AT, of=of, effect=effect
        )
        await uow.commit()
    return ok


async def _stored(session_factory: async_sessionmaker[AsyncSession]) -> tuple[Gesture, ...]:
    async with SqlUnitOfWork(session_factory) as uow:
        return await uow.gestures.gestures_for(TENANT)


async def _store(session_factory: async_sessionmaker[AsyncSession], *gestures: Gesture) -> None:
    async with SqlUnitOfWork(session_factory) as uow:
        await uow.gestures.add_batch(_batch())
        await uow.gestures.add_gestures(gestures)
        await uow.commit()


def _batch() -> GestureBatch:
    return GestureBatch(
        batch_id="b1",
        device_id="dev-1",
        tenant=TENANT.value,
        mode="passive",
        received_at="2026-10-02T00:00:00+00:00",
        started_at="2026-10-02T00:00:00+00:00",
        ended_at="2026-10-02T00:01:00+00:00",
        accepted=1,
        rejected=0,
    )


async def test_an_effect_lands_once_and_never_overwrites(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await _store(session_factory, _gesture("ges_1"))
    assert await _attach(session_factory) is True
    assert (
        await _attach(session_factory, replace(SAID, appeared=(Seen("status", "Other"),))) is False
    )
    (stored,) = await _stored(session_factory)
    assert stored.action.effect == SAID


async def test_two_gestures_in_one_millisecond_take_no_effect(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await _store(session_factory, _gesture("ges_1"), _gesture("ges_2", ref="r.1"))
    assert await _attach(session_factory) is False
    assert all(one.action.effect is None for one in await _stored(session_factory))


async def test_another_frame_does_not_match(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await _store(session_factory, _gesture("ges_1", frame=(FrameHop(2, "https://x.example/"),)))
    assert await _attach(session_factory) is False


async def test_another_tenant_tab_or_stream_does_not_match(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await _store(session_factory, _gesture("ges_1"))
    async with SqlUnitOfWork(session_factory) as uow:
        for tenant, stream, tab in (
            (TenantId("other"), "dev-1", 1),
            (TENANT, "dev-2", 1),
            (TENANT, "dev-1", 2),
        ):
            assert not await uow.gestures.attach_effect(
                tenant, stream_id=stream, tab_id=tab, frame_path=None, at=AT, of="r.1", effect=SAID
            )
    (stored,) = await _stored(session_factory)
    assert stored.action.effect is None


async def test_an_effect_of_another_ref_never_lands(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await _store(session_factory, _gesture("ges_1"))
    assert await _attach(session_factory, of="r.2") is False
    (stored,) = await _stored(session_factory)
    assert stored.action.effect is None


async def test_a_gesture_stored_without_a_ref_never_takes_an_effect(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await _store(session_factory, _gesture("ges_1", ref=None))
    assert await _attach(session_factory) is False
    (stored,) = await _stored(session_factory)
    assert stored.action.effect is None


async def test_two_effects_at_once_attach_exactly_one(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await _store(session_factory, _gesture("ges_1"))

    async def attach(text: str) -> bool:
        async with SqlUnitOfWork(session_factory) as uow:
            ok = await uow.gestures.attach_effect(
                TENANT,
                stream_id="dev-1",
                tab_id=1,
                frame_path=None,
                at=AT,
                of="r.1",
                effect=Effect(appeared=(Seen("status", text),), ended="quiet"),
            )
            await asyncio.sleep(0.2)
            await uow.commit()
        return ok

    won = await asyncio.gather(attach("first"), attach("second"))
    assert sorted(won) == [False, True]
    (stored,) = await _stored(session_factory)
    assert stored.action.effect is not None
    assert stored.action.effect.appeared[0].text in {"first", "second"}
