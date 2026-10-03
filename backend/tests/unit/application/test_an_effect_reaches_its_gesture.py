import logging
from dataclasses import replace
from datetime import UTC, datetime

import pytest

from sro.application.capture.rig_wire import Batch
from sro.application.context import RequestContext
from sro.application.observation.correlate import correlate, correlate_with_effects
from sro.application.observation.ingest import Ingested, IngestObservation
from sro.application.observation.policy import SetObservationPolicy
from sro.application.observation.register import RegisterDevice, Registered
from sro.domain.observation.batch import CaptureMode
from sro.domain.observation.gesture import Effect, Seen
from sro.domain.observation.policy import ObservationPolicy
from sro.domain.shared.identifiers import BatchId, TenantId
from tests import factories as f
from tests.unit.fakes import FakeBlobStore, FakeClock, FakeIdFactory, FakeUnitOfWork

AT = 1_790_000_000.25
ACME = RequestContext(tenant_id=TenantId("acme"), principal_id=f.OPERATOR)


def _batch(*events: dict[str, object]) -> Batch:
    return Batch.model_validate(
        {
            "batch_id": "b1",
            "device_id": "dev",
            "started_at": "2026-10-02T00:00:00+00:00",
            "ended_at": "2026-10-02T00:01:00+00:00",
            "events": list(events),
        }
    )


def _gesture(
    ref: str,
    at: float,
    name: str = "Save",
    tab: int = 1,
    frame: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    return {
        "kind": "gesture",
        "tab_id": tab,
        "gesture": {
            "kind": "click",
            "at": at,
            "ref": ref,
            "url": "https://wms.example/a",
            "frame_path": frame,
            "target": {
                "role": "button",
                "name": name,
                "labelText": "Save",
                "siblingIndex": 0,
                "siblingCount": 2,
            },
            "place": {"route": "/a", "title": "Customers"},
            "choice": {"chosen": "Retail", "index": 1, "options": ["Bulk", "Retail"]},
        },
    }


def _effect(
    of: str,
    at: float,
    text: str = "Saved",
    tab: int = 1,
    frame: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    return {
        "kind": "effect",
        "of": of,
        "of_at": at,
        "url": "https://wms.example/a",
        "tab_id": tab,
        "frame_path": frame,
        "effect": {"appeared": [{"role": "status", "text": text}], "ended": "quiet"},
    }


def test_an_effect_lands_on_the_gesture_it_names_in_the_same_batch() -> None:
    gestures, _, _, _, left, _ = correlate_with_effects(
        _batch(_gesture("r.1", AT), _gesture("r.2", AT + 1, "Cancel"), _effect("r.1", AT)), "acme"
    )
    saved = next(g for g in gestures if g.action.target and g.action.target.name == "Save")
    other = next(g for g in gestures if g.action.target and g.action.target.name == "Cancel")
    assert saved.action.effect == Effect(appeared=(Seen("status", "Saved"),), ended="quiet")
    assert other.action.effect is None
    assert left == []


def test_an_effect_whose_gesture_is_not_in_the_batch_is_handed_back() -> None:
    _, _, _, _, left, _ = correlate_with_effects(_batch(_effect("r.9", AT)), "acme")
    assert [one.of for one in left] == ["r.9"]


def test_an_effect_naming_the_right_ref_at_another_time_is_handed_back() -> None:
    gestures, _, _, _, left, _ = correlate_with_effects(
        _batch(_gesture("r.1", AT), _effect("r.1", AT + 5)), "acme"
    )
    assert gestures[0].action.effect is None
    assert [one.of for one in left] == ["r.1"]


def test_an_effect_from_another_tab_never_lands() -> None:
    gestures, _, _, _, left, _ = correlate_with_effects(
        _batch(_gesture("r.1", AT, tab=1), _effect("r.1", AT, tab=2)), "acme"
    )
    assert gestures[0].action.effect is None
    assert [one.of for one in left] == ["r.1"]


def test_an_effect_from_another_frame_never_lands() -> None:
    gestures, _, _, _, left, _ = correlate_with_effects(
        _batch(
            _gesture("r.1", AT),
            _effect("r.1", AT, frame=[{"index": 2, "url": "https://x.example/"}]),
        ),
        "acme",
    )
    assert gestures[0].action.effect is None
    assert [one.of for one in left] == ["r.1"]


def test_a_second_effect_for_one_gesture_is_dropped_and_the_first_stands(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.INFO):
        gestures, _, _, _, left, _ = correlate_with_effects(
            _batch(_gesture("r.1", AT), _effect("r.1", AT, "First"), _effect("r.1", AT, "Second")),
            "acme",
        )
    assert gestures[0].action.effect is not None
    assert gestures[0].action.effect.appeared[0].text == "First"
    assert left == []
    assert "dropped" in caplog.text


def test_two_gestures_in_one_millisecond_take_no_effect_rather_than_a_guess(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.INFO):
        gestures, _, _, _, left, _ = correlate_with_effects(
            _batch(_gesture("r.1", AT), _gesture("r.1", AT, "Also"), _effect("r.1", AT)), "acme"
        )
    assert all(g.action.effect is None for g in gestures)
    assert left == []
    assert "dropped" in caplog.text


def test_the_new_gesture_fields_reach_the_action() -> None:
    (gesture,), *_ = correlate(_batch(_gesture("r.1", AT)), "acme")
    assert gesture.action.place is not None and gesture.action.place.title == "Customers"
    assert gesture.action.choice is not None and gesture.action.choice.index == 1
    assert gesture.action.target is not None
    target = gesture.action.target
    assert (target.label_text, target.sibling_index, target.sibling_count) == ("Save", 0, 2)


def test_correlate_still_answers_its_four_things() -> None:
    assert len(correlate(_batch(_gesture("r.1", AT)), "acme")) == 4


async def _ready(devices: int = 1) -> tuple[FakeUnitOfWork, IngestObservation, list[Registered]]:
    uow = FakeUnitOfWork()
    await SetObservationPolicy(uow).execute(ACME, policy=ObservationPolicy().enabled())
    ids = FakeIdFactory()
    registered = [
        await RegisterDevice(uow, FakeClock(), ids).execute(
            ACME, label=label, extension_version="0.1.0"
        )
        for label in ("laptop", "desktop")[:devices]
    ]
    return uow, IngestObservation(uow, FakeBlobStore(), FakeClock()), registered


async def _send(
    ingest: IngestObservation, device: Registered, name: str, events: list[dict[str, object]]
) -> Ingested:
    return await ingest.execute(
        ACME,
        device_id=device.device_id,
        secret=device.secret,
        batch_id=BatchId(name),
        started_at=datetime(2026, 3, 1, 9, 0, tzinfo=UTC),
        ended_at=datetime(2026, 3, 1, 9, 5, tzinfo=UTC),
        mode=CaptureMode.PASSIVE,
        events=events,
    )


async def test_an_effect_in_the_next_batch_lands_on_the_stored_gesture() -> None:
    uow, ingest, (device,) = await _ready()
    await _send(ingest, device, "b1", [_gesture("r.1", AT)])
    await _send(ingest, device, "b2", [_effect("r.1", AT)])
    (stored,) = uow.gestures.rows.values()
    assert stored.action.effect is not None and stored.action.effect.appeared[0].text == "Saved"


async def test_an_effect_never_overwrites_one_already_there() -> None:
    uow, ingest, (device,) = await _ready()
    await _send(ingest, device, "b1", [_gesture("r.1", AT), _effect("r.1", AT, "Saved")])
    await _send(ingest, device, "b2", [_effect("r.1", AT, "Saved again")])
    (stored,) = uow.gestures.rows.values()
    assert stored.action.effect is not None and stored.action.effect.appeared[0].text == "Saved"


async def test_an_effect_matching_two_stored_gestures_lands_on_neither() -> None:
    uow, ingest, (device,) = await _ready()
    await _send(ingest, device, "b1", [_gesture("r.1", AT), _gesture("r.1", AT, "Also save")])
    await _send(ingest, device, "b2", [_effect("r.1", AT)])
    assert all(one.action.effect is None for one in uow.gestures.rows.values())


async def test_an_effect_for_another_tab_never_lands_on_a_stored_gesture() -> None:
    uow, ingest, (device,) = await _ready()
    await _send(ingest, device, "b1", [_gesture("r.1", AT)])
    await _send(ingest, device, "b2", [_effect("r.1", AT, tab=2)])
    (stored,) = uow.gestures.rows.values()
    assert stored.action.effect is None


async def test_an_effect_from_another_device_never_lands_on_a_stored_gesture() -> None:
    uow, ingest, (mine, theirs) = await _ready(2)
    await _send(ingest, mine, "b1", [_gesture("r.1", AT)])
    await _send(ingest, theirs, "b2", [_effect("r.1", AT)])
    (stored,) = uow.gestures.rows.values()
    assert stored.action.effect is None


def test_an_effect_whose_gesture_is_missing_never_lands_on_another_in_the_batch() -> None:
    gestures, _, _, _, left, dropped = correlate_with_effects(
        _batch(_gesture("r.1", AT), _effect("r.2", AT)), "acme"
    )
    assert gestures[0].action.effect is None
    assert left == []
    assert dropped == 1


async def test_an_effect_whose_gesture_is_missing_never_lands_on_another_in_the_next_batch() -> (
    None
):
    uow, ingest, (device,) = await _ready()
    await _send(ingest, device, "b1", [_gesture("r.1", AT)])
    second = await _send(ingest, device, "b2", [_effect("r.2", AT)])
    (stored,) = uow.gestures.rows.values()
    assert stored.action.effect is None
    assert second.effects_dropped == 1


async def test_an_effect_whose_gesture_is_missing_never_lands_in_the_same_batch_either() -> None:
    uow, ingest, (device,) = await _ready()
    sent = await _send(ingest, device, "b1", [_gesture("r.1", AT), _effect("r.2", AT)])
    (stored,) = uow.gestures.rows.values()
    assert stored.action.effect is None
    assert sent.effects_dropped == 1


async def test_a_stored_gesture_without_a_ref_never_takes_an_effect() -> None:
    uow, ingest, (device,) = await _ready()
    await _send(ingest, device, "b1", [_gesture("r.1", AT)])
    (stored,) = uow.gestures.rows.values()
    stored.action = replace(stored.action, ref=None)
    sent = await _send(ingest, device, "b2", [_effect("r.1", AT)])
    assert stored.action.effect is None
    assert sent.effects_dropped == 1


async def test_a_batch_without_dropped_effects_counts_none() -> None:
    _, ingest, (device,) = await _ready()
    sent = await _send(ingest, device, "b1", [_gesture("r.1", AT), _effect("r.1", AT)])
    assert sent.effects_dropped == 0
