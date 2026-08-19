"""The OpenAPI document is a contract, so it is tested like one.

The frontend's client is generated from this document. A response the document
does not describe is a frontend bug that would otherwise surface as a runtime
type error in the browser.

The route-collecting here is more work than it looks like it should be, and the
reason is why this file was rewritten: it used to filter ``app.routes`` on
``getattr(route, "include_in_schema", False)``. On this version of FastAPI the
top level holds routers rather than routes, so that expression collected nothing
at all -- and the assertion became ``set() <= documented``, which cannot fail.
The contract test guarding forty endpoints had been passing without looking at
any of them.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.routing import APIRoute
from starlette.routing import BaseRoute

from sro.interface.http.app import create_app

app = create_app()
schema_dict = app.openapi()


def _served(routes: list[BaseRoute], prefix: str = "") -> Iterator[tuple[str, APIRoute]]:
    """Every operation the app actually serves, at the path it serves it on.

    Included routers keep their own routes and the prefix they were mounted
    under, so the full path only exists once the two are put back together.
    """
    for route in routes:
        context: Any = getattr(route, "include_context", None)
        if context is not None:
            yield from _served(context.included_router.routes, prefix + (context.prefix or ""))
        elif isinstance(route, APIRoute):
            yield prefix + route.path, route


def test_every_route_is_documented() -> None:
    routed = {path for path, route in _served(app.routes) if route.include_in_schema}

    assert routed, "the collector found no routes, which is how this test used to pass"
    assert routed <= set(schema_dict["paths"])


def test_error_responses_are_declared_for_lookups() -> None:
    """A generated client that does not know 404 exists will treat the problem
    document as a RecordingDetail.

    ``422`` is what this used to assert, and FastAPI generates that one for any
    operation with parameters -- so it held whatever the code did.
    """
    get_recording = schema_dict["paths"]["/v1/recordings/{recording_id}"]["get"]

    assert "404" in get_recording["responses"]


class TestFuzz:
    """Schemathesis drives every documented operation against the live app.

    Skipped without the optional dependency so the fast suite stays dependency
    light; CI installs it.
    """

    # Schemathesis builds an ASGI transport per call and does not close it, so
    # the garbage collector raises a ResourceWarning that pytest escalates.
    # About the test harness, not about the app.
    @pytest.mark.filterwarnings("ignore::ResourceWarning")
    @pytest.mark.filterwarnings("ignore::pytest.PytestUnraisableExceptionWarning")
    def test_every_operation_answers_within_its_contract(self) -> None:
        """It used to assert that the list of operations was non-empty and send
        no request, so nothing was driven and nothing was checked. Driving them
        found that every 401 answered `{"detail": ...}` rather than the problem
        document every other failure answers with.

        Ids that do not exist, deliberately: without a database this cannot
        exercise the success paths, and what it is checking is that a failure
        is shaped the way the document says it is -- which is exactly what a
        generated client breaks on.
        """
        schemathesis = pytest.importorskip("schemathesis")
        schema = schemathesis.openapi.from_dict(schema_dict)
        schema.app = app

        for operation in schema.get_all_operations():
            ready = operation.ok()
            case = ready.Case(
                path_parameters=dict.fromkeys(re.findall(r"{(\w+)}", ready.path), "no-such-thing")
            )
            case.validate_response(case.call(app=app))
