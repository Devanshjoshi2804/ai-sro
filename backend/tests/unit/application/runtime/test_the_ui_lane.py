from sro.application.ports.page import PageAnswer
from sro.application.runtime.ui_lane import UiLane
from sro.domain.execution.lanes import SeenCall
from sro.domain.observation.gesture import AfterState
from tests.unit.runtime_support import lane_context, save_step, scripted_driver, type_step


async def test_a_write_the_page_confirms_is_done_with_no_model_and_no_sleep() -> None:
    driver = scripted_driver(
        answer=PageAnswer(ok=True, matched_by="component"),
        calls=[SeenCall("POST", "https://wms.example/api/customer-types", 201, '{"id": "ct-9"}')],
    )
    step, by_id = save_step(status=201)
    written: list[int] = []

    async def wrote() -> None:
        written.append(step.order)

    ctx = lane_context(by_id, about_to_write=wrote)

    result = await UiLane(driver).execute(step, {"Customer Type": "GT2"}, ctx)

    assert (result.verdict, result.lane.value) == ("done", "ui")
    assert result.read == {"id": "ct-9"}
    assert written == [step.order]


async def test_a_write_nothing_confirms_is_unknown_never_done() -> None:
    driver = scripted_driver(answer=PageAnswer(ok=True, matched_by="css_path"), calls=[])
    step, by_id = save_step(status=201)

    result = await UiLane(driver).execute(step, {}, lane_context(by_id))

    assert result.verdict == "unknown"


async def test_a_typed_value_is_confirmed_by_the_state_it_left() -> None:
    driver = scripted_driver(answer=PageAnswer(ok=True, matched_by="attributes"), holds=True)
    step, by_id = type_step(after=AfterState(value="GT1", visible=True, enabled=True))

    result = await UiLane(driver).execute(step, {"Customer Type": "GT2"}, lane_context(by_id))

    assert result.verdict == "done"
    assert driver.waited_for[-1]["expect"] == {"value": "GT2", "visible": True, "enabled": True}


async def test_a_missing_control_on_a_sign_in_page_is_an_expired_session() -> None:
    driver = scripted_driver(
        answer=PageAnswer(ok=False, error_kind="control_not_found"),
        sign_in=True,
        url="https://idp.example/login",
    )
    step, by_id = save_step(status=201)

    result = await UiLane(driver).execute(step, {}, lane_context(by_id))

    assert result.expired and result.verdict == "failed"


async def test_a_password_form_on_the_recorded_page_itself_is_not_an_expired_session() -> None:
    driver = scripted_driver(
        answer=PageAnswer(ok=False, error_kind="control_not_found"),
        sign_in=True,
        url="https://wms.example/app",
    )
    step, by_id = save_step(status=201)

    result = await UiLane(driver).execute(step, {}, lane_context(by_id))

    assert not result.expired and result.verdict == "failed"


async def test_a_page_that_never_settled_before_any_write_never_left() -> None:
    driver = scripted_driver(
        answer=PageAnswer(ok=False, error_kind="control_not_found"), unsettled=True
    )
    step, by_id = type_step()

    result = await UiLane(driver).execute(step, {}, lane_context(by_id))

    assert result.verdict == "failed" and result.never_left


async def test_a_page_that_never_settled_after_about_to_write_is_unknown() -> None:
    driver = scripted_driver(
        answer=PageAnswer(ok=False, error_kind="control_not_found"), unsettled=True
    )
    step, by_id = save_step(status=201)

    result = await UiLane(driver).execute(step, {}, lane_context(by_id))

    assert result.verdict == "unknown" and not result.never_left


async def test_a_missing_control_is_fingerprinted_for_the_known_broken_list() -> None:
    driver = scripted_driver(answer=PageAnswer(ok=False, error_kind="control_not_found"))
    step, by_id = save_step(status=201)

    result = await UiLane(driver).execute(step, {}, lane_context(by_id))

    assert result.verdict == "failed" and result.fingerprint
