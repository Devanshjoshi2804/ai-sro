from rig.checks import K_MIN_COVERAGE, coverage, validate
from rig.correlate import correlate
from rig.models import Answer, FakeAsker
from rig.umbrella import propose
from rig.window import Packed, Window, pack
from rig.wire import Batch
from rig.workflows import Step, Workflow
from tests.fixtures import BATCH

WMS = "https://wms.example"
SAP = "https://sap.example"


def _workflow(**over) -> Workflow:
    base = {
        "id": "wfl_1",
        "tenant": "acme",
        "title": "a job",
        "narrative": "",
        "systems": [WMS],
        "steps": [Step(order=0, says="do it", system=WMS, cites=["ges_1"])],
    }
    return Workflow(**{**base, **over})


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
    """umbrella._as_workflow substitutes None for a junk system, so an absent
    system is a silence rather than a claim -- and silence is not refused even
    when the gesture it cites is itself unattributed."""
    quiet = _workflow(
        systems=[],
        steps=[Step(order=0, says="x", system=None, cites=["ges_1"])],
    )

    assert validate(quiet, _on("ges_1", system="")) is None


def test_a_step_that_says_nothing_is_refused() -> None:
    """`says` is `cites`' sibling, and umbrella._as_workflow falls back to ""
    for a step the model left unworded rather than dropping it. A well-cited
    step with no words reaches an operator as a blank line."""
    bad = _workflow(steps=[Step(order=0, says="  ", system=None, cites=["ges_1"])])

    rejection = validate(bad, _on("ges_1"))

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
    assert validate(proposed[0], _on("ges_0", "ges_1")) is not None


def test_coverage_deciles_are_time_deciles_because_pack_sorts_by_time() -> None:
    """coverage() slices window.items into ten bins and calls the result a
    position in the day. That is only true while pack returns items in `at`
    order -- it is not a property of Window. test_window asserts the same thing
    about pack; this one lives beside the code that depends on it, so changing
    pack breaks a test that says why the order matters."""
    gestures, _, _, _ = correlate(Batch.model_validate(BATCH), "acme")

    packed = pack(gestures, {}, [], [], "")

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


def test_citing_only_the_end_of_a_window_skews_the_other_way() -> None:
    window = _window(100)
    late = _workflow(
        steps=[Step(order=i, says="x", system=WMS, cites=[f"ges_{i}"]) for i in range(90, 100)]
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
