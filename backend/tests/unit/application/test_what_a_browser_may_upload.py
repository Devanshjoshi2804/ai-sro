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


OURS = frozenset({("localhost:8000", "/"), ("localhost:3000", "/")})


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


def test_the_console_page_is_named_by_a_setting_and_not_by_the_cors_list() -> None:
    """`cors_origins` is browser origins allowed to CALL the API, and a console
    served same-origin or proxied through its own server never appears in it.
    This deployment is exactly that shape -- `cors_origins` holds only the
    extension -- so the console's own page had nothing naming it and was
    captured: 7 gestures in the real store, beside the 12 requests its API
    calls contributed."""
    from sro.config import Settings

    ours = Settings(
        api_url="http://localhost:8000",
        console_url="http://localhost:3000",
        cors_origins=("chrome-extension://abc",),
    ).our_own_origins()

    assert ("localhost:3000", "/") in ours
    assert ("abc", "/") in ours, "an origin trusted to call this API is part of this system"

    admission = admit([_at("http://localhost:3000/skills")], ON, ours=ours)
    assert admission.accepted == ()


def test_the_three_names_of_this_machine_are_one_machine() -> None:
    """`attach_hosts` says so ten lines above `our_own_origins` in the same
    class. A rule whose whole justification is "a default nobody sets is a
    default nobody has" cannot then depend on the operator having typed
    `localhost` rather than `127.0.0.1` -- Chrome records whichever they typed,
    and the tenant's `exclude_hosts` names only the one."""
    from sro.config import Settings

    ours = Settings(api_url="http://localhost:8000", console_url="").our_own_origins()

    for url in (
        "http://localhost:8000/v1/recordings/rec_1",
        "http://127.0.0.1:8000/v1/recordings/rec_1",
        "http://[::1]:8000/v1/recordings/rec_1",
    ):
        assert admit([_at(url)], ON, ours=ours).accepted == (), url


def test_a_port_written_out_in_full_is_the_same_origin_without_it() -> None:
    """`https://sro.acme.com:443` is what an operator writes, and every real
    call goes to `https://sro.acme.com/...`. Left unnormalised, the rule
    matched neither."""
    from sro.config import Settings

    ours = Settings(api_url="https://sro.acme.com:443", console_url="").our_own_origins()

    assert admit([_at("https://sro.acme.com/v1/x")], ON, ours=ours).accepted == ()
    assert admit([_at("https://sro.acme.com:443/v1/x")], ON, ours=ours).accepted == ()


def test_userinfo_and_a_trailing_dot_do_not_walk_past_the_rule() -> None:
    """`netloc` carries userinfo, keeps a trailing dot and preserves case.
    `hostname` does none of the three, which is why the comparison is built
    from its parts rather than taken whole.

    A dot after the PORT rather than the host -- `localhost:8000.` -- is a
    different thing: the port is unreadable, so this cannot tell which origin
    it is and leaves it to the tenant's policy rather than guessing wide."""
    for url in (
        "http://user:pass@localhost:8000/v1/recordings/rec_1",
        "http://localhost.:8000/v1/recordings/rec_1",
        "http://LOCALHOST:8000/v1/recordings/rec_1",
    ):
        assert admit([_at(url)], ON, ours=OURS).accepted == (), url


def test_a_shared_host_loses_only_the_path_this_system_answers_on() -> None:
    """A corporate deployment path-routing this system and the WMS on one
    hostname is an ordinary shape. Refusing the whole host would make every
    warehouse page on it permanently unrecordable -- no grant able to restore
    it, and the refusal names no host, so nobody would learn why."""
    from sro.config import Settings

    ours = Settings(api_url="https://apps.acme.com/sro", console_url="").our_own_origins()

    assert admit([_at("https://apps.acme.com/sro/v1/x")], ON, ours=ours).accepted == ()
    assert admit([_at("https://apps.acme.com/wms/orders")], ON, ours=ours).accepted_count == 1
    assert admit([_at("https://apps.acme.com/srosomething")], ON, ours=ours).accepted_count == 1


def test_a_url_with_an_unreadable_port_is_left_to_the_tenants_policy() -> None:
    """Dropping just the port would WIDEN the rule: a mistyped `localhost:8000.`
    would become bare `localhost` and refuse every page on it, the warehouse
    test server included."""
    from sro.config import Settings

    ours = Settings(
        api_url="http://localhost:8000.", console_url="", cors_origins=()
    ).our_own_origins()

    assert ours == frozenset(), "nothing, rather than a portless `localhost`"
