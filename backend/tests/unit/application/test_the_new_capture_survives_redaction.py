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
