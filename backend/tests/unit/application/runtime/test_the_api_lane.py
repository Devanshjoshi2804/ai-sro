import json
from dataclasses import replace

import httpx
import pytest

from sro.application.runtime.api_lane import K_AUTH_REFUSED, ApiLane
from sro.domain.execution.lanes import Lane, StepResult
from sro.domain.execution.verified_writes import VerifiedWrite
from sro.domain.observation.gesture import Action, Call, Gesture, Target
from sro.domain.shared.hosts import REDACTED
from sro.domain.skill.workflow import Step
from sro.infrastructure.http.httpx_caller import HttpxCaller
from tests.unit.fakes import FakeHttpCaller, FakePageDriver
from tests.unit.runtime_support import (
    WORKFLOW,
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

    result = await ApiLane(
        headers_broker({"cookie": "sid=1", "x-csrf-token": "t"}, http=http)
    ).execute(step, RUN, ctx)

    assert result.verdict == "done"
    assert http.sent[0]["headers"]["x-csrf-token"] == "t"
    assert http.sent[0]["headers"]["cookie"] == "sid=1"
    assert json.loads(str(http.sent[0]["body"])) == {"name": "GT2"}
    assert [one["method"] for one in http.sent] == ["POST", "GET"]


async def test_a_write_on_a_cookie_only_system_waits_for_no_token() -> None:
    http = FakeHttpCaller()
    http.answer(201, '{"id": "ct-9"}')
    http.answer(200, '{"name": "GT2"}')
    step, by_id, ledger = proven_write_step(read_back=LIST)
    driver = FakePageDriver()

    result = await ApiLane(headers_broker({"cookie": "sid=1"}, driver=driver, http=http)).execute(
        step, RUN, lane_context(by_id, ledger=ledger)
    )

    assert result.verdict == "done"
    assert driver.waited_out == []


async def test_the_broker_is_asked_with_the_full_request_url() -> None:
    http = FakeHttpCaller()
    driver = FakePageDriver()
    step, by_id, ledger = proven_write_step(read_back=None)

    await ApiLane(headers_broker({}, driver=driver, http=http)).execute(
        step, RUN, lane_context(by_id, ledger=ledger)
    )

    assert ("cookies_for", "sess-1", WRITE) in driver.calls


async def test_a_recorded_header_the_session_also_names_is_sent_once() -> None:
    http = FakeHttpCaller()
    step, by_id, ledger = proven_write_step(read_back=None)

    await ApiLane(headers_broker({"content-type": "application/json; v=2"}, http=http)).execute(
        step, RUN, lane_context(by_id, ledger=ledger)
    )

    assert http.sent[0]["headers"] == {"content-type": "application/json; v=2"}


@pytest.mark.parametrize("status", sorted(K_AUTH_REFUSED), ids=lambda status: f"refused-{status}")
async def test_a_refused_session_asks_for_a_fresh_one(status: int) -> None:
    http = FakeHttpCaller()
    http.answer(status, "")
    step, by_id, ledger = proven_write_step(read_back=LIST)

    result = await ApiLane(headers_broker({}, http=http)).execute(
        step, RUN, lane_context(by_id, ledger=ledger)
    )

    assert result.expired and result.verdict == "failed"
    assert len(http.sent) == 1


@pytest.mark.parametrize("status", sorted(K_AUTH_REFUSED), ids=lambda status: f"refused-{status}")
async def test_a_refusal_after_a_fresh_sign_in_is_the_lanes_own_failure(status: int) -> None:
    http = FakeHttpCaller()
    http.answer(status, "")
    step, by_id, ledger = proven_write_step(read_back=LIST)

    driver = scripted_driver(url="https://wms.example/app")

    result = await ApiLane(headers_broker({}, driver=driver, http=http)).execute(
        step, RUN, lane_context(by_id, ledger=ledger, reauthed=True)
    )

    assert result.verdict == "failed" and not result.expired and result.fingerprint


async def test_a_rejected_replay_hands_the_step_to_the_ui_lane() -> None:
    http = FakeHttpCaller()
    http.answer(400, '{"error": "bad"}')
    step, by_id, ledger = proven_write_step(read_back=LIST)

    result = await ApiLane(headers_broker({}, http=http)).execute(
        step, RUN, lane_context(by_id, ledger=ledger)
    )

    assert result.verdict == "failed" and not result.expired and result.fingerprint
    assert result.never_left, "a refused write was never made"
    assert len(http.sent) == 1


async def test_a_conflicting_replay_is_in_doubt_and_never_handed_on() -> None:
    http = FakeHttpCaller()
    http.answer(409, '{"error": "exists"}')
    step, by_id, ledger = proven_write_step(read_back=LIST)

    result = await ApiLane(headers_broker({}, http=http)).execute(
        step, RUN, lane_context(by_id, ledger=ledger)
    )

    assert result.verdict == "unknown" and not result.never_left
    assert _sent_once(http)


async def test_a_server_error_on_a_write_is_in_doubt_not_failed() -> None:
    http = FakeHttpCaller()
    http.answer(502, "")
    step, by_id, ledger = proven_write_step(read_back=LIST)

    result = await ApiLane(headers_broker({}, http=http)).execute(
        step, RUN, lane_context(by_id, ledger=ledger)
    )

    assert result.verdict == "unknown"
    assert _sent_once(http)


def _sent_once(http: FakeHttpCaller) -> bool:
    methods = [one["method"] for one in http.sent]
    return methods[0] == "POST" and set(methods[1:]) <= {"GET"}


async def test_a_write_with_no_read_back_is_unknown() -> None:
    http = FakeHttpCaller()
    http.answer(201, "{}")
    step, by_id, ledger = proven_write_step(read_back=None)

    result = await ApiLane(headers_broker({}, http=http)).execute(
        step, RUN, lane_context(by_id, ledger=ledger)
    )

    assert result.verdict == "unknown"


async def test_a_read_back_without_the_value_leaves_the_write_unknown() -> None:
    http = FakeHttpCaller()
    http.answer(201, "{}")
    http.answer(200, '[{"name": "GT1"}]')
    step, by_id, ledger = proven_write_step(read_back=LIST)

    result = await ApiLane(headers_broker({}, http=http)).execute(
        step, RUN, lane_context(by_id, ledger=ledger)
    )

    assert result.verdict == "unknown"


async def test_a_call_lost_on_the_way_is_unknown() -> None:
    http = FakeHttpCaller()
    http.unreachable = True
    step, by_id, ledger = proven_write_step(read_back=LIST)

    result = await ApiLane(headers_broker({}, http=http)).execute(
        step, RUN, lane_context(by_id, ledger=ledger)
    )

    assert result.verdict == "unknown"


async def test_a_call_refused_while_sending_is_unknown_and_says_only_what_kind() -> None:
    http = FakeHttpCaller()
    http.malformed = True
    step, by_id, ledger = proven_write_step(read_back=LIST)

    result = await ApiLane(headers_broker({}, http=http)).execute(
        step, RUN, lane_context(by_id, ledger=ledger)
    )

    assert result.verdict == "unknown" and not result.never_left
    assert result.reason.endswith("MalformedRequest")
    assert "unsupported protocol" not in result.reason


async def test_a_header_no_request_can_carry_is_refused_before_anything_is_sent() -> None:
    http = FakeHttpCaller()
    step, by_id, ledger = proven_write_step(read_back=LIST)
    warned: list[str] = []

    async def about_to_write(lane: Lane) -> None:
        warned.append("write")

    result = await ApiLane(headers_broker({"x-csrf-token": "a\r\nb"}, http=http)).execute(
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
        headers_broker({}, http=HttpxCaller(transport=httpx.MockTransport(server)))
    ).execute(step, RUN, lane_context(by_id, ledger=ledger))

    assert result.verdict == "unknown" and not result.never_left


async def test_a_write_the_ledger_never_watched_is_not_sent() -> None:
    http = FakeHttpCaller()
    step, by_id, _ = proven_write_step(read_back=LIST)
    warned: list[str] = []

    async def about_to_write(lane: Lane) -> None:
        warned.append("write")

    result = await ApiLane(headers_broker({}, http=http)).execute(
        step, RUN, lane_context(by_id, ledger=(), about_to_write=about_to_write)
    )

    assert result.verdict == "failed" and result.never_left
    assert http.sent == [] and warned == []


async def test_a_read_back_settles_an_unknown_write() -> None:
    http = FakeHttpCaller()
    http.answer(200, '[{"name": "GT1"}, {"name": "GT2"}]')
    step, by_id, ledger = proven_write_step(read_back=LIST)

    settled = await ApiLane(headers_broker({}, http=http)).read_back(
        step, RUN, lane_context(by_id, ledger=ledger)
    )

    assert settled == "done"
    assert http.sent[0]["method"] == "GET"


async def test_a_token_guarded_read_back_after_a_fresh_sign_in_waits_for_its_csrf_token() -> None:
    http = FakeHttpCaller()
    http.answer(200, '[{"name": "GT2"}]')
    step, by_id, ledger = proven_write_step(
        read_back=LIST, read_headers={"X-CSRF-Token": REDACTED, "X-Trace-Id": REDACTED}
    )
    driver = scripted_driver(url="https://wms.example/app")
    driver.headers_after_mark = {"x-csrf-token": "after"}

    settled = await ApiLane(
        headers_broker({"x-csrf-token": "before"}, driver=driver, http=http)
    ).read_back(step, RUN, lane_context(by_id, ledger=ledger, reauthed=True))

    assert settled == "done"
    assert driver.needed == ("x-csrf-token",)
    assert http.sent[0]["headers"]["x-csrf-token"] == "after"


@pytest.mark.parametrize(
    "body",
    ['[{"name": "GT1"}]', '[{"name": "GT1", "note": "GT2"}]', "<td>GT20</td>"],
    ids=["another-record", "another-field", "not-json-substring"],
)
async def test_a_read_back_that_does_not_show_the_record_settles_nothing(body: str) -> None:
    http = FakeHttpCaller()
    http.answer(200, body)
    step, by_id, ledger = proven_write_step(read_back=LIST)

    settled = await ApiLane(headers_broker({}, http=http)).read_back(
        step, RUN, lane_context(by_id, ledger=ledger)
    )

    assert settled is None


async def test_a_value_found_in_another_field_does_not_confirm_the_write() -> None:
    http = FakeHttpCaller()
    http.answer(201, "{}")
    http.answer(200, '[{"name": "GT1", "note": "GT2"}]')
    step, by_id, ledger = proven_write_step(read_back=LIST)

    result = await ApiLane(headers_broker({}, http=http)).execute(
        step, RUN, lane_context(by_id, ledger=ledger)
    )

    assert result.verdict == "unknown"


async def test_a_success_the_recording_never_saw_is_not_taken_as_done() -> None:
    http = FakeHttpCaller()
    http.answer(200, "{}")
    http.answer(200, '[{"name": "GT2"}]')
    step, by_id, ledger = proven_write_step(read_back=LIST)

    result = await ApiLane(headers_broker({}, http=http)).execute(
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

    await ApiLane(headers_broker({}, driver=driver, http=http)).execute(
        step, RUN, lane_context(by_id, ledger=ledger, reauthed=True)
    )

    assert http.sent[0]["headers"]["x-csrf-token"] == "after"


async def test_a_token_the_write_needs_that_the_session_lacks_is_refused_before_sending() -> None:
    http = FakeHttpCaller()
    step, by_id, ledger = proven_write_step(
        read_back=LIST,
        request_headers={"Content-Type": "application/json", "X-CSRF-Token": REDACTED},
    )

    result = await ApiLane(
        headers_broker({"x-requested-with": "XMLHttpRequest"}, http=http)
    ).execute(step, RUN, lane_context(by_id, ledger=ledger))

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

    await ApiLane(headers_broker({}, driver=driver, http=FakeHttpCaller())).execute(
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

    await ApiLane(headers_broker({}, http=http)).execute(
        step, RUN, lane_context(by_id, ledger=ledger)
    )

    assert http.sent[0]["headers"] == {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


async def test_a_read_back_on_another_origin_is_never_sent() -> None:
    http = FakeHttpCaller()
    http.answer(201, "{}")
    step, by_id, ledger = proven_write_step(read_back="https://analytics.example/hit")

    result = await ApiLane(headers_broker({}, http=http)).execute(
        step, RUN, lane_context(by_id, ledger=ledger)
    )

    assert result.verdict == "unknown"
    assert not [one for one in http.sent if "analytics.example" in str(one["url"])]


async def test_a_read_back_addressed_by_the_recorded_record_reads_this_runs_record() -> None:
    http = FakeHttpCaller()
    http.answer(201, "{}")
    http.answer(200, '{"name": "GT2"}')
    step, by_id, ledger = proven_write_step(read_back="/api/customer-types/{name}")

    result = await ApiLane(headers_broker({}, http=http)).execute(
        step, RUN, lane_context(by_id, ledger=ledger)
    )

    assert result.verdict == "done"
    assert http.sent[1]["url"] == "https://wms.example/api/customer-types/GT2"


async def test_a_read_back_naming_the_recorded_value_inside_a_segment_is_not_sent() -> None:
    http = FakeHttpCaller()
    http.answer(201, "{}")
    step, by_id, ledger = proven_write_step(read_back="/api/customer-types?name={name}")

    result = await ApiLane(headers_broker({}, http=http)).execute(
        step, RUN, lane_context(by_id, ledger=ledger)
    )

    assert result.verdict == "unknown"
    assert not [one for one in http.sent if "?" in str(one["url"])]


async def test_a_redirect_off_the_host_is_in_doubt_and_asks_for_a_fresh_session() -> None:
    http = FakeHttpCaller()
    http.answer(302, "", headers={"location": "https://idp.example/login"})
    step, by_id, ledger = proven_write_step(read_back=LIST)

    result = await ApiLane(headers_broker({}, http=http)).execute(
        step, RUN, lane_context(by_id, ledger=ledger)
    )

    assert result.verdict == "unknown" and result.expired and not result.never_left
    assert len(http.sent) == 1


async def test_a_redirect_on_the_same_host_is_in_doubt_but_the_session_stands() -> None:
    http = FakeHttpCaller()
    http.answer(303, "", headers={"location": "/app/customer-types/ct-9"})
    step, by_id, ledger = proven_write_step(read_back=LIST)

    result = await ApiLane(headers_broker({}, http=http)).execute(
        step, RUN, lane_context(by_id, ledger=ledger)
    )

    assert result.verdict == "unknown" and not result.expired


async def test_a_replay_with_an_absent_optional_value_sends_no_key_for_it() -> None:
    http = FakeHttpCaller()
    http.answer(201, '{"id": "ct-9"}')
    step, by_id, ledger = proven_write_step(read_back=None, described=("north", "south"))
    job = replace(
        WORKFLOW,
        parameters=[
            {"name": "Customer Type", "seen_values": ["GT0", "GT1"]},
            {"name": "Description", "seen_values": ["north", "south"], "required": False},
        ],
    )

    await ApiLane(headers_broker({}, http=http)).execute(
        step, RUN, lane_context(by_id, ledger=ledger, workflow=job)
    )

    sent = http.sent[0]
    assert json.loads(str(sent["body"])) == {"name": "GT2"}
    assert "north" not in str(sent) and "south" not in str(sent)


def _deleting() -> tuple[Step, dict[str, Gesture], tuple[VerifiedWrite, ...]]:
    by_id = {
        f"ges_del_{name}": Gesture(
            id=f"ges_del_{name}",
            tenant="acme",
            stream_id="stream-1",
            batch_id="batch-1",
            at=float(n + 1),
            url="https://wms.example/app",
            system="https://wms.example",
            tab_id=1,
            frame_url=None,
            action=Action(kind="click", at=float(n + 1), target=Target(role="button", name="OK")),
            requests=[
                Call(
                    method="DELETE",
                    url=f"{WRITE}/{name}",
                    status=204,
                    started_at=float(n + 1),
                    request_headers={"Content-Type": "application/json"},
                )
            ],
        )
        for n, name in enumerate(("GT0", "GT1"))
    }
    step = Step(order=0, says="Delete it", system="https://wms.example", cites=list(by_id))
    return step, by_id, (VerifiedWrite("DELETE", "/api/customer-types/{id}"),)


@pytest.mark.parametrize(("read_back", "verdict"), [(404, "done"), (200, "unknown")])
async def test_a_delete_is_done_when_its_record_no_longer_answers(
    read_back: int, verdict: str
) -> None:
    """Greyorange, 2026-09-29: the Undo of SR10 sent its DELETE by the proven
    call, and the run said nothing confirmed it -- the read-back looked for the
    values written, which a delete never leaves. A delete is confirmed by its
    record's own address answering that it is gone."""
    step, by_id, ledger = _deleting()
    job = replace(
        lane_context(by_id).workflow,
        parameters=[{"name": "Customer Type", "seen_values": ["GT0", "GT1"]}],
    )
    http = FakeHttpCaller()
    http.answer(204)
    http.answer(read_back, "{}")

    result = await ApiLane(headers_broker({}, http=http)).execute(
        step, RUN, lane_context(by_id, ledger=ledger, workflow=job)
    )

    assert result.verdict == verdict
    assert [(one["method"], str(one["url"]).split("?")[0]) for one in http.sent] == [
        ("DELETE", f"{WRITE}/GT2"),
        ("GET", f"{WRITE}/GT2"),
    ]


async def test_a_create_that_names_its_record_is_confirmed_by_reading_that_record() -> None:
    """Greyorange, 2026-09-29: the proven POST of a transport equipment type
    answered 201 with resourceId AITE6*!trlr_typ, and the run ended unclear:
    the read it confirmed by was the recording's GET of dock access groups,
    which never holds a new equipment type. The record the create named is
    read at its own address, and its values confirm the write."""
    http = FakeHttpCaller()
    http.answer(201, '{"data": {"resourceId": "GT2*!x"}}')
    http.answer(200, '{"data": {"name": "GT2"}}')
    step, by_id, ledger = proven_write_step(read_back="/api/something-else")

    result = await ApiLane(headers_broker({}, http=http)).execute(
        step, RUN, lane_context(by_id, ledger=ledger)
    )

    assert result.verdict == "done"
    assert [(one["method"], str(one["url"]).split("?")[0]) for one in http.sent] == [
        ("POST", WRITE),
        ("GET", f"{WRITE}/GT2%2A%21x"),
    ]


@pytest.mark.parametrize("status", [400, 409, 500], ids=lambda status: f"answered-{status}")
async def test_a_write_the_system_did_not_accept_keeps_what_it_answered_scrubbed(
    status: int,
) -> None:
    """Greyorange, 2026-09-30: PJ26's save ended unclear and its step kept
    nothing of what Blue Yonder answered -- not even the status. What the system
    said is kept on the step, secrets scrubbed, its length bounded."""
    http = FakeHttpCaller()
    http.answer(
        status,
        json.dumps(
            {
                "errors": [{"message": "Voice code 42 is already used"}],
                "password": "hunter2",
                "trace": "x" * 5000,
            }
        ),
        headers={"content-type": "application/json"},
    )
    step, by_id, ledger = proven_write_step(read_back=None)

    result = await ApiLane(headers_broker({}, http=http)).execute(
        step, RUN, lane_context(by_id, ledger=ledger)
    )

    assert result.answered["status"] == str(status)
    assert "Voice code 42 is already used" in result.answered["said"]
    assert "hunter2" not in str(dict(result.answered))
    assert len(result.answered["said"]) <= 300


DESCRIBED = {"Customer Type": "GT2", "Description": "Pet shops"}


async def _answered(*answers: tuple[int, str]) -> tuple[StepResult, FakeHttpCaller]:
    http = FakeHttpCaller()
    for status, text in answers:
        http.answer(status, text)
    step, by_id, ledger = proven_write_step(read_back=None, described=("d0", "d1"))
    job = replace(
        WORKFLOW,
        parameters=[
            {"name": "Customer Type", "seen_values": ["GT0", "GT1"]},
            {"name": "Description", "seen_values": ["d0", "d1"]},
        ],
    )
    result = await ApiLane(headers_broker({}, http=http)).execute(
        step, DESCRIBED, lane_context(by_id, ledger=ledger, workflow=job)
    )
    return result, http


async def test_a_clash_whose_record_is_absent_was_refused_in_the_system_s_own_words() -> None:
    result, http = await _answered(
        (409, '{"message": "Description Pet shops is already used"}'), (404, "")
    )

    assert result.verdict == "failed" and result.refused
    assert "Description Pet shops is already used" in result.reason
    assert [(one["method"], str(one["url"])) for one in http.sent] == [
        ("POST", WRITE),
        ("GET", f"{WRITE}/GT2"),
    ]


async def test_a_server_error_whose_record_reads_back_with_our_values_is_done() -> None:
    result, _ = await _answered((502, ""), (200, '{"name": "GT2", "description": "Pet shops"}'))

    assert result.verdict == "done" and not result.refused


async def test_a_clash_whose_record_holds_other_values_already_exists() -> None:
    result, _ = await _answered(
        (409, '{"message": "exists"}'), (200, '{"name": "GT2", "description": "Vets"}')
    )

    assert result.verdict == "failed" and result.refused
    assert "already exists with different values" in result.reason


@pytest.mark.parametrize("read", [(500, ""), (200, "not json")], ids=["refused", "unreadable"])
async def test_a_clash_whose_record_cannot_be_read_back_is_asked_about(
    read: tuple[int, str],
) -> None:
    result, _ = await _answered((409, '{"message": "exists"}'), read)

    assert result.verdict == "unknown" and not result.refused


async def test_an_accepted_write_whose_record_is_absent_is_in_doubt_not_refused() -> None:
    result, _ = await _answered((201, "{}"), (404, ""))

    assert result.verdict == "unknown" and not result.refused


@pytest.mark.parametrize("status", [500, 502, 503, 504])
async def test_a_server_error_whose_guessed_record_address_is_absent_is_not_a_refusal(
    status: int,
) -> None:
    # The system may have saved the record at an id we cannot guess: a 404 at
    # the guessed address proves nothing about the write.
    result, _ = await _answered((status, ""), (404, ""))

    assert result.verdict == "unknown" and not result.refused and not result.never_left
