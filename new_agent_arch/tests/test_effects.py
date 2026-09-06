from pathlib import Path

from rig.effects import K_EARNED_RUNS, earned, forget_effects, record_effect
from rig.runs import Run, RunStep, load_run, save_run
from rig.store import Store


def _store(tmp_path: Path) -> Store:
    store = Store(tmp_path / "rig.db")
    store.migrate()
    return store


def _held_run(store: Store, run_id: str, writes: list[int], live: bool = True) -> None:
    save_run(
        store,
        Run(
            id=run_id,
            tenant="acme",
            workflow_id="wfl_1",
            device_id="d",
            values={},
            started_by="offer",
            live=live,
            allow_focus=True,
            started_at="2026-09-06T10:00:00+00:00",
            finished_at="2026-09-06T10:01:00+00:00",
            outcome="held",
            steps=[
                RunStep(
                    order=o,
                    says="s",
                    verdict="held",
                    verdict_by="status",
                    stale=False,
                    matched_by=None,
                    result={"ok": True, "status": 201, "matched_by": None, "wrote": True},
                )
                for o in writes
            ],
        ),
    )


def test_three_live_runs_whose_writes_all_verified_by_state_earn_autonomy(tmp_path: Path) -> None:
    store = _store(tmp_path)
    for i in range(K_EARNED_RUNS):
        _held_run(store, f"run_{i}", writes=[1])
        record_effect(
            store, workflow_id="wfl_1", run_id=f"run_{i}", order=1, verified_by="status", at="t"
        )
        assert earned(store, "wfl_1") is (i == K_EARNED_RUNS - 1)


def test_a_screen_only_verification_is_not_an_effect(tmp_path: Path) -> None:
    store = _store(tmp_path)
    for i in range(K_EARNED_RUNS):
        _held_run(store, f"run_{i}", writes=[1])
        record_effect(
            store, workflow_id="wfl_1", run_id=f"run_{i}", order=1, verified_by="screen", at="t"
        )
    assert earned(store, "wfl_1") is False


def test_a_run_with_one_unverified_write_does_not_count(tmp_path: Path) -> None:
    store = _store(tmp_path)
    for i in range(K_EARNED_RUNS):
        _held_run(store, f"run_{i}", writes=[1, 3])
        record_effect(
            store, workflow_id="wfl_1", run_id=f"run_{i}", order=1, verified_by="read", at="t"
        )
    assert earned(store, "wfl_1") is False


def test_a_failed_write_starts_the_earning_again(tmp_path: Path) -> None:
    store = _store(tmp_path)
    for i in range(K_EARNED_RUNS):
        _held_run(store, f"run_{i}", writes=[1])
        record_effect(
            store, workflow_id="wfl_1", run_id=f"run_{i}", order=1, verified_by="status", at="t"
        )
    assert earned(store, "wfl_1")
    assert forget_effects(store, "wfl_1") == K_EARNED_RUNS
    assert earned(store, "wfl_1") is False


def test_the_number_of_runs_autonomy_costs_is_the_one_a_person_agreed_to() -> None:
    """Three, and moving it is a decision somebody makes on purpose."""
    assert K_EARNED_RUNS == 3


def test_a_dry_run_never_earns_anything(tmp_path: Path) -> None:
    store = _store(tmp_path)
    for i in range(K_EARNED_RUNS):
        _held_run(store, f"run_{i}", writes=[1], live=False)
        record_effect(
            store, workflow_id="wfl_1", run_id=f"run_{i}", order=1, verified_by="status", at="t"
        )
    assert earned(store, "wfl_1") is False


def test_a_held_run_that_wrote_nothing_proves_nothing_about_writing(tmp_path: Path) -> None:
    store = _store(tmp_path)
    for i in range(K_EARNED_RUNS):
        save_run(
            store,
            Run(
                id=f"run_{i}",
                tenant="acme",
                workflow_id="wfl_1",
                device_id="d",
                values={},
                started_by="offer",
                live=True,
                allow_focus=True,
                started_at="2026-09-06T10:00:00+00:00",
                finished_at="2026-09-06T10:01:00+00:00",
                outcome="held",
                steps=[
                    RunStep(
                        order=1,
                        says="read the page",
                        verdict="held",
                        verdict_by="read",
                        result={"ok": True, "status": 200, "matched_by": None},
                    )
                ],
            ),
        )
    assert earned(store, "wfl_1") is False


def test_another_tenants_run_does_not_earn_this_ones_autonomy(tmp_path: Path) -> None:
    store = _store(tmp_path)
    for i in range(K_EARNED_RUNS):
        _held_run(store, f"run_{i}", writes=[1])
        record_effect(
            store, workflow_id="wfl_1", run_id=f"run_{i}", order=1, verified_by="status", at="t"
        )
    assert earned(store, "wfl_1", tenant="acme") is True
    assert earned(store, "wfl_1", tenant="someone-else") is False


def test_a_step_that_never_sent_anything_is_not_read_as_a_write(tmp_path: Path) -> None:
    """A skipped step has no stored result at all. It is not a write the run
    has to have verified, and it must not stop one that did."""
    store = _store(tmp_path)
    for i in range(K_EARNED_RUNS):
        _held_run(store, f"run_{i}", writes=[1])
        run = load_run(store, "acme", f"run_{i}")
        assert run is not None
        run.steps.append(RunStep(order=2, says="nothing to do", verdict="skipped", result=None))
        save_run(store, run)
        record_effect(
            store, workflow_id="wfl_1", run_id=f"run_{i}", order=1, verified_by="status", at="t"
        )

    assert earned(store, "wfl_1") is True
