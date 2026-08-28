"""Registering a browser, hearing from it, and storing what it sends."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from sro.application.context import RequestContext
from sro.application.observation.forget import ForgetObservations
from sro.application.observation.ingest import Ingested, IngestObservation, ObservationRefused
from sro.application.observation.policy import SetObservationPolicy
from sro.application.observation.register import RecordHeartbeat, RegisterDevice
from sro.application.observation.retain import SweepRetention
from sro.domain.observation.batch import CaptureMode
from sro.domain.observation.device import AgentDevice
from sro.domain.observation.policy import ObservationPolicy
from sro.domain.shared.errors import Conflict
from sro.domain.shared.identifiers import BatchId, DeviceId, PrincipalId, TenantId
from tests import factories as f
from tests.unit.fakes import FakeBlobStore, FakeClock, FakeIdFactory, FakeUnitOfWork

ACME = RequestContext(tenant_id=TenantId("acme"), principal_id=f.OPERATOR)
OTHER = RequestContext(tenant_id=TenantId("acme"), principal_id=PrincipalId("priya"))

GESTURE = {
    "kind": "gesture",
    "gesture": {
        "kind": "click",
        "at": 1787654321.9,
        "url": "https://wms.acme.com/orders",
        "target": {"tag": "button", "cssPath": "div > button"},
    },
}


async def _switch_observation_on(uow: FakeUnitOfWork, ctx: RequestContext) -> None:
    await SetObservationPolicy(uow).execute(ctx, policy=ObservationPolicy().enabled())


async def _register(uow: FakeUnitOfWork, ctx: RequestContext, label: str = "laptop") -> str:
    registered = await RegisterDevice(uow, FakeClock(), FakeIdFactory()).execute(
        ctx, label=label, extension_version="0.1.0"
    )
    return registered.device_id.value


async def test_a_reinstalled_extension_comes_back_as_the_device_it_was() -> None:
    uow = FakeUnitOfWork()
    register = RegisterDevice(uow, FakeClock(), FakeIdFactory())

    first = await register.execute(ACME, label="laptop", extension_version="0.1.0")
    again = await register.execute(ACME, label="laptop", extension_version="0.2.0")

    assert again.device_id == first.device_id
    assert len(uow.devices.rows) == 1
    assert uow.devices.rows[first.device_id.value].extension_version == "0.2.0"


async def test_two_registrations_racing_the_same_label_both_come_back_as_one_device() -> None:
    # Both saw no existing row and both tried to add(); the real repository
    # turns the loser's IntegrityError into Conflict, and this is what the
    # "idempotent" docstring promises happens next -- not a 500.
    uow = FakeUnitOfWork()
    winner = AgentDevice(
        id=DeviceId("dev-winner"),
        tenant_id=TenantId("acme"),
        principal_id=f.OPERATOR,
        label="laptop",
        extension_version="0.1.0",
        registered_at=datetime(2026, 3, 1, tzinfo=UTC),
        last_seen_at=datetime(2026, 3, 1, tzinfo=UTC),
    )
    uow.devices = _RacyDevices(uow.devices, winner)  # type: ignore[assignment]

    registered = await RegisterDevice(uow, FakeClock(), FakeIdFactory()).execute(
        ACME, label="laptop", extension_version="0.2.0"
    )

    assert registered.device_id == winner.id


class _RacyDevices:
    """The other request's write already landed by the time this one flushes."""

    def __init__(self, real: object, winner: AgentDevice) -> None:
        self._real = real
        self._winner = winner

    async def add(self, device: AgentDevice) -> None:
        await self._real.add(self._winner)  # type: ignore[attr-defined]
        raise Conflict(f"a device is already registered as {device.label!r}")

    def __getattr__(self, name: str) -> object:
        return getattr(self._real, name)


async def test_registering_answers_with_a_policy_that_captures_nothing_by_default() -> None:
    uow = FakeUnitOfWork()

    registered = await RegisterDevice(uow, FakeClock(), FakeIdFactory()).execute(
        ACME, label="laptop", extension_version="0.1.0"
    )

    assert registered.policy.capture_enabled is False


async def test_a_heartbeat_carries_the_policy_only_when_the_device_is_behind() -> None:
    uow = FakeUnitOfWork()
    await _switch_observation_on(uow, ACME)
    device_id = await _register(uow, ACME)
    beat = RecordHeartbeat(uow, FakeClock())

    behind = await beat.execute(ACME, device_id=DeviceId(device_id), policy_version=0)
    current = await beat.execute(
        ACME, device_id=DeviceId(device_id), policy_version=behind.policy_version
    )

    assert behind.policy is not None
    assert current.policy is None
    assert current.policy_version == behind.policy_version


async def test_a_backlog_the_device_cannot_send_is_visible_before_the_day_is_lost() -> None:
    uow = FakeUnitOfWork()
    device_id = await _register(uow, ACME)

    await RecordHeartbeat(uow, FakeClock()).execute(
        ACME, device_id=DeviceId(device_id), queued_events=4102, queued_bytes=9_000_000
    )

    assert uow.devices.rows[device_id].queued_events == 4102
    assert uow.devices.rows[device_id].queued_bytes == 9_000_000


async def test_nothing_is_stored_for_a_tenant_that_never_agreed_to_be_observed() -> None:
    uow, blobs = FakeUnitOfWork(), FakeBlobStore()
    device_id = await _register(uow, ACME)

    with pytest.raises(ObservationRefused):
        await _ingest(uow, blobs, device_id)

    assert blobs.objects == {}
    assert uow.observations.rows == {}


async def test_a_paused_device_is_told_to_stop_rather_than_quietly_ignored() -> None:
    uow, blobs = FakeUnitOfWork(), FakeBlobStore()
    await _switch_observation_on(uow, ACME)
    device_id = await _register(uow, ACME)
    uow.devices.rows[device_id].pause(datetime(2026, 3, 1, 9, 0, tzinfo=UTC), by="admin")

    with pytest.raises(ObservationRefused):
        await _ingest(uow, blobs, device_id)


async def test_what_is_kept_goes_to_object_storage_and_the_row_points_at_it() -> None:
    uow, blobs = FakeUnitOfWork(), FakeBlobStore()
    await _switch_observation_on(uow, ACME)
    device_id = await _register(uow, ACME)
    before = uow.commits

    ingested = await _ingest(uow, blobs, device_id)

    assert ingested.accepted == 1
    assert ingested.stored_at is not None
    key = f"{f.TENANT}/{f.OPERATOR}/2026-03-01/bat_one.ndjson"
    assert blobs.objects[key].endswith(b"\n")
    assert uow.observations.rows["bat_one"].uri.endswith(key)
    assert uow.commits == before + 1


async def test_an_upload_whose_response_was_lost_is_not_counted_twice() -> None:
    uow, blobs = FakeUnitOfWork(), FakeBlobStore()
    await _switch_observation_on(uow, ACME)
    device_id = await _register(uow, ACME)

    first = await _ingest(uow, blobs, device_id)
    retried = await _ingest(uow, blobs, device_id)

    assert retried.already_had_it is True
    assert retried.accepted == first.accepted
    assert len(uow.observations.rows) == 1


async def test_an_event_the_domain_refuses_is_reported_rather_than_dropped() -> None:
    uow, blobs = FakeUnitOfWork(), FakeBlobStore()
    await _switch_observation_on(uow, ACME)
    device_id = await _register(uow, ACME)

    ingested = await _ingest(uow, blobs, device_id, events=[GESTURE, {"kind": "keylog"}])

    assert ingested.accepted == 1
    assert ingested.rejected[0].index == 1
    assert uow.observations.rows["bat_one"].rejected[0].index == 1


async def test_a_batch_where_nothing_survived_screening_writes_no_object_at_all() -> None:
    uow, blobs = FakeUnitOfWork(), FakeBlobStore()
    await _switch_observation_on(uow, ACME)
    device_id = await _register(uow, ACME)

    ingested = await _ingest(uow, blobs, device_id, events=[{"kind": "keylog"}])

    assert ingested.accepted == 0
    assert ingested.stored_at is None
    assert blobs.objects == {}


async def test_an_operator_purging_their_own_hour_does_not_touch_a_colleagues() -> None:
    uow, blobs = FakeUnitOfWork(), FakeBlobStore()
    await _switch_observation_on(uow, ACME)
    mine = await _register(uow, ACME)
    theirs = await _register(uow, OTHER, label="priya-laptop")
    await _ingest(uow, blobs, mine, batch_id="bat_mine")
    await _ingest(uow, blobs, theirs, ctx=OTHER, batch_id="bat_theirs")
    await blobs.put(
        f"{f.TENANT}/{f.OPERATOR}/2026-03-01/bat_mine/screenshot/00001.png",
        b"x",
        content_type="image/png",
    )

    forgotten = await ForgetObservations(uow, blobs, FakeClock()).execute(
        ACME, since=datetime(2026, 3, 1, 0, 0, tzinfo=UTC)
    )

    assert forgotten.batches == 1
    assert set(uow.observations.rows) == {"bat_theirs"}
    assert [key for key in blobs.objects if str(f.OPERATOR) in key] == []
    assert [key for key in blobs.objects if "priya" in key] != []


async def test_a_sweep_removes_evidence_past_its_own_tenants_window() -> None:
    uow, blobs = FakeUnitOfWork(), FakeBlobStore()
    await SetObservationPolicy(uow).execute(
        ACME, policy=ObservationPolicy(retention_days=1).enabled()
    )
    device_id = await _register(uow, ACME)
    await _ingest(uow, blobs, device_id)

    forgotten = await SweepRetention(
        uow, blobs, FakeClock(datetime(2026, 3, 5, 9, 0, tzinfo=UTC))
    ).execute()

    assert forgotten["acme"].batches == 1
    assert uow.observations.rows == {}


async def test_a_sweep_also_removes_the_batchs_screenshots() -> None:
    # StoreObservationArtifact keys a screenshot by tenant/principal/day/batch
    # with no row of its own -- this is the only way a purge finds it.
    uow, blobs = FakeUnitOfWork(), FakeBlobStore()
    await SetObservationPolicy(uow).execute(
        ACME, policy=ObservationPolicy(retention_days=1).enabled()
    )
    device_id = await _register(uow, ACME)
    await _ingest(uow, blobs, device_id)
    await blobs.put(
        f"{f.TENANT}/{f.OPERATOR}/2026-03-01/bat_one/screenshot/00001.png",
        b"x",
        content_type="image/png",
    )

    forgotten = await SweepRetention(
        uow, blobs, FakeClock(datetime(2026, 3, 5, 9, 0, tzinfo=UTC))
    ).execute()

    assert forgotten["acme"].batches == 1
    assert [key for key in blobs.objects if "bat_one" in key] == []


async def test_a_sweep_leaves_evidence_still_inside_the_window() -> None:
    uow, blobs = FakeUnitOfWork(), FakeBlobStore()
    await SetObservationPolicy(uow).execute(
        ACME, policy=ObservationPolicy(retention_days=30).enabled()
    )
    device_id = await _register(uow, ACME)
    await _ingest(uow, blobs, device_id)

    forgotten = await SweepRetention(
        uow, blobs, FakeClock(datetime(2026, 3, 5, 9, 0, tzinfo=UTC))
    ).execute()

    assert forgotten["acme"].batches == 0
    assert set(uow.observations.rows) == {"bat_one"}


async def _ingest(
    uow: FakeUnitOfWork,
    blobs: FakeBlobStore,
    device_id: str,
    *,
    ctx: RequestContext = ACME,
    batch_id: str = "bat_one",
    events: list[dict[str, object]] | None = None,
) -> Ingested:
    return await IngestObservation(uow, blobs, FakeClock()).execute(
        ctx,
        device_id=DeviceId(device_id),
        batch_id=BatchId(batch_id),
        started_at=datetime(2026, 3, 1, 9, 0, tzinfo=UTC),
        ended_at=datetime(2026, 3, 1, 9, 5, tzinfo=UTC),
        mode=CaptureMode.PASSIVE,
        events=events if events is not None else [GESTURE],
    )
