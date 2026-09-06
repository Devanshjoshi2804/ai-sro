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
        Answer(
            data={
                "workflow_id": "wfl_1",
                "values": [{"name": "clientCode", "value": "NEW9"}],
                "missing": [],
            }
        )
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
        FakeAsker(Answer(data={"workflow_id": "wfl_nope", "values": [], "missing": []})),
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
                    "values": [
                        {"name": "clientCode", "value": "A"},
                        {"name": "evil", "value": "b"},
                    ],
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
        FakeAsker(Answer(data={"workflow_id": "wfl_1", "values": [], "missing": []})),
        "m",
    )
    assert got.missing == ["clientCode"]


async def test_a_value_the_model_invented_a_name_for_leaves_its_parameter_missing() -> None:
    got = await understand(
        "make one",
        WFS,
        FakeAsker(
            Answer(
                data={
                    "workflow_id": "wfl_1",
                    "values": [{"name": "evil", "value": "b"}],
                    "missing": ["nothing"],
                }
            )
        ),
        "m",
    )
    assert got.values == {} and got.missing == ["clientCode"]


async def test_the_model_that_named_nothing_still_hands_back_what_it_cost() -> None:
    """Every gesture gets a reading, and a refusal is one too: the answer is
    carried on all three ways out, so the caller can bill it."""
    for data in (None, {"workflow_id": "wfl_nope", "values": [], "missing": []}):
        answer = Answer(data=data, cost_usd=0.0003, in_tokens=120)
        got = await understand("x", WFS, FakeAsker(answer), "m")
        assert got.workflow_id is None
        assert got.answer is answer

    named = Answer(data={"workflow_id": "wfl_1", "values": [], "missing": []}, cost_usd=0.0009)
    got = await understand("x", WFS, FakeAsker(named), "m")
    assert got.answer is named


async def test_the_reading_is_asked_of_the_model_it_was_given_under_the_declared_schema() -> None:
    asker = FakeAsker(Answer(data={"workflow_id": "wfl_1", "values": [], "missing": []}))
    await understand("x", WFS, asker, "gemini-3.8-flash")
    [asked] = asker.asked
    assert asked["model"] == "gemini-3.8-flash"
    assert asked["schema"] is UNDERSTAND_SCHEMA, "structured output, or the reading is prose"
    assert asked["instructions"], "a model told nothing answers about nothing"


def test_no_schema_in_the_package_uses_what_the_developer_api_refuses() -> None:
    """`additionalProperties` is refused by the Gemini Developer API with a
    400 -- "only supported in Gemini Enterprise Agent Platform mode". The
    chat door shipped with one and had never met the real API; every schema
    the package asks under is walked here so the next one cannot."""
    import importlib
    import pkgutil

    import rig

    def walk(node: object, at: str) -> list[str]:
        found = []
        if isinstance(node, dict):
            if "additionalProperties" in node:
                found.append(at)
            for k, v in node.items():
                found += walk(v, f"{at}.{k}")
        elif isinstance(node, list):
            for i, v in enumerate(node):
                found += walk(v, f"{at}[{i}]")
        return found

    offenders = []
    for info in pkgutil.iter_modules(rig.__path__):
        module = importlib.import_module(f"rig.{info.name}")
        for name in dir(module):
            if name.endswith("_SCHEMA") and isinstance(getattr(module, name), dict):
                offenders += walk(getattr(module, name), f"rig.{info.name}.{name}")
    assert offenders == [], offenders
