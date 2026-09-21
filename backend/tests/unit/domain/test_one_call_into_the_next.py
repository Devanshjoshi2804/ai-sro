"""A value out of one write's answer and into the next write's body.

Composition, one level below where item 7 has been looking. There is no chain
between two mined jobs -- 306 ordered pairs on the deployment, none -- but the
platform does this behind every cascade create, and the research capture holds
the exchange: `POST /wm/clients` carries `addressId: A000365896`, which no
operator typed and `POST /wm/addresses` answered with
(`knowledge-base/KNOWLEDGE-BASE.md` 3b).

The fixtures here are that cascade, with the shapes and the field names the
capture really has.
"""

from __future__ import annotations

import json

from sro.domain.execution.cascade import flows_in, writes_of
from sro.domain.execution.verified_writes import VerifiedWrite
from sro.domain.observation.gesture import Action, Body, Call, Gesture

WMS = "https://wms.test"
ADDRESSES = f"{WMS}/data/WM/wm/addresses"
CLIENTS = f"{WMS}/data/WM/wm/clients"

LEDGER = (
    VerifiedWrite(method="POST", path_pattern="/data/WM/wm/addresses"),
    VerifiedWrite(method="POST", path_pattern="/data/WM/wm/clients"),
)


def _call(
    method: str,
    url: str,
    sent: dict[str, object] | None = None,
    back: dict[str, object] | None = None,
    status: int = 201,
) -> Call:
    said = json.dumps(sent) if sent is not None else None
    answered = json.dumps({"@type": "ResponseBodyWrapper", "data": back}) if back else None
    return Call(
        method=method,
        url=url,
        status=status,
        started_at=1.0,
        request_body=None if said is None else Body(text=said, size_bytes=len(said)),
        response_body=None if answered is None else Body(text=answered, size_bytes=len(answered)),
    )


def _save(*calls: Call) -> Gesture:
    """One click on Save, and everything the page fired from it."""
    return Gesture(
        id="ges-save",
        tenant="acme",
        stream_id="s",
        batch_id="b",
        at=100.0,
        url=f"{WMS}/clients",
        system=WMS,
        tab_id=1,
        frame_url=None,
        action=Action(kind="click", at=100.0, url=f"{WMS}/clients"),
        requests=list(calls),
    )


def _the_client_cascade() -> Gesture:
    return _save(
        _call("POST", ADDRESSES, {"addressName": "ZV Batt Sup Addr"}, {"addressId": "A000365896"}),
        _call(
            "POST",
            CLIENTS,
            {"clientId": "ZV097223", "addressId": "A000365896"},
            {"clientId": "ZV097223"},
        ),
    )


def test_the_second_write_carrying_the_first_answer_is_the_flow() -> None:
    (flow,) = flows_in(_the_client_cascade())

    assert flow.key == "addressId"
    assert flow.into == "addressId"
    assert flow.made_at == "POST /data/WM/wm/addresses"
    assert flow.used_at == "POST /data/WM/wm/clients"


def test_the_flow_is_found_by_value_and_never_by_the_name() -> None:
    """The two bodies name it themselves. A rule that matched `addressId` to
    `addressId` would be the correspondence `write_plan` refuses -- and would
    miss a platform that calls the same id two things."""
    doing = _save(
        _call("POST", ADDRESSES, {"addressName": "x"}, {"resourceId": "A000365896"}),
        _call("POST", CLIENTS, {"addressId": "A000365896"}, None),
    )

    (flow,) = flows_in(doing)

    assert (flow.key, flow.into) == ("resourceId", "addressId")


def test_a_value_the_operator_typed_into_both_is_not_a_flow() -> None:
    """The whole rule. A form that posts back what somebody typed is their
    value coming round again, and an edit that PUTs a record it has just read
    carries the entire record back."""
    doing = _save(
        _call("POST", ADDRESSES, {"clientId": "ZV097223"}, {"clientId": "ZV097223"}),
        _call("POST", CLIENTS, {"clientId": "ZV097223"}, None),
    )

    assert flows_in(doing) == []


def test_a_value_typed_before_the_answer_carried_it_is_not_a_flow() -> None:
    """Measured on the deployment: `RKUCHIYAGM` is the operator's own username,
    stamped onto a create's answer by the warehouse. Read without this it is a
    work-area job producing a value the login job takes."""
    doing = _save(
        _call("POST", ADDRESSES, {"addressName": "x"}, {"lastModifiedBy": "RKUCHIYAGM"}),
        _call("POST", CLIENTS, {"userId": "RKUCHIYAGM"}, None),
    )

    assert flows_in(doing, {"RKUCHIYAGM": 1.0}) == []
    # And without the typing evidence it is only what it looks like.
    assert len(flows_in(doing)) == 1


def test_a_read_answers_nothing_anybody_can_depend_on() -> None:
    """A confirming read answers with the record that was just sent, and its
    own request has no body to subtract. Counted as a producer it makes every
    typed value the warehouse's own work -- which is the defect `995a0b53`
    fixed one layer up."""
    doing = _save(
        _call("GET", ADDRESSES, None, {"addressId": "A000365896"}, status=200),
        _call("POST", CLIENTS, {"addressId": "A000365896"}, None),
    )

    assert flows_in(doing) == []


def test_a_beacon_is_not_one_of_the_writes() -> None:
    """The same click fires keepalives and telemetry. Counting those makes
    every real write look like a cascade."""
    doing = _save(
        _call("POST", ADDRESSES, {"addressName": "x"}, {"addressId": "A1"}),
        _call("POST", f"{WMS}/data/WM/wm/webPerformanceEntries/batch", {"t": "1"}, None, 200),
    )

    assert [call.url for call in writes_of(doing, LEDGER)] == [ADDRESSES]
    assert len(writes_of(doing)) == 2, "without a ledger, every mutation counts"


def test_one_write_alone_flows_into_nothing() -> None:
    assert flows_in(_save(_call("POST", CLIENTS, {"clientId": "ZV1"}, {"clientId": "ZV1"}))) == []


def test_a_short_value_carries_no_dependency() -> None:
    """`SG` is the site and it is in every body on this platform."""
    doing = _save(
        _call("POST", ADDRESSES, {"addressName": "x"}, {"warehouseId": "SG"}),
        _call("POST", CLIENTS, {"warehouseId": "SG"}, None),
    )

    assert flows_in(doing) == []
