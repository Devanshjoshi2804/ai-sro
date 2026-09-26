"""Ported from `new_agent_arch/tests/test_umbrella.py`, names unchanged.

Only the tests that do not call `propose`. `propose` asks a model and belongs to
the mining use case, so the fifteen tests that reach it travel with that task
instead; they are named in this task's report. Eight of those fifteen are really
`workflow_from` tests wearing a `propose` costume and are ported against the
function directly over there; five genuinely need `propose` -- one of them
guards `propose`'s own `isinstance(raw, list)` and never reaches `workflow_from`
at all -- and two are portable only by dropping an assertion.
"""

import copy
import hashlib
import json

from sro.domain.observation.window import (
    K_ENDS,
    K_WINDOW_TOKENS,
    Packed,
    Window,
    arrange,
    pack,
    tokens,
)
from sro.domain.prompts.mine import MINE
from sro.domain.skill.umbrella import (
    _PROBE_DAY,
    K_MAX_CROSSING_TOKENS,
    bounded_crossings,
    mining_blocks,
    workflow_from,
)
from tests.unit.domain.rig.conftest import gestures as _gestures

ROLE_AND_TASK = MINE.role + "\n\n" + MINE.task


def _blocks(
    window: Window, crossings: dict[str, list[str]], known: list[dict[str, object]], kb: str
) -> dict[str, str]:
    return mining_blocks([item.evidence for item in arrange(window.items)], crossings, known, kb)


def _shown(
    window: Window, crossings: dict[str, list[str]], known: list[dict[str, object]], kb: str
) -> str:
    return "\n".join(_blocks(window, crossings, known, kb).values())


def _map(value: object) -> dict[str, object]:
    """MINE.output_schema is `dict[str, object]` -- `Any` is banned in the domain --
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
    workflows = _map(_map(MINE.output_schema["properties"])["workflows"])
    step = _map(_map(workflows["items"])["properties"])["steps"]
    keys = list(_map(_map(_map(step)["items"])["properties"]).keys())

    assert keys.index("cites") < keys.index("says")


def test_the_prompt_the_model_is_given_is_the_one_the_rig_measured() -> None:
    """The prompt IS the product, and nothing pinned ROLE_AND_TASK beyond its
    first and last 40 characters -- a reworded middle instruction shipped green.
    The hash was the rig's own, sha256 of `new_agent_arch/src/rig/umbrella.py`'s
    ROLE_AND_TASK, and it is what the port's parity was proved with in review;
    proved-once in a review that is now gone is not a guarantee.

    It is no longer the rig's, and this is why the model reads something else:
    the rig's prompt never said what a title is for, so the model named each
    job after the one doing it was reading -- "Create Customer Type DSS" over a
    customer type since observed as DSS, DPP, CCD and CCF. The paragraph added
    is the only place a title can be got right on a FIRST doing, where nothing
    yet knows which of its values vary.

    And it says what a job is for, which is the second thing the rig's prompt
    left to the model's judgment. The first pass over this tenant's readings
    proposed **Search Mail** -- two steps, "navigate to the Inbox" and "type a
    query into the search bar", parameter `cvv` -- and every check kept it: it
    is not the apparatus, not a transit hop, not a sign-in, and `is_write` sees
    Gmail POST its own sync traffic on every gesture and calls it a write. No
    rule available here separates looking something up from doing something,
    because structurally there is nothing between them; the difference is what
    the job was FOR, which is a question only the model reading it can answer.
    So it is asked.

    And it says that a job done four times is one job. The miner folded
    repetition into length instead: the same real day mined three times gave
    `Create a Customer Type` as 5 steps twice and as **17 steps** once, with
    all four doings inline and no parameters. Steps are what is always done and
    parameters are what varies, and nothing had ever said so.

    And it says what the "Jobs already proven" block is FOR, which the prompt
    handed the model with no guidance at all. Left to infer, the model treated
    it as a list of things not to report: an acme pass over 247 gestures
    proposed ONE job and filed **226 gestures under `unplaced`**, 160 of them
    on the warehouse host, its own readings of them saying "save new equipment
    type", "create work operation", "create activity code". That is the work,
    declined because a job of that name was already stored -- and a second
    doing is the only thing `learn_parameters` can widen a parameter from, so
    skipping repeats also starved the one mechanism that makes a job general.

    And it no longer asks which values look like the same thing appearing in
    two systems. No field carried the answer and nothing read it; the code
    computes those values itself and shows them as the `crossings` block.

    Changing the wording is allowed. Changing it silently is not: update this
    hash in the same commit and say why the model should read something else."""
    assert (
        hashlib.sha256(ROLE_AND_TASK.encode()).hexdigest()
        == "cd3d9fee825886d5c15884c3abe2787c75188311238cfb9e3012e084f21cdeed"
    )
    assert '"Create a Customer Type", never' in ROLE_AND_TASK
    assert "A stretch that only looked at things goes\nunder `unplaced`." in ROLE_AND_TASK
    assert "once, at the top level\nbeside `workflows`" in ROLE_AND_TASK
    assert "That is ONE job done four times." in ROLE_AND_TASK
    assert "so you can RECOGNISE work, not so\nyou can skip it" in ROLE_AND_TASK


def test_the_schema_asks_for_the_parameter_shape_the_rest_of_the_code_reads() -> None:
    """`seen_values` is read in three places and was declared in none.

    The schema said `{"type": "array", "items": {"type": "object"}}`, which
    tells a model nothing at all -- while `chat.understand` builds its match on
    `p.get("seen_values", [])`, `skill.shape` reads the same key, and
    `workflow_from` drops any parameter without a usable `name`. So a
    model-supplied parameter arrived in whatever shape the model guessed and
    was either discarded or carried no values anybody reads. Three clean mines
    of a real day returned `parameters: []` every time, on jobs whose evidence
    plainly showed four different customer types being typed.

    A field the code reads and the schema does not ask for is a field that
    arrives by luck.
    """
    shape = MINE.output_schema["properties"]
    assert isinstance(shape, dict)
    workflows = shape["workflows"]
    assert isinstance(workflows, dict)
    item = workflows["items"]
    assert isinstance(item, dict)
    parameters = item["properties"]["parameters"]

    assert parameters["items"]["properties"].keys() == {"name", "seen_values"}
    assert parameters["items"]["required"] == ["name", "seen_values"]
    assert parameters["items"]["properties"]["seen_values"]["type"] == "array"


def test_what_the_pass_could_not_place_is_asked_for_once_beside_the_jobs() -> None:
    """The prompt asks for the leftovers of the WINDOW -- "list anything you
    could not place" -- and the schema used to ask for them per workflow. So
    the model attached the day's residue to whichever job it happened to emit,
    and four readers took that for a property of the job and refused to serve,
    schedule or fire it. A real day always leaves residue, so no offer was ever
    made once mining worked at all: the first cross-tab job this system mined
    from a real deployment carried thirty-six unplaced ids, a third of them
    gestures supporting its own steps.

    The prompt and the schema asking for the same thing at two different levels
    is the defect, so both ends are asserted here.
    """
    shape = MINE.output_schema["properties"]
    assert isinstance(shape, dict)
    workflows = shape["workflows"]
    assert isinstance(workflows, dict)
    item = workflows["items"]
    assert isinstance(item, dict)

    assert "unplaced" in shape, "beside `workflows`, which is whose fact it is"
    assert "unplaced" not in item["properties"], "never a property of one job"
    assert "unproven" not in item["properties"], "nor under its old name"
    assert shape["unplaced"] == {"type": "array", "items": {"type": "string"}}


def test_the_task_is_stated_at_both_ends_of_the_prompt() -> None:
    """Question-first was strongest at long context, and restating the
    constraints after the evidence costs almost nothing."""
    evidence = MINE.evidence({}, _blocks(_window(), {}, [], ""))

    # The whole of the task at both ends, not the first and last 40
    # characters: the prompt IS the product, and reworded middle instructions
    # shipped green while only the ends were pinned.
    assert ROLE_AND_TASK in MINE.instructions
    assert evidence.rstrip().endswith(MINE.task.strip())


def test_the_overhead_probe_still_counts_the_crossings_heading_it_pays_for() -> None:
    """`_PROBE_DAY` holds the two ids its crossing names because mining_blocks renders
    only crossings whose gestures are IN the window. Shrink it to one and the
    block disappears from the probe, PROMPT_OVERHEAD_TOKENS stops counting a
    heading the real prompt still pays for, and every window silently gains ~19
    tokens of budget it does not have. Five lines of comment exist to prevent
    exactly that drift; this is the thing that fails when it happens."""
    probed = mining_blocks(_PROBE_DAY, {"x": ["y", "z"]}, [{"x": "y"}], "x")

    assert "crossings" in probed


def test_the_evidence_is_in_the_prompt_in_window_order() -> None:
    prompt = _shown(_window(), {}, [], "")

    assert prompt.index("ges_1") < prompt.index("ges_2")


def test_a_crossing_is_labelled_but_never_called_important() -> None:
    """Telling a model which context is most relevant was measured to REDUCE
    accuracy in all five languages tested."""
    prompt = _shown(_window(), {"TestYonder2": ["ges_1", "ges_2"]}, [], "")

    assert "TestYonder2" in prompt
    assert "most relevant" not in prompt.lower()
    assert "most important" not in prompt.lower()


def test_strength_never_reaches_the_prompt() -> None:
    """Telling a model which evidence is most relevant was measured to reduce
    accuracy, so strength orders the window and is never stated. That was held
    structurally -- mining_blocks serialises item.evidence and never the Packed
    -- and structure is not a regression test."""
    window = _window()
    for item in window.items:
        item.strength = 99.0
        item.tokens = 4242

    prompt = _shown(window, {}, [], "")

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
        for line in _shown(window, {}, [], "").splitlines()
        if "ges_" in line
    ]

    assert order[0] == 39, "the strongest evidence opens the prompt"
    assert order[-1] == 38, "the second strongest closes it"
    assert order[K_ENDS // 2 : -K_ENDS // 2] == sorted(order[K_ENDS // 2 : -K_ENDS // 2])
    assert [item.at for item in window.items] == sorted(item.at for item in window.items)


def test_a_window_packed_to_the_budget_still_fits_the_budget() -> None:
    """The assertion nobody wrote, and the only one that catches this.

    pack() budgeted each item as compact JSON while mining_blocks ships the list
    at indent=1, and subtracted neither ROLE_AND_TASK (twice), nor the response
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
    shipped = (
        tokens(MINE.instructions)
        + tokens(MINE.evidence({}, _blocks(window, crossings, known, kb)))
        + tokens(json.dumps(dict(MINE.output_schema)))
    )
    assert shipped <= K_WINDOW_TOKENS, f"prompt is {shipped} tokens against {K_WINDOW_TOKENS}"


def test_the_crossings_block_cannot_outgrow_the_window_it_hints_at() -> None:
    """`crossings` is computed over the whole store, so it grows with capture
    rather than with the window -- and nothing bounded it or budgeted it."""
    # Every id is one of the window's own: mining_blocks names only what the
    # model may cite, so a crossing over ids outside it is not a block this cap
    # could ever have to bound.
    crossings = {f"ACME-{n:05d}": ["ges_1", "ges_2"] * 3 for n in range(5_000)}

    block = _blocks(_window(), crossings, [], "")["crossings"]

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

    prompt = MINE.evidence({}, _blocks(_window(), crossings, known, "the knowledge base"))

    for section in (
        '<untrusted name="day">',
        "ges_1",
        '<untrusted name="crossings">',
        '<untrusted name="known">',
        "a job already proven",
        '<untrusted name="knowledge">',
        "the knowledge base",
    ):
        assert section in prompt, section
    assert ROLE_AND_TASK in MINE.instructions
    assert prompt.rstrip().endswith(MINE.task.strip()), "and the task is still restated"


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
    """Everything here came off the model. `systems` and `parameters`
    are both optional in practice -- a model that returned only the
    required fields would have crashed the parse on a missing key rather than
    being read as a workflow with none of them."""
    bare = {
        "title": "a job",
        "narrative": "what happened",
        "steps": [{"order": 0, "says": "did a thing", "cites": ["ges_1"]}],
    }

    workflow = workflow_from(bare, tenant="acme")

    assert workflow is not None
    assert workflow.title == "a job"
    assert (workflow.systems, workflow.parameters) == ([], [])
    assert workflow.steps[0].parameters == []


def _one(**over: object) -> dict[str, object]:
    """The well-formed workflow the rig's `_answer` carried, fields replaced.

    The rig drove these eight through `propose` and a `FakeAsker`, which meant
    every guard below was watched only through a model call it does not need.
    `workflow_from` is the thing under test, so it is the thing called.
    """
    base: dict[str, object] = {
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
    }
    return {**base, **over}


def test_a_steps_list_that_is_not_a_list_costs_the_workflow() -> None:
    """A model is at least as likely to return a good workflows list with a bad
    `steps` in it as a bad list, and every guard below that line had nothing
    exercising it."""
    for junk in ("one two three", 7, None, {"a": "dict"}):
        assert workflow_from(_one(steps=junk), tenant="acme") is None


def test_a_step_that_is_not_a_step_is_dropped() -> None:
    """`steps` is a list, so the workflow stands -- but 1 has no .get()."""
    for junk in ([1, 2, 3], [None], ["one", "two"], [["order", 0]]):
        workflow = workflow_from(_one(steps=junk), tenant="acme")

        assert workflow is not None and workflow.steps == []


def test_a_junk_field_inside_a_step_falls_back_to_nothing() -> None:
    """says, system, cites and parameters, one level below where the malformed
    answer test stops."""
    workflow = workflow_from(
        _one(steps=[{"order": 0, "says": 7, "system": 7, "cites": "ges_1", "parameters": "code"}]),
        tenant="acme",
    )
    assert workflow is not None
    step = workflow.steps[0]

    assert step.says == ""
    assert step.system is None
    assert step.cites == []
    assert step.parameters == []

    workflow = workflow_from(
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
        ),
        tenant="acme",
    )
    assert workflow is not None
    step = workflow.steps[0]

    assert step.cites == ["ges_1"]
    assert step.parameters == ["code"]


def test_a_junk_field_beside_the_steps_falls_back_to_nothing() -> None:
    """title, narrative and systems."""
    workflow = workflow_from(_one(title=7, narrative=7, systems="wms"), tenant="acme")
    assert workflow is not None

    assert workflow.title == ""
    assert workflow.narrative == ""
    assert workflow.systems == []

    also = workflow_from(_one(systems=["a", 7]), tenant="acme")
    assert also is not None

    assert also.systems == ["a"]


def test_a_step_order_is_a_sort_key_and_the_steps_are_numbered_by_position() -> None:
    """A model's order past a Postgres integer failed in the driver, before the
    server, so the transaction lived on and the pass committed a job row with
    no steps. The order only says where a step goes."""
    workflow = workflow_from(
        _one(
            steps=[
                {"order": 2**40, "cites": ["ges_2"], "says": "second"},
                {"order": 5, "cites": ["ges_1"], "says": "first"},
                {"order": 2**31, "cites": ["ges_3"], "says": "between"},
            ]
        ),
        tenant="acme",
    )
    assert workflow is not None

    assert [(step.order, step.says) for step in workflow.steps] == [
        (0, "first"),
        (1, "between"),
        (2, "second"),
    ]


def test_a_step_order_of_true_is_not_a_step_order() -> None:
    """True is an int in Python, and sorts as 1."""
    workflow = workflow_from(
        _one(
            steps=[
                {
                    "order": True,
                    "cites": ["ges_1"],
                    "says": "s",
                    "system": "https://wms.example",
                    "parameters": [],
                }
            ]
        ),
        tenant="acme",
    )
    assert workflow is not None

    assert workflow.steps[0].order == 0
    assert workflow.steps[0].order is not True


def test_a_parameter_with_no_name_is_not_a_parameter() -> None:
    """Every other container in `workflow_from` is checked down to a scalar;
    this one filtered to dict and stopped."""
    workflow = workflow_from(
        _one(
            parameters=[
                {"name": "code", "seen_values": ["ACME"]},
                {"seen_values": ["nameless"]},
                {"name": "", "seen_values": ["empty"]},
                {"name": 7, "seen_values": ["not a string"]},
            ]
        ),
        tenant="acme",
    )
    assert workflow is not None

    assert [p["name"] for p in workflow.parameters] == ["code"]


def test_a_step_parameter_is_judged_by_the_same_rule() -> None:
    """The ninth sibling: `parameters` at step level and `parameters` at
    workflow level arrive from one model answer, and only one of them was
    checked for a usable name. The shapes differ because the schema declares
    them differently -- a step names a parameter, a workflow declares one --
    but "no usable name is no parameter" is now one rule at both."""
    workflow = workflow_from(
        _one(
            steps=[
                {
                    "order": 0,
                    "cites": ["ges_1"],
                    "says": "s",
                    "parameters": ["code", "", "   ", 7, None],
                }
            ],
            parameters=[{"name": "code"}, {"name": "   "}],
        ),
        tenant="acme",
    )
    assert workflow is not None

    assert workflow.steps[0].parameters == ["code"]
    assert [p["name"] for p in workflow.parameters] == ["code"]


def test_the_schema_asks_for_nothing_nobody_reads() -> None:
    """`same_as` was the model's opinion that a proposal was one it had seen
    before. It decided nothing (identity is arithmetic) and every proposal paid
    for it, so the field is gone from the schema and the parse alike."""
    assert '"same_as"' not in json.dumps(dict(MINE.output_schema))
