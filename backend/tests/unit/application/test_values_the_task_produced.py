"""An id the system minted mid-task is not a constant to replay.

The diff sees what varies between two runs, so a record id the server assigned
during the demonstration is invisible to it: each run got its own, and the
value each one sent onward was whatever that run's server said. Left as a
literal, every replay writes to the record the demonstration happened to create.
"""

from __future__ import annotations

import json

from sro.application.induction.diff import parameterise
from sro.application.induction.sites import JsonBodySite, UrlPathSite
from sro.domain.recording.events import ActionFrame, ActionKind, InputAction
from sro.domain.recording.network import Body
from sro.domain.skill.parameter import ParameterKind
from tests import factories as f

CREATE = "https://wms.test/data/WM/wm/suppliers"
SITE = "https://wms.test/data/WM/wm/addresses?siteId=SG"


def _create(index: int, address_id: str) -> ActionFrame:
    """A Save whose response hands back the address the system just allocated."""
    return f.frame(
        index=index,
        action=InputAction(kind=ActionKind.CLICK, target=f.fingerprint(accessible_name="Save")),
        requests=(
            f.request(
                method="POST",
                url=CREATE,
                status=201,
                request_body=Body(text=json.dumps({"data": {"name": "Acme"}})),
                response_body=Body(text=json.dumps({"data": {"addressId": address_id}})),
            ),
        ),
    )


def _use(index: int, address_id: str) -> ActionFrame:
    """A later call that sends that address back, in the path and the body."""
    return f.frame(
        index=index,
        action=InputAction(kind=ActionKind.CLICK, target=f.fingerprint(accessible_name="Address")),
        requests=(
            f.request(
                method="PUT",
                url=f"https://wms.test/data/WM/wm/addresses/{address_id}?siteId=SG",
                status=200,
                request_body=Body(
                    text=json.dumps({"data": {"addressId": address_id, "state": "ON"}})
                ),
            ),
        ),
    )


def test_a_value_the_system_minted_is_bound_to_the_call_that_returned_it() -> None:
    result = parameterise(
        (_create(0, "A1"), _use(1, "A1")),
        (_create(0, "A2"), _use(1, "A2")),
    )

    derived = [p for p in result.parameters if p.kind is ParameterKind.DERIVED]
    assert [(p.source_step_index, p.source_pointer) for p in derived] == [(0, "/data/addressId")]
    assert set(result.for_step(1)) == {UrlPathSite(4), JsonBodySite("/data/addressId")}


def test_the_same_id_in_both_runs_is_still_bound_to_where_it_came_from() -> None:
    """The point of this pass: nothing varies, so the diff alone sees nothing."""
    result = parameterise(
        (_create(0, "A1"), _use(1, "A1")),
        (_create(0, "A1"), _use(1, "A1")),
    )

    derived = [p for p in result.parameters if p.kind is ParameterKind.DERIVED]
    assert [(p.source_step_index, p.source_pointer) for p in derived] == [(0, "/data/addressId")]


def test_a_value_the_operator_already_had_is_not_called_derived() -> None:
    """A facility code echoed back by a response was not produced by it."""
    lookup = f.frame(
        index=0,
        action=InputAction(kind=ActionKind.CLICK, target=f.fingerprint(accessible_name="Site")),
        requests=(
            f.request(
                method="GET",
                url=SITE,
                status=200,
                response_body=Body(text=json.dumps({"data": {"siteId": "SG"}})),
            ),
        ),
    )
    write = f.frame(
        index=1,
        action=InputAction(kind=ActionKind.CLICK, target=f.fingerprint(accessible_name="Save")),
        requests=(
            f.request(
                method="POST",
                url=CREATE,
                status=201,
                request_body=Body(text=json.dumps({"data": {"siteId": "SG"}})),
            ),
        ),
    )

    result = parameterise((lookup, write), (lookup, write))

    assert [p for p in result.parameters if p.kind is ParameterKind.DERIVED] == []


def test_a_value_sitting_in_a_lookup_list_is_not_a_dependency() -> None:
    """Row 44 of a list of addresses is a coincidence, not a source.

    The supplier task matched "CAN" against the country of the forty-fifth
    address on a lookup screen. Position in a collection is not stable between
    runs, so the pointer that found it would not find it again.
    """
    lookup = f.frame(
        index=0,
        action=InputAction(kind=ActionKind.CLICK, target=f.fingerprint(accessible_name="Country")),
        requests=(
            f.request(
                method="GET",
                url=SITE,
                status=200,
                response_body=Body(
                    text=json.dumps({"data": [{"countryName": "USA"}, {"countryName": "CAN"}]})
                ),
            ),
        ),
    )
    write = f.frame(
        index=1,
        action=InputAction(kind=ActionKind.CLICK, target=f.fingerprint(accessible_name="Save")),
        requests=(
            f.request(
                method="POST",
                url=CREATE,
                status=201,
                request_body=Body(text=json.dumps({"data": {"countryName": "CAN"}})),
            ),
        ),
    )

    result = parameterise((lookup, write), (lookup, write))

    assert [p for p in result.parameters if p.kind is ParameterKind.DERIVED] == []


def test_a_body_field_the_response_calls_something_else_stays_a_literal() -> None:
    """Where a value is sent under a name, the response has to use that name.

    Agreement on the system's own vocabulary is the evidence. A URL path segment
    has no name to agree on, so it rests on the value being unique in the
    response and held by nobody beforehand -- which is why the path below still
    binds while the body field does not.
    """
    minted = f.frame(
        index=0,
        action=InputAction(kind=ActionKind.CLICK, target=f.fingerprint(accessible_name="Save")),
        requests=(
            f.request(
                method="POST",
                url=CREATE,
                status=201,
                response_body=Body(text=json.dumps({"data": {"somethingElse": "A1"}})),
            ),
        ),
    )

    result = parameterise((minted, _use(1, "A1")), (minted, _use(1, "A1")))

    assert JsonBodySite("/data/addressId") not in result.for_step(1)
    assert UrlPathSite(4) in result.for_step(1)
