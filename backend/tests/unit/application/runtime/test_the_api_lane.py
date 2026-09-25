import json

import httpx
import pytest

from sro.application.runtime.api_lane import K_AUTH_REFUSED, ApiLane
from sro.domain.shared.hosts import REDACTED
from sro.infrastructure.http.httpx_caller import HttpxCaller
from tests.unit.fakes import FakeHttpCaller, FakePageDriver
from tests.unit.runtime_support import (
    headers_broker,
    lane_context,
    proven_write_step,
    scripted_driver,
)

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


async def test_a_call_refused_while_sending_is_unknown_and_says_only_what_kind() -> None:
    http = FakeHttpCaller()
    http.malformed = True
    step, by_id, ledger = proven_write_step(read_back=LIST)

    result = await ApiLane(http, headers_broker({})).execute(
        step, RUN, lane_context(by_id, ledger=ledger)
    )

    assert result.verdict == "unknown" and not result.never_left
    assert result.reason.endswith("MalformedRequest")
    assert "unsupported protocol" not in result.reason


async def test_a_header_no_request_can_carry_is_refused_before_anything_is_sent() -> None:
    http = FakeHttpCaller()
    step, by_id, ledger = proven_write_step(read_back=LIST)
    warned: list[str] = []

    async def about_to_write() -> None:
        warned.append("write")

    result = await ApiLane(http, headers_broker({"x-csrf-token": "a\r\nb"})).execute(
        step, RUN, lane_context(by_id, ledger=ledger, about_to_write=about_to_write)
    )

    assert result.verdict == "failed" and result.never_left and result.fingerprint
    assert "a\r\nb" not in result.reason
    assert http.sent == [] and warned == []


async def test_a_created_answer_whose_body_cannot_be_decoded_is_unknown() -> None:
    def server(request: httpx.Request) -> httpx.Response:
        return httpx.Response(201, headers={"content-encoding": "gzip"}, content=b"not gzip")

    step, by_id, ledger = proven_write_step(read_back=LIST)

    result = await ApiLane(
        HttpxCaller(transport=httpx.MockTransport(server)), headers_broker({})
    ).execute(step, RUN, lane_context(by_id, ledger=ledger))

    assert result.verdict == "unknown" and not result.never_left


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


@pytest.mark.parametrize(
    "body",
    ['[{"name": "GT1"}]', '[{"name": "GT1", "note": "GT2"}]', "<td>GT20</td>"],
    ids=["another-record", "another-field", "not-json-substring"],
)
async def test_a_read_back_that_does_not_show_the_record_settles_nothing(body: str) -> None:
    http = FakeHttpCaller()
    http.answer(200, body)
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


async def test_the_retry_after_a_fresh_sign_in_carries_the_new_token() -> None:
    http = FakeHttpCaller()
    driver = scripted_driver(url="https://wms.example/app")
    driver.headers = {"x-csrf-token": "before"}
    driver.headers_after_mark = {"x-csrf-token": "after"}
    step, by_id, ledger = proven_write_step(read_back=None)

    await ApiLane(http, headers_broker({}, driver=driver)).execute(
        step, RUN, lane_context(by_id, ledger=ledger, reauthed=True)
    )

    assert http.sent[0]["headers"]["x-csrf-token"] == "after"


async def test_a_token_the_write_needs_that_the_session_lacks_is_refused_before_sending() -> None:
    http = FakeHttpCaller()
    step, by_id, ledger = proven_write_step(
        read_back=LIST,
        request_headers={"Content-Type": "application/json", "X-CSRF-Token": REDACTED},
    )

    result = await ApiLane(http, headers_broker({"x-requested-with": "XMLHttpRequest"})).execute(
        step, RUN, lane_context(by_id, ledger=ledger)
    )

    assert result.verdict == "failed" and result.never_left and result.expired
    assert not result.fingerprint
    assert http.sent == []


async def test_the_session_is_asked_to_wait_for_every_token_the_write_carried() -> None:
    driver = FakePageDriver()
    step, by_id, ledger = proven_write_step(
        read_back=None,
        request_headers={
            "Content-Type": "application/json",
            "X-CSRF-Token": REDACTED,
            "Authorization": REDACTED,
            "X-User-Id": REDACTED,
        },
    )

    await ApiLane(FakeHttpCaller(), headers_broker({}, driver=driver)).execute(
        step, RUN, lane_context(by_id, ledger=ledger)
    )

    assert sorted(driver.needed) == ["authorization", "x-csrf-token"]


async def test_only_representation_headers_come_from_the_recording() -> None:
    http = FakeHttpCaller()
    step, by_id, ledger = proven_write_step(
        read_back=None,
        request_headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-User-Id": "recorder-7",
        },
    )

    await ApiLane(http, headers_broker({})).execute(step, RUN, lane_context(by_id, ledger=ledger))

    assert http.sent[0]["headers"] == {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


async def test_a_read_back_on_another_origin_is_never_sent() -> None:
    http = FakeHttpCaller()
    http.answer(201, "{}")
    step, by_id, ledger = proven_write_step(read_back="https://analytics.example/hit")

    result = await ApiLane(http, headers_broker({})).execute(
        step, RUN, lane_context(by_id, ledger=ledger)
    )

    assert result.verdict == "unknown"
    assert len(http.sent) == 1


async def test_a_read_back_addressed_by_the_recorded_record_reads_this_runs_record() -> None:
    http = FakeHttpCaller()
    http.answer(201, "{}")
    http.answer(200, '{"name": "GT2"}')
    step, by_id, ledger = proven_write_step(read_back="/api/customer-types/{name}")

    result = await ApiLane(http, headers_broker({})).execute(
        step, RUN, lane_context(by_id, ledger=ledger)
    )

    assert result.verdict == "done"
    assert http.sent[1]["url"] == "https://wms.example/api/customer-types/GT2"


async def test_a_read_back_naming_the_recorded_value_inside_a_segment_is_not_sent() -> None:
    http = FakeHttpCaller()
    http.answer(201, "{}")
    step, by_id, ledger = proven_write_step(read_back="/api/customer-types?name={name}")

    result = await ApiLane(http, headers_broker({})).execute(
        step, RUN, lane_context(by_id, ledger=ledger)
    )

    assert result.verdict == "unknown"
    assert len(http.sent) == 1


async def test_a_redirect_off_the_host_is_in_doubt_and_asks_for_a_fresh_session() -> None:
    http = FakeHttpCaller()
    http.answer(302, "", headers={"location": "https://idp.example/login"})
    step, by_id, ledger = proven_write_step(read_back=LIST)

    result = await ApiLane(http, headers_broker({})).execute(
        step, RUN, lane_context(by_id, ledger=ledger)
    )

    assert result.verdict == "unknown" and result.expired and not result.never_left
    assert len(http.sent) == 1


async def test_a_redirect_on_the_same_host_is_in_doubt_but_the_session_stands() -> None:
    http = FakeHttpCaller()
    http.answer(303, "", headers={"location": "/app/customer-types/ct-9"})
    step, by_id, ledger = proven_write_step(read_back=LIST)

    result = await ApiLane(http, headers_broker({})).execute(
        step, RUN, lane_context(by_id, ledger=ledger)
    )

    assert result.verdict == "unknown" and not result.expired
