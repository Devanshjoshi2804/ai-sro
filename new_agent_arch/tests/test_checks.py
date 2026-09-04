from rig.checks import K_MIN_COVERAGE, coverage, validate
from rig.models import Answer, FakeAsker
from rig.umbrella import propose
from rig.window import Packed, Window
from rig.workflows import Step, Workflow


def _workflow(**over) -> Workflow:
    base = {
        "id": "wfl_1",
        "tenant": "acme",
        "title": "a job",
        "narrative": "",
        "systems": ["https://wms.example"],
        "steps": [Step(order=0, says="do it", system="https://wms.example", cites=["ges_1"])],
    }
    return Workflow(**{**base, **over})


def _window(n: int) -> Window:
    return Window(items=[Packed(f"ges_{i}", float(i), {}, 1.0, 10) for i in range(n)])


def _citing(indices: range) -> Workflow:
    return _workflow(
        steps=[
            Step(order=i, says="x", system="https://wms.example", cites=[f"ges_{i}"])
            for i in indices
        ]
    )


def test_a_workflow_citing_real_evidence_is_kept() -> None:
    assert validate(_workflow(), {"ges_1"}) is None


def test_a_step_citing_nothing_is_refused() -> None:
    """Models omit citations wherever the output shape lets them, which
    inflates apparent accuracy. An uncited step is a rejected step."""
    bad = _workflow(steps=[Step(order=0, says="do it", system=None, cites=[])])

    rejection = validate(bad, {"ges_1"})

    assert rejection is not None
    assert "uncited" in rejection.reason


def test_a_step_citing_a_gesture_that_does_not_exist_is_refused() -> None:
    bad = _workflow(steps=[Step(order=0, says="x", system=None, cites=["ges_nope"])])

    rejection = validate(bad, {"ges_1"})

    assert rejection is not None
    assert "ges_nope" in rejection.detail


def test_a_workflow_with_no_steps_is_refused() -> None:
    """The reason is asserted, not just the rejection. A stepless workflow that
    still names a system is rejected for the system it cannot evidence, so
    `is not None` alone stays green with the no-steps guard deleted."""
    rejection = validate(_workflow(steps=[]), {"ges_1"})

    assert rejection is not None
    assert rejection.reason == "no steps"


def test_a_workflow_claiming_a_system_its_evidence_never_touched_is_refused() -> None:
    """This is what stops a workflow claiming to touch SAP when nothing it
    cited ever spoke to SAP -- the failure that would put an invented origin in
    front of a runner."""
    bad = _workflow(
        systems=["https://wms.example", "https://sap.example"],
        steps=[Step(order=0, says="x", system="https://wms.example", cites=["ges_1"])],
    )

    rejection = validate(bad, {"ges_1"})

    assert rejection is not None
    assert "sap.example" in rejection.detail


def test_a_workflow_naming_an_empty_system_is_not_refused_for_it() -> None:
    """`systems`' elements are only checked to be strings upstream, and "" is a
    string. An unnamed system is no system rather than an invented one, and a
    rejection whose detail is "" tells a reader nothing."""
    assert validate(_workflow(systems=["", "https://wms.example"]), {"ges_1"}) is None


def test_a_step_that_says_nothing_is_refused() -> None:
    """`says` is `cites`' sibling, and umbrella._as_workflow falls back to ""
    for a step the model left unworded rather than dropping it. A well-cited
    step with no words reaches an operator as a blank line."""
    bad = _workflow(steps=[Step(order=0, says="  ", system=None, cites=["ges_1"])])

    rejection = validate(bad, {"ges_1"})

    assert rejection is not None
    assert "wordless" in rejection.reason


async def test_a_proposal_whose_steps_are_all_junk_is_refused() -> None:
    """End to end: _as_workflow drops junk steps individually, so an answer
    whose steps are ALL junk is proposed with steps=[] and zero citations --
    and 'an uncited step is a rejected step' then has nothing to reject."""
    answer = Answer(
        data={"workflows": [{"title": "a job", "steps": [1, None, "two"]}]},
        in_tokens=1,
        out_tokens=1,
        cost_usd=0.001,
    )

    proposed, _ = await propose(
        _window(2),
        {},
        [],
        "",
        asker=FakeAsker(answer),
        model="gemini-3.1-pro",
        tenant="acme",
    )

    assert proposed[0].steps == []
    assert validate(proposed[0], {"ges_0", "ges_1"}) is not None


def test_coverage_of_an_evenly_cited_window_is_complete() -> None:
    window = _window(100)
    everywhere = _workflow(
        steps=[
            Step(order=i, says="x", system="https://wms.example", cites=[f"ges_{i}"])
            for i in range(0, 100, 5)
        ]
    )

    measured = coverage([everywhere], window)

    assert measured.coverage == 1.0
    assert abs(measured.skew) < 0.2


def test_citing_only_the_opening_of_a_window_is_visible_as_skew() -> None:
    """Long-context citation shows strong primacy bias in published work -- and
    it is model-specific, so this measures rather than assumes."""
    window = _window(100)
    early = _workflow(
        steps=[
            Step(order=i, says="x", system="https://wms.example", cites=[f"ges_{i}"])
            for i in range(10)
        ]
    )

    measured = coverage([early], window)

    assert measured.coverage < K_MIN_COVERAGE
    assert measured.skew > 0.5


def test_citing_only_the_end_of_a_window_skews_the_other_way() -> None:
    window = _window(100)
    late = _workflow(
        steps=[
            Step(order=i, says="x", system="https://wms.example", cites=[f"ges_{i}"])
            for i in range(90, 100)
        ]
    )

    assert coverage([late], window).skew < -0.5


def test_coverage_of_an_empty_window_does_not_divide_by_zero() -> None:
    measured = coverage([], Window())

    assert measured.coverage == 0.0
    assert measured.skew == 0.0


def test_a_window_nobody_cited_is_uncovered_rather_than_undefined() -> None:
    """No citation lands in any decile, so the mass has nothing to normalise
    by -- the other way this arithmetic divides by zero."""
    measured = coverage([_citing(range(0))], _window(100))

    assert measured.coverage == 0.0
    assert measured.skew == 0.0
    assert measured.gini == 0.0


def test_coverage_of_a_short_window_is_not_capped_by_ten_deciles() -> None:
    """A window of four gestures has four parts, not ten. Divided by a flat
    ten, a FULLY cited short window reported 0.4 -- under K_MIN_COVERAGE."""
    measured = coverage([_citing(range(4))], _window(4))

    assert measured.coverage == 1.0


def test_gini_separates_an_even_window_from_a_clustered_one() -> None:
    """coverage says how much of the window was read; gini says how evenly.
    Twenty citations in one decile cover as much of it as two."""
    window = _window(100)

    assert abs(coverage([_citing(range(0, 100, 5))], window).gini) < 1e-9
    assert coverage([_citing(range(10))], window).gini > 0.8
