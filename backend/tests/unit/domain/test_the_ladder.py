from sro.domain.execution.lanes import (
    Broken,
    Lane,
    SeenCall,
    StepResult,
    fingerprint_of,
    lanes_for,
    never_left_step,
    write_confirmed,
)
from sro.domain.observation.gesture import Call


def test_a_browser_step_with_a_proven_call_starts_on_the_api_lane() -> None:
    assert lanes_for(2, tool=False, api=True, browser=True, broken=()) == (
        Lane.API,
        Lane.UI,
        Lane.SIGHT,
    )


def test_a_mail_step_is_a_tool_call_and_never_a_tab() -> None:
    assert lanes_for(0, tool=True, api=True, browser=True, broken=()) == (Lane.TOOL,)


def test_a_step_starts_on_the_first_lane_still_trusted() -> None:
    broken = (Broken(2, Lane.API, "f1"), Broken(3, Lane.UI, "f2"))
    assert lanes_for(2, tool=False, api=True, browser=True, broken=broken) == (
        Lane.UI,
        Lane.SIGHT,
    )


def test_a_step_whose_lanes_are_all_broken_still_offers_sight() -> None:
    broken = (
        Broken(2, Lane.API, "f1"),
        Broken(2, Lane.UI, "f2"),
        Broken(2, Lane.SIGHT, "f3"),
    )
    assert lanes_for(2, tool=False, api=True, browser=True, broken=broken) == (Lane.SIGHT,)


def test_the_page_s_own_call_confirms_a_write() -> None:
    recorded = Call(method="POST", url="https://wms.example/api/customer-types")
    seen = [SeenCall("POST", "https://wms.example/api/customer-types", 201)]
    rejected = [SeenCall("POST", "https://wms.example/api/customer-types", 409)]

    assert write_confirmed(recorded=recorded, wanted={201}, calls=seen) == "done"
    assert write_confirmed(recorded=recorded, wanted={201}, calls=rejected) == "failed"
    assert write_confirmed(recorded=recorded, wanted={201}, calls=[]) is None


def test_a_success_before_a_later_failure_is_still_done() -> None:
    recorded = Call(method="POST", url="https://wms.example/api/customer-types")
    calls = [
        SeenCall("POST", "https://wms.example/api/customer-types", 201),
        SeenCall("POST", "https://wms.example/api/customer-types", 409),
    ]
    assert write_confirmed(recorded=recorded, wanted={201}, calls=calls) == "done"


def test_a_gateway_5xx_with_no_success_is_unknown_not_failed() -> None:
    recorded = Call(method="POST", url="https://wms.example/api/customer-types")
    calls = [SeenCall("POST", "https://wms.example/api/customer-types", 504)]
    assert write_confirmed(recorded=recorded, wanted={201}, calls=calls) == "unknown"


def test_a_4xx_with_no_success_is_failed() -> None:
    recorded = Call(method="POST", url="https://wms.example/api/customer-types")
    calls = [SeenCall("POST", "https://wms.example/api/customer-types", 409)]
    assert write_confirmed(recorded=recorded, wanted={201}, calls=calls) == "failed"


def test_never_left_is_true_only_when_no_attempt_left() -> None:
    left = StepResult(verdict="failed", lane=Lane.UI, never_left=False)
    stayed = StepResult(verdict="failed", lane=Lane.API, never_left=True)

    assert never_left_step((stayed,))
    assert not never_left_step((stayed, left))
    assert never_left_step(())


def test_a_fingerprint_is_stable_and_names_its_lane() -> None:
    assert fingerprint_of(Lane.UI, "control_not_found", "css") == fingerprint_of(
        Lane.UI, "control_not_found", "css"
    )
    assert fingerprint_of(Lane.UI, "x") != fingerprint_of(Lane.API, "x")
