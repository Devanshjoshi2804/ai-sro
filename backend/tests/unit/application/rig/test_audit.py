"""What a person is shown after the fact: four reads, one tenant, one bound.

Ported from the rig's `GET /v1/audit` in `new_agent_arch/src/rig/api.py`. The
route's shaping is phase 4's; what is here is the part that can be wrong
without looking wrong -- the bound, the tenant on each of the four calls, and
which run's approvals land on which run.

The bound is the whole point of the module, so it is checked at the boundary
rather than in the middle of a window: a read that dropped its `since`
entirely returns strictly more, which is the failure that reads as a working
audit right up until somebody trusts it to say what happened this morning.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sro.application.analytics.audit import ReadAudit
from sro.application.context import RequestContext
from sro.domain.chat.reading import ChatReading
from sro.domain.execution.workflow_run import RunStep, WorkflowRun
from sro.domain.shared.identifiers import DeviceId, TenantId
from sro.domain.skill.offers import Offer
from tests import factories as f
from tests.unit.fakes import FakeUnitOfWork

ACME = RequestContext(tenant_id=f.TENANT, principal_id=f.OPERATOR)
OTHER = RequestContext(tenant_id=TenantId("other-corp"), principal_id=f.OPERATOR)

BOUND = f.at(600)
"""March 2026, and deliberately not today.

Every rule here turns on a comparison against this instant, and a fixture
dated on the day it was written lets a read that ignores its argument and asks
the repository for "today" agree with it by the calendar until the next
morning. That has happened in this plan already.
"""

BEFORE = BOUND - timedelta(seconds=1)
AFTER = BOUND + timedelta(seconds=1)

LAPTOP = DeviceId("dev-1")


def _run(run_id: str, *, at: datetime, tenant: str = "acme", says: str = "save") -> WorkflowRun:
    return WorkflowRun(
        id=run_id,
        tenant=tenant,
        workflow_id="wfl-1",
        device_id="dev-1",
        values={},
        started_by="offer",
        live=True,
        allow_focus=True,
        started_at=at.isoformat(),
        outcome="held",
        steps=[RunStep(order=0, says=says, verdict="held", verdict_by="status")],
    )


def _offer(offer_id: str, *, at: datetime, tenant: str = "acme") -> Offer:
    return Offer(
        id=offer_id,
        tenant=tenant,
        workflow_id="wfl-1",
        device_id="dev-1",
        k=2,
        fate="accepted",
        at=at.isoformat(),
    )


def _chat(chat_id: str, *, at: datetime, tenant: str = "acme") -> ChatReading:
    return ChatReading(id=chat_id, tenant=tenant, at=at.isoformat(), cost_usd=0.01)


async def _afternoon(tenant: str = "acme", *, when: datetime = AFTER) -> FakeUnitOfWork:
    """One of everything the audit reads, all of it inside the window."""
    uow = FakeUnitOfWork()
    await uow.workflow_runs.save(_run(f"run-{tenant}", at=when, tenant=tenant))
    await uow.offers.record(_offer(f"off-{tenant}", at=when, tenant=tenant))
    await uow.chats.record(_chat(f"cht-{tenant}", at=when, tenant=tenant))
    await uow.devices.add(
        f.device(
            id=DeviceId(f"dev-{tenant}"),
            tenant_id=TenantId(tenant),
            registered_at=when,
            last_seen_at=when,
        )
    )
    return uow


async def test_the_audit_is_the_four_reads_taken_on_one_bound() -> None:
    uow = await _afternoon()

    audit = await ReadAudit(uow).execute(ACME, since=BOUND)

    assert [audited.run.id for audited in audit.runs] == ["run-acme"]
    assert [offer.id for offer in audit.offers] == ["off-acme"]
    assert [device.id for device in audit.devices] == [DeviceId("dev-acme")]
    assert [chat.id for chat in audit.chats] == ["cht-acme"]
    assert audit.since == BOUND.isoformat()


async def test_nothing_before_the_bound_is_in_it() -> None:
    """A second either side, in all four tables. An audit that ignores its
    `since` answers a superset and looks like a working audit; the boundary is
    where the two implementations differ and no real afternoon lands on it by
    accident."""
    uow = await _afternoon()
    await uow.workflow_runs.save(_run("run-early", at=BEFORE))
    await uow.offers.record(_offer("off-early", at=BEFORE))
    await uow.chats.record(_chat("cht-early", at=BEFORE))
    await uow.devices.add(
        f.device(id=DeviceId("dev-early"), registered_at=BEFORE, last_seen_at=BEFORE)
    )

    audit = await ReadAudit(uow).execute(ACME, since=BOUND)

    assert [audited.run.id for audited in audit.runs] == ["run-acme"]
    assert [offer.id for offer in audit.offers] == ["off-acme"]
    assert [device.id for device in audit.devices] == [DeviceId("dev-acme")]
    assert [chat.id for chat in audit.chats] == ["cht-acme"]


async def test_a_row_exactly_on_the_bound_is_in_it() -> None:
    """`>=`, as every `since` read plan 2 landed is: the bound is the instant
    the audit starts at, and an audit asked from midnight that omitted
    midnight would be a different question."""
    uow = await _afternoon(when=BOUND)

    audit = await ReadAudit(uow).execute(ACME, since=BOUND)

    assert [audited.run.id for audited in audit.runs] == ["run-acme"]
    assert [offer.id for offer in audit.offers] == ["off-acme"]
    assert [device.id for device in audit.devices] == [DeviceId("dev-acme")]
    assert [chat.id for chat in audit.chats] == ["cht-acme"]


async def test_another_tenants_afternoon_is_not_in_it() -> None:
    """Four calls, four tenants to pass, and the rig's own device select passed
    none -- one tenant's audit listed every tenant's browsers by id. The
    repository fixed that; this is the caller's half."""
    uow = await _afternoon()
    await uow.workflow_runs.save(_run("run-theirs", at=AFTER, tenant="other-corp"))
    await uow.offers.record(_offer("off-theirs", at=AFTER, tenant="other-corp"))
    await uow.chats.record(_chat("cht-theirs", at=AFTER, tenant="other-corp"))
    await uow.devices.add(
        f.device(
            id=DeviceId("dev-theirs"),
            tenant_id=OTHER.tenant_id,
            registered_at=AFTER,
            last_seen_at=AFTER,
        )
    )

    audit = await ReadAudit(uow).execute(ACME, since=BOUND)

    assert [audited.run.id for audited in audit.runs] == ["run-acme"]
    assert [offer.id for offer in audit.offers] == ["off-acme"]
    assert [device.id for device in audit.devices] == [DeviceId("dev-acme")]
    assert [chat.id for chat in audit.chats] == ["cht-acme"]


async def test_a_run_carries_the_approvals_a_person_gave_on_it_and_no_others() -> None:
    """Which write a person let out, when, and from which browser -- against
    the run it was given on. `approvals` is tenant-blind and asked with a run
    id, so a caller that walked the runs and asked with the wrong one would
    hand somebody else's authorisation to this run's audit line."""
    uow = await _afternoon()
    await uow.workflow_runs.save(_run("run-second", at=AFTER, says="delete"))
    await uow.workflow_runs.approve("run-acme", 0, at=AFTER.isoformat(), device_id="dev-1")
    await uow.workflow_runs.approve("run-second", 0, at=AFTER.isoformat(), device_id="dev-2")

    audit = await ReadAudit(uow).execute(ACME, since=BOUND)

    assert {audited.run.id: audited.approvals for audited in audit.runs} == {
        "run-acme": ((0, AFTER.isoformat(), "dev-1"),),
        "run-second": ((0, AFTER.isoformat(), "dev-2"),),
    }


async def test_a_run_nobody_approved_carries_no_approvals() -> None:
    uow = await _afternoon()

    [audited] = (await ReadAudit(uow).execute(ACME, since=BOUND)).runs

    assert audited.approvals == ()
    assert [step.says for step in audited.run.steps] == ["save"], "the steps come with it"


async def test_a_browser_revoked_since_is_in_it_though_it_registered_before() -> None:
    """`revoked_at` is the one fact the runs and the offers cannot carry: who
    could act, and until when. A browser registered last month and revoked this
    morning belongs in this morning's audit as much as one registered in it,
    and a device read that only asked about registration would silently drop
    the most audit-worthy row it has."""
    uow = FakeUnitOfWork()
    await uow.devices.add(
        f.device(
            id=LAPTOP,
            registered_at=f.at(0),
            last_seen_at=f.at(0),
            revoked_at=AFTER.isoformat(),
        )
    )

    audit = await ReadAudit(uow).execute(ACME, since=BOUND)

    assert [device.id for device in audit.devices] == [LAPTOP]
    assert audit.devices[0].revoked_at == AFTER.isoformat()


async def test_the_same_instant_in_another_offset_reads_the_same_audit() -> None:
    """One bound, spelled two ways, answering the same afternoon.

    The four reads compare instants, so an offset spelled differently does not
    move the window -- what it moves is what the caller is told the window was.
    `since` is handed back so a reader can tell which instant they got, in the
    one spelling every clock in the store is read back in, and a bound echoed
    as it arrived tells a reader in Kolkata one thing and the row beside it
    another.
    """
    uow = await _afternoon()
    await uow.workflow_runs.save(_run("run-early", at=BEFORE))
    elsewhere = BOUND.astimezone(timezone(timedelta(hours=5, minutes=30)))

    audit = await ReadAudit(uow).execute(ACME, since=elsewhere)

    assert elsewhere.isoformat() != BOUND.isoformat(), "the same instant, spelled differently"
    assert audit.since == BOUND.isoformat(), "and reported as the reads compared it"
    assert [audited.run.id for audited in audit.runs] == ["run-acme"]


async def test_a_bound_with_no_zone_is_read_as_utc() -> None:
    """Not as the server's local time. A bound quietly shifted by the host's
    offset does not fail -- it returns an audit starting hours from where it
    was asked to, and looks exactly like one that does not.

    Like `test_a_now_with_no_zone_is_read_as_utc` beside it, this cannot fail
    on a host whose local zone *is* UTC, which is most CI containers: there the
    wrong reading and the right one are the same clock. It catches the mistake
    on a developer machine and nowhere else.
    """
    uow = await _afternoon()

    audit = await ReadAudit(uow).execute(ACME, since=BOUND.replace(tzinfo=None))

    assert audit.since == BOUND.isoformat()
    assert [audited.run.id for audited in audit.runs] == ["run-acme"]


async def test_each_list_is_newest_first() -> None:
    """The store's order, handed back rather than re-sorted. An audit read
    oldest first is not wrong so much as unreadable: the page is one screen and
    the thing a person came for is what just happened."""
    uow = FakeUnitOfWork()
    for seconds in (700, 900, 800):
        moment = f.at(seconds)
        await uow.workflow_runs.save(_run(f"run-{seconds}", at=moment))
        await uow.offers.record(_offer(f"off-{seconds}", at=moment))
        await uow.chats.record(_chat(f"cht-{seconds}", at=moment))
        await uow.devices.add(
            f.device(id=DeviceId(f"dev-{seconds}"), registered_at=moment, last_seen_at=moment)
        )

    audit = await ReadAudit(uow).execute(ACME, since=BOUND)

    assert [audited.run.id for audited in audit.runs] == ["run-900", "run-800", "run-700"]
    assert [offer.id for offer in audit.offers] == ["off-900", "off-800", "off-700"]
    assert [chat.id for chat in audit.chats] == ["cht-900", "cht-800", "cht-700"]
    assert [device.id.value for device in audit.devices] == ["dev-900", "dev-800", "dev-700"]
