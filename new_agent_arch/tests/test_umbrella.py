import json
from pathlib import Path
from typing import Any

from rig.models import Answer, FakeAsker
from rig.store import Store
from rig.umbrella import (
    INSTRUCTIONS,
    K_EFFORT,
    K_SAMPLES,
    WORKFLOW_SCHEMA,
    build_prompt,
    propose,
)
from rig.window import Packed, Window
from rig.workflows import Workflow, known_workflows, save_workflow

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


def _one(**over: Any) -> dict[str, Any]:
    """The well-formed workflow out of `_answer`, with fields replaced."""
    data = _answer().data
    assert data is not None
    return {**data["workflows"][0], **over}


async def _propose_one(workflow: dict[str, Any]) -> list[Workflow]:
    workflows, _ = await propose(
        _window(),
        {},
        [],
        "",
        asker=FakeAsker(_answer(workflows=[workflow])),
        model=MODEL,
        tenant="acme",
    )
    return workflows


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


async def test_a_steps_list_that_is_not_a_list_costs_the_workflow() -> None:
    """The test above malforms the workflows list. A model is at least as
    likely to return a good list with a bad `steps` in it, and every guard
    below that line had nothing exercising it."""
    for junk in ("one two three", 7, None, {"a": "dict"}):
        assert await _propose_one(_one(steps=junk)) == []


async def test_a_step_that_is_not_a_step_is_dropped() -> None:
    """`steps` is a list, so the workflow stands -- but 1 has no .get()."""
    for junk in ([1, 2, 3], [None], ["one", "two"], [["order", 0]]):
        workflows = await _propose_one(_one(steps=junk))

        assert workflows[0].steps == []


async def test_a_junk_field_inside_a_step_falls_back_to_nothing() -> None:
    """says, system, cites and parameters, one level below where the malformed
    answer test stops."""
    workflows = await _propose_one(
        _one(steps=[{"order": 0, "says": 7, "system": 7, "cites": "ges_1", "parameters": "code"}])
    )
    step = workflows[0].steps[0]

    assert step.says == ""
    assert step.system is None
    assert step.cites == []
    assert step.parameters == []

    workflows = await _propose_one(
        _one(
            steps=[
                {
                    "order": 0,
                    "says": "s",
                    "system": "https://wms.example",
                    "cites": ["ges_1", 7, None],
                    "parameters": ["code", 7],
                }
            ]
        )
    )
    step = workflows[0].steps[0]

    assert step.cites == ["ges_1"]
    assert step.parameters == ["code"]


async def test_a_junk_field_beside_the_steps_falls_back_to_nothing() -> None:
    """title, narrative, systems, unproven and same_as."""
    workflows = await _propose_one(
        _one(title=7, narrative=7, systems="wms", unproven="ges_2", same_as=7)
    )
    workflow = workflows[0]

    assert workflow.title == ""
    assert workflow.narrative == ""
    assert workflow.systems == []
    assert workflow.unproven == []
    assert workflow.same_as is None

    workflows = await _propose_one(_one(systems=["a", 7], unproven=["ges_2", None]))

    assert workflows[0].systems == ["a"]
    assert workflows[0].unproven == ["ges_2"]


async def test_two_steps_claiming_the_same_order_can_still_be_stored(tmp_path: Path) -> None:
    """PRIMARY KEY (workflow_id, ord). "order": 1 twice is schema-valid, so a
    model that repeats itself produced a workflow that raised IntegrityError on
    the way into the store."""
    workflows = await _propose_one(
        _one(
            steps=[
                {"order": 1, "cites": ["ges_1"], "says": "first"},
                {"order": 1, "cites": ["ges_2"], "says": "second"},
            ]
        )
    )
    store = Store(tmp_path / "rig.db")
    store.migrate()

    save_workflow(store, workflows[0])
    back = known_workflows(store, "acme")

    assert [step.order for step in workflows[0].steps] == [0, 1]
    assert len(back[0].steps) == 2


async def test_steps_the_model_numbered_itself_keep_their_numbering() -> None:
    """Renumbering is for a repeated order, not for every answer."""
    workflows = await _propose_one(
        _one(
            steps=[
                {"order": 5, "cites": ["ges_1"], "says": "first"},
                {"order": 9, "cites": ["ges_2"], "says": "second"},
            ]
        )
    )

    assert [step.order for step in workflows[0].steps] == [5, 9]


async def test_one_sample_by_default() -> None:
    asker = FakeAsker(_answer())

    await propose(_window(), {}, [], "", asker=asker, model=MODEL, tenant="acme")

    assert len(asker.asked) == 1
    assert K_SAMPLES == 1


async def test_the_task_is_not_repeated_outside_the_prompt() -> None:
    """build_prompt states the task at both ends, which is the measured
    decision. Sending it as the instruction too put it in three times, twice
    adjacently, on the most expensive call in the system."""
    asker = FakeAsker(_answer())

    await propose(_window(), {}, [], "", asker=asker, model=MODEL, tenant="acme")

    assert asker.asked[0]["instructions"] == ""
    assert asker.asked[0]["evidence"].count(INSTRUCTIONS.strip()) == 2


async def test_the_pass_asks_for_the_effort_it_names() -> None:
    """K_SAMPLES is 1 because self-consistency bought 0.4% for 20x the cost.
    Effort is the knob that replaced it, so it has to reach the API."""
    asker = FakeAsker(_answer())

    await propose(_window(), {}, [], "", asker=asker, model=MODEL, tenant="acme")

    assert asker.asked[0]["effort"] == K_EFFORT


async def test_a_step_order_of_true_is_not_a_step_order() -> None:
    """True is an int in Python, and sorts as 1."""
    answer = _answer(
        workflows=[
            {
                "title": "t",
                "narrative": "n",
                "systems": ["https://wms.example"],
                "steps": [
                    {
                        "order": True,
                        "cites": ["ges_1"],
                        "says": "s",
                        "system": "https://wms.example",
                        "parameters": [],
                    }
                ],
                "parameters": [],
                "same_as": None,
                "unproven": [],
            }
        ]
    )

    workflows, _ = await propose(
        _window(), {}, [], "", asker=FakeAsker(answer), model=MODEL, tenant="acme"
    )

    assert workflows[0].steps[0].order == 0
    assert workflows[0].steps[0].order is not True


async def test_a_parameter_with_no_name_is_not_a_parameter() -> None:
    """Every other container in _as_workflow is checked down to a scalar; this
    one filtered to dict and stopped."""
    answer = _answer(
        workflows=[
            {
                "title": "t",
                "narrative": "n",
                "steps": [{"order": 0, "cites": ["ges_1"], "says": "s"}],
                "parameters": [
                    {"name": "code", "seen_values": ["ACME"]},
                    {"seen_values": ["nameless"]},
                    {"name": "", "seen_values": ["empty"]},
                    {"name": 7, "seen_values": ["not a string"]},
                ],
            }
        ]
    )

    workflows, _ = await propose(
        _window(), {}, [], "", asker=FakeAsker(answer), model=MODEL, tenant="acme"
    )

    assert [p["name"] for p in workflows[0].parameters] == ["code"]


async def test_a_step_parameter_is_judged_by_the_same_rule() -> None:
    """The ninth sibling: `parameters` at step level and `parameters` at
    workflow level arrive from one model answer, and only one of them was
    checked for a usable name. The shapes differ because the schema declares
    them differently -- a step names a parameter, a workflow declares one --
    but "no usable name is no parameter" is now one rule at both."""
    answer = _answer(
        workflows=[
            {
                "title": "t",
                "narrative": "n",
                "steps": [
                    {
                        "order": 0,
                        "cites": ["ges_1"],
                        "says": "s",
                        "parameters": ["code", "", "   ", 7, None],
                    }
                ],
                "parameters": [{"name": "code"}, {"name": "   "}],
            }
        ]
    )

    workflows, _ = await propose(
        _window(), {}, [], "", asker=FakeAsker(answer), model=MODEL, tenant="acme"
    )

    assert workflows[0].steps[0].parameters == ["code"]
    assert [p["name"] for p in workflows[0].parameters] == ["code"]


def test_strength_never_reaches_the_prompt() -> None:
    """Telling a model which evidence is most relevant was measured to reduce
    accuracy, so strength orders the window and is never stated. That was held
    structurally -- build_prompt serialises item.evidence and never the Packed
    -- and structure is not a regression test."""
    window = _window()
    for item in window.items:
        item.strength = 99.0
        item.tokens = 4242

    prompt = build_prompt(window, {}, [], "")

    assert "99.0" not in prompt
    assert "4242" not in prompt
    assert "strength" not in prompt.lower()


def test_the_strongest_evidence_is_at_both_ends_of_the_prompt() -> None:
    """`arrange` was defined, documented in three places and called by nothing
    but its own unit test, so the reordering algorithms.md and window.py's own
    docstring both describe was absent from every prompt this branch sent.

    The middle stays in time order -- a workflow is a sequence -- and `pack`
    still hands back a time-ordered window, because checks.coverage slices it
    into TIME deciles.
    """
    from rig.window import K_ENDS

    window = Window(
        items=[Packed(f"ges_{n}", float(n), {"id": f"ges_{n}"}, float(n), 10) for n in range(40)]
    )

    order = [
        int(line.split("ges_")[1].rstrip('",'))
        for line in build_prompt(window, {}, [], "").splitlines()
        if "ges_" in line
    ]

    assert order[0] == 39, "the strongest evidence opens the prompt"
    assert order[-1] == 38, "the second strongest closes it"
    assert order[K_ENDS // 2 : -K_ENDS // 2] == sorted(order[K_ENDS // 2 : -K_ENDS // 2])
    assert [item.at for item in window.items] == sorted(item.at for item in window.items)


def test_a_window_packed_to_the_budget_still_fits_the_budget() -> None:
    """The assertion nobody wrote, and the only one that catches this.

    pack() budgeted each item as compact JSON while build_prompt ships the list
    at indent=1, and subtracted neither INSTRUCTIONS (twice), nor the response
    schema, nor the crossings block. Measured on the real 83-gesture acme
    window the item ratio alone is 1.176, so a window filled to
    K_WINDOW_TOKENS shipped ~177,000 tokens -- over the 200K boundary this
    budget exists to stay under, at double the input price.

    The schema is counted because it is sent with the call and billed as input.
    """
    import copy

    from rig.correlate import correlate
    from rig.window import K_WINDOW_TOKENS, pack, tokens
    from rig.wire import Batch
    from tests.fixtures import BATCH

    seed, _, _, _ = correlate(Batch.model_validate(BATCH), "acme")
    gestures = []
    for run in range(220):
        for gesture in seed:
            dup = copy.deepcopy(gesture)
            dup.id = f"{gesture.id}_{run}"
            gestures.append(dup)

    known = [
        {"id": f"wf_{n}", "title": "create a supplier", "systems": ["https://wms.example"]}
        for n in range(30)
    ]
    crossings = {f"ACME-{n:04d}": [f"ges_{n}", f"ges_{n + 1}"] for n in range(400)}
    kb = "The WMS is Blue Yonder. " * 200

    window = pack(gestures, {}, [], known, kb)

    assert window.left_out, "the budget must actually bite, or this proves nothing"
    shipped = tokens(build_prompt(window, crossings, known, kb)) + tokens(
        json.dumps(WORKFLOW_SCHEMA)
    )
    assert shipped <= K_WINDOW_TOKENS, f"prompt is {shipped} tokens against {K_WINDOW_TOKENS}"


def test_the_crossings_block_cannot_outgrow_the_window_it_hints_at() -> None:
    """`crossings` is computed over the whole store, so it grows with capture
    rather than with the window -- and nothing bounded it or budgeted it."""
    from rig.umbrella import K_MAX_CROSSING_TOKENS
    from rig.window import tokens

    crossings = {f"ACME-{n:05d}": [f"ges_{n}"] * 6 for n in range(5_000)}

    prompt = build_prompt(_window(), crossings, [], "")
    # json.dumps(indent=1) never writes a blank line, so the blank line between
    # sections is where the block ends.
    block = prompt.split("## Values appearing in more than one system\n")[1].split("\n\n")[0]

    assert tokens(block) <= K_MAX_CROSSING_TOKENS
    assert "ACME-00000" in block, "the crossings that fit are still there"
