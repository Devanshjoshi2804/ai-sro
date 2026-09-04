from rig.models import Answer, FakeAsker
from rig.umbrella import (
    INSTRUCTIONS,
    K_SAMPLES,
    WORKFLOW_SCHEMA,
    build_prompt,
    propose,
)
from rig.window import Packed, Window

MODEL = "gemini-3.1-pro"


def _window() -> Window:
    items = [
        Packed("ges_1", 1.0, {"id": "ges_1", "gesture": {"kind": "type"}}, 2.0, 10),
        Packed("ges_2", 2.0, {"id": "ges_2", "gesture": {"kind": "click"}}, 1.0, 10),
    ]
    return Window(items=items, spent=20, left_out=[])


def _answer(**over) -> Answer:
    base = {
        "workflows": [
            {
                "title": "create a supplier",
                "narrative": "the operator created a supplier",
                "systems": ["https://wms.example"],
                "steps": [
                    {
                        "order": 0,
                        "cites": ["ges_1"],
                        "says": "type the code",
                        "system": "https://wms.example",
                        "parameters": ["code"],
                    }
                ],
                "parameters": [{"name": "code", "seen_values": ["ACME"]}],
                "same_as": None,
                "unproven": ["ges_2"],
            }
        ]
    }
    return Answer(data={**base, **over}, in_tokens=1000, out_tokens=200, cost_usd=0.004)


def test_the_schema_puts_the_citations_before_the_sentence() -> None:
    """Identifying the relevant evidence before composing the answer measurably
    beats composing first."""
    step = WORKFLOW_SCHEMA["properties"]["workflows"]["items"]["properties"]["steps"]
    keys = list(step["items"]["properties"].keys())

    assert keys.index("cites") < keys.index("says")


def test_the_task_is_stated_at_both_ends_of_the_prompt() -> None:
    """Question-first was strongest at long context, and restating the
    constraints after the evidence costs almost nothing."""
    prompt = build_prompt(_window(), {}, [], "")

    assert prompt.startswith(INSTRUCTIONS[:40])
    assert prompt.rstrip().endswith(INSTRUCTIONS.strip()[-40:])


def test_the_evidence_is_in_the_prompt_in_window_order() -> None:
    prompt = build_prompt(_window(), {}, [], "")

    assert prompt.index("ges_1") < prompt.index("ges_2")


def test_a_crossing_is_labelled_but_never_called_important() -> None:
    """Telling a model which context is most relevant was measured to REDUCE
    accuracy in all five languages tested."""
    prompt = build_prompt(_window(), {"TestYonder2": ["ges_1", "ges_2"]}, [], "")

    assert "TestYonder2" in prompt
    assert "most relevant" not in prompt.lower()
    assert "most important" not in prompt.lower()


async def test_a_proposal_becomes_a_workflow() -> None:
    workflows, answer = await propose(
        _window(), {}, [], "", asker=FakeAsker(_answer()), model=MODEL, tenant="acme"
    )

    assert len(workflows) == 1
    assert workflows[0].title == "create a supplier"
    assert workflows[0].steps[0].cites == ["ges_1"]
    assert workflows[0].unproven == ["ges_2"]
    assert answer.cost_usd == 0.004


async def test_the_pass_carries_its_own_cost() -> None:
    """The umbrella pass is the most expensive call in the system."""
    workflows, _ = await propose(
        _window(), {}, [], "", asker=FakeAsker(_answer()), model=MODEL, tenant="acme"
    )

    assert workflows[0].cost_usd == 0.004
    assert workflows[0].unpriced is False


async def test_a_refusal_proposes_nothing_and_says_why() -> None:
    workflows, answer = await propose(
        _window(),
        {},
        [],
        "",
        asker=FakeAsker(Answer(error="503")),
        model=MODEL,
        tenant="acme",
    )

    assert workflows == []
    assert answer.error == "503"


async def test_a_malformed_answer_does_not_take_the_pass_down() -> None:
    """The schema is advisory. A model returning workflows as a string, or a
    step as a number, must cost the pass -- not the process."""
    for junk in ("not a list", {"a": "dict"}, [1, 2, 3], None):
        workflows, _ = await propose(
            _window(),
            {},
            [],
            "",
            asker=FakeAsker(_answer(workflows=junk)),
            model=MODEL,
            tenant="acme",
        )

        assert workflows == []


async def test_one_sample_by_default() -> None:
    asker = FakeAsker(_answer())

    await propose(_window(), {}, [], "", asker=asker, model=MODEL, tenant="acme")

    assert len(asker.asked) == 1
    assert K_SAMPLES == 1
