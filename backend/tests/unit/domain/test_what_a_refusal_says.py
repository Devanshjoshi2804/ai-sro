"""What a system answered is kept for the run's step, the chat and the
sender's draft: never more than its message, or the first line of a page."""

from __future__ import annotations

import pytest

from sro.domain.execution.records import told_by

JWT = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.abcdefghijklmnopqrstu"


def test_a_text_body_keeps_its_first_line_and_no_token() -> None:
    said = told_by(500, f"Upstream refused Bearer {JWT}\nat db-3.corp.internal:5432", "text/plain")

    assert JWT not in said["said"] and "db-3" not in said["said"]
    assert said["said"].startswith("Upstream refused")


def test_a_bare_jwt_first_line_is_scrubbed() -> None:
    assert JWT not in told_by(401, f"token {JWT} expired\nsecond line", "text/plain")["said"]


@pytest.mark.parametrize("kind", ["text/html", None])
def test_an_html_error_page_keeps_only_its_heading(kind: str | None) -> None:
    page = (
        "<html><body><h1>502 Bad Gateway</h1><p>upstream db-3.corp.internal:5432 refused</p>"
        "<pre>at com.acme.Pool.get(Pool.java:88)</pre></body></html>"
    )

    assert told_by(502, page, kind)["said"] == "502 Bad Gateway"


def test_json_without_a_message_key_says_nothing_of_its_body() -> None:
    body = '{"trace": "at com.acme.Pool.get(Pool.java:88)", "host": "db-3.internal"}'

    assert told_by(500, body)["said"] == ""
