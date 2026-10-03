from sro.application.capture.rig_wire import Batch, EffectEvent, Gesture, PageEvent, Target
from sro.application.observation.admit import admit
from sro.application.observation.redact import redact_events
from sro.domain.observation.policy import ObservationPolicy

ON = ObservationPolicy(capture_enabled=True)


def _gesture(**extra: object) -> dict[str, object]:
    return {
        "kind": "gesture",
        "tab_id": 7,
        "gesture": {
            "kind": "click",
            "at": 1_790_000_000.25,
            "url": "https://wms.example/a",
            "ref": "r.1",
            "target": {
                "role": "button",
                "name": "Save",
                "labelText": "Save",
                "fullName": "Save",
                "siblingIndex": 2,
                "siblingCount": 3,
            },
            "place": {"route": "/a", "title": "Customers", "headings": ["Customers"]},
            "choice": {"chosen": "Retail", "index": 1, "options": ["Bulk", "Retail"]},
            **extra,
        },
    }


def _effect() -> dict[str, object]:
    return {
        "kind": "effect",
        "of": "r.1",
        "of_at": 1_790_000_000.25,
        "url": "https://wms.example/a",
        "tab_id": 7,
        "effect": {
            "appeared": [{"role": "status", "text": "Saved"}],
            "quiet_ms": 640,
            "ended": "quiet",
        },
    }


def test_every_key_the_recorder_now_sends_is_declared_on_the_wire() -> None:
    assert {"place", "choice"} <= set(Gesture.model_fields)
    assert {"labelText", "fullName", "siblingIndex", "siblingCount"} <= set(Target.model_fields)
    assert {"cookies", "mail_thread"} <= set(PageEvent.model_fields)
    assert {"of", "of_at", "effect", "url", "tab_id", "frame_path"} <= set(EffectEvent.model_fields)


def test_the_new_gesture_keys_reach_storage() -> None:
    (out,) = redact_events([_gesture()])
    gesture = out["gesture"]
    assert gesture["place"]["title"] == "Customers"
    assert gesture["choice"]["chosen"] == "Retail"
    assert gesture["target"]["labelText"] == "Save" and gesture["target"]["siblingIndex"] == 2


def test_an_undeclared_gesture_key_is_still_dropped() -> None:
    (out,) = redact_events([_gesture(somethingNew="x")])
    assert "somethingNew" not in out["gesture"]


def test_an_effect_event_is_admitted_kept_and_parsed() -> None:
    admitted = admit([_gesture(), _effect()], ON)
    assert admitted.rejected == ()
    _, effect = redact_events(admitted.accepted)
    assert effect["effect"]["appeared"][0]["text"] == "Saved"
    batch = Batch.model_validate(
        {
            "batch_id": "b",
            "device_id": "d",
            "started_at": "2026-10-02T00:00:00+00:00",
            "ended_at": "2026-10-02T00:01:00+00:00",
            "events": [effect],
        }
    )
    assert isinstance(batch.events[0], EffectEvent)


def test_an_effect_on_an_excluded_host_is_refused() -> None:
    event = _effect() | {"url": "https://accounts.google.com/x"}
    assert admit([event], ON).accepted == ()


def test_an_effect_without_its_gesture_reference_is_refused() -> None:
    event = {key: value for key, value in _effect().items() if key != "of_at"}
    assert admit([event], ON).accepted == ()


def test_an_effect_s_unlisted_keys_never_reach_storage() -> None:
    (out,) = redact_events([_effect() | {"body": "everything typed"}])
    assert "body" not in out


def test_cookie_names_and_a_mail_thread_reach_storage_and_values_never_do() -> None:
    page = {
        "kind": "page",
        "at": "2026-10-02T00:00:00+00:00",
        "page_kind": "cookies_set",
        "url": "https://wms.example/a",
        "tab_id": 7,
        "cookies": [{"name": "JSESSIONID", "expires_at": 1_790_003_600.0, "value": "secret"}],
        "mail_thread": "FMfcgzQXJWDsKmbXrhvpnLtqzqZJbQqk",
    }
    (out,) = redact_events([page])
    assert out["cookies"] == [
        {"name": "JSESSIONID", "expires_at": 1_790_003_600.0, "domain": None, "session": False}
    ]
    assert out["mail_thread"] == "FMfcgzQXJWDsKmbXrhvpnLtqzqZJbQqk"


async def _ingest(events: list[dict[str, object]]) -> tuple[str, str, int, int]:
    from datetime import UTC, datetime

    from sro.application.context import RequestContext
    from sro.application.observation.ingest import IngestObservation
    from sro.application.observation.policy import SetObservationPolicy
    from sro.application.observation.register import RegisterDevice
    from sro.domain.observation.batch import CaptureMode
    from sro.domain.shared.identifiers import BatchId, TenantId
    from tests import factories as f
    from tests.unit.fakes import FakeBlobStore, FakeClock, FakeIdFactory, FakeUnitOfWork

    ctx = RequestContext(tenant_id=TenantId("acme"), principal_id=f.OPERATOR)
    uow, blobs = FakeUnitOfWork(), FakeBlobStore()
    await SetObservationPolicy(uow).execute(ctx, policy=ObservationPolicy().enabled())
    registered = await RegisterDevice(uow, FakeClock(), FakeIdFactory()).execute(
        ctx, label="laptop", extension_version="0.1.0"
    )
    stored = await IngestObservation(uow, blobs, FakeClock()).execute(
        ctx,
        device_id=registered.device_id,
        secret=registered.secret,
        batch_id=BatchId("bat_new_keys"),
        started_at=datetime(2026, 3, 1, 9, 0, tzinfo=UTC),
        ended_at=datetime(2026, 3, 1, 9, 5, tzinfo=UTC),
        mode=CaptureMode.PASSIVE,
        events=events,
    )
    written = b"" if stored.stored_at is None else await blobs.read(stored.stored_at)
    return (
        written.decode("utf-8"),
        repr(list(uow.gestures.rows.values())),
        stored.accepted,
        len(stored.rejected),
    )


_SECRET_ROUTES = [
    "/y#password: hunter2xyz",
    "/y#password:hunter2xyz",
    "/y#!/k/token: hunter2xyz",
    "/y#api key = hunter2xyz",
    "/y/password%3A%20hunter2xyz",
    "/y#secret is hunter2xyz",
]


import pytest  # noqa: E402


@pytest.mark.parametrize("route", _SECRET_ROUTES)
async def test_a_route_with_a_secret_value_stores_none_of_it(route: str) -> None:
    gesture = _gesture()
    gesture["gesture"]["place"] = {"route": route, "title": "T"}
    effect = _effect()
    effect["effect"]["route_after"] = route
    written, kept, accepted, _ = await _ingest([gesture, effect])
    assert accepted == 2
    assert "hunter2xyz" not in written and "hunter2xyz" not in kept


def test_a_decoded_route_with_spaces_and_ids_still_survives() -> None:
    (out,) = redact_events(
        [
            _gesture()
            | {
                "gesture": _gesture()["gesture"]
                | {"place": {"route": "/a/new%20order/123456#!/e/9"}}
            }
        ]
    )
    assert out["gesture"]["place"]["route"] == "/a/new order/*#!/e/*"


@pytest.mark.parametrize("of", ["", "x" * 65, "a@b.co", "r 1", "r/1", 5, None, "a" * 5_000_000])
def test_an_effect_whose_gesture_ref_is_not_a_ref_is_refused(of: object) -> None:
    assert admit([_effect() | {"of": of}], ON).accepted == ()


def test_a_recorder_ref_is_admitted() -> None:
    assert admit([_effect() | {"of": "r.1-A_b"}], ON).accepted != ()


@pytest.mark.parametrize("of_at", [float("nan"), float("inf"), float("-inf")])
def test_an_effect_with_a_non_finite_gesture_time_is_refused(of_at: float) -> None:
    assert admit([_effect() | {"of_at": of_at}], ON).accepted == ()


@pytest.mark.parametrize(
    "effect", [{}, {"appeared": [{"role": "status", "text": "a@b.co"}]}, {"ended": "never"}]
)
def test_an_effect_that_says_nothing_after_sanitising_is_refused(effect: dict[str, object]) -> None:
    admitted = admit([_effect() | {"effect": effect}], ON)
    assert admitted.accepted == () and len(admitted.rejected) == 1


def test_effect_frame_hops_are_capped_and_keep_only_their_own_keys() -> None:
    hops = [{"index": i, "url": "https://x.example/f", "junk": "j" * 50} for i in range(100_000)]
    (out,) = redact_events([_effect() | {"frame_path": hops}])
    assert len(out["frame_path"]) <= 16
    assert all(set(hop) <= {"index", "url"} for hop in out["frame_path"])


def test_the_wire_models_sanitise_on_their_own() -> None:
    from sro.application.capture.rig_wire import Choice, Effect, Place

    place = Place.model_validate({"route": "/y#password: hunter2xyz", "title": "a@b.co"})
    assert place.route is None and place.title is None
    choice = Choice.model_validate({"chosen": "a@b.co", "options": ["Bulk", "tok=abcdefgh"]})
    assert choice.chosen is None and choice.options == ["Bulk"]
    effect = Effect.model_validate(
        {"route_after": "/y#password: hunter2xyz", "errors": ["a@b.co"], "ended": "quiet"}
    )
    assert effect.route_after is None and effect.errors == [] and effect.ended == "quiet"
