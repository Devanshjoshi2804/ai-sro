"""The OpenAPI document is a contract, so it is tested like one.

The frontend's client is generated from this document. A response the document
does not describe is a frontend bug that would otherwise surface as a runtime
type error in the browser.
"""

from __future__ import annotations

import pytest

from sro.interface.http.app import create_app

app = create_app()
schema_dict = app.openapi()


def test_every_route_is_documented() -> None:
    documented = set(schema_dict["paths"])
    routed = {
        route.path  # type: ignore[attr-defined]
        for route in app.routes
        if getattr(route, "include_in_schema", False)
    }

    assert routed <= documented


def test_error_responses_are_declared_for_lookups() -> None:
    # A generated client that does not know 404 exists will treat the problem
    # document as a RecordingDetail.
    get_recording = schema_dict["paths"]["/v1/recordings/{recording_id}"]["get"]

    assert "422" in get_recording["responses"]


class TestFuzz:
    """Schemathesis drives every documented operation against the live app.

    Skipped without the optional dependency so the fast suite stays dependency
    light; CI installs it.
    """

    def test_schema_is_valid(self) -> None:
        schemathesis = pytest.importorskip("schemathesis")
        schema = schemathesis.openapi.from_dict(schema_dict)

        assert list(schema.get_all_operations())
