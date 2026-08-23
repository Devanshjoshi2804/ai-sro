"""Screening an upload, and refusing an extension that sends what it should not.

The extension enforces the policy by not injecting a content script on an
excluded host. This is the second check, and it exists because the first one
runs in software the deployment does not control.
"""

from __future__ import annotations

from sro.application.observation.admit import admit
from sro.domain.observation.policy import ObservationPolicy

ON = ObservationPolicy().enabled()


def _gesture(**target: object) -> dict[str, object]:
    return {
        "kind": "gesture",
        "gesture": {
            "kind": "click",
            "at": 1787654321.9,
            "url": "https://wms.acme.com/orders",
            "target": {"tag": "button", "cssPath": "div > button", **target},
        },
    }


def test_an_ordinary_gesture_is_kept() -> None:
    admission = admit([_gesture()], ON)

    assert admission.accepted_count == 1
    assert admission.rejected == ()


def test_an_element_nothing_could_find_again_is_refused_at_the_door() -> None:
    # ElementFingerprint refuses one carrying no signal, so this would be
    # evidence that cannot be replayed, aligned or matched -- discovered by a
    # mining run months later rather than by the extension's own test suite.
    admission = admit([_gesture(cssPath=None, tag="button")], ON)

    assert admission.accepted == ()
    assert "no signal" in admission.rejected[0].reason


def test_a_page_the_tenant_excluded_leaves_no_trace_of_itself() -> None:
    policy = ON.excluding(("payroll.acme.com",))
    event = _gesture()
    event["gesture"] = {**event["gesture"], "url": "https://payroll.acme.com/payslips"}  # type: ignore[dict-item]

    admission = admit([event], policy)

    assert admission.accepted == ()
    # The refusal must not name the URL: the point of an exclusion is that the
    # excluded page is not recorded anywhere, and this reason is stored.
    assert "payroll" not in admission.rejected[0].reason


def test_an_event_kind_the_protocol_does_not_declare_is_refused_by_name() -> None:
    admission = admit([{"kind": "keylog", "at": 1.0}], ON)

    assert "keylog" in admission.rejected[0].reason


def test_a_request_with_no_start_time_cannot_be_attributed_to_an_action() -> None:
    admission = admit(
        [{"kind": "request", "request": {"method": "POST", "url": "https://wms.acme.com/x"}}], ON
    )

    assert admission.accepted == ()
    assert "start time" in admission.rejected[0].reason


def test_the_index_of_a_refusal_is_the_index_the_extension_sent() -> None:
    admission = admit([_gesture(), {"kind": "nonsense"}, _gesture()], ON)

    assert admission.accepted_count == 2
    assert admission.rejected[0].index == 1
