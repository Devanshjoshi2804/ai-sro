"""The two ways a model-backed route says no before it spends anything."""

from __future__ import annotations

import pytest
from fastapi import FastAPI, HTTPException, status
from fastapi.testclient import TestClient

from sro.application.execution.call_run_wrong import NotYours as _WrongNotYours
from sro.application.execution.revise_run import NotYours as _ReviseNotYours
from sro.application.ports.model import AskerUnavailable
from sro.application.shared.refusals import OverCap
from sro.interface.http.errors import _problem, install_error_handlers


def _app_that_raises(exc: Exception) -> TestClient:
    app = FastAPI()
    install_error_handlers(app)

    @app.get("/boom")
    async def boom() -> None:
        raise exc

    return TestClient(app, raise_server_exceptions=False)


def test_no_asker_is_a_dependency_problem_and_not_the_callers_fault() -> None:
    response = _app_that_raises(AskerUnavailable("no model is configured")).get("/boom")

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["detail"] == "no model is configured"


def test_the_cap_is_429_and_carries_the_sentence_that_says_which_number_stopped_it() -> None:
    said = "daily cap reached: $5.0100 of $5.00 spent today, 0 unpriced call(s)"

    response = _app_that_raises(OverCap(said)).get("/boom")

    assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    # The title and slug matter as much as the status: a client that renders
    # `problem.title` showed "Error" for every 429 until 429 was in the table,
    # and `problem.type` is how the console tells one refusal from another.
    body = response.json()
    assert body["title"] == "Too many requests"
    assert body["type"] == "https://ai-sro.dev/problems/over_cap"
    assert body["detail"] == said


def test_a_bare_429_still_has_a_slug_and_not_error() -> None:
    """`OverCap` never reads `_SLUGS`: it brings its own `code`. The only
    reader is `_http_problem`, so without this the 429 slug could be deleted
    and every suite stayed green -- the same hole, in the same table, that the
    entry was added to close for 401."""
    app = FastAPI()
    install_error_handlers(app)

    @app.get("/limited")
    async def limited() -> None:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "slow down")

    body = TestClient(app, raise_server_exceptions=False).get("/limited").json()

    assert body["type"] == "https://ai-sro.dev/problems/too_many_requests"
    assert body["title"] == "Too many requests"


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("gemini_mine_model", "gemini-3.8-flash"),
        ("gemini_plan_model", "gemini-3.8-flash"),
        ("gemini_rescue_model", "gemini-3.1-pro-preview"),
    ],
)
def test_the_three_model_names_are_the_rigs(name: str, expected: str) -> None:
    """Rule 4: `new_agent_arch/src/rig/config.py` lines 41 and 45 are the
    measured choices -- the pro model truncates a plan and the flash model
    cannot rescue one. A drift there is a different system wearing the same
    numbers.

    **The mine model is deliberately no longer the rig's**, and it is the one
    of the three that was measured HERE rather than inherited: pro and flash
    over identical copies of the deployed store, 2026-09-21, both proposing
    zero new jobs, pro at twice the price and straddling its own timeout. The
    reasoning is in `config.gemini_mine_model`. This line is still the guard
    it always was -- a change to any of the three has to come with a
    measurement, and changing it without one turns this red.

    `_env_file=None` like every other Settings assertion in this suite: the
    default is what is being asserted, and a developer with the name in their
    own `.env` must not turn that into a red suite.
    """
    from sro.config import Settings

    assert getattr(Settings(_env_file=None), name) == expected


def test_the_mine_model_is_not_the_interpreters() -> None:
    """They hold the same string today and answer different questions. One
    setting serving two purposes means re-tuning one silently re-tunes the
    other."""
    from sro.config import Settings

    fields = Settings.model_fields
    assert "gemini_mine_model" in fields
    assert "gemini_interpreter_model" in fields


def test_a_run_that_is_not_yours_is_a_403_and_not_a_500() -> None:
    """Both classes named `NotYours`, on both doors that raise one.

    Neither is a `DomainError`, so `install_error_handlers`'s blanket line does
    not reach them and neither did anything else: `NotYours` sat in
    `_STATUS_BY_ERROR` at 403 while no handler was registered for it, and
    `revise_run.NotYours` was in neither. Measured before the fix -- both
    answered **500 in text/plain**, so a caller who is simply not the person a
    run was performed for was told the server broke, on
    `POST /v1/runs/{run_id}/wrong` and `POST /v1/runs/{run_id}/values`.

    Parametrised over both on purpose: they are separate classes with one name
    in two modules, and fixing the one that was already in the table would have
    left the other exactly as broken.

    And the `type` as well as the status. Neither class carried a `code`, so
    `_problem` fell back to `error` and the 403 they were finally given was
    untellable from every other refusal in the system -- which is the failure
    `_SLUGS` exists to have removed once already. One `code`, shared: two doors,
    one refusal to the same person, and a console matching on `problem.type`
    should not have to learn two spellings of it.
    """
    for raised in (_WrongNotYours, _ReviseNotYours):
        response = _app_that_raises(raised("that run is not yours")).get("/boom")

        assert response.status_code == status.HTTP_403_FORBIDDEN, raised.__module__
        assert response.headers["content-type"].startswith("application/problem+json")
        assert response.json()["detail"] == "that run is not yours"
        assert response.json()["type"].endswith("/not_yours"), raised.__module__


def test_every_mapped_error_names_a_problem_type_a_reader_could_look_up() -> None:
    """RFC 9457 §3.1.1: when `type` is a locator, "dereferencing it should
    provide human-readable documentation for the problem type".

    So a URI under `/problems/` is a promise that a documented kind of problem
    lives there. Seven mapped errors carried no `code` and answered
    `.../problems/error` -- a locator pointing at the absence of a kind, which
    is a page that can never be written. Among them were the two the operator
    is most likely to meet: no model configured, and no usable secret store.
    """
    from sro.interface.http.errors import _STATUS_BY_ERROR

    uncoded = sorted(e.__name__ for e in _STATUS_BY_ERROR if not getattr(e, "code", ""))

    assert not uncoded, f"these answer .../problems/error, which documents nothing: {uncoded}"


def test_an_error_with_no_code_says_about_blank_rather_than_inventing_a_kind() -> None:
    """The spec's own value for "adds no semantics beyond the status code".

    Unreached by anything mapped -- the test above keeps it that way -- so this
    guards the next error type somebody adds and forgets to give a code. It must
    tell that reader nothing, rather than tell them a lie.
    """

    class _Nameless(Exception):
        """No `code`, deliberately."""

    # Registered by hand: an UNregistered exception never reaches `_problem` at
    # all -- it raises through to Starlette as a 500 in text/plain, which is the
    # separate defect two shipped doors carried until `0302584`. This test is
    # about what `_problem` renders, so it has to be reached.
    app = FastAPI()
    install_error_handlers(app)
    app.add_exception_handler(_Nameless, _problem)

    @app.get("/nameless")
    async def nameless() -> None:
        raise _Nameless("something went wrong")

    body = TestClient(app, raise_server_exceptions=False).get("/nameless").json()

    assert body["type"] == "about:blank"
    assert body["detail"] == "something went wrong"


def test_every_mapped_error_is_also_registered_so_its_status_can_fire() -> None:
    """A status with no handler is a 500, and so is a handler with no status.

    `_STATUS_BY_ERROR` decides WHAT a refusal answers; `install_error_handlers`
    decides WHETHER anything gets to ask. Writing one half without the other
    changes nothing observable, which is how `NotYours`, `NotYoursToRevise`,
    `DispatchFailed` and `UiUnavailable` each spent their whole lives answering
    `500 text/plain` with a correct entry sitting in the table above them. This
    walks the MRO the way `_status_for` does, so a subclass registered through
    its base counts -- that is exactly why `DomainError` needs no per-subclass
    line.
    """
    from sro.interface.http.errors import _STATUS_BY_ERROR

    app = FastAPI()
    install_error_handlers(app)
    registered = set(app.exception_handlers)

    unreachable = sorted(
        error.__name__
        for error in _STATUS_BY_ERROR
        if not any(klass in registered for klass in error.__mro__)
    )

    assert not unreachable, f"these answer 500 whatever the table says: {unreachable}"


def test_a_browser_that_cannot_be_reached_is_a_conflict_and_not_a_broken_server() -> None:
    """`AnswerConfirmation.approve` calls the same `start_for` that
    `FireTrigger` guards and does not guard it, so an operator tapping Approve
    on a card whose laptop is closed was told the server broke -- on the one
    door in the system whose whole job is a person authorising an unattended
    write. 409 and not 503, because this deployment is fine: the same tap
    succeeds when the laptop opens.
    """
    from sro.application.ports.dispatch import DispatchFailed

    response = _app_that_raises(DispatchFailed("this process cannot reach a browser")).get("/boom")

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.headers["content-type"].startswith("application/problem+json")
    body = response.json()
    assert body["type"] == "https://ai-sro.dev/problems/dispatch_failed"
    assert body["detail"] == "this process cannot reach a browser"


def test_the_four_port_failures_are_503_rather_than_500() -> None:
    """Each is caught at every call site that exists today and at no call site
    that does not, which is why `UiUnavailable` escaped `vision_step.py`'s one
    unguarded `perform_at` to `POST /v1/skills/{id}/batch` while a reviewer
    tracing catch clauses rather than call sites cleared it. Mapped here, the
    next call site outside a guard is a 503 instead of a 500.
    """
    from sro.application.ports.http import TargetUnreachable
    from sro.application.ports.tools import ToolsUnavailable
    from sro.application.ports.ui import UiUnavailable
    from sro.application.ports.vision import VisionUnavailable

    for raised, slug in (
        (TargetUnreachable, "target_unreachable"),
        (ToolsUnavailable, "tools_unavailable"),
        (UiUnavailable, "ui_unavailable"),
        (VisionUnavailable, "vision_unavailable"),
    ):
        response = _app_that_raises(raised("nothing answered")).get("/boom")

        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE, raised.__name__
        assert response.json()["type"].endswith(f"/{slug}"), raised.__name__
        assert response.json()["title"] == "Dependency unavailable", raised.__name__
