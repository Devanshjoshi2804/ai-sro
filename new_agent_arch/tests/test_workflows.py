from pathlib import Path

from rig.store import Store
from rig.workflows import (
    Step,
    Workflow,
    cited_ids,
    known_workflows,
    new_workflow_id,
    save_workflow,
)


def _store(tmp_path: Path) -> Store:
    store = Store(tmp_path / "rig.db")
    store.migrate()
    return store


def _workflow(**over) -> Workflow:
    base = {
        "id": new_workflow_id(),
        "tenant": "acme",
        "title": "create a supplier",
        "narrative": "the operator created a supplier and set its status",
        "systems": ["https://wms.example", "https://sap.example"],
        "steps": [
            Step(
                order=0,
                says="create the supplier",
                system="https://wms.example",
                cites=["ges_1", "ges_2"],
                parameters=["supplier_name"],
            ),
            Step(
                order=1,
                says="set the status",
                system="https://sap.example",
                cites=["ges_3"],
                parameters=[],
            ),
        ],
        "parameters": [{"name": "supplier_name", "seen_values": ["TestYonder2"]}],
        "shape_key": [["https://wms.example", "clientCode", "type"]],
        "same_as": None,
        "unproven": ["ges_9"],
        "cost_usd": 0.42,
        "unpriced": False,
    }
    return Workflow(**{**base, **over})


def test_a_workflow_survives_a_round_trip(tmp_path: Path) -> None:
    store = _store(tmp_path)
    workflow = _workflow()

    save_workflow(store, workflow)
    back = known_workflows(store, "acme")

    assert len(back) == 1
    assert back[0].title == "create a supplier"
    assert [s.says for s in back[0].steps] == ["create the supplier", "set the status"]
    assert back[0].steps[0].cites == ["ges_1", "ges_2"]
    assert back[0].systems == ["https://wms.example", "https://sap.example"]


def test_the_cost_of_proving_it_is_kept(tmp_path: Path) -> None:
    """The umbrella pass is the most expensive call in the system."""
    store = _store(tmp_path)

    save_workflow(store, _workflow(cost_usd=1.25, unpriced=True))
    back = known_workflows(store, "acme")[0]

    assert back.cost_usd == 1.25
    assert back.unpriced is True


def test_another_tenants_workflows_are_not_returned(tmp_path: Path) -> None:
    store = _store(tmp_path)
    save_workflow(store, _workflow(tenant="acme"))
    save_workflow(store, _workflow(tenant="other"))

    assert len(known_workflows(store, "acme")) == 1


def test_cited_ids_gathers_every_step(tmp_path: Path) -> None:
    assert cited_ids(_workflow()) == {"ges_1", "ges_2", "ges_3"}


def test_saving_the_same_workflow_twice_keeps_one(tmp_path: Path) -> None:
    store = _store(tmp_path)
    workflow = _workflow()

    save_workflow(store, workflow)
    save_workflow(store, workflow)

    assert len(known_workflows(store, "acme")) == 1
    assert len(known_workflows(store, "acme")[0].steps) == 2
