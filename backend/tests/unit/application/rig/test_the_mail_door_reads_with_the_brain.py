"""The mail door, asked of the brain (live) or compared with it (shadow)."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from sro.application.chat.about_an_offer import AskAboutTheOffer
from sro.application.chat.brain_reader import MailReading
from sro.application.chat.feedback import RecordFeedback
from sro.application.chat.mailbox import Unread
from sro.application.context import RequestContext
from sro.domain.chat.asking import NEEDS
from tests import factories as f
from tests.unit.application.rig.test_from_the_mail import (
    CTX,
    JOB,
    _found,
    _Gathers,
    _held,
    _look,
    _mail,
    _Mailbox,
    _reading,
    _Reads,
    _short,
    _thread,
    mail_world,
)
from tests.unit.fakes import FakeClock, FakeIdFactory

GOT = {"Customer Type": "GPX", "Customer Type Description": "north dock"}
LIVE = frozenset({f.TENANT.value})


class _Reader:
    def __init__(self, reading: MailReading | None) -> None:
        self.reading, self.asked = reading, 0
        self.seen: list[dict[str, Any]] = []

    async def read(self, ctx: RequestContext, **kept: object) -> MailReading | None:
        self.asked += 1
        self.seen.append(kept)
        return self.reading


def _to(reader: Any) -> Any:
    return lambda: reader


class _Fails:
    async def read(self, ctx: RequestContext, **_: object) -> MailReading | None:
        raise Unread("the brain could not answer")


class _NeverRead:
    async def read(self, ctx: RequestContext, **_: object) -> MailReading | None:
        raise AssertionError("a reply is not read for a new job")


def _mailbox(thread: str = "") -> _Mailbox:
    return _Mailbox(search=_found("m-1"), **{"m-1": _mail("please create GPX", thread)})


async def _live(reader: Any, thread: str = "", drafts: Any = None) -> Any:
    uow = await _held()
    asks = AskAboutTheOffer(uow, FakeClock(), FakeIdFactory(), drafts)
    reads = _Reads()
    door = _look(uow, _mailbox(thread), reads, asks=asks, reader=_to(reader), reader_tenants=LIVE)
    return uow, reads, door


async def test_a_live_tenant_s_complete_mail_starts_one_run_from_the_brain_s_reading() -> None:
    world = await mail_world(sure=True, values={}, steel=True, thread="t-1")
    world.mailbox._answers["m-1"] = json.dumps(
        {
            "id": "m-1",
            "subject": "new type",
            "body": "please add GT2",
            "thread_id": "t-1",
            "from": "priya@acme.example",
            "date": "Fri, 02 Oct 2026 09:00:00 +0000",
        }
    )
    reader = _Reader(MailReading(JOB, {"Customer Type": "GT2"}, (), True))
    door = _look(
        world.uow,
        world.mailbox,
        world.reads,
        start=world.start,
        reader=_to(reader),
        reader_tenants=LIVE,
    )

    await door.execute(CTX)

    assert world.reads.saw == [], "the old matcher was not asked"
    (run,) = await world.uow.workflow_runs.for_workflow(f.TENANT, JOB)
    assert run.offer == "mail:m-1" and run.values == {"Customer Type": "GT2"}
    assert set(run.mail) >= {"thread", "subject", "sender", "arrived"}


async def test_a_live_tenant_s_mail_missing_the_description_is_asked_and_drafted() -> None:
    world = await mail_world(sure=True, values={}, steel=True, thread="t-1")
    drafted: list[Any] = []

    async def drafts(ctx: RequestContext, pending: Any, thread: str, question: str) -> bool:
        drafted.append((pending, thread))
        return True

    asks = AskAboutTheOffer(world.uow, FakeClock(), FakeIdFactory(), drafts)
    reader = _Reader(
        MailReading(JOB, {"Customer Type": "GPX"}, ("Customer Type Description",), False)
    )
    door = _look(
        world.uow,
        world.mailbox,
        world.reads,
        start=world.start,
        asks=asks,
        reader=_to(reader),
        reader_tenants=LIVE,
    )

    await door.execute(CTX)

    assert world.durable.runs_started == []
    last = (await _thread(world.uow)).messages[-1]
    assert last.decision["kind"] == NEEDS
    assert "Customer Type Description" in last.decision["missing"]
    assert len(drafted) == 1 and drafted[0][1] == "t-1"


async def test_a_live_tenant_s_injection_mail_starts_nothing_asks_nothing_drafts_nothing() -> None:
    world = await mail_world(sure=True, values={}, steel=True, thread="t-1")
    drafted: list[Any] = []

    async def drafts(*a: Any) -> bool:
        drafted.append(a)
        return True

    asks = AskAboutTheOffer(world.uow, FakeClock(), FakeIdFactory(), drafts)
    door = _look(
        world.uow,
        world.mailbox,
        world.reads,
        start=world.start,
        asks=asks,
        reader=_to(_Reader(None)),
        reader_tenants=LIVE,
    )

    looked = await door.execute(CTX)

    assert looked.offered == () and world.durable.runs_started == [] and drafted == []
    assert await _thread(world.uow) is None
    assert world.reads.saw == [], "no fallback to the old matcher"


async def test_a_reply_on_a_standing_question_never_reaches_the_reader() -> None:
    uow = await _held()
    await uow.workflow_runs.save(
        _short("t-9", needs=["Customer Type"], values={"Customer Type Description": "north dock"})
    )
    gather = _Gathers(**{"Customer Type": "GU9"})
    door = _look(
        uow, _mailbox("t-9"), _Reads(), gather, reader=_to(_NeverRead()), reader_tenants=LIVE
    )

    looked = await door.execute(CTX)

    (one,) = looked.offered
    assert one.values == {"Customer Type Description": "north dock", "Customer Type": "GU9"}, (
        "the existing answer path ran"
    )


async def test_a_live_mail_the_gather_completes_starts_its_run() -> None:
    world = await mail_world(sure=True, values={}, steel=True, thread="t-1")
    reader = _Reader(
        MailReading(JOB, {"Customer Type": "GPX"}, ("Customer Type Description",), True)
    )
    gather = _Gathers(**{"Customer Type Description": "north dock"})
    door = _look(
        world.uow,
        world.mailbox,
        world.reads,
        gather,
        start=world.start,
        reader=_to(reader),
        reader_tenants=LIVE,
    )

    looked = await door.execute(CTX)

    (run,) = await world.uow.workflow_runs.for_workflow(f.TENANT, JOB)
    assert run.offer == "mail:m-1" and looked.offered[0].started


async def test_a_brain_that_could_not_read_leaves_the_mail_for_the_next_look() -> None:
    world = await mail_world(sure=True, values={}, steel=True)
    door = _look(
        world.uow,
        world.mailbox,
        world.reads,
        start=world.start,
        reader=_to(_Fails()),
        reader_tenants=LIVE,
    )

    looked = await door.execute(CTX)
    assert looked.stopped and looked.asks_nothing == ()

    reader = _Reader(MailReading(JOB, {"Customer Type": "GT2"}, (), True))
    again = _look(
        world.uow,
        world.mailbox,
        world.reads,
        start=world.start,
        reader=_to(reader),
        reader_tenants=LIVE,
    )
    await again.execute(CTX)
    assert reader.asked == 1, "the mail was read again, not remembered as asking for nothing"


async def test_the_reader_is_built_on_first_use_and_asked_with_the_offer_and_earlier_mails() -> (
    None
):
    world = await mail_world(sure=True, values={}, steel=True, thread="t-1")
    world.mailbox._answers["t-1"] = json.dumps(
        {
            "id": "t-1",
            "messages": [
                {"id": "m-0", "body": "the old mail"},
                {"id": "m-1", "body": "please create GPX"},
            ],
        }
    )
    reader = _Reader(None)
    built: list[int] = []

    def build() -> _Reader:
        built.append(1)
        return reader

    door = _look(world.uow, world.mailbox, world.reads, reader=build, reader_tenants=LIVE)
    assert built == []

    await door.execute(CTX)

    assert built == [1] and reader.seen[0]["offer"] == "mail:m-1"
    assert "the old mail" in reader.seen[0]["earlier"]
    assert "please create GPX" not in reader.seen[0]["earlier"]


async def test_a_live_sign_in_chore_is_refused_as_the_matcher_refuses_it() -> None:
    from dataclasses import replace

    world = await mail_world(sure=True, values={}, steel=True)
    base = await world.uow.workflows.get(f.TENANT, JOB)
    async with world.uow as uow:
        await uow.workflows.save(
            replace(
                base,
                id="wfl_chore",
                title="Sign in to the console",
                narrative="sign in to the console",
                signs_in=True,
            )
        )
        await uow.commit()
    world.mailbox._answers["m-1"] = _mail("please sign in to the console")
    reader = _Reader(MailReading(JOB, {"Customer Type": "GT2"}, (), True))
    door = _look(
        world.uow,
        world.mailbox,
        world.reads,
        start=world.start,
        reader=_to(reader),
        reader_tenants=LIVE,
    )

    looked = await door.execute(CTX)

    assert looked.offered[0].cannot_run and world.durable.runs_started == []


async def _shadow(reading: MailReading | None) -> tuple[Any, _Reader]:
    uow = await _held()
    reads = _Reads(_reading(JOB))  # old matcher: JOB with Customer Type GPX
    reader = _Reader(reading)
    spawned: list[Any] = []
    door = _look(
        uow,
        _mailbox(),
        reads,
        reader=_to(reader),
        shadow_tenants=LIVE,
        feedback=lambda: RecordFeedback(uow, FakeIdFactory(), FakeClock()),
        spawn=spawned.append,
    )
    looked = await door.execute(CTX)
    assert looked.offered, "the old matcher still decides"
    await asyncio.gather(*spawned)
    return uow, reader


async def test_a_shadow_disagreement_is_recorded() -> None:
    uow, reader = await _shadow(MailReading(JOB, {"Customer Type": "OTHER"}, (), True))
    assert reader.asked == 1
    (row,) = uow.chat_feedback.rows
    assert row.kind == "disagreement" and row.message_id == "m-1"
    assert row.brain["read"] == {"job": JOB, "values": {"Customer Type": "OTHER"}}
    assert row.other["read"] == {"job": JOB, "values": {"Customer Type": "GPX"}}
    assert reader.seen[0]["offer"] == "mail:m-1"


async def test_a_shadow_agreement_records_nothing() -> None:
    uow, _ = await _shadow(
        MailReading(JOB, {"Customer Type": "GPX"}, ("Customer Type Description",), False)
    )
    assert uow.chat_feedback.rows == []


async def test_a_shadow_reader_that_raises_never_breaks_the_look() -> None:
    class _Boom:
        async def read(self, ctx: RequestContext, **_: object) -> MailReading | None:
            raise RuntimeError("down")

    uow = await _held()
    spawned: list[Any] = []
    door = _look(
        uow,
        _mailbox(),
        _Reads(_reading(JOB)),
        reader=_to(_Boom()),
        shadow_tenants=LIVE,
        feedback=lambda: RecordFeedback(uow, FakeIdFactory(), FakeClock()),
        spawn=spawned.append,
    )
    assert (await door.execute(CTX)).offered
    await asyncio.gather(*spawned)
    assert uow.chat_feedback.rows == []


async def test_a_secret_a_shadow_read_carries_is_not_kept() -> None:
    uow, _ = await _shadow(MailReading(JOB, {"Password": "hunter2"}, (), True))
    assert "hunter2" not in repr(uow.chat_feedback.rows[0].brain)


async def test_a_mail_the_brain_gave_no_job_is_not_read_again_and_does_not_stop_the_next() -> None:
    world = await mail_world(sure=True, values={}, steel=True)
    world.mailbox._answers["search"] = _found("m-1", "m-2")
    world.mailbox._answers["m-2"] = _mail("please create GPX again")
    reader = _Reader(None)
    door = _look(
        world.uow,
        world.mailbox,
        world.reads,
        start=world.start,
        reader=_to(reader),
        reader_tenants=LIVE,
    )

    first = await door.execute(CTX)
    await door.execute(CTX)

    assert first.stopped == "" and reader.asked == 2, "both mails read once, none again"
