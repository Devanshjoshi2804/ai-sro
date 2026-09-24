import pytest

from sro.domain.execution.progress import K_BUDGET_FLOOR_S, Account, Progress, run_budget
from sro.domain.observation.gesture import Action, Gesture
from sro.domain.skill.workflow import Step, Workflow


def timed_job(*, seconds: float, steps: int) -> tuple[Workflow, dict[str, Gesture]]:
    gestures = {
        f"g{n}": Gesture(
            id=f"g{n}",
            tenant="t",
            stream_id="s",
            batch_id="b",
            at=n * seconds / max(steps - 1, 1),
            url=None,
            system=None,
            tab_id=1,
            frame_url=None,
            action=Action(kind="click", at=0.0),
        )
        for n in range(steps)
    }
    job = Workflow(
        id="wfl_t",
        tenant="t",
        title="t",
        narrative="n",
        steps=[Step(order=n, says=f"s{n}", system=None, cites=[f"g{n}"]) for n in range(steps)],
    )
    return job, gestures


def test_progress_survives_its_row() -> None:
    progress = Progress(
        step=2,
        read={"id": "ct-9"},
        tabs={"main": "T1"},
        lease="lse_1",
        account=Account(origin="https://example.com", username="op"),
        start_url="https://example.com/start",
    )
    progress.sending(1)
    progress.settle(0, lane="ui", verdict="done")

    again = Progress.of(progress.as_json())

    assert again == progress


def test_a_write_in_flight_is_in_doubt_and_never_written() -> None:
    progress = Progress()
    progress.sending(3)

    assert progress.in_doubt(3) and not progress.written(3)


def test_a_settled_write_is_written_once() -> None:
    progress = Progress()
    progress.sending(3)
    progress.settle(3, lane="api", verdict="done")

    assert progress.written(3) and not progress.in_doubt(3)


def test_a_done_mark_is_never_overwritten() -> None:
    progress = Progress()
    progress.sending(3)
    progress.settle(3, lane="api", verdict="done")

    progress.sending(3)
    progress.settle(3, lane="ui", verdict="failed", never_left=True)

    assert progress.written(3) and not progress.in_doubt(3)
    assert progress.marks[3].lane == "api" and progress.marks[3].verdict == "done"


def test_settle_unknown_leaves_the_write_in_doubt() -> None:
    progress = Progress()
    progress.sending(3)
    progress.settle(3, lane="ui", verdict="unknown")

    assert progress.in_doubt(3) and not progress.written(3)


def test_settle_failed_without_confirmation_is_still_in_doubt() -> None:
    """A lane that fails after its write may already have sent it -- so a bare
    `failed` must never read as "safe to retry"."""
    progress = Progress()
    progress.sending(3)
    progress.settle(3, lane="ui", verdict="failed")

    assert progress.in_doubt(3) and not progress.written(3)


def test_settle_failed_that_never_left_clears_the_mark() -> None:
    progress = Progress()
    progress.sending(3)
    progress.settle(3, lane="ui", verdict="failed", never_left=True)

    assert not progress.in_doubt(3) and not progress.written(3)


def test_a_malformed_row_raises_rather_than_reading_as_empty() -> None:
    """Reading a malformed row as empty would restart a run from zero and
    repeat every write it already made -- so it must raise instead."""
    with pytest.raises(ValueError):
        Progress.of({"step": "not-a-number"})

    with pytest.raises(ValueError):
        Progress.of({"marks": {"not-a-number": {"wrote": "done"}}})


def test_account_never_carries_a_secret() -> None:
    raw = {"account": {"origin": "https://example.com", "username": "op", "password": "hunter2"}}

    progress = Progress.of(raw)

    assert progress.account == Account(origin="https://example.com", username="op")


def test_account_rejects_extra_keys() -> None:
    with pytest.raises(TypeError):
        Progress(account=Account(origin="o", username="u", password="hunter2"))  # type: ignore[call-arg] # noqa: S106


def test_as_json_never_carries_a_key_other_than_origin_and_username() -> None:
    progress = Progress(account=Account(origin="https://example.com", username="op"))

    account = progress.as_json()["account"]
    assert isinstance(account, dict)
    assert set(account) == {"origin", "username"}


def test_the_budget_grows_with_what_the_operator_took() -> None:
    slow, quick = timed_job(seconds=600, steps=5), timed_job(seconds=20, steps=5)

    assert run_budget(*slow) > run_budget(*quick) >= K_BUDGET_FLOOR_S
