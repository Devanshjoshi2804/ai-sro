import json
from pathlib import Path

from rig.api import save_batch
from rig.runs import Run, save_run
from rig.shapes import shapes_for
from rig.store import Store
from rig.wire import Batch
from rig.workflows import Step, Workflow, save_workflow
from tests.fixtures import BATCH


def _store(tmp_path: Path) -> Store:
    store = Store(tmp_path / "rig.db")
    store.migrate()
    save_batch(store, Batch.model_validate(BATCH), "acme")
    return store


def _ids(store: Store) -> list[str]:
    return [r["id"] for r in store.query("SELECT id FROM gestures ORDER BY at")]


def _workflow(store: Store, wid: str = "wfl_1", unproven: list[str] | None = None) -> Workflow:
    ids = _ids(store)
    # `gesture_json` is pydantic's own compact dump, so a substring probe for
    # `"kind": "type"` never matches. Read the column rather than grep it.
    typed = next(
        r["id"]
        for r in store.query("SELECT id, gesture_json FROM gestures ORDER BY at")
        if json.loads(r["gesture_json"]).get("kind") == "type"
        and json.loads(r["gesture_json"]).get("value") == "ACME-4471"
    )
    wf = Workflow(
        id=wid,
        tenant="acme",
        title="create a client",
        narrative="n",
        systems=["http://127.0.0.1:63319"],
        steps=[
            Step(
                order=0, says="type the code", system=None, cites=[typed], parameters=["clientCode"]
            ),
            Step(order=1, says="save", system=None, cites=[ids[-1]]),
        ],
        parameters=[{"name": "clientCode", "seen_values": ["ACME-4471"]}],
        unproven=unproven or [],
    )
    save_workflow(store, wf)
    return wf


def test_a_proven_workflow_is_served_as_its_shape_with_where_each_parameter_was_typed(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    _workflow(store)

    [shape] = shapes_for(store, "acme")

    assert shape.id == "wfl_1" and shape.title == "create a client"
    assert shape.starts_on and shape.starts_on.startswith("http://127.0.0.1:63319")
    assert "http://127.0.0.1:63319" in shape.hosts
    assert len(shape.shape) == 2 and shape.shape[0][2] == "type" and shape.shape[1][2] == "click"
    assert shape.parameters == [{"name": "clientCode", "at": 0}], (
        "the parameter was typed at shape index 0"
    )
    assert shape.held_runs == 0


def test_an_unproven_workflow_is_not_served(tmp_path: Path) -> None:
    store = _store(tmp_path)
    _workflow(store, unproven=["the save was never confirmed"])
    assert shapes_for(store, "acme") == []


def test_once_any_run_exists_only_workflows_that_have_held_are_served(tmp_path: Path) -> None:
    store = _store(tmp_path)
    _workflow(store, "wfl_1")
    _workflow(store, "wfl_2")
    save_run(
        store,
        Run(
            id="run_1",
            tenant="acme",
            workflow_id="wfl_1",
            device_id="dev_1",
            values={},
            started_by="form",
            live=True,
            allow_focus=True,
            started_at="2026-09-06T10:00:00+00:00",
            finished_at="2026-09-06T10:01:00+00:00",
            outcome="held",
        ),
    )

    served = shapes_for(store, "acme")

    assert [s.id for s in served] == ["wfl_1"]
    assert served[0].held_runs == 1


def test_a_parameter_no_cited_gesture_typed_has_no_index(tmp_path: Path) -> None:
    store = _store(tmp_path)
    wf = _workflow(store)
    wf.parameters.append({"name": "description", "seen_values": ["never typed here"]})
    save_workflow(store, wf)

    [shape] = shapes_for(store, "acme")

    assert {"name": "description", "at": None} in shape.parameters
