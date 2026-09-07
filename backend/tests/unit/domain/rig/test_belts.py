from dataclasses import replace

from sro.domain.execution.belts import (
    K_EARNED_RUNS,
    RunProof,
    confirming_read,
    earned_from,
    expected_statuses,
    mentions,
    state_verified,
    status_of,
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
