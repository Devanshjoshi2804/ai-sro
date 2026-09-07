"""Ported from `new_agent_arch/tests/test_umbrella.py`, names unchanged.

Only the tests that do not call `propose`. `propose` asks a model and belongs to
the mining use case, so the fifteen tests that drive `workflow_from` through it
travel with that task instead; they are named in this task's report.
"""

import copy
import json

from sro.domain.observation.window import K_ENDS, K_WINDOW_TOKENS, Packed, Window, pack, tokens
from sro.domain.skill.umbrella import (
    INSTRUCTIONS,
    K_MAX_CROSSING_TOKENS,
    WORKFLOW_SCHEMA,
    bounded_crossings,
    build_prompt,
    workflow_from,
)
from tests.unit.domain.rig.conftest import gestures as _gestures


def _map(value: object) -> dict[str, object]:
    """WORKFLOW_SCHEMA is `dict[str, object]` -- `Any` is banned in the domain --
    so walking into it needs a narrowing step per level."""
    assert isinstance(value, dict)
    return value


def _window() -> Window:
    items = [
        Packed("ges_1", 1.0, {"id": "ges_1", "gesture": {"kind": "type"}}, 2.0, 10),
        Packed("ges_2", 2.0, {"id": "ges_2", "gesture": {"kind": "click"}}, 1.0, 10),
    ]
    return Window(items=items, spent=20, left_out=[])


def test_the_schema_puts_the_citations_before_the_sentence() -> None:
    """Identifying the relevant evidence before composing the answer measurably
    beats composing first."""
    workflows = _map(_map(WORKFLOW_SCHEMA["properties"])["workflows"])
    step = _map(_map(workflows["items"])["properties"])["steps"]
    keys = list(_map(_map(_map(step)["items"])["properties"]).keys())

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
    seed = _gestures()
    gestures = []
    for run in range(220):
        for gesture in seed:
            dup = copy.deepcopy(gesture)
            dup.id = f"{gesture.id}_{run}"
            gestures.append(dup)

    known: list[dict[str, object]] = [
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
    # Every id is one of the window's own: build_prompt names only what the
    # model may cite, so a crossing over ids outside it is not a block this cap
    # could ever have to bound.
    crossings = {f"ACME-{n:05d}": ["ges_1", "ges_2"] * 3 for n in range(5_000)}

    prompt = build_prompt(_window(), crossings, [], "")
    # json.dumps(indent=1) never writes a blank line, so the blank line between
    # sections is where the block ends.
    block = prompt.split("## Values appearing in more than one system\n")[1].split("\n\n")[0]

    assert tokens(block) <= K_MAX_CROSSING_TOKENS
    assert "ACME-00000" in block, "the crossings that fit are still there"


def test_every_section_adds_to_the_prompt_rather_than_replacing_it() -> None:
    """`parts +=` and `parts =` look alike and differ by everything.

    Assigning instead of appending at any of the optional sections drops the
    instructions AND the evidence that came before it -- and the citation
    requirement is the thing that took hallucinated steps from 21% to under
    7.5%. A prompt that quietly lost it would still return workflows, and they
    would be worse in a way no assertion here was watching for.
    """
    crossings = {"SUP-1": ["ges_1", "ges_2"]}
    known: list[dict[str, object]] = [
        {"id": "wfl_1", "title": "a job already proven", "shape_key": ["x"]}
    ]

    prompt = build_prompt(_window(), crossings, known, "the knowledge base")

    for section in (
        INSTRUCTIONS[:40],
        "## The day",
        "ges_1",
        "## Values appearing in more than one system",
        "## Jobs already proven",
        "a job already proven",
        "## What is known about these systems",
        "the knowledge base",
    ):
        assert section in prompt, section
    assert prompt.rstrip().endswith(INSTRUCTIONS.strip()[-40:]), "and the task is still restated"


def test_a_crossing_too_big_to_fit_does_not_take_the_smaller_ones_with_it() -> None:
    """`break` walks away from every crossing after the one that overflowed, and
    they are sorted by how many gestures carry them -- so the entry that breaks
    the budget is followed by the cheapest, most numerous links, which are
    exactly the ones worth keeping. Bounded means bounded, not truncated at the
    first expensive value."""
    huge = {"HUGE": [f"ges_{n}" for n in range(K_MAX_CROSSING_TOKENS)]}
    small = {f"S{n}": [f"ges_{n}", f"ges_{n + 1}"] for n in range(3)}

    kept = bounded_crossings({**huge, **small})

    assert "HUGE" not in kept, "it does not fit"
    assert kept == small, "and the ones that do come through whole, ids and all"


def test_a_proposal_missing_its_optional_fields_is_still_a_workflow() -> None:
    """Everything here came off the model. `systems`, `parameters`, `unproven`
    and `same_as` are all optional in practice -- a model that returned only
    the required fields would have crashed the parse on a missing key rather
    than being read as a workflow with none of them."""
    bare = {
        "title": "a job",
        "narrative": "what happened",
        "steps": [{"order": 0, "says": "did a thing", "cites": ["ges_1"]}],
    }

    workflow = workflow_from(bare, tenant="acme")

    assert workflow is not None
    assert workflow.title == "a job"
    assert (workflow.systems, workflow.parameters, workflow.unproven) == ([], [], [])
    assert workflow.same_as is None
    assert workflow.steps[0].parameters == []


def test_the_model_saying_which_job_this_already_is_survives_the_parse() -> None:
    """`same_as` is how a proposal says it recognised an existing workflow, and
    identity reads it. Dropped, every re-reading of a known job looks new."""
    said = {
        "title": "a job",
        "narrative": "what happened",
        "same_as": "wfl_already_known",
        "steps": [{"order": 0, "says": "did a thing", "cites": ["ges_1"]}],
    }

    workflow = workflow_from(said, tenant="acme")

    assert workflow is not None and workflow.same_as == "wfl_already_known"
    also = workflow_from({**said, "same_as": 7}, tenant="acme")
    assert also is not None and also.same_as is None, "and only a string"
