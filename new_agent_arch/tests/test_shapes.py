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


def _run(store: Store, run_id: str, workflow_id: str, outcome: str) -> None:
    save_run(
        store,
        Run(
            id=run_id,
            tenant="acme",
            workflow_id=workflow_id,
            device_id="dev_1",
            values={},
            started_by="form",
            live=True,
            allow_focus=True,
            started_at="2026-09-06T10:00:00+00:00",
            finished_at="2026-09-06T10:01:00+00:00",
            outcome=outcome,
        ),
    )


def test_the_held_gate_is_per_workflow_and_never_silences_one_that_never_ran(
    tmp_path: Path,
) -> None:
    """One workflow's failure must not withdraw every sibling in the tenant."""
    store = _store(tmp_path)
    _workflow(store, "wfl_1")
    _workflow(store, "wfl_2")
    _workflow(store, "wfl_3")
    _run(store, "run_1", "wfl_1", "held")
    _run(store, "run_2", "wfl_2", "failed")

    served = shapes_for(store, "acme")

    assert [s.id for s in served] == ["wfl_1", "wfl_3"], (
        "wfl_2 has been run and never held; wfl_3 has never been run at all"
    )
    assert served[0].held_runs == 1
    assert served[1].held_runs == 0


def test_a_parameter_no_cited_gesture_typed_has_no_index(tmp_path: Path) -> None:
    store = _store(tmp_path)
    wf = _workflow(store)
    wf.parameters.append({"name": "description", "seen_values": ["never typed here"]})
    save_workflow(store, wf)

    [shape] = shapes_for(store, "acme")

    assert {"name": "description", "at": None} in shape.parameters


def test_a_workflow_that_starts_somewhere_its_own_evidence_never_names_is_not_served(
    tmp_path: Path,
) -> None:
    """The tab was on one origin while the frame that recorded the gesture was
    on another. Serving that sends the extension to an unproven host."""
    store = _store(tmp_path)
    workflow = _workflow(store)
    with store.connect() as connection:
        connection.execute(
            "UPDATE gestures SET page_url = ? WHERE id = ?",
            ("https://other.example/x", workflow.steps[0].cites[0]),
        )

    assert shapes_for(store, "acme") == []


def test_a_parameter_is_placed_by_the_step_that_declares_it_not_the_first_match(
    tmp_path: Path,
) -> None:
    """Search-then-create types the same code twice. The first typing is the
    search box, which is not the control the workflow is filling."""
    store = _store(tmp_path)
    workflow = _workflow(store)
    searched = workflow.steps[0].cites[0]
    workflow.steps = [
        Step(order=0, says="search for it first", system=None, cites=[searched]),
        Step(
            order=1,
            says="type the code",
            system=None,
            cites=[searched],
            parameters=["clientCode"],
        ),
        *[
            Step(order=s.order + 1, says=s.says, system=s.system, cites=s.cites)
            for s in workflow.steps[1:]
        ],
    ]
    save_workflow(store, workflow)

    [shape] = shapes_for(store, "acme")

    assert len(shape.shape) == 3
    assert shape.parameters == [{"name": "clientCode", "at": 1}], (
        "index 0 is the search box the first value match would have bound"
    )


def _scroll(store: Store) -> str:
    """A scroll in the store, put there the way the recorder would have.

    The committed batch holds none -- the browser test that produced it never
    scrolled -- and the rule below is entirely about scrolls, so one goes
    through `save_batch` rather than into the table by hand.
    """
    typed = next(e for e in BATCH["events"] if e["kind"] == "gesture")
    scrolled = {
        **typed,
        "gesture": {
            "kind": "scroll",
            "value": "300",
            "at": typed["gesture"]["at"] - 1,
            "url": typed["gesture"]["url"],
        },
    }
    save_batch(
        store,
        Batch.model_validate({**BATCH, "batch_id": "bat_scrolled", "events": [scrolled]}),
        "acme",
    )
    return next(
        r["id"]
        for r in store.query("SELECT id, gesture_json FROM gestures")
        if json.loads(r["gesture_json"])["kind"] == "scroll"
    )


def _scrolled_first(store: Store) -> Workflow:
    """The same workflow, with a scroll cited ahead of the gesture that types
    the parameter -- which is what a real recording looks like the moment the
    field is below the fold."""
    workflow = _workflow(store)
    workflow.steps[0].cites = [_scroll(store), *workflow.steps[0].cites]
    save_workflow(store, workflow)
    return workflow


def test_a_scroll_is_not_part_of_the_shape_that_is_served(tmp_path: Path) -> None:
    """`recognise.js` drops a scroll before the tail is ever written, so a
    served shape carrying one could not be matched at any k -- and a job whose
    first triple is a scroll could never be offered at all."""
    store = _store(tmp_path)
    workflow = _scrolled_first(store)

    [shape] = shapes_for(store, "acme")

    cited = [gesture for step in workflow.steps for gesture in step.cites]
    assert not any(triple[1] == "anon|scroll" for triple in shape.shape)
    assert len(shape.shape) == len(cited) - 1, "three cited gestures, one of them the scroll"


def test_a_parameter_typed_after_a_scroll_is_indexed_into_the_shape_as_served(
    tmp_path: Path,
) -> None:
    """`at` is walked against the shape the extension is handed, which has no
    scroll in it. Counted against the unfiltered evidence it would point one
    control to the right and fill the wrong box."""
    store = _store(tmp_path)
    _scrolled_first(store)

    [shape] = shapes_for(store, "acme")

    assert shape.parameters == [{"name": "clientCode", "at": 0}], (
        "index 1 is where the scroll put it in the unfiltered list"
    )


def _saver_first(store: Store, wid: str) -> Workflow:
    """A workflow that begins on the click rather than the typing, so the
    `page_url` edit below does not touch where it starts."""
    saver = _ids(store)[-1]
    wf = Workflow(
        id=wid,
        tenant="acme",
        title="save it",
        narrative="n",
        systems=["http://127.0.0.1:63319"],
        steps=[Step(order=0, says="save", system=None, cites=[saver])],
        parameters=[],
    )
    save_workflow(store, wf)
    return wf


def test_a_workflow_that_cannot_be_served_never_withdraws_the_ones_behind_it(
    tmp_path: Path,
) -> None:
    """Three reasons to skip one job, and a fourth job that is fine. Each skip
    is that job's alone: a tenant's whole offer list must not end at the first
    workflow that is unproven, unevidenced, or starts somewhere unproven."""
    store = _store(tmp_path)
    _workflow(store, "wfl_unproven", unproven=["the save was never confirmed"])
    save_workflow(
        store,
        Workflow(
            id="wfl_uncited",
            tenant="acme",
            title="cites nothing the store holds",
            narrative="n",
            steps=[Step(order=0, says="s", system=None, cites=["ges_remined_away"])],
        ),
    )
    _workflow(store, "wfl_elsewhere")
    _saver_first(store, "wfl_fine")
    typed = next(
        r["id"]
        for r in store.query("SELECT id, gesture_json FROM gestures")
        if json.loads(r["gesture_json"]).get("value") == "ACME-4471"
    )
    with store.connect() as connection:
        connection.execute(
            "UPDATE gestures SET page_url = ? WHERE id = ?", ("https://other.example/x", typed)
        )

    assert [s.id for s in shapes_for(store, "acme")] == ["wfl_fine"]


def test_a_parameter_the_workflow_declares_badly_is_dropped_rather_than_served(
    tmp_path: Path,
) -> None:
    """A parameter with no name is not a parameter the extension can fill, and
    one with no recorded values was simply never typed anywhere."""
    store = _store(tmp_path)
    wf = _workflow(store)
    wf.parameters = [{"seen_values": ["ACME-4471"]}, {"name": "notes"}, *wf.parameters]
    save_workflow(store, wf)

    [shape] = shapes_for(store, "acme")

    assert shape.parameters == [
        {"name": "notes", "at": None},
        {"name": "clientCode", "at": 0},
    ]


def test_a_job_whose_first_step_is_only_a_scroll_still_says_where_it_begins(
    tmp_path: Path,
) -> None:
    """`primary_gesture` has nothing to return when every gesture the first
    step cites is a scroll, and the job still begins somewhere."""
    store = _store(tmp_path)
    workflow = _workflow(store)
    workflow.steps[0].cites = [_scroll(store)]
    workflow.steps[0].parameters = []
    save_workflow(store, workflow)

    [shape] = shapes_for(store, "acme")

    assert shape.starts_on and shape.starts_on.startswith("http://127.0.0.1:63319")


def test_a_stored_key_from_an_older_rule_is_recomputed_once(tmp_path: Path) -> None:
    from rig.mine import rekey_workflows

    store = _store(tmp_path)
    wf = _workflow(store)
    stale = [
        ["https://old", "text|a paragraph of page copy that no longer names anything", "click"]
    ]
    wf.shape_key = stale
    save_workflow(store, wf)

    assert rekey_workflows(store, "acme") == 1
    row = store.query("SELECT shape_key FROM workflows WHERE id = 'wfl_1'")[0]
    key = json.loads(row["shape_key"])
    # One triple per cited gesture, in step order: the typed code, then the
    # save -- the key the cited gestures make now, not the one written before.
    assert key != stale and len(key) == 2 and [t[2] for t in key] == ["type", "click"]
    assert rekey_workflows(store, "acme") == 0, "a key that agrees is left alone"


def test_a_workflow_whose_evidence_is_partly_gone_keeps_its_key(tmp_path: Path) -> None:
    from rig.mine import rekey_workflows

    store = _store(tmp_path)
    wf = _workflow(store)
    wf.steps[0].cites.append("ges_gone_with_its_batch")
    stale = [["https://old", "text|whatever it was", "click"]]
    wf.shape_key = stale
    save_workflow(store, wf)

    assert rekey_workflows(store, "acme") == 0
    row = store.query("SELECT shape_key FROM workflows WHERE id = 'wfl_1'")[0]
    assert json.loads(row["shape_key"]) == stale, "not rekeyed over the survivors"
