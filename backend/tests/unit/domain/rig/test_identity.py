import pytest

from sro.domain.observation.identity import K_MIN_SHARED_STEPS, K_SAME_JOB, resolve
from sro.domain.skill.workflow import Step, Workflow


def _workflow(cites: list[str], shape: list[list[str]], **over: object) -> Workflow:
    base: dict[str, object] = {
        "id": "wfl_x",
        "tenant": "acme",
        "title": "a job",
        "narrative": "",
        "systems": ["https://wms.example"],
        "steps": [
            Step(order=i, says="x", system="https://wms.example", cites=[c])
            for i, c in enumerate(cites)
        ],
        "shape_key": shape,
    }
    return Workflow(**{**base, **over})


SHAPE = [
    ["https://wms.example", "clientCode", "type"],
    ["https://wms.example", "saveButton", "click"],
]


def test_nothing_known_means_a_new_job() -> None:
    assert resolve(_workflow(["ges_1"], SHAPE), []).kind == "new"


def test_the_same_evidence_again_is_the_same_occurrence() -> None:
    """Mining re-runs over evidence it has already read. A key that answered
    differently on a second pass would breed a workflow that can never pair."""
    known = _workflow(["ges_1", "ges_2"], SHAPE, id="wfl_known")
    again = _workflow(["ges_1", "ges_2"], SHAPE)

    resolution = resolve(again, [known])

    assert resolution.kind == "same_occurrence"
    assert resolution.workflow_id == "wfl_known"


def test_the_same_job_on_wholly_different_evidence_is_recognised() -> None:
    """This is the question ids cannot answer: two occurrences cite disjoint
    gestures, so overlap between them is zero by construction."""
    known = _workflow(["ges_1", "ges_2"], SHAPE, id="wfl_known")
    tuesday = _workflow(["ges_90", "ges_91"], SHAPE)

    resolution = resolve(tuesday, [known])

    assert resolution.kind == "same_job"
    assert resolution.workflow_id == "wfl_known"
    assert resolution.score >= K_SAME_JOB


def test_a_different_job_sharing_one_lookup_is_not_folded_in() -> None:
    """Containment divides by the smaller shape, so a two-step job is half
    contained by anything sharing one step. A ratio cannot tell "half of two"
    from "half of twenty"; the overlap has to be real in absolute terms too."""
    known = _workflow(["ges_1"], SHAPE, id="wfl_known")
    other = _workflow(
        ["ges_50"],
        [["https://wms.example", "clientCode", "type"]]
        + [["https://sap.example", f"field{n}", "type"] for n in range(8)],
    )

    assert resolve(other, [known]).kind == "new"


def test_a_small_job_inside_a_big_one_is_the_same_job_and_says_which_contains() -> None:
    big = _workflow(
        ["ges_1"],
        SHAPE + [["https://sap.example", f"f{n}", "click"] for n in range(6)],
        id="wfl_big",
    )
    small = _workflow(["ges_70"], SHAPE)

    resolution = resolve(small, [big])

    assert resolution.kind == "same_job"
    assert resolution.contains is False


def test_the_models_own_opinion_decides_nothing() -> None:
    """A model re-judging its earlier verdict disagrees with itself at roughly
    90%, and same_as asks exactly that."""
    known = _workflow(["ges_1"], SHAPE, id="wfl_known")
    unrelated = _workflow(
        ["ges_50"],
        [["https://other.example", "wholly", "click"]],
        same_as="wfl_known",
    )

    assert resolve(unrelated, [known]).kind == "new"


def test_a_workflow_with_no_shape_is_new_rather_than_a_match() -> None:
    known = _workflow(["ges_1"], SHAPE, id="wfl_known")

    assert resolve(_workflow(["ges_9"], []), [known]).kind == "new"


def test_one_cited_gesture_in_common_is_not_a_re_read() -> None:
    """The two layers, told apart. Jaccard on ids says 1-in-10 is not the same
    window; containment on the same ids would say 1.0 and call it a re-read.
    Which layer answers is the whole of this module, so a test that passes
    under either measure tests nothing."""
    known = _workflow([f"ges_{n}" for n in range(10)], SHAPE, id="wfl_known")
    sliver = _workflow(["ges_0"], SHAPE)

    resolution = resolve(sliver, [known])

    assert resolution.kind == "same_job"
    assert resolution.score == 1.0


def test_the_measured_overlap_is_reported_not_assumed() -> None:
    """Three citations of four is the same occurrence and is not identity. A
    flat 1.0 is a number no caller can threshold on twice."""
    known = _workflow(["ges_1", "ges_2", "ges_3"], SHAPE, id="wfl_known")
    again = _workflow(["ges_1", "ges_2", "ges_3", "ges_4"], SHAPE)

    resolution = resolve(again, [known])

    assert resolution.kind == "same_occurrence"
    assert resolution.score == 0.75


def test_the_closest_evidence_match_wins_not_the_first_listed() -> None:
    partial = _workflow(["ges_1", "ges_2", "ges_3"], SHAPE, id="wfl_partial")
    exact = _workflow(["ges_1", "ges_2", "ges_3", "ges_4"], SHAPE, id="wfl_exact")
    again = _workflow(["ges_1", "ges_2", "ges_3", "ges_4"], SHAPE)

    resolution = resolve(again, [partial, exact])

    assert resolution.workflow_id == "wfl_exact"
    assert resolution.score == 1.0


def test_a_real_match_is_not_masked_by_a_higher_scoring_stub() -> None:
    """A one-step stub is 1.0-contained by anything that begins where it does.
    Take the best of what clears both bars, not the best overall and then the
    bars -- otherwise the stub wins the comparison, fails the step count, and
    the genuine match standing behind it is never reached."""
    proposal = _workflow(["ges_1"], [*SHAPE, ["https://sap.example", "post", "click"]])
    stub = _workflow(["ges_2"], SHAPE[:1], id="wfl_stub")
    real = _workflow(
        ["ges_3"],
        SHAPE + [["https://sap.example", f"other{n}", "type"] for n in range(2)],
        id="wfl_real",
    )

    resolution = resolve(proposal, [stub, real])

    assert resolution.kind == "same_job"
    assert resolution.workflow_id == "wfl_real"
    assert resolution.score == pytest.approx(2 / 3)


def test_exactly_the_minimum_shared_steps_at_exactly_the_threshold_matches() -> None:
    """Both bars are sat on at once: containment is exactly K_SAME_JOB and the
    shared count is exactly K_MIN_SHARED_STEPS. Either comparison written `>`
    instead of `>=` refuses this."""
    shared = [["https://wms.example", f"shared{n}", "type"] for n in range(K_MIN_SHARED_STEPS)]
    known = _workflow(
        ["ges_1"],
        shared + [["https://sap.example", f"theirs{n}", "click"] for n in range(2)],
        id="wfl_known",
    )
    mine = _workflow(
        ["ges_9"],
        shared + [["https://sap.example", f"mine{n}", "click"] for n in range(2)],
    )

    resolution = resolve(mine, [known])

    assert resolution.kind == "same_job"
    assert resolution.score == K_SAME_JOB


def test_another_tenants_workflow_is_never_the_same_thing() -> None:
    """Same shape, same citations, different customer. known_workflows() scopes
    its query by tenant; resolve() takes whatever list it is handed, and welding
    one tenant's job onto another's is not a mistake you can undo."""
    theirs = _workflow(["ges_1", "ges_2"], SHAPE, id="wfl_theirs", tenant="globex")
    mine = _workflow(["ges_1", "ges_2"], SHAPE)

    assert resolve(mine, [theirs]).kind == "new"


def test_two_shared_steps_out_of_five_is_not_enough_of_the_job() -> None:
    """The mirror of the one-shared-lookup case, and the reason both bars are
    needed rather than either. There the ratio passed and the count refused;
    here the count passes -- two steps really are shared -- and the ratio
    refuses, because two steps of a five-step job is not that job."""
    shared = [["https://wms.example", f"shared{n}", "type"] for n in range(K_MIN_SHARED_STEPS)]
    known = _workflow(
        ["ges_1"],
        shared + [["https://sap.example", f"theirs{n}", "click"] for n in range(3)],
        id="wfl_known",
    )
    mine = _workflow(
        ["ges_9"],
        shared + [["https://sap.example", f"mine{n}", "click"] for n in range(3)],
    )

    assert resolve(mine, [known]).kind == "new"


def test_the_closest_shape_match_wins_not_the_last_one_that_qualified() -> None:
    """Two knowns can both clear both bars. The one the proposal actually is
    has to win, whatever order the store handed them over in."""
    proposal = _workflow(["ges_1"], [*SHAPE, ["https://sap.example", "post", "click"]])
    exact = _workflow(["ges_2"], [*SHAPE, ["https://sap.example", "post", "click"]], id="wfl_exact")
    looser = _workflow(
        ["ges_3"],
        SHAPE + [["https://sap.example", f"other{n}", "type"] for n in range(2)],
        id="wfl_looser",
    )

    resolution = resolve(proposal, [exact, looser])

    assert resolution.workflow_id == "wfl_exact"
    assert resolution.score == 1.0
