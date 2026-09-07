"""Ported from `new_agent_arch/tests/test_checks.py`, all 20, names unchanged.

One shape adaptation, in `test_a_proposal_whose_steps_are_all_junk_is_refused`:
the rig drove `_as_workflow` through `propose`, which asks a model and belongs
to the mining use case. It calls `workflow_from` directly here instead -- the
same junk steps, the same two assertions, no `Asker` and no `await`.
"""

from sro.domain.observation.window import Packed, Window, pack
from sro.domain.skill.checks import K_MAX_SKEW, K_MIN_COVERAGE, coverage, validate
from sro.domain.skill.umbrella import workflow_from
from sro.domain.skill.workflow import Step, Workflow
from tests.unit.domain.rig.conftest import gestures as _gestures

WMS = "https://wms.example"
SAP = "https://sap.example"


def _workflow(*, systems: list[str] | None = None, steps: list[Step] | None = None) -> Workflow:
    """The rig's `**over` splat, spelled out: mypy is strict on these tests and
    `Workflow(**{**base, **over})` does not typecheck."""
    return Workflow(
        id="wfl_1",
        tenant="acme",
        title="a job",
        narrative="",
        systems=[WMS] if systems is None else systems,
        steps=[Step(order=0, says="do it", system=WMS, cites=["ges_1"])]
        if steps is None
        else steps,
    )


def _window(n: int) -> Window:
    return Window(items=[Packed(f"ges_{i}", float(i), {}, 1.0, 10) for i in range(n)])


def _on(*ids: str, system: str = WMS) -> dict[str, str]:
    """The window as `validate` reads it: gesture id -> the system it happened
    on. `Gesture.system` is `str | None`, and an unknown one arrives here as
    ""."""
    return dict.fromkeys(ids, system)


def _citing(indices: range) -> Workflow:
    return _workflow(
        steps=[Step(order=i, says="x", system=WMS, cites=[f"ges_{i}"]) for i in indices]
    )


def test_a_workflow_citing_real_evidence_is_kept() -> None:
    assert validate(_workflow(), _on("ges_1")) is None


def test_a_step_citing_nothing_is_refused() -> None:
    """Models omit citations wherever the output shape lets them, which
    inflates apparent accuracy. An uncited step is a rejected step."""
    bad = _workflow(steps=[Step(order=0, says="do it", system=None, cites=[])])

    rejection = validate(bad, _on("ges_1"))

    assert rejection is not None
    assert "uncited" in rejection.reason


def test_a_step_citing_a_gesture_that_does_not_exist_is_refused() -> None:
    bad = _workflow(steps=[Step(order=0, says="x", system=None, cites=["ges_nope"])])

    rejection = validate(bad, _on("ges_1"))

    assert rejection is not None
    assert "ges_nope" in rejection.detail


def test_a_workflow_with_no_steps_is_refused() -> None:
    """The reason is asserted, not just the rejection. A stepless workflow that
    still names a system is rejected for the system it cannot evidence, so
    `is not None` alone stays green with the no-steps guard deleted."""
    rejection = validate(_workflow(steps=[]), _on("ges_1"))

    assert rejection is not None
    assert rejection.reason == "no steps"


def test_a_workflow_claiming_a_system_its_evidence_never_touched_is_refused() -> None:
    """This is what stops a workflow claiming to touch SAP when nothing it
    cited ever spoke to SAP -- the failure that would put an invented origin in
    front of a runner."""
    bad = _workflow(
        systems=[WMS, SAP],
        steps=[Step(order=0, says="x", system=WMS, cites=["ges_1"])],
    )

    rejection = validate(bad, _on("ges_1"))

    assert rejection is not None
    assert "sap.example" in rejection.detail


def test_a_workflow_naming_an_empty_system_is_not_refused_for_it() -> None:
    """`systems`' elements are only checked to be strings upstream, and "" is a
    string. An unnamed system is no system rather than an invented one, and a
    rejection whose detail is "" tells a reader nothing."""
    assert validate(_workflow(systems=["", WMS]), _on("ges_1")) is None


def test_a_step_claiming_a_system_none_of_its_evidence_touched_is_refused() -> None:
    """The check this replaces compared the model against itself: it took
    step.system as the evidence for step.system. A tidy invented answer passed.
    This architecture exists to find two-system jobs, so a fabricated second
    system is the one lie it must not accept."""
    bad = _workflow(
        systems=[WMS, SAP],
        steps=[Step(order=0, says="x", system=SAP, cites=["ges_1"])],
    )

    rejection = validate(bad, _on("ges_1", system=WMS))

    assert rejection is not None
    assert rejection.reason == "step system not in evidence"
    assert SAP in rejection.detail


def test_a_step_whose_evidence_really_is_on_that_system_is_kept() -> None:
    """The mirror of the one above, and the reason it is here: a check that
    refuses everything catches the invented system too."""
    good = _workflow(
        systems=[SAP],
        steps=[Step(order=0, says="x", system=SAP, cites=["ges_1"])],
    )

    assert validate(good, _on("ges_1", system=SAP)) is None


def test_a_step_whose_evidence_has_no_known_system_cannot_confirm_it() -> None:
    """An unknown system is not a system -- the rule shared_values and
    correlate._owner already apply. Refusing is the deliberate direction: a
    lost workflow is visible, a fabricated cross-system job is not."""
    bad = _workflow(steps=[Step(order=0, says="x", system=WMS, cites=["ges_1"])])

    rejection = validate(bad, _on("ges_1", system=""))

    assert rejection is not None
    assert rejection.reason == "unattributed evidence"


def test_a_step_naming_no_system_is_not_asked_to_evidence_one() -> None:
    """umbrella.workflow_from substitutes None for a junk system, so an absent
    system is a silence rather than a claim -- and silence is not refused even
    when the gesture it cites is itself unattributed."""
    quiet = _workflow(
        systems=[],
        steps=[Step(order=0, says="x", system=None, cites=["ges_1"])],
    )

    assert validate(quiet, _on("ges_1", system="")) is None


def test_a_step_that_says_nothing_is_refused() -> None:
    """`says` is `cites`' sibling, and umbrella.workflow_from falls back to ""
    for a step the model left unworded rather than dropping it. A well-cited
    step with no words reaches an operator as a blank line."""
    bad = _workflow(steps=[Step(order=0, says="  ", system=None, cites=["ges_1"])])

    rejection = validate(bad, _on("ges_1"))

    assert rejection is not None
    assert "wordless" in rejection.reason


def test_a_proposal_whose_steps_are_all_junk_is_refused() -> None:
    """End to end: workflow_from drops junk steps individually, so an answer
    whose steps are ALL junk becomes a workflow with steps=[] and zero
    citations -- and 'an uncited step is a rejected step' then has nothing to
    reject."""
    proposed = workflow_from({"title": "a job", "steps": [1, None, "two"]}, "acme")

    assert proposed is not None
    assert proposed.steps == []
    assert validate(proposed, _on("ges_0", "ges_1")) is not None


def test_coverage_deciles_are_time_deciles_because_pack_sorts_by_time() -> None:
    """coverage() slices window.items into ten bins and calls the result a
    position in the day. That is only true while pack returns items in `at`
    order -- it is not a property of Window. test_window asserts the same thing
    about pack; this one lives beside the code that depends on it, so changing
    pack breaks a test that says why the order matters."""
    packed = pack(_gestures(), {}, [], [], "")

    ats = [item.at for item in packed.items]
    assert ats == sorted(ats)
    # Without the final sort the window comes back in the strength order pack
    # selects in, and in this capture the strongest gesture is the last one of
    # the day -- so the assertion above would fail rather than pass by accident.
    assert packed.items[0].strength < max(item.strength for item in packed.items)


def test_coverage_of_an_evenly_cited_window_is_complete() -> None:
    window = _window(100)
    everywhere = _workflow(
        steps=[Step(order=i, says="x", system=WMS, cites=[f"ges_{i}"]) for i in range(0, 100, 5)]
    )

    measured = coverage([everywhere], window)

    assert measured.coverage == 1.0
    assert abs(measured.skew) < 0.2


def test_citing_only_the_opening_of_a_window_is_visible_as_skew() -> None:
    """Long-context citation shows strong primacy bias in published work -- and
    it is model-specific, so this measures rather than assumes."""
    window = _window(100)
    early = _workflow(
        steps=[Step(order=i, says="x", system=WMS, cites=[f"ges_{i}"]) for i in range(10)]
    )

    measured = coverage([early], window)

    assert measured.coverage < K_MIN_COVERAGE
    assert measured.skew > 0.5
    # Strengthened over the rig's own, which asserted the 0.5 and left the
    # constant unread. K_MIN_COVERAGE is checked against a measurement one line
    # up; K_MAX_SKEW is its pair and had nothing checking it at all -- widening
    # it to ten times its value broke no test in this file. The mining pass is
    # what rejects on both, and this is the half of that relationship this
    # module can state: an opening-only reading skews past the limit.
    assert measured.skew > K_MAX_SKEW


def test_citing_only_the_end_of_a_window_skews_the_other_way() -> None:
    window = _window(100)
    late = _workflow(
        steps=[Step(order=i, says="x", system=WMS, cites=[f"ges_{i}"]) for i in range(90, 100)]
    )

    assert coverage([late], window).skew < -0.5


def test_the_skew_window_is_three_deciles_wide_at_each_end() -> None:
    """Every other skew fixture cites decile 0 or decile 9, where `mass[:3]` and
    `mass[:2]` both give exactly +/-1.0 -- so narrowing the window from three
    deciles to two broke nothing. The third decile is the only place the two
    spellings disagree: cited there, a reading skews fully under the rule as
    written and not at all under the narrower one."""
    window = _window(100)

    assert coverage([_citing(range(20, 30))], window).skew == 1.0
    assert coverage([_citing(range(70, 80))], window).skew == -1.0


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
