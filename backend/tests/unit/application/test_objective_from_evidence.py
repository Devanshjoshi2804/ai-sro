"""The task names itself from what it did, so the operator types only a URL."""

from __future__ import annotations

from sro.application.capture.identity import derive_objective_key
from sro.domain.shared.objective import Direction
from tests import factories as f

ADJUST = "https://bf56-kms-wms-web-np2.jdadelivers.com/data/WM/wm/inventory/adjust?siteId=SG"
LOOKUP = "https://bf56-kms-wms-web-np2.jdadelivers.com/data/WM/wm/inventoryItems?siteId=SG"


def _adjustment() -> tuple:
    return (
        f.frame(0, requests=(f.request(method="GET", url=LOOKUP),)),
        f.frame(1, requests=(f.request(method="PUT", url=ADJUST),)),
    )


async def test_the_call_the_task_ended_on_names_the_task() -> None:
    key = derive_objective_key(_adjustment(), system="blue_yonder")

    assert key is not None
    assert key.slug() == "blue_yonder/SG/inventory/internal/adjust"


async def test_the_facility_comes_from_the_parameter_every_call_carried() -> None:
    key = derive_objective_key(_adjustment())

    assert key is not None
    assert key.facility == "SG"
    assert key.target_system == "jdadelivers", "no connection was named, so the host stands in"


async def test_a_task_that_asked_the_server_nothing_names_itself_nothing() -> None:
    silent = (f.frame(0, requests=()),)

    assert derive_objective_key(silent) is None


async def test_a_read_only_task_is_named_by_its_method() -> None:
    frames = (f.frame(0, requests=(f.request(method="GET", url=LOOKUP),)),)

    key = derive_objective_key(frames, system="blue_yonder")

    assert key is not None
    assert key.objective_type == "view"
    assert key.entity_type == "inventory_item"


async def test_a_record_id_in_the_path_never_names_the_task() -> None:
    frames = (
        f.frame(
            0,
            requests=(f.request(method="POST", url="https://wms.test/api/waves/W-8817/release"),),
        ),
    )

    key = derive_objective_key(frames, system="blue_yonder")

    assert key is not None
    assert key.entity_type == "wave"
    assert key.objective_type == "release"
    assert key.direction is Direction.OUTBOUND


async def test_a_keepalive_landing_on_a_step_never_names_the_task() -> None:
    frames = (
        f.frame(
            0,
            requests=(
                f.request(request_id="beacon", method="POST", url="https://wms.test/rum/keepalive"),
                f.request(method="PUT", url=ADJUST),
            ),
        ),
    )

    key = derive_objective_key(frames, system="blue_yonder")

    assert key is not None
    assert key.entity_type == "inventory"
