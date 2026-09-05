from pathlib import Path

from rig.effects import K_EARNED_RUNS, earned, forget_effects, record_effect
from rig.runs import Run, RunStep, save_run
from rig.store import Store


def _store(tmp_path: Path) -> Store:
    store = Store(tmp_path / "rig.db")
    store.migrate()
    return store


def _held_run(store: Store, run_id: str, writes: list[int]) -> None:
    save_run(
        store,
        Run(
            id=run_id,
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
