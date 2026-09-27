"""Whether a job signs out, decided by code from what the operator did.

Real QA, 2026-09-27: seven of 23 jobs were sign-in or sign-out chores and drew
44% of the offers. `Log Out` was never flagged, because nothing asked whether a
job ends the session: a sign-out control pressed, then a sign-in page or a
signed-out page.
"""

from __future__ import annotations

from dataclasses import replace

from sro.domain.observation.gesture import Action, Call, Gesture, PageMark, Target
from sro.domain.skill.checks import signs_out
from sro.domain.skill.workflow import Step, Workflow

WMS = "https://wms.example"
B2C = "https://tenant.b2clogin.example"


def _click(gesture_id: str, at: float, name: str, *, url: str = WMS) -> Gesture:
    return Gesture(
        id=gesture_id,
        tenant="acme",
        stream_id="s",
        batch_id="b",
        at=at,
        url=f"{url}/portal/page",
        system=url,
        tab_id=1,
        frame_url=None,
        action=Action(kind="click", at=at, target=Target(tag="a", role="menuitem", name=name)),
    )


def _landed(gesture: Gesture, *urls: str) -> Gesture:
    return replace(
        gesture,
        page_events=[PageMark(at=gesture.at, page_kind="navigated", url=one) for one in urls],
    )


def _typed_user(gesture_id: str, at: float, url: str) -> Gesture:
    return replace(
        _click(gesture_id, at, "Username or email", url=url),
        url=f"{url}/signin",
        action=Action(kind="type", at=at, target=Target(tag="input", name="Username or email")),
    )


def _job(*cites: str) -> Workflow:
    return Workflow(
        id="wfl_out",
        tenant="acme",
        title="Log Out",
        narrative="n",
        steps=[
            Step(order=n, says=f"step {n}", system=WMS, cites=[one]) for n, one in enumerate(cites)
        ],
    )


def _the_real_log_out() -> dict[str, Gesture]:
    """The deployed shape: the user menu, then `Log Out`, which sends the
    browser to Azure B2C's logout and on to its sign-in page, where the
    operator starts typing a username that no step cites."""
    return {
        "menu": _click("menu", 1, "admin"),
        "out": _landed(
            _click("out", 2, "Log Out"),
            f"{B2C}/tenant.onmicrosoft.com/b2c_1a_signin/oauth2/v2.0/logout",
            f"{B2C}/tenant.onmicrosoft.com/b2c_1a_signin/oauth2/v2.0/authorize",
        ),
        "user": _typed_user("user", 5, B2C),
    }


def test_the_real_log_out_signs_out() -> None:
    assert signs_out(_job("menu", "out"), _the_real_log_out()) is True


def test_a_log_out_that_lands_on_its_own_sign_in_page_signs_out() -> None:
    store = {
        "menu": _click("menu", 1, "admin"),
        "out": _landed(_click("out", 2, "Sign out"), f"{WMS}/login?reason=signed-out"),
    }

    assert signs_out(_job("menu", "out"), store) is True


def test_a_log_out_followed_by_a_credential_field_signs_out() -> None:
    """No page mark recorded, but the next thing the operator touched was a
    sign-in form."""
    store = {"out": _click("out", 2, "Logout"), "user": _typed_user("user", 4, WMS)}

    assert signs_out(_job("out"), store) is True


def test_a_log_out_control_with_no_sign_of_the_session_ending_does_not_sign_out() -> None:
    store = {"menu": _click("menu", 1, "admin"), "out": _click("out", 2, "Log Out")}

    assert signs_out(_job("menu", "out"), store) is False


def test_a_job_that_goes_on_working_after_a_log_out_does_not_end_the_session() -> None:
    """A lookup that happens to pass a sign-out: the job's last act is back in
    the signed-in system, so the steps do not end the session."""
    store = {
        **_the_real_log_out(),
        "grid": _click("grid", 9, "Inventory"),
    }

    assert signs_out(_job("menu", "out", "grid"), store) is False


def test_a_job_that_writes_and_then_logs_out_is_work() -> None:
    store = {
        "save": replace(
            _click("save", 1, "Save"),
            action=Action(kind="press", at=1, target=Target(tag="button", name="Save")),
            requests=[Call(method="POST", url=f"{WMS}/api/things", status=201)],
        ),
        **{key: one for key, one in _the_real_log_out().items() if key != "menu"},
    }

    assert signs_out(_job("save", "out"), store) is False


def test_a_control_whose_name_only_contains_the_words_is_not_a_sign_out() -> None:
    store = {
        "out": _landed(_click("out", 2, "Logoutput report"), f"{WMS}/login"),
    }

    assert signs_out(_job("out"), store) is False


def test_a_job_citing_nothing_anybody_kept_does_not_sign_out() -> None:
    assert signs_out(_job("gone"), {}) is False


def test_a_job_that_signs_in_or_out_is_a_chore_and_an_undecided_one_is_not() -> None:
    job = _job("out")
    assert replace(job, signs_out=True).chore is True
    assert replace(job, signs_in=True).chore is True
    assert replace(job, signs_in=False, signs_out=False).chore is False
    assert job.chore is False


def _pressed(gesture_id: str, at: float, name: str, *calls: Call) -> Gesture:
    return replace(
        _click(gesture_id, at, name),
        action=Action(kind="press", at=at, target=Target(tag="button", role="button", name=name)),
        requests=list(calls),
    )


def test_any_write_before_the_log_out_is_work_whatever_its_method_status_or_host() -> None:
    """The codebase's own write check -- any method that is not a read, at any
    status -- and not `_did_business`'s 2xx POST/PUT/PATCH. A write to the
    API's own subdomain or one with no status recorded is still a write."""
    for call in (
        Call(method="DELETE", url=f"{WMS}/api/things/1", status=204),
        Call(method="POST", url=f"{WMS}/portal/form", status=302),
        Call(method="POST", url="https://api.wms.example/things", status=201),
        Call(method="POST", url=f"{WMS}/api/things", status=None),
    ):
        store = {
            "save": _pressed("save", 1, "Save", call),
            **{key: one for key, one in _the_real_log_out().items() if key != "menu"},
        }

        assert signs_out(_job("save", "out"), store) is False, call


def test_a_log_out_that_is_itself_a_post_is_the_control_not_a_write() -> None:
    store = _the_real_log_out()
    store["out"] = replace(
        store["out"], requests=[Call(method="POST", url=f"{WMS}/portal/logout", status=200)]
    )

    assert signs_out(_job("menu", "out"), store) is True


def test_a_sign_off_queue_is_not_a_sign_out() -> None:
    """Quality -> Sign-Off Queue -> the operator's next gesture is in Outlook.
    "Sign off" is an approval, and another origin alone never proves the
    session ended."""
    store = {
        "quality": _click("quality", 1, "Quality"),
        "queue": _click("queue", 2, "Sign-Off Queue"),
        "mail": _click("mail", 4, "Inbox", url="https://outlook.office.example"),
    }

    assert signs_out(_job("quality", "queue"), store) is False


def test_a_log_out_whose_next_gesture_is_merely_on_another_host_does_not_sign_out() -> None:
    store = {
        "menu": _click("menu", 1, "admin"),
        "out": _landed(_click("out", 2, "Log Out"), "https://intranet.example/home"),
        "next": _click("next", 4, "News", url="https://intranet.example"),
    }

    assert signs_out(_job("menu", "out"), store) is False


def test_a_sign_in_page_in_another_tab_is_not_this_log_out_s_landing() -> None:
    store = {
        "menu": _click("menu", 1, "admin"),
        "out": _click("out", 2, "Log Out"),
        "user": replace(_typed_user("user", 4, B2C), tab_id=2),
    }

    assert signs_out(_job("menu", "out"), store) is False


def test_a_job_whose_only_substance_is_the_log_out_signs_out_and_one_that_exports_is_work() -> None:
    """Product ruling M4: the steps before the control may only open menus and
    move between pages to reach it. Exporting a report -- a button that reads,
    moves nowhere and opens nothing -- is work, even with a log out after it."""
    reach = {
        **_the_real_log_out(),
        "settings": _landed(_click("settings", 0.5, "Settings"), f"{WMS}/portal/settings"),
    }
    assert signs_out(_job("settings", "menu", "out"), reach) is True

    exports = {
        **_the_real_log_out(),
        "export": _pressed(
            "export", 0.5, "Export", Call(method="GET", url=f"{WMS}/api/report.csv", status=200)
        ),
    }
    assert signs_out(_job("export", "menu", "out"), exports) is False
