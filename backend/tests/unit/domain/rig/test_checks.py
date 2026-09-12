"""Ported from `new_agent_arch/tests/test_checks.py`, all 20, names unchanged.

One shape adaptation, in `test_a_proposal_whose_steps_are_all_junk_is_refused`:
the rig drove `_as_workflow` through `propose`, which asks a model and belongs
to the mining use case. It calls `workflow_from` directly here instead -- the
same junk steps, the same two assertions, no `Asker` and no `await`.

The `work_only` tests below are this repo's own and have no rig ancestor. Their
shapes are the two jobs the real acme store actually holds -- the console
watching itself, and a sign-in chain read as the start of a job -- plus the two
real jobs each half of the transit rule exists to keep.
"""

from dataclasses import replace

from sro.domain.observation.gesture import Action, Call, Component, Gesture, PageMark, Target
from sro.domain.observation.window import Packed, Window, pack
from sro.domain.skill.checks import (
    K_MAX_SKEW,
    K_MIN_COVERAGE,
    K_SITTING_GAP_S,
    coverage,
    one_occurrence,
    undeliverable,
    validate,
    work_only,
)
from sro.domain.skill.umbrella import workflow_from
from sro.domain.skill.workflow import Step, Workflow
from tests.unit.domain.rig.conftest import gestures as _gestures

WMS = "https://wms.example"
SAP = "https://sap.example"
MAIL = "https://mail.example"
SSO = "https://login.example"
CONSOLE = "http://localhost:3000"
OURS = frozenset({"localhost:3000", "localhost:8000"})
"""This deployment as `Settings.our_own_origins` names it: host and port, no
scheme and no path."""


def _workflow(*, systems: list[str] | None = None, steps: list[Step] | None = None) -> Workflow:
    """The rig's `**over` splat, spelled out: mypy is strict on these tests and
    `Workflow(**{**base, **over})` does not typecheck."""
    return Workflow(
        id="wfl_1",
        tenant="acme",
        title="a job",
        narrative="",
        systems=[WMS] if systems is None else systems,
        # Two steps by default, both citing the same gesture: `validate`
        # refuses anything shorter than `identity.K_MIN_SHARED_STEPS`, since
        # `resolve` can never match such a proposal to a later doing of the
        # same job. Sharing one citation keeps `cited_ids` and every system
        # check reading exactly as they did when this was one step.
        steps=[
            Step(order=0, says="do it", system=WMS, cites=["ges_1"]),
            Step(order=1, says="save it", system=WMS, cites=["ges_1"]),
        ]
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
        steps=[
            Step(order=0, says="x", system=SAP, cites=["ges_1"]),
            Step(order=1, says="y", system=SAP, cites=["ges_1"]),
        ],
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
        steps=[
            Step(order=0, says="x", system=None, cites=["ges_1"]),
            Step(order=1, says="y", system=None, cites=["ges_1"]),
        ],
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


def _gesture(gesture_id: str, system: str, *, left_for: tuple[str, ...] = ()) -> Gesture:
    """One gesture as `work_only` reads it: the system it happened on, and the
    pages it ended on. `left_for` is where the browser took the operator
    without being asked -- the shape of a redirect."""
    return Gesture(
        id=gesture_id,
        tenant="acme",
        stream_id="str_1",
        batch_id="bat_1",
        at=0.0,
        url=f"{system}/page",
        system=system,
        tab_id=1,
        frame_url=None,
        action=Action(kind="click", at=0.0),
        page_events=[
            PageMark(at=0.0, page_kind="navigated", url=f"{where}/landed") for where in left_for
        ],
    )


def _typed_into(gesture_id: str, system: str, *, item_id: str, label: str) -> Gesture:
    """A gesture on a real, named control -- the shape `value_for` reads."""
    return replace(
        _gesture(gesture_id, system),
        action=Action(
            kind="type",
            at=0.0,
            value="2",
            target=Target(
                tag="input",
                name=None,
                component=Component(item_id=item_id, field_label=label),
            ),
        ),
    )


def _job(*evidence: Gesture, systems: list[str]) -> tuple[Workflow, dict[str, Gesture]]:
    """A workflow whose steps cite this evidence in the order it is given,
    which is the order `ordered_cites` reads it back in."""
    workflow = _workflow(
        systems=systems,
        steps=[
            Step(order=index, says="do it", system=one.system, cites=[one.id])
            for index, one in enumerate(evidence)
        ],
    )
    return workflow, {one.id: one for one in evidence}


def test_a_job_whose_only_system_is_this_deployments_own_console_is_not_a_job() -> None:
    """The miner watched somebody use SRO while capture was on and proposed
    "using SRO" as warehouse work. The console is the apparatus."""
    job, evidence = _job(_gesture("ges_1", CONSOLE), systems=[CONSOLE])

    rejection = work_only(job, evidence, ours=OURS)

    assert rejection is not None
    assert rejection.reason == "not a job"


def test_the_console_on_a_default_port_is_the_same_console() -> None:
    """`https://sro.acme.com:443` and `https://sro.acme.com` are one origin,
    and a deployment that wrote the first left every call to the second
    proposable."""
    job, evidence = _job(
        _gesture("ges_1", "https://sro.acme.com:443"), systems=["https://sro.acme.com:443"]
    )

    assert work_only(job, evidence, ours=frozenset({"sro.acme.com"})) is not None


def test_a_job_on_a_real_warehouse_host_is_left_exactly_as_it_was() -> None:
    job, evidence = _job(_gesture("ges_1", WMS), _gesture("ges_2", WMS), systems=[WMS])

    assert work_only(job, evidence, ours=OURS) is None
    assert job.systems == [WMS]


def test_a_sign_in_hop_is_struck_and_the_job_keeps_where_the_work_landed() -> None:
    """`Search for Work Areas` in the real store opens on two identity hosts
    and does its work on the third. The chain is how it got there, not what it
    is."""
    job, evidence = _job(
        _gesture("ges_1", SSO, left_for=(WMS,)),
        _gesture("ges_2", WMS),
        systems=[SSO, WMS],
    )

    assert work_only(job, evidence, ours=OURS) is None
    assert job.systems == [WMS]


def test_a_system_the_job_comes_back_to_is_not_a_hop_through() -> None:
    """Half the rule. The warehouse host bounced somewhere else on 4 of its 495
    real gestures; it is never transit, because the work ends on it."""
    job, evidence = _job(
        _gesture("ges_1", WMS, left_for=(SAP,)),
        _gesture("ges_2", SAP),
        _gesture("ges_3", WMS),
        systems=[WMS, SAP],
    )

    assert work_only(job, evidence, ours=OURS) is None
    assert job.systems == [WMS, SAP]


def test_a_system_that_bounced_nobody_is_not_a_hop_through_however_early_it_comes() -> None:
    """The other half. Two stored jobs read a mail and then go and do the work,
    so the mail host is never the last system either -- and it is kept, because
    nothing there sent the operator anywhere."""
    job, evidence = _job(
        _gesture("ges_1", MAIL),
        _gesture("ges_2", WMS),
        systems=[MAIL, WMS],
    )

    assert work_only(job, evidence, ours=OURS) is None
    assert job.systems == [MAIL, WMS]


IDENTITY = "https://blueyonderalphaus.b2clogin.com"
KEYCLOAK = "https://keycloak-service-exec-wms-keycloak-prod.us.live.external.byp.ai"


def _credential(gesture_id: str, system: str) -> Gesture:
    """Typing a password, as the recorder marks it: the value is struck and
    the gesture carries `secret`."""
    return Gesture(
        id=gesture_id,
        tenant="new",
        stream_id="str_1",
        batch_id="bat_1",
        at=0.0,
        url=f"{system}/login",
        system=system,
        tab_id=1,
        frame_url=None,
        action=Action(kind="type", at=0.0, secret=True),
    )


def _wrote_here(gesture_id: str, system: str) -> Gesture:
    """A gesture that saved something back to the system it happened on."""
    return Gesture(
        id=gesture_id,
        tenant="new",
        stream_id="str_1",
        batch_id="bat_1",
        at=0.0,
        url=f"{system}/page",
        system=system,
        tab_id=1,
        frame_url=None,
        action=Action(kind="click", at=0.0),
        requests=[Call(method="POST", url=f"{system}/data/save", status=200)],
    )


def test_a_job_that_is_only_signing_in_is_not_a_job() -> None:
    """`Sign In to WMS`, mined off the real `new` store by the first pass that
    ever ran over real readings: three steps on two identity hosts, no
    parameters, and it would have been offered to an operator as work.

    The transit rule cannot reach it. That one strikes a system the job
    carried on FROM, and this job never carries on anywhere -- its last
    gesture is on the identity host, so the hop stands as if it were the work.
    """
    job, evidence = _job(
        _gesture("ges_1", IDENTITY, left_for=(KEYCLOAK,)),
        _credential("ges_2", KEYCLOAK),
        _gesture("ges_3", KEYCLOAK),
        systems=[IDENTITY, KEYCLOAK],
    )

    rejection = work_only(job, evidence, ours=OURS)

    assert rejection is not None
    assert rejection.reason == "not a job"


def test_the_credential_that_proves_a_sign_in_is_the_one_nobody_cites() -> None:
    """The rule reads what the operator DID, not what the model cited.

    Shipped against the cited list alone, this refusal could not fire on the
    evidence it was written from. A clean re-mine of that same real day
    proposed `Log in to Warehouse Management System` -- SSO option, username,
    Sign In -- and `work_only` let it straight through. The password gesture
    was in the store the whole time; the model had simply not cited it, and
    reasonably so: redaction strips a credential gesture of its value and of
    its target name, so there is nothing left worth pointing at. The one
    gesture that proves a job is a sign-in is the one a model summarising that
    job leaves out.

    Both halves of the span are pinned here. The uncited credential INSIDE the
    job's own time range counts; the one after it does not, or every job that
    happened to precede a sign-in would be condemned by it.
    """
    signed_in = replace(_credential("ges_secret", KEYCLOAK), at=2.0)
    later = replace(_credential("ges_later", KEYCLOAK), at=99.0)
    job, evidence = _job(
        replace(_gesture("ges_1", IDENTITY, left_for=(KEYCLOAK,)), at=1.0),
        replace(_gesture("ges_3", KEYCLOAK), at=3.0),
        systems=[IDENTITY, KEYCLOAK],
    )
    evidence[signed_in.id] = signed_in
    evidence[later.id] = later

    rejection = work_only(job, evidence, ours=OURS)

    assert rejection is not None
    assert rejection.reason == "not a job"

    # And with the credential only OUTSIDE the span, the same job is kept:
    # nothing in what the operator did here was a sign-in.
    kept_job, kept_evidence = _job(
        replace(_gesture("ges_1", IDENTITY, left_for=(KEYCLOAK,)), at=1.0),
        replace(_gesture("ges_3", KEYCLOAK), at=3.0),
        systems=[IDENTITY, KEYCLOAK],
    )
    kept_evidence[later.id] = later

    assert work_only(kept_job, kept_evidence, ours=OURS) is None


def test_another_tabs_credential_is_not_this_jobs_sign_in() -> None:
    """The span is bounded by stream as well as by time. An operator signing
    in to something else in another tab, while this job was running, has not
    turned this job into a sign-in."""
    elsewhere = replace(_credential("ges_other_tab", KEYCLOAK), at=2.0, stream_id="str_2")
    job, evidence = _job(
        replace(_gesture("ges_1", IDENTITY, left_for=(KEYCLOAK,)), at=1.0),
        replace(_gesture("ges_3", KEYCLOAK), at=3.0),
        systems=[IDENTITY, KEYCLOAK],
    )
    evidence[elsewhere.id] = elsewhere

    assert work_only(job, evidence, ours=OURS) is None


def test_a_parameter_no_step_can_be_given_is_named() -> None:
    """`value_for` looks a run's value up by four names: the component's
    `item_id`, its `field_label`, the target's `name`, and the step's own
    `parameters`. A declared parameter that is none of those, on any step, is a
    name nothing will ever ask for -- and that is worse than declaring nothing,
    because `StartWorkflowRun` refuses a press that leaves it empty, so the
    operator types a value and then the step performs with the one the
    RECORDING carried. The job reports success having done something else.

    Real: three clean mines of one day declared six parameters and three of
    them named controls absent from the evidence -- `Description` where the
    label reads `Customer Type Description`, `LPN Limit` for `LPN Warehouse
    Equipment Type Limit`. They bound only because the model had written the
    same invented string into `step.parameters` too, which nothing required.
    """
    typed = _typed_into(
        "ges_1", WMS, item_id="vehicleLimit", label="LPN Warehouse Equipment Type Limit"
    )
    job = _workflow(
        systems=[WMS],
        steps=[Step(order=0, says="enter the limit", system=WMS, cites=["ges_1"])],
    )
    job.parameters = [
        {"name": "LPN Warehouse Equipment Type Limit", "seen_values": ["2"]},
        {"name": "LPN Limit", "seen_values": ["2"]},
    ]

    assert undeliverable(job, {"ges_1": typed}) == ["LPN Limit"]


def test_a_step_may_name_a_parameter_the_control_does_not() -> None:
    """The escape hatch is real and stays: `value_for` checks `step.parameters`
    last precisely so a job can call a field something an operator would
    recognise. What this refuses is only a name that appears in NEITHER."""
    typed = _typed_into(
        "ges_1", WMS, item_id="vehicleLimit", label="LPN Warehouse Equipment Type Limit"
    )
    job = _workflow(
        systems=[WMS],
        steps=[
            Step(
                order=0,
                says="enter the limit",
                system=WMS,
                cites=["ges_1"],
                parameters=["LPN Limit"],
            )
        ],
    )
    job.parameters = [{"name": "LPN Limit", "seen_values": ["2"]}]

    assert undeliverable(job, {"ges_1": typed}) == []


def test_a_warehouse_job_that_sets_a_password_is_still_a_job() -> None:
    """The other half of the rule, and the reason a credential alone does not
    condemn a system: setting a password for a new user is real warehouse
    work, and it types one. What separates it is that the WMS also took the
    write."""
    job, evidence = _job(
        _credential("ges_1", WMS),
        _wrote_here("ges_2", WMS),
        systems=[WMS],
    )

    assert work_only(job, evidence, ours=OURS) is None
    assert job.systems == [WMS]


def test_a_job_that_signs_in_and_then_does_the_work_is_kept() -> None:
    """The third signal, which nothing else here was pinning.

    A credential and a redirect together still describe plenty of real work:
    an operator signs in, the browser moves them on, and then they do the job.
    What separates that from `Sign In to WMS` is whether anything was ever
    written back -- so removing the write check must break a test, and before
    this one it did not.
    """
    job, evidence = _job(
        _credential("ges_1", KEYCLOAK),
        _gesture("ges_2", KEYCLOAK, left_for=(WMS,)),
        _wrote_here("ges_3", WMS),
        systems=[KEYCLOAK, WMS],
    )

    assert work_only(job, evidence, ours=OURS) is None
    assert WMS in job.systems


def test_a_job_too_short_for_resolve_to_ever_match_is_refused() -> None:
    """A one-step proposal is honest and still unkeepable.

    `identity.resolve` needs K_MIN_SHARED_STEPS shared shape entries before it
    will call two proposals the same job, so a shorter one always comes back
    "new" and every pass over the same evidence mints another copy. The real
    acme store grew a second `Create a Customer Type` of one step -- "Save the
    customer type configuration" -- beside the six-step job it was a fragment
    of.

    Nothing else about this workflow is wrong: it cites real evidence, on a
    system that evidence touched, and says something a person could act on. The
    reason is asserted so the guard cannot be satisfied by some other rejection.
    """
    short = _workflow(steps=[Step(order=0, says="save it", system=WMS, cites=["ges_1"])])

    rejection = validate(short, _on("ges_1"))

    assert rejection is not None
    assert rejection.reason == "too few steps to recognise"


def test_a_short_job_is_refused_for_its_dishonesty_first() -> None:
    """The step floor is last of `validate`'s rejections, and deliberately.

    A one-step proposal that also cites a gesture nobody recorded has two
    things wrong with it, and "you cited evidence that does not exist" is the
    one that diagnoses. Ordering this the other way makes every citation bug in
    a short proposal read as a length problem.
    """
    short_and_lying = _workflow(steps=[Step(order=0, says="x", system=WMS, cites=["ges_nope"])])

    rejection = validate(short_and_lying, _on("ges_1"))

    assert rejection is not None
    assert rejection.reason == "unknown gesture"


def _at(gesture_id: str, at: float, system: str = WMS) -> Gesture:
    """A cited gesture that exists only to carry a time."""
    return replace(_gestures("acme")[0], id=gesture_id, at=at, system=system)


def test_a_job_the_operator_did_twice_keeps_one_doing() -> None:
    """The model answers a repeated job as ONE job citing every doing.

    Acme's `Create a Work Area` cites a gesture from 08-26 10:39 and another
    from 08-27 13:16 on the SAME step. `shape_key` then serves a shape with
    both doings interleaved, and the extension's matcher -- which asks whether
    the operator's last k gestures ARE this shape's first k -- can never match
    it against either doing. The three acme jobs with more than one doing in
    them are exactly the three the offer replay never offers.
    """
    day = 86_400.0
    workflow = _workflow(
        steps=[
            Step(order=0, says="open", system=WMS, cites=["mon_1", "tue_1"]),
            Step(order=1, says="type", system=WMS, cites=["mon_2", "tue_2"]),
            Step(order=2, says="save", system=WMS, cites=["tue_3"]),
        ]
    )
    gestures = {
        "mon_1": _at("mon_1", 0.0),
        "mon_2": _at("mon_2", 30.0),
        "tue_1": _at("tue_1", day),
        "tue_2": _at("tue_2", day + 30.0),
        "tue_3": _at("tue_3", day + 60.0),
    }

    one_occurrence(workflow, gestures)

    assert [step.cites for step in workflow.steps] == [["tue_1"], ["tue_2"], ["tue_3"]], (
        "the doing that reaches the most steps, and the later one on a tie"
    )


def test_the_cross_system_job_keeps_every_step_and_loses_the_stray() -> None:
    """The real shape of tenant `new`'s `Create a Warehouse Equipment Type`.

    This is what the architecture exists to find: one step reads a request on
    `mail.google.com`, the rest create the equipment type on the real Blue
    Yonder host. Read down the step list it looks like it has a 22-minute pause
    in it -- step 2 at 15:56:28, step 3 at 16:18:35 -- and a bound read off
    STEP order would split it there and lose step 2.

    In time order there is no 22-minute pause. Step 2 cites TWO gestures, one
    at 15:56:28 left over from an earlier doing and one at 16:18:35 in the
    middle of this one, and every other cited gesture falls between 16:18:35
    and 16:19:24. The only long gap is in front of the whole job.

    So the stray goes, all seven steps survive, and the opening gap falls from
    22 minutes to nothing -- which is what takes the job under the browser's
    own `K_TAIL_TTL_S` and makes it offerable. Narrowing it correctly needed
    the time-order correction first; the two changes are one change.
    """
    mail_read = 16 * 3600 + 18 * 60 + 46
    workflow = _workflow(
        systems=[MAIL, WMS],
        steps=[
            Step(order=0, says="read the mail", system=MAIL, cites=["mail_1"]),
            Step(order=1, says="click add", system=WMS, cites=["stray", "wms_add"]),
            Step(order=2, says="type the code", system=WMS, cites=["wms_code"]),
        ],
    )
    gestures = {
        "mail_1": _at("mail_1", float(mail_read), MAIL),
        # 15:56:28, twenty-two minutes before anything else: the earlier doing.
        "stray": _at("stray", float(15 * 3600 + 56 * 60 + 28)),
        "wms_add": _at("wms_add", float(16 * 3600 + 18 * 60 + 35)),
        "wms_code": _at("wms_code", float(16 * 3600 + 18 * 60 + 38)),
    }

    one_occurrence(workflow, gestures)

    assert [step.cites for step in workflow.steps] == [["mail_1"], ["wms_add"], ["wms_code"]], (
        "the stray goes and no step is left uncited"
    )
    kept = sorted(gestures[c].at for step in workflow.steps for c in step.cites)
    assert kept[1] - kept[0] <= K_SITTING_GAP_S, "and what is left fits in one browser tail"


def test_a_job_done_once_is_left_exactly_as_it_was() -> None:
    """A check that strikes everything strikes the single-doing job too."""
    workflow = _workflow(
        steps=[
            Step(order=0, says="open", system=WMS, cites=["a", "b"]),
            Step(order=1, says="save", system=WMS, cites=["c"]),
        ]
    )
    gestures = {"a": _at("a", 0.0), "b": _at("b", 5.0), "c": _at("c", 11.0)}

    one_occurrence(workflow, gestures)

    assert [step.cites for step in workflow.steps] == [["a", "b"], ["c"]]
