from pathlib import Path

from rig.runs import (
    OUTCOMES,
    VERDICTS,
    Run,
    RunStep,
    fail_orphans,
    load_run,
    new_run_id,
    runs_for,
    save_run,
)
from rig.store import Store


def _store(tmp_path: Path) -> Store:
    store = Store(tmp_path / "rig.db")
    store.migrate()
    return store


def _run(**over) -> Run:
    base = {
        "id": new_run_id(),
        "tenant": "acme",
        "workflow_id": "wfl_1",
        "device_id": "dev_1",
        "values": {"workArea": "THIRD"},
        "started_by": "form",
        "live": False,
        "allow_focus": True,
        "started_at": "2026-09-05T10:00:00+00:00",
        "finished_at": None,
        "outcome": "running",
        "steps": [],
        "withheld": [],
    }
    return Run(**{**base, **over})


def test_a_run_id_has_the_shape_the_other_ids_have() -> None:
    assert new_run_id().startswith("run_") and len(new_run_id()) == 36


def test_a_run_round_trips_with_every_step_and_every_withheld_write(tmp_path: Path) -> None:
    store = _store(tmp_path)
    run = _run(
        steps=[
            RunStep(
                order=0,
                says="type the code",
                planned_by="gemini-3.8-flash",
                sent={"kind": "ui.perform", "payload": {"action": "type", "value": "THIRD"}},
                result={"performed": True, "matched_by": "component", "candidates": 1},
                verdict="held",
                verdict_by="screen",
                reason="the field shows THIRD",
                matched_by="component",
                stale=False,
                before_url="https://wms/x",
                after_url="https://wms/x",
                in_tokens=300,
                out_tokens=40,
                thought_tokens=10,
                cost_usd=0.0004,
                unpriced=False,
            ),
            RunStep(
                order=1,
                says="save",
                planned_by="gemini-3.8-flash",
                sent={"kind": "ui.perform", "payload": {"action": "click"}},
                result={"withheld": True},
                verdict="withheld",
                verdict_by="dry",
                reason="a dry run does not send writes",
                matched_by=None,
                stale=False,
                before_url=None,
                after_url=None,
            ),
        ],
        withheld=[
            {
                "step": 1,
                "method": "POST",
                "url": "https://wms/data/WM/wm/workAreas",
                "body": '{"workArea":"THIRD"}',
            }
        ],
        outcome="held",
        finished_at="2026-09-05T10:01:00+00:00",
        in_tokens=300,
        out_tokens=40,
        thought_tokens=10,
        cost_usd=0.0004,
    )

    save_run(store, run)
    back = load_run(store, "acme", run.id)

    assert back == run
    assert runs_for(store, "acme", "wfl_1") == [run]
    assert load_run(store, "acme", "run_nobody") is None


def test_saving_again_replaces_the_steps_rather_than_appending(tmp_path: Path) -> None:
    """A run is saved after every step so the page can poll it; the second
    save must not double the first step."""
    store = _store(tmp_path)
    run = _run(steps=[RunStep(order=0, says="a", verdict="held", verdict_by="status", reason="")])
    save_run(store, run)
    run.steps.append(RunStep(order=1, says="b", verdict="held", verdict_by="status", reason=""))
    save_run(store, run)

    assert [s.order for s in load_run(store, "acme", run.id).steps] == [0, 1]


def test_the_vocabularies_are_closed() -> None:
    assert "running" in OUTCOMES and "withheld" in VERDICTS


def test_a_run_still_running_when_the_rig_starts_is_failed_and_says_why(tmp_path: Path) -> None:
    store = _store(tmp_path)
    orphan = _run(steps=[RunStep(order=0, says="s", verdict="held")])
    bare = _run()
    done = _run(outcome="held", finished_at="2026-09-05T10:01:00+00:00")
    for run in (orphan, bare, done):
        save_run(store, run)

    assert fail_orphans(store, "the rig restarted") == 2

    failed = load_run(store, "acme", orphan.id)
    assert failed is not None and failed.outcome == "failed" and failed.finished_at
    assert failed.steps[-1].verdict == "failed" and failed.steps[-1].reason == "the rig restarted"
    stepless = load_run(store, "acme", bare.id)
    assert stepless is not None and stepless.steps[0].reason == "the rig restarted"
    untouched = load_run(store, "acme", done.id)
    assert untouched is not None and untouched.outcome == "held"


def test_the_flags_a_run_carries_survive_the_round_trip(tmp_path: Path) -> None:
    """`live`, `stale` and `unpriced` are all stored as integers and all read
    back as booleans. A run read back as a dry one would be re-offered as
    though it had never written; a cost read back as priced is a bill nobody
    knows to distrust."""
    store = _store(tmp_path)
    run = _run(
        live=True,
        allow_focus=False,
        unpriced=True,
        steps=[RunStep(order=0, says="a", verdict="held", stale=True, unpriced=True, cost_usd=0.0)],
    )
    save_run(store, run)

    back = load_run(store, "acme", run.id)

    assert back is not None
    assert (back.live, back.allow_focus, back.unpriced) == (True, False, True)
    assert (back.steps[0].stale, back.steps[0].unpriced) == (True, True)


def test_an_orphan_with_no_step_at_all_gets_one_that_says_who_failed(tmp_path: Path) -> None:
    """The reason has to land somewhere the page shows it, and a run that died
    before its first step has nowhere -- so it gets step zero."""
    store = _store(tmp_path)
    bare = _run()
    save_run(store, bare)

    fail_orphans(store, "the rig restarted")

    stepless = load_run(store, "acme", bare.id)
    assert stepless is not None
    [only] = stepless.steps
    assert (only.order, only.says) == (0, "")
    assert (only.verdict, only.verdict_by) == ("failed", "none")
    # UTC, spelled out: a naive local timestamp beside the UTC ones every other
    # writer produces reads as a run that finished hours before it started.
    assert stepless.finished_at is not None and stepless.finished_at.endswith("+00:00")


def test_the_reason_lands_on_the_step_the_orphan_died_in(tmp_path: Path) -> None:
    store = _store(tmp_path)
    orphan = _run(steps=[RunStep(order=0, says="s", verdict="held", verdict_by="status")])
    save_run(store, orphan)

    fail_orphans(store, "the rig restarted")

    failed = load_run(store, "acme", orphan.id)
    assert failed is not None and len(failed.steps) == 1
    assert (failed.steps[0].verdict, failed.steps[0].verdict_by) == ("failed", "none")
