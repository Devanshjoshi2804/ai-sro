from sro.domain.execution.lanes import (
    Broken,
    Lane,
    SeenCall,
    after_matches,
    fingerprint_of,
    lanes_for,
    write_confirmed,
)
from sro.domain.observation.gesture import AfterState, Call


def test_a_browser_step_with_a_proven_call_starts_on_the_api_lane() -> None:
    assert lanes_for(2, tool=False, api=True, browser=True, broken=()) == (
        Lane.API,
        Lane.UI,
        Lane.SIGHT,
    )


def test_a_mail_step_is_a_tool_call_and_never_a_tab() -> None:
    assert lanes_for(0, tool=True, api=False, browser=False, broken=()) == (Lane.TOOL,)


def test_a_step_starts_on_the_first_lane_still_trusted() -> None:
    broken = (Broken(2, Lane.API, "f1"), Broken(3, Lane.UI, "f2"))
    assert lanes_for(2, tool=False, api=True, browser=True, broken=broken) == (
        Lane.UI,
        Lane.SIGHT,
    )


def test_the_page_s_own_call_confirms_a_write() -> None:
    recorded = Call(method="POST", url="https://wms.example/api/customer-types")
    seen = [SeenCall("POST", "https://wms.example/api/customer-types", 201)]
    rejected = [SeenCall("POST", "https://wms.example/api/customer-types", 409)]

    assert write_confirmed(recorded=recorded, wanted={201}, calls=seen) == "done"
    assert write_confirmed(recorded=recorded, wanted={201}, calls=rejected) == "failed"
    assert write_confirmed(recorded=recorded, wanted={201}, calls=[]) is None


def test_the_after_state_is_checked_against_this_run_s_value() -> None:
    recorded = AfterState(value="GT1", visible=True, enabled=True)

    assert after_matches(recorded, AfterState("GT2", True, True), value="GT2")
    assert not after_matches(recorded, AfterState("GT1", True, True), value="GT2")
    assert not after_matches(None, AfterState("GT2", True, True), value="GT2")


def test_a_fingerprint_is_stable_and_names_its_lane() -> None:
    assert fingerprint_of(Lane.UI, "control_not_found", "css") == fingerprint_of(
        Lane.UI, "control_not_found", "css"
    )
    assert fingerprint_of(Lane.UI, "x") != fingerprint_of(Lane.API, "x")
