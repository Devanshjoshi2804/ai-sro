"""What to call each system a demonstration reached.

`systems` decides three things: whether a version is a workflow at all, which
breakers stop it, and -- through the run -- which system's stored session each
step of it is allowed to use. All three are wrong if two systems arrive under
one name, and the name for a host nobody connected is derived from the host
itself: `sap.acme.com` derives `acme`, which is also what somebody is likely to
have called their WMS connection.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sro.application.capture.identity import systems_touched
from sro.domain.connection.connection import Connection, ConnectionId
from sro.domain.recording.recording import Recording
from tests import factories as f


def _connection(system: str, base_url: str) -> Connection:
    connection = Connection(
        id=ConnectionId(f"con-{system}"),
        tenant_id=f.TENANT,
        name=system,
        target_system=system,
        base_url=base_url,
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    connection.authenticated(datetime(2026, 1, 2, tzinfo=UTC))
    return connection


def _touching(*urls: str) -> Recording:
    recording = f.recording(frames=0)
    for index, url in enumerate(urls):
        recording.append_frame(f.frame(index=index, requests=(f.request(url=url),)))
    return recording


def test_a_connected_host_is_called_what_the_operator_called_it() -> None:
    connections = [_connection("blue_yonder", "https://wms.acme.com/portal")]

    assert systems_touched(connections, _touching("https://wms.acme.com/api/waves")) == (
        "blue_yonder",
    )


def test_a_portal_and_its_api_are_one_system() -> None:
    """Two hosts deriving one name is ordinary and they merge -- otherwise every
    single-system skill whose API answers on another name would look like a
    workflow, and be refused for want of a browser."""
    assert systems_touched(
        [], _touching("https://wms.acme.com/screen", "https://api.acme.com/waves")
    ) == ("acme",)


def test_a_second_system_is_not_swallowed_by_the_first_one_s_name() -> None:
    """The bug this exists for.

    `sap.acme.com` derives `acme`; the WMS connection is called `acme` too. One
    name means: not a workflow, so no browser required and no second breaker --
    and every credential keyed to the WMS resolved and sent to the ERP.
    """
    connections = [_connection("acme", "https://wms.acme.com/portal")]

    named = systems_touched(
        connections,
        _touching("https://wms.acme.com/api/waves", "https://sap.acme.com/api/receipts"),
    )

    assert named == ("acme", "sap.acme.com")
    assert len(named) > 1, "the version would not have been treated as a workflow"


def test_the_host_stands_in_only_for_the_system_nobody_connected() -> None:
    """The connected one keeps its name: that name is what the breaker, the
    vault scope and the objective key all use."""
    connections = [
        _connection("acme", "https://wms.acme.com/portal"),
        _connection("finance", "https://sap.acme.com/portal"),
    ]

    assert systems_touched(
        connections,
        _touching("https://wms.acme.com/api/waves", "https://sap.acme.com/api/receipts"),
    ) == ("acme", "finance")
