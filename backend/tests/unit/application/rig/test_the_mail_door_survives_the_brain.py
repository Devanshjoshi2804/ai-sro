"""A mail the brain cannot read must not block the inbox for ever, and shadow compares are
separate units of work."""

from __future__ import annotations

import asyncio
from typing import Any

from sro.application.chat.about_an_offer import AskAboutTheOffer
from sro.application.chat.brain_reader import MailReading
from sro.application.chat.feedback import RecordFeedback
from sro.application.chat.mailbox import ModelUnavailable, Unread
from sro.application.chat.read_threads import ReadThreads
from sro.application.context import RequestContext
from tests import factories as f
from tests.unit.application.rig.test_from_the_mail import (
    CTX,
    JOB,
    _found,
    _held,
    _look,
    _mail,
    _Mailbox,
    _reading,
    _Reads,
)
from tests.unit.fakes import FakeClock, FakeIdFactory

LIVE = frozenset({f.TENANT.value})


class _Picky:
    """Cannot read m-1, ever; reads m-2 as no request."""

    def __init__(self) -> None:
        self.read_of: list[str] = []

    async def read(self, ctx: RequestContext, *, offer: str, **_: object) -> MailReading | None:
        self.read_of.append(offer)
        if offer == "mail:m-1":
            raise Unread("the brain could not answer")
        return None


async def test_a_mail_that_fails_three_looks_is_dropped_with_a_row_and_later_mail_is_read() -> None:
    uow = await _held()
    box = _Mailbox(
        search=_found("m-1", "m-2"),
        **{"m-1": _mail("please create GPX"), "m-2": _mail("please create GPY")},
    )
    reader = _Picky()
    door = _look(
        uow,
        box,
        _Reads(),
        reader=lambda: reader,
        reader_tenants=LIVE,
        feedback=lambda: RecordFeedback(uow, FakeIdFactory(), FakeClock()),
    )

    first, second = await door.execute(CTX), await door.execute(CTX)
    assert first.stopped and second.stopped
    assert "mail:m-2" not in reader.read_of, "a failing mail holds the look for now"
    assert uow.chat_feedback.rows == []

    third = await door.execute(CTX)

    assert third.stopped == "" and "mail:m-2" in reader.read_of
    (row,) = uow.chat_feedback.rows
    assert row.kind == "mail_unreadable" and row.message_id == "m-1"

    reader.read_of.clear()
    await door.execute(CTX)
    assert "mail:m-1" not in reader.read_of, "a dropped mail is not read again"


class _ModelDown:
    async def read(self, ctx: RequestContext, *, offer: str, **_: object) -> MailReading | None:
        raise ModelUnavailable("the model is down")


async def test_a_model_outage_never_drops_a_mail_however_long_it_lasts() -> None:
    uow = await _held()
    box = _Mailbox(search=_found("m-1"), **{"m-1": _mail("please create GPX")})
    door = _look(
        uow,
        box,
        _Reads(),
        reader=lambda: _ModelDown(),
        reader_tenants=LIVE,
        feedback=lambda: RecordFeedback(uow, FakeIdFactory(), FakeClock()),
    )

    for _ in range(5):
        assert (await door.execute(CTX)).stopped
    assert uow.chat_feedback.rows == []


async def test_a_dropped_mail_leaves_a_note_in_its_own_ask_chat() -> None:
    uow = await _held()
    box = _Mailbox(search=_found("m-1"), **{"m-1": _mail("please create GPX", "t-1")})
    door = _look(
        uow,
        box,
        _Reads(),
        reader=lambda: _Picky(),
        reader_tenants=LIVE,
        asks=AskAboutTheOffer(uow, FakeClock(), FakeIdFactory(), None),
        feedback=lambda: RecordFeedback(uow, FakeIdFactory(), FakeClock()),
    )

    for _ in range(3):
        await door.execute(CTX)

    found = await ReadThreads(uow).asking(CTX, "t-1")
    assert found is not None
    assert "could not read this mail" in found.messages[-1].text


class _Overlapping:
    """Reads that overlap: each waits for the other to have begun."""

    def __init__(self, arrived: list[str], gate: asyncio.Event) -> None:
        self.arrived, self.gate = arrived, gate

    async def read(self, ctx: RequestContext, *, offer: str, **_: object) -> MailReading | None:
        self.arrived.append(offer)
        if len(self.arrived) == 2:
            self.gate.set()
        await asyncio.wait_for(self.gate.wait(), 2)
        return MailReading(JOB, {"Customer Type": "OTHER"}, (), True)


async def test_two_overlapping_shadow_compares_are_separate_units_of_work() -> None:
    uow = await _held()
    box = _Mailbox(
        search=_found("m-1", "m-2"),
        **{"m-1": _mail("please create GPX"), "m-2": _mail("please create GPX again")},
    )
    arrived: list[str] = []
    gate = asyncio.Event()
    readers: list[Any] = []
    recorders: list[Any] = []

    def build() -> Any:
        readers.append(_Overlapping(arrived, gate))
        return readers[-1]

    def feedback() -> RecordFeedback:
        recorders.append(RecordFeedback(uow, FakeIdFactory(), FakeClock()))
        return recorders[-1]

    spawned: list[Any] = []
    door = _look(
        uow,
        box,
        _Reads(_reading(JOB), _reading(JOB)),
        reader=build,
        shadow_tenants=LIVE,
        feedback=feedback,
        spawn=spawned.append,
    )
    await door.execute(CTX)
    await asyncio.gather(*spawned)

    assert len(readers) == 2 and readers[0] is not readers[1], "one reader a compare"
    assert len(recorders) == 2 and recorders[0] is not recorders[1], "one recorder a compare"
    assert sorted(arrived) == ["mail:m-1", "mail:m-2"]
    assert len(uow.chat_feedback.rows) == 2


async def test_a_mail_the_model_blocks_is_dropped_at_the_third_look_with_a_note_and_a_row() -> None:
    from sro.application.chat.brain_reader import BrainReader
    from sro.domain.shared.prices import Answer
    from tests.unit.application.chat.test_brain_tools import _acting
    from tests.unit.application.chat.test_the_brain import _brain

    class _Blocks:
        async def ask(self, **_: object) -> Answer:
            return Answer(data=None, error="the model returned no candidates")

    uow = await _held()
    box = _Mailbox(search=_found("m-1"), **{"m-1": _mail("please create GPX", "t-1")})
    brain, _ = _brain(await _acting(), asker=_Blocks())
    door = _look(
        uow,
        box,
        _Reads(),
        reader=lambda: BrainReader(brain),
        reader_tenants=LIVE,
        asks=AskAboutTheOffer(uow, FakeClock(), FakeIdFactory(), None),
        feedback=lambda: RecordFeedback(uow, FakeIdFactory(), FakeClock()),
    )

    looks = [await door.execute(CTX) for _ in range(3)]

    assert looks[0].stopped and looks[1].stopped and looks[2].stopped == ""
    (row,) = uow.chat_feedback.rows
    assert row.kind == "mail_unreadable" and row.message_id == "m-1"
    found = await ReadThreads(uow).asking(CTX, "t-1")
    assert found is not None and "could not read this mail" in found.messages[-1].text
