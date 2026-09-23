"""Whether a job signs in, decided once from what the operator did.

The rule it replaces read "every cited gesture on one origin" as a sign-in,
which is also every ordinary job done on one warehouse host: a run of `Create
a Customer Type` that lost its page was reported as succeeded with its Save
never pressed. A sign-in is a credential typed and nothing written back.
"""

from __future__ import annotations

from dataclasses import replace

from sro.domain.observation.gesture import Action, Call, Gesture
from sro.domain.skill.checks import signs_in
from sro.domain.skill.workflow import Step, Workflow

KEYCLOAK = "https://keycloak.example"
WMS = "https://wms.example"


def _at(gesture_id: str, url: str, at: float) -> Gesture:
    return Gesture(
        id=gesture_id,
        tenant="acme",
        stream_id="s",
        batch_id="b",
        at=at,
        url=f"{url}/page",
        system=url,
        tab_id=1,
        frame_url=None,
        action=Action(kind="click", at=at),
    )


def _secret(gesture_id: str, url: str, at: float) -> Gesture:
    return replace(_at(gesture_id, url, at), action=Action(kind="type", at=at, secret=True))


def _wrote(gesture_id: str, url: str, at: float, status: int = 201) -> Gesture:
    return replace(
        _at(gesture_id, url, at),
        requests=[Call(method="POST", url=f"{url}/api/things", status=status)],
    )


def _job(*cites: str) -> Workflow:
    return Workflow(
        id="wfl_1",
        tenant="acme",
        title="t",
        narrative="n",
        steps=[
            Step(order=n, says=f"step {n}", system=None, cites=[one]) for n, one in enumerate(cites)
        ],
    )


def test_a_credential_typed_and_nothing_written_is_a_sign_in() -> None:
    """The credential need not be cited: redaction strips it of anything a
    model would point at, so it is read off the job's span."""
    store = {"a": _at("a", KEYCLOAK, 1), "b": _secret("b", KEYCLOAK, 2), "c": _at("c", KEYCLOAK, 3)}

    assert signs_in(_job("a", "c"), store) is True


def test_a_job_on_one_host_that_types_no_credential_does_not_sign_in() -> None:
    """The shape the old rule got wrong: one origin, no password."""
    store = {"a": _at("a", WMS, 1), "b": _at("b", WMS, 2)}

    assert signs_in(_job("a", "b"), store) is False


def test_a_credential_typed_on_the_way_to_a_write_is_not_a_sign_in() -> None:
    """Signed in, then created something: work that happens to start with a
    password."""
    store = {"a": _secret("a", WMS, 1), "b": _wrote("b", WMS, 2)}

    assert signs_in(_job("a", "b"), store) is False


def test_a_credential_post_that_redirects_is_not_business() -> None:
    """A sign-in posts the credential and is sent somewhere else; the post is
    not written back to the page it came from."""
    store = {"a": _secret("a", KEYCLOAK, 1), "b": _wrote("b", KEYCLOAK, 2, status=302)}

    assert signs_in(_job("a", "b"), store) is True


def test_a_job_citing_nothing_anybody_kept_does_not_sign_in() -> None:
    assert signs_in(_job("gone"), {}) is False
