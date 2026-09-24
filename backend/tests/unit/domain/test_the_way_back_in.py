"""Which job signs in at the page a run is stuck on.

The deployment's own shape, 2026-09-19: an expired WMS session bounced a run to
`blueyonderalphaus.b2clogin.com`, and the tenant had already mined the way
through that chooser -- `Log in using Azure B2C SSO`, two clicks, every gesture
on that host. `Log in to Keycloak` touches the same host once, in the middle of
crossing into Keycloak, and is not the job for that page.
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from sro.domain.observation.gesture import Action, Gesture, PageMark, Target
from sro.domain.skill.signing_in import sign_in_chain, signs_in_at
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


def test_a_sign_in_that_crosses_hosts_is_the_way_in_where_it_starts() -> None:
    """The real chain: the chooser on one host, then the form on another. A
    job is the way through the page it STARTS on; entirely-on-one-host would
    reject every sign-in that crosses from a chooser into a form."""
    chain = _job("wfl_chain", "Log in", "b2c-1", "kc-1", "kc-2")

    assert signs_in_at(f"{B2C}/oauth2", [chain], _store()) == "wfl_chain"
    assert signs_in_at(f"{KEYCLOAK}/auth", [chain], _store()) is None


def _did(
    gesture_id: str,
    url: str,
    at: float,
    kind: str = "click",
    *,
    secret: bool = False,
    to: str = "",
    field: str = "",
) -> Gesture:
    target = Target(tag="input", css_path=field, secret=secret) if field else None
    return replace(
        _at(gesture_id, url),
        at=at,
        action=Action(kind=kind, at=at, url=f"{url}/page", secret=secret, target=target),
        page_events=[PageMark(at=at, page_kind="load", url=f"{to}/landed")] if to else [],
    )


def _azure() -> tuple[Workflow, dict[str, Gesture]]:
    """The deployed Azure B2C sign-in, as the QA export holds it (2026-09-23):
    the chooser on b2clogin, the username and password on Keycloak, and a last
    step that cites both the submit that left Keycloak and a click in the WMS
    nineteen seconds later."""
    gestures = {
        one.id: one
        for one in (
            _did("chooser", B2C, 1.0, to=KEYCLOAK),
            _did("user-box", KEYCLOAK, 2.0),
            _did("user", KEYCLOAK, 3.0, "type"),
            _did("password", KEYCLOAK, 4.0, "type", secret=True),
            _did("submit", KEYCLOAK, 5.0, to=WMS),
            _did("wms-click", WMS, 24.0),
        )
    }
    steps = [
        Step(order=0, says="Click the chooser", system=B2C, cites=["chooser"]),
        Step(order=1, says="Type the username", system=KEYCLOAK, cites=["user-box", "user"]),
        Step(order=2, says="Type the password", system=KEYCLOAK, cites=["password"]),
        Step(
            order=3,
            says="Sign in and open the portal",
            system=KEYCLOAK,
            cites=["submit", "wms-click"],
        ),
    ]
    return Workflow(
        id="wfl_azure", tenant="t", title="Log in", narrative="n", steps=steps
    ), gestures


def test_the_azure_chain_is_spliced_through_the_submit_that_left_the_host_only() -> None:
    """The chooser also leaves its host, but nothing was typed before it: it
    is a door, not a submit. The chain ends at the submit, inside its step."""
    job, gestures = _azure()

    chain = sign_in_chain(job, gestures)

    assert [step.order for step in chain] == [0, 1, 2, 3]
    assert chain[-1].cites == ["submit"]
    assert "wms-click" not in {one for step in chain for one in step.cites}
    assert job.steps[3].cites == ["submit", "wms-click"], "the job itself was changed"


def test_a_step_after_the_landing_is_never_part_of_the_chain() -> None:
    job, gestures = _azure()
    job.steps[3].cites = ["submit"]
    job.steps.append(Step(order=4, says="Open Customers", system=WMS, cites=["wms-click"]))

    assert [step.order for step in sign_in_chain(job, gestures)] == [0, 1, 2, 3]


def test_a_job_that_never_left_the_host_after_typing_is_all_chain() -> None:
    """Nothing says where the sign-in ends, so every step is the sign-in, as
    before."""
    job, gestures = _azure()
    gestures["submit"] = replace(gestures["submit"], page_events=[])

    chain = sign_in_chain(job, gestures)

    assert [step.cites for step in chain] == [step.cites for step in job.steps]


def test_the_credential_decides_where_the_chain_can_end_not_the_username() -> None:
    """Identifier first: the username page's Next leaves for the password's
    host. The chain goes on to the submit after the password."""
    job, gestures = _azure()
    gestures["user-next"] = _did("user-next", KEYCLOAK, 3.5, to=B2C)
    job.steps[1].cites = ["user-box", "user", "user-next"]

    assert sign_in_chain(job, gestures)[-1].cites == ["submit"]


def test_the_cut_is_the_first_submit_in_time_not_in_step_order() -> None:
    """A step ordered early can cite a click made after the landing; walking by
    order would end the chain there and lose the password and the submit."""
    job, gestures = _azure()
    gestures["later-nav"] = _did("later-nav", KEYCLOAK, 30.0, to=WMS)
    job.steps[1].cites = ["user-box", "user", "later-nav"]

    chain = sign_in_chain(job, gestures)

    assert [step.order for step in chain] == [0, 1, 2, 3]
    assert chain[1].cites == ["user-box", "user"]
    assert chain[-1].cites == ["submit"]


def test_a_credential_step_ordered_after_the_submit_is_replayed_before_it() -> None:
    """The deployed job files a `Type the password` step after the one that
    first cites the password. Replayed in step order, the submit would press
    on an empty box and the password would be typed on the landed page; the
    chain is replayed in the order it happened, the leaving submit last."""
    job, gestures = _azure()
    job.steps[2].order, job.steps[3].order = 3, 2

    chain = sign_in_chain(job, gestures)

    assert [step.says for step in chain] == [
        "Click the chooser",
        "Type the username",
        "Type the password",
        "Sign in and open the portal",
    ]
    assert chain[-1].cites == ["submit"]


def test_a_refused_submit_in_the_evidence_is_not_replayed() -> None:
    """The deployed recording (`wfl_5873ec01`, step 2): the operator focused
    the password box, typed, pressed Sign In and stayed on Keycloak, focused
    again, retyped and pressed Enter -- recorded a millisecond before the Sign
    In click that left, which is the browser submitting the form for it.
    Replayed as recorded, the first submit goes in early. The chain keeps the
    typing and the focusing, and submits once, last."""
    job, gestures = _azure()
    for one in (
        _did("pw-box", KEYCLOAK, 3.5, secret=True, field="input#password"),
        _did("pw", KEYCLOAK, 3.6, "type", secret=True, field="input#password"),
        _did("early-sign-in", KEYCLOAK, 3.7, field="input#kc-login"),
        _did("pw-box-again", KEYCLOAK, 3.8, secret=True, field="input#password"),
        _did("pw-again", KEYCLOAK, 4.999, "type", secret=True, field="input#password"),
        _did("enter", KEYCLOAK, 4.999, "press", secret=True, field="input#password"),
    ):
        gestures[one.id] = one
    job.steps[2].cites = ["pw-box", "pw", "early-sign-in", "pw-box-again", "pw-again", "enter"]

    chain = sign_in_chain(job, gestures)

    assert chain[2].cites == ["pw-box", "pw", "pw-box-again", "pw-again"]
    kept = [gestures[one] for step in chain for one in step.cites]
    assert [one.id for one in kept if one.action.kind in ("click", "press")] == [
        "chooser",
        "user-box",
        "pw-box",
        "pw-box-again",
        "submit",
    ]
    assert chain[-1].cites == ["submit"]


def test_a_next_before_the_password_is_not_a_refused_submit() -> None:
    """Identifier first on one host: the username page's Next stays, and it
    is the way to the password box, not a refused attempt."""
    job, gestures = _azure()
    gestures["next"] = _did("next", KEYCLOAK, 3.2, field="input#next")
    job.steps[1].cites = ["user-box", "user", "next"]

    assert sign_in_chain(job, gestures)[1].cites == ["user-box", "user", "next"]


LOGIN_HOST = "https://login.example.org"
APP = "https://app.example.org"


def _kmsi(*, enter: bool = False) -> tuple[Workflow, dict[str, Gesture]]:
    """Identifier first, then an accepted password whose page is followed by
    "Stay signed in? Yes" on the same host -- the click that leaves."""
    submit = (
        _did("sign-in", LOGIN_HOST, 4.0, "press", secret=True, field="input#passwd")
        if enter
        else _did("sign-in", LOGIN_HOST, 4.0, field="input#idSIButton9")
    )
    gestures = {
        one.id: one
        for one in (
            _did("u", LOGIN_HOST, 1.0, "type", field="input#loginfmt"),
            _did("next", LOGIN_HOST, 2.0, field="input#idSIButton9"),
            _did("pw", LOGIN_HOST, 3.0, "type", secret=True, field="input#passwd"),
            submit,
            _did("yes", LOGIN_HOST, 6.0, field="input#idSIButton9", to=APP),
        )
    }
    steps = [
        Step(order=n, says=one, system=LOGIN_HOST, cites=[one])
        for n, one in enumerate(("u", "next", "pw", "sign-in", "yes"))
    ]
    job = Workflow(id="wfl_kmsi", tenant="t", title="Log in", narrative="n", steps=steps)
    return job, gestures


def test_an_accepted_submit_followed_by_a_same_host_page_is_kept() -> None:
    """Nothing typed the password again after `Sign in`, so it was not refused:
    the next page (stay signed in, a one-time code, consent) came on the same
    host. Dropping it would click Yes on a password page never submitted."""
    job, gestures = _kmsi()

    assert [step.cites for step in sign_in_chain(job, gestures)] == [
        ["u"],
        ["next"],
        ["pw"],
        ["sign-in"],
        ["yes"],
    ]


def test_an_accepted_enter_followed_by_a_same_host_page_is_kept() -> None:
    job, gestures = _kmsi(enter=True)

    assert ["sign-in"] in [step.cites for step in sign_in_chain(job, gestures)]


@pytest.mark.parametrize(("detail", "kept"), [(0, False), (1, True), (None, True)])
def test_an_enter_that_made_the_submit_click_is_the_same_submit(
    detail: int | None, kept: bool
) -> None:
    job, gestures = _azure()
    gestures["enter"] = _did("enter", KEYCLOAK, 4.5, "press", field="input#password")
    job.steps[2].cites = ["password", "enter"]
    submit = gestures["submit"]
    gestures["submit"] = replace(submit, action=replace(submit.action, detail=detail))

    replayed = {one for step in sign_in_chain(job, gestures) for one in step.cites}

    assert ("enter" in replayed) is kept


def test_a_gesture_cited_by_two_steps_is_replayed_once() -> None:
    """The deployed job cites its first password typing in both `Focus the
    Password field...` and `Type the password.`"""
    job, gestures = _azure()
    job.steps.insert(3, Step(order=5, says="Type it again", system=KEYCLOAK, cites=["password"]))
    job.steps[2].cites = ["password"]
    gestures["pw-box"] = _did("pw-box", KEYCLOAK, 3.5, secret=True, field="input#password")
    job.steps[3].cites = ["pw-box", "password"]

    chain = sign_in_chain(job, gestures)

    replayed = [one for step in chain for one in step.cites]
    assert replayed.count("password") == 1
    assert replayed[-1] == "submit"


@pytest.mark.parametrize("cites", [["pw-box", "submit"], ["submit", "pw-box"]])
def test_a_submit_cited_by_two_steps_is_still_replayed_last(cites: list[str]) -> None:
    """Whichever steps cite the submit that left, it is the last thing
    replayed, and every other gesture those steps cite replays once before it."""
    job, gestures = _azure()
    gestures["pw-box"] = _did("pw-box", KEYCLOAK, 3.5, field="input#password")
    job.steps.append(Step(order=4, says="Focus and sign in", system=KEYCLOAK, cites=cites))

    chain = sign_in_chain(job, gestures)

    replayed = [one for step in chain for one in step.cites]
    assert replayed[-1] == "submit"
    assert sorted(replayed) == sorted(
        ["chooser", "user-box", "user", "password", "pw-box", "submit"]
    )
