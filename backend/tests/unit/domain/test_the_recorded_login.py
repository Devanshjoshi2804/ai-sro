"""Which recorded login a server-side sign-in borrows its username from.

The one that starts on the system's own page, when there is one; otherwise the
only tagged sign-in job that carries a credential at all. Two candidates and
no way to tell them apart is not a choice to make on somebody's account.
"""

from __future__ import annotations

from sro.domain.observation.gesture import Action, Gesture, Target
from sro.domain.skill.signing_in import recorded_login
from sro.domain.skill.workflow import Step, Workflow

SYSTEM = "https://wms.example.com"


def _typed(gesture_id: str, at: float, origin: str, *, value: str | None, secret: bool) -> Gesture:
    return Gesture(
        id=gesture_id,
        tenant="acme",
        stream_id="s",
        batch_id="b",
        at=at,
        url=f"{origin}/login",
        system=origin,
        tab_id=1,
        frame_url=None,
        action=Action(
            kind="type", at=at, value=value, url=f"{origin}/login", target=Target(secret=secret)
        ),
    )


def _job(job_id: str, *cites: str) -> Workflow:
    return Workflow(
        id=job_id,
        tenant="acme",
        title=job_id,
        narrative="n",
        steps=[Step(order=n, says="s", system=None, cites=[one]) for n, one in enumerate(cites)],
        signs_in=True,
    )


STORE = {
    "a-user": _typed("a-user", 1.0, "https://a.example.com", value="alice", secret=False),
    "a-pass": _typed("a-pass", 2.0, "https://a.example.com", value=None, secret=True),
    "b-user": _typed("b-user", 1.0, "https://b.example.com", value="bob", secret=False),
    "b-pass": _typed("b-pass", 2.0, "https://b.example.com", value=None, secret=True),
    "s-user": _typed("s-user", 1.0, SYSTEM, value="sam", secret=False),
    "s-pass": _typed("s-pass", 2.0, SYSTEM, value=None, secret=True),
}


def test_the_only_credential_carrying_job_is_the_one() -> None:
    found = recorded_login(f"{SYSTEM}/portal", [_job("a", "a-user", "a-pass")], STORE)

    assert found is not None
    assert (found.origin, found.username) == ("a.example.com", "alice")


def test_two_candidates_and_nothing_to_choose_between_them_is_none() -> None:
    among = [_job("a", "a-user", "a-pass"), _job("b", "b-user", "b-pass")]

    assert recorded_login(f"{SYSTEM}/portal", among, STORE) is None


def test_the_job_starting_on_the_systems_own_page_wins() -> None:
    among = [_job("a", "a-user", "a-pass"), _job("s", "s-user", "s-pass")]

    found = recorded_login(f"{SYSTEM}/portal", among, STORE)

    assert found is not None
    assert found.username == "sam"


def test_a_job_with_no_credential_in_it_lends_nothing() -> None:
    assert recorded_login(f"{SYSTEM}/portal", [_job("a", "a-user")], STORE) is None
