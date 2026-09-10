"""Registering a browser, hearing from it, and storing what it sends."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import cast

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
from sro.domain.recording.sensitivity import REDACTED
from sro.domain.shared.errors import Conflict
from sro.domain.shared.identifiers import BatchId, DeviceId, PrincipalId, TenantId
from tests import factories as f
from tests.unit.fakes import (
    FakeBlobStore,
    FakeClock,
    FakeGestureRepository,
    FakeIdFactory,
    FakeUnitOfWork,
)

ACME = RequestContext(tenant_id=TenantId("acme"), principal_id=f.OPERATOR)
OTHER = RequestContext(tenant_id=TenantId("acme"), principal_id=PrincipalId("priya"))

SNAPSHOT: dict[str, object] = {
    "kind": "snapshot",
    "url": "https://wms.acme.com/orders",
    "taken_at": "2026-03-01T09:01:00Z",
    "snapshot": {"role": "main"},
}

JWT = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJvcHMifQ.c2lnbmF0dXJlLWhlcmU"
"""A signed JWT, the shape `SECRET_SHAPES` matches and the audit found in this
deployment's own store."""

AT = 1772355630.0
"""2026-03-01T09:00:30Z as the recorder writes it -- Unix seconds, so that a
request's ISO `started_at` lands inside this gesture's correlation window."""

GESTURE: dict[str, object] = {
    "kind": "gesture",
    "gesture": {
        "kind": "click",
        "at": 1787654321.9,
        "url": "https://wms.acme.com/orders",
        "target": {"tag": "button", "cssPath": "div > button"},
    },
}


def _evidence(uow: FakeUnitOfWork) -> FakeGestureRepository:
    """`FakeUnitOfWork.gestures` is annotated as the port, and the port is
    write-only for batches and orphans -- so reading what ingest actually
    stored needs the concrete fake. One cast here rather than one per
    assertion."""
    return cast(FakeGestureRepository, uow.gestures)


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
        secret="the-winner-was-minted-one",  # noqa: S106 -- not a credential
    )
    uow.devices = _RacyDevices(uow.devices, winner)  # type: ignore[assignment]

    registered = await RegisterDevice(uow, FakeClock(), FakeIdFactory()).execute(
        ACME, label="laptop", extension_version="0.2.0"
    )

    assert registered.device_id == winner.id
    # And with the winner's secret, not a freshly minted one the row does not
    # hold: the loser is the browser that will present it.
    assert registered.secret == winner.secret


class _RacyDevices:
    """The other request's write already landed by the time this one flushes."""

    def __init__(self, real: object, winner: AgentDevice) -> None:
        self._real = real
        self._winner = winner

    async def add(self, device: AgentDevice) -> None:
        await self._real.add(self._winner)
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

    secret = uow.devices.rows[device_id].secret
    behind = await beat.execute(
        ACME, device_id=DeviceId(device_id), secret=secret, policy_version=0
    )
    current = await beat.execute(
        ACME,
        device_id=DeviceId(device_id),
        secret=secret,
        policy_version=behind.policy_version,
    )

    assert behind.policy is not None
    assert current.policy is None
    assert current.policy_version == behind.policy_version


async def test_a_backlog_the_device_cannot_send_is_visible_before_the_day_is_lost() -> None:
    uow = FakeUnitOfWork()
    device_id = await _register(uow, ACME)

    await RecordHeartbeat(uow, FakeClock()).execute(
        ACME,
        device_id=DeviceId(device_id),
        secret=uow.devices.rows[device_id].secret,
        queued_events=4102,
        queued_bytes=9_000_000,
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
    secret: str | None = None,
) -> Ingested:
    return await IngestObservation(uow, blobs, FakeClock()).execute(
        ctx,
        device_id=DeviceId(device_id),
        # The browser's own, unless a test is deliberately presenting another's.
        secret=uow.devices.rows[device_id].secret if secret is None else secret,
        batch_id=BatchId(batch_id),
        started_at=datetime(2026, 3, 1, 9, 0, tzinfo=UTC),
        ended_at=datetime(2026, 3, 1, 9, 5, tzinfo=UTC),
        mode=CaptureMode.PASSIVE,
        events=events if events is not None else [GESTURE],
    )


async def test_an_upload_lands_in_the_evidence_plane_and_not_only_the_blob_store() -> None:
    """The link that was never made.

    `correlate` turns a batch into gestures and `add_gestures` stores them, and
    until this existed neither had a caller anywhere in `src/`: ingest stopped
    at `observation_batches`, so a browser could upload all day and the miner
    would read an empty store. Found by running the real thing -- 397 real
    batches, 4,661 real events, and 0 gestures.
    """
    uow, blobs = FakeUnitOfWork(), FakeBlobStore()
    ctx = RequestContext(tenant_id=f.TENANT, principal_id=f.OPERATOR)
    await _switch_observation_on(uow, ctx)
    device_id = await _register(uow, ctx)

    await _ingest(uow, blobs, device_id, ctx=ctx)

    kept = await uow.gestures.gestures_for(f.TENANT, ids=None)
    assert len(kept) == 1, "the upload was stored and read out of by nobody"
    assert kept[0].url == "https://wms.acme.com/orders"
    assert kept[0].batch_id == "bat_one"
    assert kept[0].tenant == f.TENANT.value


async def test_the_batch_the_miner_reads_counts_the_gestures_and_not_the_events() -> None:
    """Two tables describing one upload, neither derived from the other.

    `observation_batches` counts events admitted; this one counts what was read
    out of them. A snapshot is admitted and stored and is not a gesture, so the
    two numbers are allowed to differ -- and a tally that copied the other's
    would say a batch of pictures was a batch of work.
    """
    uow, blobs = FakeUnitOfWork(), FakeBlobStore()
    ctx = RequestContext(tenant_id=f.TENANT, principal_id=f.OPERATOR)
    await _switch_observation_on(uow, ctx)
    device_id = await _register(uow, ctx)

    ingested = await _ingest(
        uow,
        blobs,
        device_id,
        ctx=ctx,
        events=[
            GESTURE,
            SNAPSHOT,
        ],
    )

    assert ingested.accepted == 2, "both events were admitted and stored"
    kept = await uow.gestures.gestures_for(f.TENANT, ids=None)
    assert len(kept) == 1, "the snapshot was read out as a gesture"
    # The store and the tally are two facts, not one. `accepted=len(gestures)`
    # is what this test is named for, and asserting only the store leaves the
    # number free to be `admission.accepted_count` -- the other table's count,
    # which would say a batch of pictures was a batch of work.
    assert next(iter(_evidence(uow).batches.values())).accepted == 1


async def test_the_gesture_stored_says_which_field_the_blob_store_lost() -> None:
    """The decision at `ingest.py`'s `_as_wire_batch(batch, redacted)`.

    Correlating from `admission.accepted` instead is very nearly -- but not
    quite -- invisible, and the reason is worth writing down: `rig_wire`'s
    models redact on their own validators, so a url, a typed value, a prose
    label, a header and a body TEXT come out identical down the either path.
    The belt that is not doubled is `redacted_fields`: the wire's
    `redact_body` reports only shapes, while the one `redact_events` runs
    reports the field NAMES too. So a gesture correlated from the raw events
    carries a body whose password is gone and which does not say a password
    was ever there -- and `redacted_fields` is exactly the record a reviewer
    greps to decide the store is clean.

    Named for the whole decision rather than for that one field, because the
    doubling is an accident of two modules agreeing today and this line is
    what stops them diverging tomorrow.
    """
    uow, blobs = FakeUnitOfWork(), FakeBlobStore()
    ctx = RequestContext(tenant_id=f.TENANT, principal_id=f.OPERATOR)
    await _switch_observation_on(uow, ctx)
    device_id = await _register(uow, ctx)

    await _ingest(
        uow,
        blobs,
        device_id,
        ctx=ctx,
        events=[
            {
                "kind": "gesture",
                "tab_id": 1,
                "gesture": {
                    "kind": "type",
                    "at": AT,
                    "url": f"https://wms.acme.com/login?code={JWT}",
                    "value": JWT,
                    "target": {"tag": "input", "cssPath": "div > input"},
                },
            },
            {
                "kind": "request",
                "tab_id": 1,
                "request": {
                    "request_id": "req_0",
                    "method": "POST",
                    "started_at": "2026-03-01T09:00:35+00:00",
                    "url": "https://wms.acme.com/api/session",
                    "request_body": {
                        "text": '{"user": "ops", "password": "hunter2"}',
                        "mime_type": "application/json",
                    },
                    "status": 200,
                },
            },
        ],
    )

    stored = (await uow.gestures.gestures_for(f.TENANT, ids=None))[0]
    body = stored.requests[0].request_body
    assert body is not None
    assert body.redacted_fields == ("password",), "the store no longer says what it lost"
    # Guarded twice -- once here and once by the wire model's own validators.
    # Asserted anyway: the day one belt is loosened, this says which.
    assert stored.url == f"https://wms.acme.com/login?code={REDACTED}"
    assert stored.action.value == REDACTED
    assert all(JWT.encode() not in blob for blob in blobs.objects.values()), "nor the blob"


async def test_an_event_nothing_could_read_is_counted_as_a_loss_and_not_a_silence() -> None:
    """`rejected=len(admission.rejected) + unreadable`, the `unreadable` half.

    `admit()` requires only that a gesture name some kind; the wire model the
    miner reads knows seven of them. A `drag` is therefore admitted, stored and
    answered for, and then read by nothing -- and dropping the `+ unreadable`
    passes the rest of this suite, because a batch that quietly had fewer
    gestures looks exactly like a batch that had fewer gestures.
    """
    uow, blobs = FakeUnitOfWork(), FakeBlobStore()
    ctx = RequestContext(tenant_id=f.TENANT, principal_id=f.OPERATOR)
    await _switch_observation_on(uow, ctx)
    device_id = await _register(uow, ctx)

    ingested = await _ingest(
        uow,
        blobs,
        device_id,
        ctx=ctx,
        events=[
            {
                "kind": "gesture",
                "gesture": {
                    "kind": "drag",
                    "at": 1787654321.9,
                    "url": "https://wms.acme.com/orders",
                    "target": {"tag": "div", "cssPath": "div > div"},
                },
            }
        ],
    )

    assert ingested.accepted == 1, "admitted, stored, and paid for"
    batch = next(iter(_evidence(uow).batches.values()))
    assert batch.accepted == 0, "nothing read it"
    assert batch.rejected == 1, "and the batch does not pretend it never arrived"


async def test_a_call_that_lands_in_the_next_batch_is_kept_and_not_dropped() -> None:
    """Cross-batch correlation, which was dead on this side and alive in the rig.

    The extension uploads on a timer, so a click at the end of one batch
    routinely has its XHR arrive in the next. `correlate` sees one batch, so it
    hands that call back as an orphan -- and ingest discarded it as `_calls`,
    which made it a call the operator's browser made and this store has no
    record of. `add_orphan_request` and `add_orphan_page` existed on the port,
    the adapter, the fake and two test suites with no production caller
    anywhere in `src/`: the same no-caller defect `add_gestures` had.
    """
    uow, blobs = FakeUnitOfWork(), FakeBlobStore()
    ctx = RequestContext(tenant_id=f.TENANT, principal_id=f.OPERATOR)
    await _switch_observation_on(uow, ctx)
    device_id = await _register(uow, ctx)

    await _ingest(uow, blobs, device_id, ctx=ctx, batch_id="bat_one", events=[GESTURE])
    await _ingest(
        uow,
        blobs,
        device_id,
        ctx=ctx,
        batch_id="bat_two",
        events=[
            {
                "kind": "request",
                "tab_id": 1,
                "request": {
                    "request_id": "req_0",
                    "method": "POST",
                    "started_at": "2026-03-01T09:00:35+00:00",
                    "url": "https://wms.acme.com/api/orders",
                    "status": 200,
                },
            },
            {
                "kind": "page",
                "tab_id": 1,
                "at": "2026-03-01T09:00:36+00:00",
                "page_kind": "navigated",
                "url": "https://wms.acme.com/orders/new",
            },
        ],
    )

    assert _evidence(uow).orphan_requests[("bat_two", "req_0")]["url"] == (
        "https://wms.acme.com/api/orders"
    )
    tenant, batch_id, at, payload = _evidence(uow).orphan_pages[0]
    assert (tenant, batch_id) == (f.TENANT.value, "bat_two")
    assert at == "2026-03-01T09:00:36+00:00", "epoch seconds in, ISO out, as the column wants"
    assert payload["url"] == "https://wms.acme.com/orders/new"


async def test_a_batch_of_pictures_says_so_on_the_way_out() -> None:
    """`snapshots_ignored`, which `correlate` counts and nothing carried.

    A snapshot is admitted, stored, billed and read by nothing -- there is
    nowhere in the schema to put one. `correlate`'s docstring says the count
    exists because silently dropping them is not the same as never having
    received them, and until this it was bound to a local and dropped one line
    later. The rig returns it in the same 202 body.
    """
    uow, blobs = FakeUnitOfWork(), FakeBlobStore()
    ctx = RequestContext(tenant_id=f.TENANT, principal_id=f.OPERATOR)
    await _switch_observation_on(uow, ctx)
    device_id = await _register(uow, ctx)

    ingested = await _ingest(uow, blobs, device_id, ctx=ctx, events=[GESTURE, SNAPSHOT, SNAPSHOT])

    assert ingested.snapshots_ignored == 2
