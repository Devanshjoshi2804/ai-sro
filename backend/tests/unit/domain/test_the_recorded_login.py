"""Which recorded login a server-side sign-in borrows its username from.

The tagged sign-in job that lands on the connection's own system. A system no
job lands on has no recorded login: one system's login is never lent to
another, where its password would be typed into the wrong form. Two jobs
landing on one system and nothing to tell them apart is not a choice to make
on somebody's account.
"""

from __future__ import annotations

from sro.domain.observation.gesture import Action, Gesture, PageMark, Target
from sro.domain.skill.signing_in import Logins, recorded_login, recorded_logins
from sro.domain.skill.workflow import Step, Workflow

A = "https://a.example.com"
B = "https://b.example.com"
C = "https://c.example.com"
IDP = "https://login.example.com"


def _gesture(gesture_id: str, stream: str, at: float, origin: str, action: Action) -> Gesture:
    return Gesture(
        id=gesture_id,
        tenant="acme",
        stream_id=stream,
        batch_id="b",
        at=at,
        url=f"{origin}/page",
        system=origin,
        tab_id=1,
        frame_url=None,
        action=action,
    )


def _sign_in(name: str, user: str | None, lands: str, *, at: float = 1.0) -> dict[str, Gesture]:
    typed = Target(tag="input", name="username")
    secret = Target(tag="input", name="password", secret=True)
    submit = _gesture(f"{name}-go", name, at + 2, IDP, Action(kind="click", at=at + 2))
    submit.page_events.append(PageMark(at=at + 2.5, page_kind="load", url=f"{lands}/home"))
    return {
        f"{name}-user": _gesture(
            f"{name}-user", name, at, IDP, Action(kind="type", at=at, value=user, target=typed)
        ),
        f"{name}-pass": _gesture(
            f"{name}-pass", name, at + 1, IDP, Action(kind="type", at=at + 1, target=secret)
        ),
        f"{name}-go": submit,
        f"{name}-there": _gesture(
            f"{name}-there", name, at + 3, lands, Action(kind="click", at=at + 3)
        ),
    }


def _job(name: str, *, cites: tuple[str, ...] = ("user", "pass", "go")) -> Workflow:
    return Workflow(
        id=name,
        tenant="acme",
        title=name,
        narrative="n",
        steps=[
            Step(order=n, says="s", system=None, cites=[f"{name}-{one}"])
            for n, one in enumerate(cites)
        ],
        signs_in=True,
    )


STORE = {**_sign_in("a", "alice", A), **_sign_in("b", "bob", B)}


def test_each_system_gets_the_sign_in_that_lands_on_it() -> None:
    among = [_job("a"), _job("b")]

    for system, job, user in ((A, "a", "alice"), (B, "b", "bob")):
        found = recorded_login(f"{system}/portal", among, STORE)
        assert found is not None
        assert (found.job_id, found.origin, found.username) == (job, "login.example.com", user)


def test_a_system_no_sign_in_lands_on_gets_none() -> None:
    assert recorded_login(f"{C}/portal", [_job("a"), _job("b")], STORE) is None


def test_the_only_sign_in_the_tenant_has_is_not_lent_to_another_system() -> None:
    assert recorded_login(f"{B}/portal", [_job("a")], STORE) is None


def test_two_sign_ins_landing_on_one_system_and_nothing_to_choose_between_them_is_none() -> None:
    store = {**_sign_in("a", "alice", A), **_sign_in("b", "bob", A, at=100.0)}

    assert recorded_login(f"{A}/portal", [_job("a"), _job("b")], store) is None


def test_a_job_with_no_credential_in_it_lends_nothing() -> None:
    assert recorded_login(f"{A}/portal", [_job("a", cites=("user", "go"))], STORE) is None


def test_the_logins_are_each_system_s_recorded_username_and_the_box_it_was_typed_in() -> None:
    """Never a value a work job typed before re-entering a password: a job that
    types GT7 and then signs in again (session expired, username prefilled)
    would otherwise make GT7 a login for every job of the tenant."""
    work = {
        "w-code": _gesture(
            "w-code", "w", 50.0, A, Action(kind="type", at=50.0, value="GT7", target=Target())
        ),
        "w-pass": _gesture(
            "w-pass",
            "w",
            51.0,
            IDP,
            Action(kind="type", at=51.0, target=Target(tag="input", name="password", secret=True)),
        ),
    }
    worked = Workflow(
        id="w",
        tenant="acme",
        title="Create a Customer Type",
        narrative="n",
        steps=[Step(order=0, says="s", system=None, cites=list(work))],
    )

    found = recorded_logins([_job("a"), _job("b"), worked], {**STORE, **work})

    assert found == Logins(names=frozenset({"alice", "bob"}), labels=frozenset({"username"}))
