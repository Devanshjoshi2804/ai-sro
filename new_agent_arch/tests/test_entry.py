from rig.entry import UNDERSTAND_SCHEMA, understand
from rig.models import Answer, FakeAsker
from rig.workflows import Step, Workflow

WFS = [
    Workflow(
        id="wfl_1",
        tenant="acme",
        title="create a client",
        narrative="n",
        steps=[Step(order=0, says="s", system=None, cites=["g"])],
        parameters=[{"name": "clientCode", "seen_values": ["A"]}],
    )
]


async def test_an_utterance_is_read_against_the_workflows_held_and_asks_for_what_is_missing() -> (
    None
):
    asker = FakeAsker(
        Answer(data={"workflow_id": "wfl_1", "values": {"clientCode": "NEW9"}, "missing": []})
    )
    got = await understand("create client NEW9", WFS, asker, "m")
    assert got.workflow_id == "wfl_1" and got.values == {"clientCode": "NEW9"} and got.missing == []
    assert "create a client" in asker.asked[0]["evidence"], (
        "the workflows are what it reads against"
    )


async def test_a_workflow_the_rig_does_not_hold_is_not_offered() -> None:
    got = await understand(
        "x",
        WFS,
        FakeAsker(Answer(data={"workflow_id": "wfl_nope", "values": {}, "missing": []})),
        "m",
    )
    assert got.workflow_id is None


async def test_a_value_for_a_parameter_the_workflow_does_not_declare_is_dropped() -> None:
    got = await understand(
        "x",
        WFS,
        FakeAsker(
            Answer(
                data={
                    "workflow_id": "wfl_1",
                    "values": {"clientCode": "A", "evil": "b"},
                    "missing": [],
                }
            )
        ),
        "m",
    )
    assert got.values == {"clientCode": "A"}


def test_the_schema_is_the_specs() -> None:
    assert set(UNDERSTAND_SCHEMA["properties"]) == {"workflow_id", "values", "missing"}
