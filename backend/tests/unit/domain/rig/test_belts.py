from dataclasses import replace

from sro.domain.execution.belts import (
    K_EARNED_RUNS,
    RunProof,
    carries_in_slot,
    confirming_read,
    earned_from,
    expected_statuses,
    mentions,
    proven_runs,
    state_verified,
    status_of,
    unreturned,
)
from sro.domain.observation.gesture import Call, Gesture
from sro.domain.skill.workflow import Step
from tests.unit.domain.rig.conftest import gestures as _gestures

# The batch's own instants, as epoch seconds: the write at ...781, and two
# moments after everything it recorded.
_AFTER = 1788165604.9
_LATER = 1788165605.9


def _saver() -> Gesture:
    return next(g for g in _gestures() if g.requests)


def _step(gesture: Gesture) -> Step:
    return Step(order=0, says="save", system=None, cites=[gesture.id])


def _get(
    url: str = "http://127.0.0.1:63319/api/after",
    started_at: float | None = _AFTER,
    *,
    request_id: str = "probe",
    method: str = "GET",
    status: int | None = 200,
    failure_reason: str | None = None,
) -> Call:
    return Call(
        method=method,
        url=url,
        request_id=request_id,
        started_at=started_at,
        status=status,
        failure_reason=failure_reason,
    )


def test_expected_statuses_and_the_confirming_read_come_from_the_evidence() -> None:
    saver = _saver()
    by_id = {saver.id: saver}
    assert expected_statuses(_step(saver), by_id) == {
        r.status for r in saver.requests if r.method == "POST" and r.status
    }
    read = confirming_read(_step(saver), by_id)
    assert read is not None and read.method == "GET"


def test_a_read_the_evidence_made_is_never_an_expected_write_status() -> None:
    """`expected_statuses` is what the mutation came back with. A GET's 204
    counted there would teach the verifier that 204 means the write landed."""
    saver = _saver()
    post = next(r for r in saver.requests if r.method == "POST")
    saver.requests = [
        replace(post, status=201),
        _get(status=204),
        _get(request_id="head", method="HEAD", status=205),
        _get(request_id="pre", method="OPTIONS", status=206),
    ]

    assert expected_statuses(_step(saver), {saver.id: saver}) == {201}


def test_a_call_that_never_returned_names_no_status_the_warehouse_gave() -> None:
    saver = _saver()
    dead = replace(
        next(r for r in saver.requests if r.method == "POST"),
        status=502,
        failure_reason="Failed to fetch",
    )
    saver.requests = [dead]

    assert expected_statuses(_step(saver), {saver.id: saver}) == set()


def test_a_cited_gesture_the_store_lost_does_not_hide_the_evidence_behind_it() -> None:
    saver = _saver()
    step = Step(order=0, says="save", system=None, cites=["ges_gone", saver.id])
    by_id = {saver.id: saver}

    assert expected_statuses(step, by_id) == {200}
    read = confirming_read(step, by_id)
    assert read is not None and read.url.endswith("/api/stream")


def test_the_confirming_read_comes_after_the_write_and_came_back() -> None:
    """Same instant is not after: a read that raced the write saw the state
    before it. And a read that never returned confirms nothing."""
    saver = _saver()
    call = next(r for r in saver.requests if r.method == "POST")
    saver.requests = [
        call,
        _get(request_id="same", started_at=call.started_at),
        # A call at no time at all cannot be shown to have come after the
        # write, which is the only thing that would make it the confirming one.
        _get(request_id="untimed", started_at=None),
        # A status on a call that reports a failure is not a status the
        # warehouse gave back -- the same reading `expected_statuses` makes.
        _get(request_id="dead", status=502, failure_reason="Failed to fetch"),
    ]

    assert confirming_read(_step(saver), {saver.id: saver}) is None


def test_a_write_at_no_time_at_all_has_no_after_for_a_read_to_come_in() -> None:
    """The other end of the same strictness: `confirming_read` compares the
    read's instant against the write's, and a write with no `started_at` gives
    it nothing to compare. A hand-built call is the one that arrives this way --
    the recorder always timed its own."""
    saver = _saver()
    post = next(r for r in saver.requests if r.method == "POST")
    saver.requests = [
        replace(post, started_at=None),
        # Timed, later than anything in the batch, and it came back: the read
        # that would confirm the write if the write said when it happened.
        _get(request_id="later", started_at=_LATER),
    ]

    assert confirming_read(_step(saver), {saver.id: saver}) is None


def test_a_step_whose_recorded_call_is_itself_a_read_has_nothing_to_confirm() -> None:
    """`confirming_read` answers "the read this page makes after its write".
    A step that never wrote has no after -- however that read is spelled."""
    for method in ("GET", "HEAD", "OPTIONS"):
        saver = _saver()
        saver.requests = [
            _get(request_id="first", method=method),
            _get(request_id="later", started_at=_LATER),
        ]

        assert confirming_read(_step(saver), {saver.id: saver}) is None, method


def test_the_read_shows_a_whole_value_at_any_depth_and_never_a_substring_of_one() -> None:
    """Leaf equality, not substring: the capture's own order list answers
    `{"orders": [{"id": "ORD-1"}]}` and a run value of "1" is inside that
    string without being in it. Depth is no barrier the other way -- the read
    of a created record answers the record, not a flat dictionary of it."""
    assert mentions('{"orders":[{"id":"ORD-1"}]}', {"n": "1"}) is False
    assert mentions('{"code":"THIRD"}', {"clientCode": "THIRD"}) is True
    assert mentions('{"data":{"order":{"workArea":"THIRD"}}}', {"workArea": "THIRD"}) is True


def test_a_status_is_read_off_the_reply_only_when_the_reply_carries_one() -> None:
    assert status_of({"status": 201, "body": "{}"}) == 201
    assert status_of({"performed": True}) is None
    assert status_of({"status": "201"}) is None


def _proof(run_id: str, *, wrote: set[int], verified: set[int]) -> RunProof:
    return RunProof(run_id=run_id, wrote=frozenset(wrote), verified=frozenset(verified))


def test_three_live_runs_whose_writes_all_verified_by_state_earn_autonomy() -> None:
    proofs: list[RunProof] = []
    for i in range(K_EARNED_RUNS):
        proofs.append(_proof(f"run_{i}", wrote={1}, verified={1}))
        assert earned_from(proofs) is (i == K_EARNED_RUNS - 1)
        # The count the panel draws as "N of 3" is the one the verdict reads.
        assert proven_runs(proofs) == i + 1


def test_a_screen_only_verification_is_not_an_effect() -> None:
    """A verdict by screen is never recorded as an effect, so a run whose write
    only ever convinced a model reading a picture reaches the rule with nothing
    in `verified` -- and does not count."""
    assert state_verified("screen") is False
    assert state_verified("status") is True and state_verified("read") is True

    proofs = [_proof(f"run_{i}", wrote={1}, verified=set()) for i in range(K_EARNED_RUNS)]
    assert earned_from(proofs) is False


def test_a_run_with_one_unverified_write_does_not_count() -> None:
    proofs = [_proof(f"run_{i}", wrote={1, 3}, verified={1}) for i in range(K_EARNED_RUNS)]
    assert earned_from(proofs) is False
    assert proven_runs(proofs) == 0


def test_a_failed_write_starts_the_earning_again() -> None:
    """Forgetting what a job had earned is the repository's to do; the rule
    only ever reads the proofs it is handed, so a cleared table is no proofs."""
    proofs = [_proof(f"run_{i}", wrote={1}, verified={1}) for i in range(K_EARNED_RUNS)]
    assert earned_from(proofs) is True
    assert earned_from([]) is False


def test_the_number_of_runs_autonomy_costs_is_the_one_a_person_agreed_to() -> None:
    """Three, and moving it is a decision somebody makes on purpose."""
    assert K_EARNED_RUNS == 3


def test_a_dry_run_never_earns_anything() -> None:
    """A `RunProof` is only ever built from a live run that held -- a dry run
    reaches the rule as no proof at all -- and short of three proofs the rule
    does not earn."""
    proofs = [_proof(f"run_{i}", wrote={1}, verified={1}) for i in range(K_EARNED_RUNS - 1)]
    assert earned_from(proofs) is False


def test_a_held_run_that_wrote_nothing_proves_nothing_about_writing() -> None:
    proofs = [_proof(f"run_{i}", wrote=set(), verified=set()) for i in range(K_EARNED_RUNS)]
    assert earned_from(proofs) is False


def test_another_tenants_run_does_not_earn_this_ones_autonomy() -> None:
    """The caller scopes by tenant when it gathers the runs; the rule counts
    the proofs it is given and asks nothing about whose they were."""
    proofs = [_proof(f"run_{i}", wrote={1}, verified={1}) for i in range(K_EARNED_RUNS)]
    assert earned_from(proofs) is True
    assert earned_from(proofs[:1]) is False


def test_a_step_that_never_sent_anything_is_not_read_as_a_write() -> None:
    """A skipped step has no stored result at all, so it is not in `wrote`. It
    is not a write the run has to have verified, and it must not stop one that
    did."""
    proofs = [_proof(f"run_{i}", wrote={1}, verified={1}) for i in range(K_EARNED_RUNS)]
    assert earned_from(proofs) is True


def test_a_beacon_beside_the_write_names_no_status_the_write_came_back_with() -> None:
    """The set is the replayed endpoint's, not the cited gesture's.

    Four steps across both real tenants fire a 201 create AND a 200 keep-alive
    or telemetry batch on the same gesture -- acme's `Create a Customer Type`
    steps 1 and 6, its `Create an Activity Code` step 7, and `new`'s `Create a
    Customer Type` step 5. Taking every mutating call gave `{200, 201}` there,
    so a replayed create that came back 200 would be held by rung 1 of `verify`
    on a performance beacon's status code, with the read-back never asked.
    """
    saver = _saver()
    write = replace(next(r for r in saver.requests if r.method == "POST"), status=201)
    saver.requests = [
        write,
        Call(
            method="POST",
            url="http://127.0.0.1:63319/data/WM/wm/webPerformanceEntries/batch",
            request_id="beacon",
            started_at=_LATER,
            status=200,
        ),
    ]

    assert expected_statuses(_step(saver), {saver.id: saver}) == {201}


def test_the_same_endpoint_twice_names_both_statuses_it_gave() -> None:
    """Narrowing to one endpoint is not narrowing to one call: a job whose
    evidence saved twice, once created and once accepted, is verified against
    both, and neither reading is the browser's background traffic."""
    saver = _saver()
    write = next(r for r in saver.requests if r.method == "POST")
    saver.requests = [
        replace(write, status=201),
        replace(write, request_id="again", started_at=_LATER, status=202),
    ]

    assert expected_statuses(_step(saver), {saver.id: saver}) == {201, 202}


def test_a_method_the_browser_recorded_in_lower_case_is_still_a_read() -> None:
    """`READ_METHODS` holds upper case, and the extension has always sent upper
    case -- so the `.upper()` guarding that comparison is doing nothing any
    fixture can see. It is doing something a `fetch("...", {method: "get"})`
    can: without it a recorded read is classified as a write, given an expected
    status, and a dry run that replays it is read as having sent one."""
    saver = _saver()
    saver.requests = [_get(method="get", request_id="lower", status=200)]

    assert expected_statuses(_step(saver), {saver.id: saver}) == set()


# -- the value in the key the plan put it in ----------------------------------


def test_a_value_in_the_wrong_key_is_not_the_record_this_run_asked_for() -> None:
    """What the whole-body search cannot ask.

    `carries_every` looks for the value anywhere in the record, so a record
    carrying the right code in a key the plan never wrote reads as confirmed.
    That is not a hypothetical shape: a create's answer echoes the request's
    own fields back, and a job that fills two of them is confirmed by one.
    """
    assert carries_in_slot('{"customerType":"GPDP"}', {"customerType": "GPDP"})
    assert not carries_in_slot('{"shotDescription":"GPDP"}', {"customerType": "GPDP"})


def test_every_slot_or_none_of_them() -> None:
    """One slot right and one wrong is a record that is not the one asked for,
    and the truncation this belt exists for looks exactly like that: the
    description still matches and the code does not."""
    record = '{"customerType":"GPDP","longDescription":"WAS TRUNCATED"}'

    assert not carries_in_slot(record, {"customerType": "GPDP", "longDescription": "asked for"})
    assert carries_in_slot(record, {"customerType": "GPDP"})


def test_the_envelope_is_removed_before_the_record_is_read() -> None:
    """Blue Yonder answers with `{"@type": …, "data": {…}}` -- 112 of the 114
    successful writes in the recorded exchanges -- and read at the top level
    that record has none of its own fields in it."""
    assert carries_in_slot(
        '{"@type":"ResponseBodyWrapper","data":{"customerType":"GPDP"}}',
        {"customerType": "GPDP"},
    )


def test_a_read_that_answers_with_the_whole_collection_still_settles_it() -> None:
    """A confirming read is whatever GET the page made after its write, and on
    the real system that is the COLLECTION.

    Measured live 2026-09-16: the read after `POST /wm/customerTypes` is
    `GET /wm/customerTypes?siteId=SG&…`, a list of every customer type. A rule
    that could only read one record called a 201'd create failed, because it
    looked for `customerType` on the envelope of a list.
    """
    page = (
        '{"@type":"ResponseBodyWrapper","data":['
        '{"customerType":"GGD","longDescription":"the demonstration"},'
        '{"customerType":"ZQ43","longDescription":"this run"}]}'
    )

    assert carries_in_slot(page, {"customerType": "ZQ43", "longDescription": "this run"})
    assert not carries_in_slot(page, {"customerType": "ZQ43", "longDescription": "not sent"})


def test_one_row_must_carry_every_slot_not_the_page_between_them() -> None:
    """`any` over records and `all` over slots, and the pairing is the point.

    A page where one row matches the code and another matches the description
    shows neither record. The whole-body search this replaced flattened the
    page to a set of leaves and could not tell that from a match -- so a
    collection confirmed a write whenever the values existed anywhere in it,
    including across two rows and including in the row the demonstration made.
    """
    split = (
        '{"data":[{"customerType":"ZQ43","longDescription":"the demonstration"},'
        '{"customerType":"GGD","longDescription":"this run"}]}'
    )

    assert not carries_in_slot(split, {"customerType": "ZQ43", "longDescription": "this run"})


def test_a_bare_list_is_read_the_same_way_as_a_wrapped_one() -> None:
    """Two of the 114 recorded writes answer with a list under `data`, and
    nothing promises an envelope on every endpoint."""
    assert carries_in_slot('[{"customerType":"ZQ43"}]', {"customerType": "ZQ43"})


def test_nothing_to_check_is_not_something_shown() -> None:
    """An empty `confirm` means no slot survived the demonstration's own
    answer, so the read settles nothing. `verify` does not even make the read
    for one; this says what the belt answers if anybody does."""
    assert not carries_in_slot('{"customerType":"GPDP"}', {})
    assert not carries_in_slot("not json", {"customerType": "GPDP"})


def test_a_value_the_record_did_not_come_back_with_is_named() -> None:
    """The failure that looks like a success, and the reason every belt misses
    it.

    A warehouse that silently shortens a field answers exactly like one that
    stored it. Send a code and a long description, have the description
    truncated on save, and the code comes back: `mentions` is satisfied, the
    step holds by `read`, and the status and the screenshot agree -- because
    every one of those compares the record to ITSELF. The status is the
    server's own, the read-back is the record as stored, and a picture of the
    resulting row looks right to a model that has no idea what was asked for.

    So the step still holds -- one value back is the record back, and
    requiring all of them was measured wrong at one correct create in six --
    and what did not come back is named.
    """
    body = '{"customerType": "GV3", "longDescription": "leaning new SRO"}'
    sent = {"Customer Type": "GV3", "Description": "leaning new SRO type 047"}

    assert mentions(body, sent), "one value back is the record back"
    assert unreturned(body, sent) == ("Description",)


def test_a_record_that_came_back_whole_names_nothing() -> None:
    body = '{"customerType": "GV3", "longDescription": "leaning new SRO"}'
    assert unreturned(body, {"Customer Type": "GV3", "Description": "leaning new SRO"}) == ()
    # And nothing supplied is nothing missing, rather than everything.
    assert unreturned(body, {}) == ()


def test_a_body_that_is_not_json_is_read_as_text_for_this_too() -> None:
    """`mentions` falls back to substring for a body with no leaves to compare,
    and so does this: the two have to agree about what came back, or a step
    holds on a value this says is missing."""
    body = "customerType=GV3&longDescription=leaning+new+SRO"
    assert unreturned(body, {"Customer Type": "GV3", "Description": "a different thing"}) == (
        "Description",
    )
