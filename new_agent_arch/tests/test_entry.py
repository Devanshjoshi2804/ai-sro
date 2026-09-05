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


async def test_a_parameter_with_no_value_is_missing_whatever_the_model_says() -> None:
    """The model's own `missing` is read and ignored: it is the one field it
    can get wrong in the direction that matters, because a parameter dropped
    from `missing` is a parameter the form never asks for and the run then
    performs with whatever the recording happened to contain."""
    got = await understand(
        "make one",
        WFS,
        FakeAsker(Answer(data={"workflow_id": "wfl_1", "values": {}, "missing": []})),
        "m",
    )
    assert got.missing == ["clientCode"]


async def test_a_value_the_model_invented_a_name_for_leaves_its_parameter_missing() -> None:
    got = await understand(
        "make one",
        WFS,
        FakeAsker(
            Answer(data={"workflow_id": "wfl_1", "values": {"evil": "b"}, "missing": ["nothing"]})
        ),
        "m",
    )
    assert got.values == {} and got.missing == ["clientCode"]
