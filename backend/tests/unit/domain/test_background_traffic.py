"""Beacons fire on a timer, so no step is ever *about* one.

Two runs of one task recorded against Blue Yonder differed only in that one
run's search step happened to catch a `webPerformanceEntries/batch` call, which
became that step's primary request. The diff compares runs step by step and
refused the pair. Nothing about the demonstration diverged; the browser's own
telemetry did.
"""

from __future__ import annotations

from tests import factories as f

KEEPALIVE = "https://wms.example.com/refs/data/api/v1/rp/admin/sessionKeepAlive"
ADJUST = "https://wms.example.com/data/WM/wm/inventory/adjust?reasonCode=AA"


def test_a_beacon_is_never_the_call_a_step_is_about() -> None:
    frame = f.frame(
        requests=(
            f.request(request_id="beacon", started_at=f.at(11), url=KEEPALIVE),
            f.request(request_id="adjust", started_at=f.at(12), url=ADJUST),
        )
    )

    assert frame.primary_request is not None
    assert frame.primary_request.request_id == "adjust"


def test_a_step_that_caught_only_a_beacon_has_no_primary_request() -> None:
    frame = f.frame(requests=(f.request(request_id="beacon", url=KEEPALIVE),))

    assert frame.primary_request is None, "otherwise the matching step in the other run diverges"
    assert len(frame.requests) == 1, "the evidence still holds it verbatim"


def test_parallel_reads_pick_the_same_call_in_both_runs() -> None:
    """One gesture, several reads, and the arrival order is a race."""
    items = "https://wms.example.com/data/WM/wm/inventoryItems?expand=x"
    locations = "https://wms.example.com/data/WM/wm/inventoryLocations?showFourWallOnly=true"

    run_a = f.frame(
        requests=(
            f.request(request_id="a1", method="GET", started_at=f.at(11), url=items),
            f.request(request_id="a2", method="GET", started_at=f.at(12), url=locations),
        )
    )
    run_b = f.frame(
        requests=(
            f.request(request_id="b1", method="GET", started_at=f.at(11), url=locations),
            f.request(request_id="b2", method="GET", started_at=f.at(12), url=items),
        )
    )

    assert run_a.primary_request is not None and run_b.primary_request is not None
    assert run_a.primary_request.url.split("?")[0] == run_b.primary_request.url.split("?")[0]
