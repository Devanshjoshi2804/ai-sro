from sro.domain.skill.workflow import Step, Workflow, cited_ids, new_workflow_id


def _workflow(**over: object) -> Workflow:
    base: dict[str, object] = {
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
        "pass_id": "pas_1",
    }
    return Workflow(**{**base, **over})


def test_a_workflow_id_has_the_rig_shape() -> None:
    assert new_workflow_id().startswith("wfl_") and len(new_workflow_id()) == 36


def test_cited_ids_gathers_every_step() -> None:
    assert cited_ids(_workflow()) == {"ges_1", "ges_2", "ges_3"}
