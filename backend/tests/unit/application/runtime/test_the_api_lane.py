import json

import pytest

from sro.application.runtime.api_lane import K_AUTH_REFUSED, ApiLane
from tests.unit.fakes import FakeHttpCaller, FakePageDriver
from tests.unit.runtime_support import headers_broker, lane_context, proven_write_step

LIST = "/api/customer-types"
WRITE = "https://wms.example/api/customer-types"
RUN = {"Customer Type": "GT2"}


async def test_a_replayed_write_confirmed_by_its_read_back_is_done() -> None:
    http = FakeHttpCaller()
    http.answer(201, '{"id": "ct-9"}')
    http.answer(200, '{"name": "GT2"}')
    step, by_id, ledger = proven_write_step(read_back=LIST)
    ctx = lane_context(by_id, ledger=ledger)

    result = await ApiLane(http, headers_broker({"cookie": "sid=1", "x-csrf-token": "t"})).execute(
        step, RUN, ctx
    )

    assert result.verdict == "done"
    assert http.sent[0]["headers"]["x-csrf-token"] == "t"
    assert http.sent[0]["headers"]["cookie"] == "sid=1"
    assert json.loads(str(http.sent[0]["body"])) == {"name": "GT2"}
    assert [one["method"] for one in http.sent] == ["POST", "GET"]


async def test_the_broker_is_asked_with_the_full_request_url() -> None:
    http = FakeHttpCaller()
    driver = FakePageDriver()
    step, by_id, ledger = proven_write_step(read_back=None)

    await ApiLane(http, headers_broker({}, driver=driver)).execute(
        step, RUN, lane_context(by_id, ledger=ledger)
    )

    assert ("cookies_for", "sess-1", WRITE) in driver.calls


async def test_a_recorded_header_the_session_also_names_is_sent_once() -> None:
    http = FakeHttpCaller()
    step, by_id, ledger = proven_write_step(read_back=None)

    await ApiLane(http, headers_broker({"content-type": "application/json; v=2"})).execute(
        step, RUN, lane_context(by_id, ledger=ledger)
    )

    assert http.sent[0]["headers"] == {"content-type": "application/json; v=2"}


@pytest.mark.parametrize("status", sorted(K_AUTH_REFUSED), ids=lambda status: f"refused-{status}")
async def test_a_refused_session_asks_for_a_fresh_one(status: int) -> None:
    http = FakeHttpCaller()
    http.answer(status, "")
    step, by_id, ledger = proven_write_step(read_back=LIST)

    result = await ApiLane(http, headers_broker({})).execute(
        step, RUN, lane_context(by_id, ledger=ledger)
    )

    assert result.expired and result.verdict == "failed"
    assert len(http.sent) == 1


async def test_a_rejected_replay_hands_the_step_to_the_ui_lane() -> None:
    http = FakeHttpCaller()
    http.answer(400, '{"error": "bad"}')
    step, by_id, ledger = proven_write_step(read_back=LIST)

    result = await ApiLane(http, headers_broker({})).execute(
        step, RUN, lane_context(by_id, ledger=ledger)
    )

    assert result.verdict == "failed" and not result.expired and result.fingerprint
    assert len(http.sent) == 1


async def test_a_server_error_on_a_write_is_in_doubt_not_failed() -> None:
    http = FakeHttpCaller()
    http.answer(502, "")
    step, by_id, ledger = proven_write_step(read_back=LIST)

    result = await ApiLane(http, headers_broker({})).execute(
        step, RUN, lane_context(by_id, ledger=ledger)
    )

    assert result.verdict == "unknown"
    assert len(http.sent) == 1


async def test_a_write_with_no_read_back_is_unknown() -> None:
    http = FakeHttpCaller()
    http.answer(201, "{}")
    step, by_id, ledger = proven_write_step(read_back=None)

    result = await ApiLane(http, headers_broker({})).execute(
        step, RUN, lane_context(by_id, ledger=ledger)
    )

    assert result.verdict == "unknown"


async def test_a_read_back_without_the_value_leaves_the_write_unknown() -> None:
    http = FakeHttpCaller()
    http.answer(201, "{}")
    http.answer(200, '[{"name": "GT1"}]')
    step, by_id, ledger = proven_write_step(read_back=LIST)

    result = await ApiLane(http, headers_broker({})).execute(
        step, RUN, lane_context(by_id, ledger=ledger)
    )

    assert result.verdict == "unknown"


async def test_a_call_lost_on_the_way_is_unknown() -> None:
    http = FakeHttpCaller()
    http.unreachable = True
    step, by_id, ledger = proven_write_step(read_back=LIST)

    result = await ApiLane(http, headers_broker({})).execute(
        step, RUN, lane_context(by_id, ledger=ledger)
    )

    assert result.verdict == "unknown"


async def test_a_call_that_could_not_be_built_never_left() -> None:
    http = FakeHttpCaller()
    http.malformed = True
    step, by_id, ledger = proven_write_step(read_back=LIST)

    result = await ApiLane(http, headers_broker({})).execute(
        step, RUN, lane_context(by_id, ledger=ledger)
    )

    assert result.verdict == "failed" and result.never_left and result.fingerprint


async def test_a_write_the_ledger_never_watched_is_not_sent() -> None:
    http = FakeHttpCaller()
    step, by_id, _ = proven_write_step(read_back=LIST)
    warned: list[str] = []

    async def about_to_write() -> None:
        warned.append("write")

    result = await ApiLane(http, headers_broker({})).execute(
        step, RUN, lane_context(by_id, ledger=(), about_to_write=about_to_write)
    )

    assert result.verdict == "failed" and result.never_left
    assert http.sent == [] and warned == []


async def test_a_read_back_settles_an_unknown_write() -> None:
    http = FakeHttpCaller()
    http.answer(200, '[{"name": "GT1"}, {"name": "GT2"}]')
    step, by_id, ledger = proven_write_step(read_back=LIST)

    settled = await ApiLane(http, headers_broker({})).read_back(
        step, RUN, lane_context(by_id, ledger=ledger)
    )

    assert settled == "done"
    assert http.sent[0]["method"] == "GET"


async def test_a_read_back_that_does_not_show_the_value_settles_nothing() -> None:
    http = FakeHttpCaller()
    http.answer(200, '[{"name": "GT1"}]')
    step, by_id, ledger = proven_write_step(read_back=LIST)

    settled = await ApiLane(http, headers_broker({})).read_back(
        step, RUN, lane_context(by_id, ledger=ledger)
    )

    assert settled is None


async def test_a_value_found_in_another_field_does_not_confirm_the_write() -> None:
    http = FakeHttpCaller()
    http.answer(201, "{}")
    http.answer(200, '[{"name": "GT1", "note": "GT2"}]')
    step, by_id, ledger = proven_write_step(read_back=LIST)

    result = await ApiLane(http, headers_broker({})).execute(
        step, RUN, lane_context(by_id, ledger=ledger)
    )

    assert result.verdict == "unknown"


async def test_a_success_the_recording_never_saw_is_not_taken_as_done() -> None:
    http = FakeHttpCaller()
    http.answer(200, "{}")
    http.answer(200, '[{"name": "GT2"}]')
    step, by_id, ledger = proven_write_step(read_back=LIST)

    result = await ApiLane(http, headers_broker({})).execute(
        step, RUN, lane_context(by_id, ledger=ledger)
    )

    assert result.verdict == "unknown"
    assert len(http.sent) == 1
