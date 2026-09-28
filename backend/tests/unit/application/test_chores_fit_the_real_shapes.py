"""The sign-in and sign-out flags, read off the shapes QA actually recorded.

Greyorange QA, 2026-09-28: three recorded chores were not flagged, so they
were offered as work. `Log in to Google Account` posted twice on the identity
host before it left (the identifier lookup and the password), and no page
event was recorded, so nothing proved it left. `Log in using Azure B2C SSO`
counted another tab's mail traffic as its own business. `Log Out` was pressed
on a control whose label says nothing about logging out.

Every gesture here goes through `correlate`, the ingest path production uses,
and every verdict through `judged`, the path the sweep uses. The hosts are
made up; the structure is QA's.
"""

from __future__ import annotations

from datetime import UTC, datetime
from itertools import count
from typing import Any

from sro.application.capture.rig_wire import Batch
from sro.application.observation.chores import judged
from sro.application.observation.correlate import correlate
from sro.domain.observation.gesture import Gesture
from sro.domain.skill.checks import signs_in_to
from sro.domain.skill.workflow import Step, Workflow

T0 = 1_788_000_000.0
ENTRY = "https://www.idp-home.example"
IDP = "https://accounts.idp-home.example"
LAND = "https://myaccount.idp-home.example"
MAIL = "https://mail.elsewhere.example"
B2C = "https://tenant.b2c-login.example"
KEYCLOAK = "https://keycloak.example"
WMS = "https://wms.example"

_ids = count()


def _stamp(at: float) -> str:
    return datetime.fromtimestamp(T0 + at, tz=UTC).isoformat().replace("+00:00", "Z")


def _did(
    kind: str,
    page: str,
    at: float,
    *,
    name: str = "Next",
    secret: bool = False,
    value: str | None = None,
    tab: int = 1,
    menu: bool = False,
) -> dict[str, Any]:
    typing = kind == "type"
    return {
        "kind": "gesture",
        "gesture": {
            "kind": kind,
            "target": {
                "tag": "input" if typing else "button",
                "role": "textbox" if typing else "button",
                "name": name,
                "secret": secret,
                "attributes": {"aria-haspopup": "menu"} if menu else {},
            },
            "value": value,
            "secret": secret and typing,
            "at": T0 + at,
            "url": page,
        },
        "tab_id": tab,
        "frame_url": page,
        "page_url": page,
    }


def _post(url: str, at: float, status: int = 200, *, tab: int = 1) -> dict[str, Any]:
    return {
        "kind": "request",
        "request": {
            "request_id": f"r{next(_ids)}",
            "method": "POST",
            "url": url,
            "started_at": _stamp(at),
            "status": status,
        },
        "tab_id": tab,
    }


def _page(url: str, at: float, *, tab: int = 1) -> dict[str, Any]:
    return {"kind": "page", "at": _stamp(at), "page_kind": "navigated", "url": url, "tab_id": tab}


def _recorded(*events: dict[str, Any]) -> list[Gesture]:
    batch = Batch.model_validate(
        {
            "batch_id": "bat_1",
            "device_id": "dev_1",
            "started_at": _stamp(0),
            "ended_at": _stamp(600),
            "events": list(events),
        }
    )
    return correlate(batch, "acme")[0]


def _job(recorded: list[Gesture], *cited: int) -> tuple[Workflow, dict[str, Gesture]]:
    job = Workflow(
        id="wfl_1",
        tenant="acme",
        title="t",
        narrative="n",
        steps=[
            Step(order=n, says=f"step {n}", system=None, cites=[recorded[one].id])
            for n, one in enumerate(cited)
        ],
    )
    return job, {one.id: one for one in recorded}


def _google(*tail: dict[str, Any]) -> list[Gesture]:
    """`Log in to Google Account`: two clicks on the entry page, the email and
    Next on the identity host (Next posts the identifier lookup), Enter in the
    password box, the password (it posts), and nothing recorded as a page
    event anywhere. What comes next in the same tab is on the landing host."""
    return _recorded(
        _did("click", f"{ENTRY}/", 0, name="Sign in"),
        _did("click", f"{ENTRY}/", 2, name="Continue"),
        _did("type", f"{IDP}/signin/identifier", 4, name="Email", value="someone"),
        _did("click", f"{IDP}/signin/identifier", 6, name="Next"),
        _post(f"{IDP}/lookup", 6.2),
        _did("press", f"{IDP}/signin/challenge", 8, name="Password", secret=True),
        _did("type", f"{IDP}/signin/challenge", 8.1, name="Password", secret=True),
        _post(f"{IDP}/challenge", 8.3),
        *tail,
    )


_LANDED = (
    _did("click", f"{LAND}/", 11, name="Personal info"),
    _did("click", f"{LAND}/", 13, name="Security"),
)


def test_the_google_sign_in_is_a_sign_in() -> None:
    """Its own posts on the identity host, before the flow left it, are the
    sign-in -- not business -- and where the operator acted next proves it
    left."""
    job, by_id = _job(_google(*_LANDED), 0, 1, 2, 3, 4, 5)

    assert judged(job, by_id) == (True, False)
    assert signs_in_to(job, by_id) == ("accounts.idp-home.example", "myaccount.idp-home.example")


def test_a_sign_in_form_with_nothing_after_it_proves_no_leaving() -> None:
    """The same form, typed and submitted, and then nothing in the stream:
    no page event and no next gesture, so nothing proves it left."""
    job, by_id = _job(_google(), 0, 1, 2, 3, 4, 5)

    assert judged(job, by_id) == (False, False)
    assert signs_in_to(job, by_id) is None


def test_what_another_tab_does_next_proves_no_leaving() -> None:
    job, by_id = _job(_google(_did("click", f"{MAIL}/", 11, tab=2)), 0, 1, 2, 3, 4, 5)

    assert judged(job, by_id) == (False, False)


def test_a_business_write_on_the_landing_system_is_business() -> None:
    recorded = _google(
        *_LANDED, _did("click", f"{LAND}/", 15, name="Save"), _post(f"{LAND}/x", 15.2)
    )
    job, by_id = _job(recorded, 0, 1, 2, 3, 4, 5, 8)

    assert judged(job, by_id) == (False, False)


def test_a_write_back_on_the_identity_host_after_landing_is_business() -> None:
    recorded = _google(
        *_LANDED, _did("click", f"{IDP}/settings", 15, name="Save"), _post(f"{IDP}/x", 15.2)
    )
    job, by_id = _job(recorded, 0, 1, 2, 3, 4, 5, 6, 8)

    assert judged(job, by_id) == (False, False)


def test_a_single_origin_login_then_business_is_not_a_sign_in() -> None:
    """The app's own form posts the password, then the operator saves
    something on the same host, then moves on to another one."""
    recorded = _recorded(
        _did("type", f"{WMS}/login", 1, name="User", value="u"),
        _did("type", f"{WMS}/login", 2, name="Password", secret=True),
        _did("click", f"{WMS}/login", 3, name="Sign in"),
        _post(f"{WMS}/session", 3.2),
        _did("click", f"{WMS}/orders", 5, name="Save"),
        _post(f"{WMS}/orders", 5.2, 201),
        _did("click", f"{LAND}/", 8),
    )
    job, by_id = _job(recorded, 0, 1, 2, 3)

    assert judged(job, by_id) == (False, False)


def test_business_before_a_pin_on_the_same_host_is_not_signing_in() -> None:
    """A write, a PIN typed and approved on the same host, then the operator
    goes elsewhere in the same tab. Nobody arrived on that host to sign in, so
    the write before the PIN is still the job's business."""
    recorded = _recorded(
        _did("click", f"{WMS}/orders", 1, name="Save"),
        _post(f"{WMS}/orders", 1.2, 201),
        _did("type", f"{WMS}/orders", 2, name="PIN", secret=True),
        _did("click", f"{WMS}/orders", 3, name="Approve"),
        _did("click", f"{LAND}/", 6),
    )
    job, by_id = _job(recorded, 0, 1, 2)

    assert judged(job, by_id) == (False, False)


def test_a_pin_whose_approve_stayed_on_its_host_did_not_leave_it() -> None:
    """The recorder did capture where the Approve went -- its own host -- so
    the next click being elsewhere proves nothing about leaving."""
    recorded = _recorded(
        _did("type", f"{WMS}/orders", 2, name="PIN", secret=True),
        _did("click", f"{WMS}/orders", 3, name="Approve"),
        _page(f"{WMS}/approved", 3.2),
        _did("click", f"{LAND}/", 6),
    )
    job, by_id = _job(recorded, 0, 1)

    assert judged(job, by_id) == (False, False)


def _azure(*extra: dict[str, Any]) -> list[Gesture]:
    """`Log in using Azure B2C SSO`: the chooser, the credential on the
    identity host, a Sign In that leaves for the warehouse, a click there --
    and, while it ran, another tab posting on a host the job never touches."""
    return _recorded(
        _did("click", f"{B2C}/authorize", 1, name="Local users"),
        _did("type", f"{KEYCLOAK}/auth", 2, name="User", value="u"),
        _did("type", f"{KEYCLOAK}/auth", 3, name="Password", secret=True),
        _did("click", f"{KEYCLOAK}/auth", 4, name="Sign In"),
        _post(f"{KEYCLOAK}/auth/authenticate", 4.1, 302),
        _page(f"{WMS}/home", 4.3),
        _did("click", f"{MAIL}/inbox", 10, tab=2, name="Refresh"),
        _post(f"{MAIL}/sync", 10.2, tab=2),
        *extra,
        _did("click", f"{WMS}/home", 20, name="Inventory"),
    )


def test_another_tabs_mail_is_not_the_jobs_business() -> None:
    recorded = _azure()
    job, by_id = _job(recorded, 0, 1, 2, 3, 5)

    assert judged(job, by_id) == (True, False)


def test_an_uncited_write_on_the_jobs_own_system_is_still_business() -> None:
    """The sitting window is for exactly this: a save the model left
    uncited, on a system the job acts on."""
    recorded = _azure(_did("click", f"{WMS}/home", 12, tab=3), _post(f"{WMS}/x", 12.2, tab=3))
    job, by_id = _job(recorded, 0, 1, 2, 3, 6)

    assert judged(job, by_id) == (False, False)


def test_a_keycloak_sign_in_is_still_a_sign_in() -> None:
    recorded = _recorded(
        _did("type", f"{KEYCLOAK}/auth", 1, name="User", value="u"),
        _did("type", f"{KEYCLOAK}/auth", 2, name="Password", secret=True),
        _did("click", f"{KEYCLOAK}/auth", 3, name="Sign In"),
        _post(f"{KEYCLOAK}/auth/authenticate", 3.1, 302),
        _page(f"{WMS}/home", 3.3),
    )
    job, by_id = _job(recorded, 0, 1, 2)

    assert judged(job, by_id) == (True, False)


def _log_out(label: str, *lands: str) -> list[Gesture]:
    return _recorded(
        _did("click", f"{WMS}/home", 1, name="admin", menu=True),
        _did("click", f"{WMS}/home", 2, name=label),
        *(_page(one, 2.3 + index / 10) for index, one in enumerate(lands)),
    )


def test_a_click_that_lands_signed_out_ends_the_session() -> None:
    """The label says nothing (an icon's name); the page it lands on does."""
    job, by_id = _job(_log_out("Session", f"{WMS}/login"), 0, 1)

    assert judged(job, by_id) == (False, True)


def test_a_click_to_an_ordinary_page_does_not_sign_out() -> None:
    """Including one that passes a token refresh on the way: where it ends
    is what it landed on."""
    for lands in ((f"{WMS}/orders",), (f"{WMS}/auth/refresh", f"{WMS}/orders")):
        job, by_id = _job(_log_out("Orders", *lands), 0, 1)

        assert judged(job, by_id) == (False, False)


def test_a_sign_ins_final_click_is_not_a_sign_out() -> None:
    """It leaves a sign-in page for the app: the other direction -- even
    when, as on the deployed Azure chain, its last page mark is the
    identity chooser's `/authorize`, and even when the job cites only the
    submit, with nothing else to disqualify it."""
    for lands in ((f"{WMS}/home",), (f"{B2C}/authorize",)):
        recorded = _recorded(
            _did("type", f"{KEYCLOAK}/login", 1, name="Password", secret=True),
            _did("click", f"{KEYCLOAK}/login", 2, name="Go"),
            *(_page(one, 2.2) for one in lands),
        )
        job, by_id = _job(recorded, 0, 1)

        assert judged(job, by_id) == (True, False)
        submit_only, _ = _job(recorded, 1)
        assert judged(submit_only, by_id) == (False, False)
