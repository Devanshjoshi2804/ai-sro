"""The two ways a model-backed route says no before it spends anything."""

from __future__ import annotations

import pytest
from fastapi import FastAPI, HTTPException, status
from fastapi.testclient import TestClient

from sro.application.execution.call_run_wrong import NotYours as _WrongNotYours
from sro.application.execution.revise_run import NotYours as _ReviseNotYours
from sro.application.ports.model import AskerUnavailable
from sro.application.shared.refusals import OverCap
from sro.interface.http.errors import install_error_handlers


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
        ("gemini_mine_model", "gemini-3.1-pro-preview"),
        ("gemini_plan_model", "gemini-3.8-flash"),
        ("gemini_rescue_model", "gemini-3.1-pro-preview"),
    ],
)
def test_the_three_model_names_are_the_rigs(name: str, expected: str) -> None:
    """Rule 4: `new_agent_arch/src/rig/config.py` lines 20, 41 and 45 are the
    measured choices -- the pro model truncates a plan and the flash model
    cannot rescue one. A drift here is a different system wearing the same
    numbers.

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
