"""Which job signs in at the page a run is stuck on.

The deployment's own shape, 2026-09-19: an expired WMS session bounced a run to
`blueyonderalphaus.b2clogin.com`, and the tenant had already mined the way
through that chooser -- `Log in using Azure B2C SSO`, two clicks, every gesture
on that host. `Log in to Keycloak` touches the same host once, in the middle of
crossing into Keycloak, and is not the job for that page.
"""

from __future__ import annotations

from sro.domain.observation.gesture import Action, Gesture
from sro.domain.skill.signing_in import signs_in_at
from sro.domain.skill.workflow import Step, Workflow

B2C = "https://blueyonderalphaus.b2clogin.com"
KEYCLOAK = "https://keycloak-service-exec-wms-keycloak-prod.us.live.external.byp.ai"
WMS = "https://bf56-kms-wms-web-np2.jdadelivers.com"


def _at(gesture_id: str, url: str) -> Gesture:
    return Gesture(
        id=gesture_id,
        tenant="greyorange",
        stream_id="s",
        batch_id="b",
        at=1.0,
        url=f"{url}/page",
        system=url,
        tab_id=1,
        frame_url=None,
        action=Action(kind="click", at=1.0, url=f"{url}/page"),
    )


def _job(workflow_id: str, title: str, *cites: str, signs_in: bool = True) -> Workflow:
    return Workflow(
        id=workflow_id,
        tenant="greyorange",
        title=title,
        narrative="n",
        steps=[
            Step(order=n, says=f"step {n}", system=None, cites=[one]) for n, one in enumerate(cites)
        ],
        signs_in=signs_in,
    )


def _store() -> dict[str, Gesture]:
    return {
        "b2c-1": _at("b2c-1", B2C),
        "b2c-2": _at("b2c-2", B2C),
        "b2c-3": _at("b2c-3", B2C),
        "kc-1": _at("kc-1", KEYCLOAK),
        "kc-2": _at("kc-2", KEYCLOAK),
        "wms-1": _at("wms-1", WMS),
    }


SSO = _job("wfl_sso", "Log in using Azure B2C SSO", "b2c-1", "b2c-2")
KEYCLOAK_JOB = _job("wfl_kc", "Log in to Keycloak", "kc-1", "b2c-3", "kc-2")
CREATE = _job("wfl_make", "Create a Customer Type", "wms-1", signs_in=False)


def test_the_job_whose_evidence_is_that_page_is_the_way_back_in() -> None:
    found = signs_in_at(
        f"{B2C}/oauth2/v2.0/authorize?client_id=x", [CREATE, SSO, KEYCLOAK_JOB], _store()
    )

    assert found == "wfl_sso"


def test_a_job_that_merely_touches_the_host_is_not_the_job_for_it() -> None:
    """`Log in to Keycloak` cites one b2clogin gesture -- the operator crossed
    from the chooser into Keycloak in the middle of it. Running it here would
    start half way through somebody else's page."""
    found = signs_in_at(f"{B2C}/oauth2", [KEYCLOAK_JOB], _store())

    assert found is None


def test_the_host_decides_and_never_the_title() -> None:
    """`Log in using Azure B2C SSO` is a model's sentence about a job; the host
    is a fact about where the gestures happened. A name match would send a
    warehouse that bounced to Google into the Google sign-in."""
    google = _job("wfl_google", "Log in to Google Account", "kc-1", "kc-2")

    assert signs_in_at(f"{B2C}/oauth2", [google], _store()) is None
    assert signs_in_at(f"{KEYCLOAK}/auth", [google], _store()) == "wfl_google"


def test_two_ways_in_are_no_way_in() -> None:
    """Picking between them is guessing with somebody's credentials."""
    other = _job("wfl_other", "Sign in again", "b2c-3")

    assert signs_in_at(f"{B2C}/oauth2", [SSO, other], _store()) is None


def test_a_job_cannot_be_its_own_way_back_in() -> None:
    """The sign-in job meeting its own sign-in page is a run that would rescue
    itself forever."""
    assert signs_in_at(f"{B2C}/oauth2", [SSO], _store(), not_this="wfl_sso") is None


def test_a_page_nothing_was_ever_demonstrated_on_has_no_way_back_in() -> None:
    """Which is the honest answer, and what the run says out loud: this session
    has gone and nobody has shown me how to get back in."""
    assert signs_in_at("https://login.microsoftonline.com/x", [SSO, KEYCLOAK_JOB], _store()) is None


def test_a_job_whose_evidence_has_aged_out_says_nothing() -> None:
    assert signs_in_at(f"{B2C}/oauth2", [_job("wfl_gone", "Log in", "vanished")], _store()) is None


def test_a_job_that_does_not_sign_in_is_never_the_way_back_in() -> None:
    """Being entirely on the page is where, not what. A job entirely on one
    host that was never found to sign in is somebody's work there, and
    splicing it in would do that work on a run that asked for something else."""
    ordinary = _job("wfl_browse", "Browse the chooser", "b2c-1", "b2c-2", signs_in=False)

    assert signs_in_at(f"{B2C}/oauth2", [ordinary], _store()) is None
    assert signs_in_at(f"{B2C}/oauth2", [ordinary, SSO], _store()) == "wfl_sso"
