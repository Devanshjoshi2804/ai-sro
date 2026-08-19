"""The task names itself from what it did, so the operator types only a URL."""

from __future__ import annotations

from typing import Any

from sro.application.capture.identity import derive_objective_key
from sro.domain.recording.events import ActionFrame, ActionKind, InputAction
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


WMS = "https://bf56-kms-wms-web-np2.jdadelivers.com/data/WM/wm"


def _clicking(index: int, name: str, **overrides: Any) -> ActionFrame:
    return f.frame(
        index=index,
        action=InputAction(kind=ActionKind.CLICK, target=f.fingerprint(accessible_name=name)),
        requests=overrides.pop("requests", ()),
        **overrides,
    )


async def test_the_screen_says_which_of_four_writes_was_the_task() -> None:
    """One Save posted an address, the client, its warehouse link and a packing
    configuration. Taking the last named the demonstration after a child row --
    `create packing_configuration` for a task the operator would call creating a
    client, and which nothing afterwards could find by asking for clients.

    The screen is not an inference: they clicked a control that says Clients.
    """
    frames = (
        _clicking(0, "Clients"),
        _clicking(
            1,
            "Save",
            requests=(
                f.request(method="POST", url=f"{WMS}/addresses?siteId=SG"),
                f.request(method="POST", url=f"{WMS}/clients?siteId=SG"),
                f.request(method="POST", url=f"{WMS}/clientWarehouse?siteId=SG"),
                f.request(method="POST", url=f"{WMS}/packingConfigurations?siteId=SG"),
            ),
        ),
    )

    key = derive_objective_key(frames, system="blue_yonder")

    assert key is not None
    assert key.entity_type == "client"
    assert key.objective_type == "create"


async def test_a_paragraph_the_operator_read_never_names_the_task() -> None:
    """Only labels vote. The help text on that screen names every warehouse noun
    there is, and letting it count would name the task after whatever was on the
    page rather than after what was clicked."""
    frames = (
        _clicking(
            0,
            "Clients use third party logistics providers 3PL to provide "
            "logistics-related services such as receiving, storage and shipping",
        ),
        _clicking(
            1,
            "Save",
            requests=(
                f.request(method="POST", url=f"{WMS}/addresses?siteId=SG"),
                f.request(method="POST", url=f"{WMS}/packingConfigurations?siteId=SG"),
            ),
        ),
    )

    key = derive_objective_key(frames, system="blue_yonder")

    assert key is not None
    assert key.entity_type == "packing_configuration", "the last write, as before"
