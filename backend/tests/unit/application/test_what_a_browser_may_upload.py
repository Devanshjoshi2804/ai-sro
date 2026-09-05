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


OURS = frozenset({"localhost:8000", "localhost:3000"})


def _at(url: str) -> dict[str, object]:
    event = _gesture()
    gesture = event["gesture"]
    assert isinstance(gesture, dict)
    gesture["url"] = url
    return event


def test_the_recording_apparatus_is_not_the_work_it_records() -> None:
    """It happened. The operator had the console open in a tab while
    demonstrating, so the extension captured the console asking the API for its
    own recordings -- twelve requests in the real store, one of them a POST that
    a mined workflow then reported as the write its job performs."""
    admission = admit([_at("http://localhost:8000/v1/recordings/rec_1")], ON, ours=OURS)

    assert admission.accepted == ()
    assert (
        admission.rejected[0].reason == "this is the recording apparatus, not the work it records"
    )


def test_no_operator_grant_widens_our_own_hosts() -> None:
    """The difference between this rule and `exclude_hosts`. A default is the
    kind of thing the person at the screen may decide otherwise about for one
    page -- and pressing "observe this page" while looking at the console would
    switch the apparatus back on. Nobody ever means that by watching the work."""
    granted = frozenset({"localhost"})

    admission = admit([_at("http://localhost:8000/v1/recordings/rec_1")], ON, granted, OURS)

    assert admission.accepted == ()


def test_our_own_port_is_refused_and_the_neighbouring_one_is_not() -> None:
    """Host AND port. An API on 8000 beside a console on 3000 is the ordinary
    shape, and matching on hostname alone would refuse `localhost` entirely --
    which on a developer's machine is also where the warehouse test server
    lives, and is where the extension's own fixtures are served from."""
    admission = admit(
        [_at("http://localhost:8000/v1/x"), _at("http://localhost:63319/wms/orders")],
        ON,
        ours=OURS,
    )

    assert admission.accepted_count == 1
    assert len(admission.rejected) == 1


def test_a_deployment_that_names_no_hosts_of_its_own_refuses_nothing_extra() -> None:
    """The parameter defaults to empty, so every existing caller behaves as it
    did. A rule this quiet must not change what it was not given."""
    assert admit([_at("http://localhost:8000/v1/x")], ON).accepted_count == 1
