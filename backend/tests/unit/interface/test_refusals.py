"""The two ways a model-backed route says no before it spends anything."""

from __future__ import annotations

import pytest
from fastapi import FastAPI, HTTPException, status
from fastapi.testclient import TestClient

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
