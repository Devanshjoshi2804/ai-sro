"""What a demonstration proves besides the thing it was about.

The trap here is enthusiasm. A screen reads its subject and then reads three
things named after its subject, and claiming all of them gives an operator four
"List transport mode" skills to choose between -- worse than none, because now
somebody has to pick.
"""

from __future__ import annotations

from sro.application.induction.capabilities import normalise, reads_about
from sro.domain.recording.events import ActionFrame
from tests import factories as f

HOST = "https://wms.test/data/WM/wm"


def _read(index: int, resource: str, rows: int, status: int = 200) -> ActionFrame:
    body = '{"@type":"Wrapper","data":[' + ",".join(['{"id":1}'] * rows) + "]}"
    return f.frame(
        index=index,
        requests=(
            f.request(
                method="GET",
                url=f"{HOST}/{resource}?siteId=SG",
                status=status,
                response_body=f.Body(text=body, size_bytes=len(body), mime_type="application/json"),
            ),
        ),
    )


def test_the_subject_wins_over_everything_named_after_it() -> None:
    """The bug this was written for.

    `warehouseTransportModeUoms` contains `transportmode`, is a list of unit
    conversions, and was empty. It sorted first, and the skill built from it
    told the operator there were 0 transport modes while seventeen were on
    screen.
    """
    frames = (
        _read(0, "warehouseTransportModeUoms", rows=0),
        _read(1, "warehouseTransportModes", rows=17),
    )

    best = reads_about(frames, "transport_mode")[0]

    assert best.entity == "warehouseTransportModes"
    assert best.rows == 17


def test_calls_about_something_else_are_not_claimed() -> None:
    """A screen fetches its policies before it shows anything. That is not a
    capability anybody asked for."""
    frames = (_read(0, "policies", rows=4), _read(1, "warehouseTransportModes", rows=2))

    assert [read.entity for read in reads_about(frames, "transport_mode")] == [
        "warehouseTransportModes"
    ]


def test_a_failed_read_proves_nothing() -> None:
    assert reads_about((_read(0, "transportModes", rows=0, status=403),), "transport_mode") == ()


def test_a_name_is_reduced_to_its_subject() -> None:
    assert normalise("warehouseTransportModes") == "transportmode"
    assert normalise("transport_mode") == "transportmode"
    assert normalise("transportModes") == "transportmode"
