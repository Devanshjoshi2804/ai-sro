"""The served shape, without the queries that gather its evidence.

Every one of these went through `shapes_for(store, ...)` in the rig. Here the
evidence is handed in: the cited pairs, the held tally and this job's counsel.
The loop, the held gate, the per-workflow queries and rekeying stay for the
application layer -- the tests that exercise them are listed at the foot.
"""

import copy
from dataclasses import replace

from sro.domain.observation.gesture import Action, Component, Gesture, Target
from sro.domain.skill.offers import K_OFFER_AFTER, Counsel
from sro.domain.skill.shape import (
    Shape,
    cited_pairs,
    put_by,
    resumes_at,
    shape_of,
    walkable,
)
from sro.domain.skill.workflow import Step, Workflow
from tests.unit.domain.rig.conftest import gestures as _gestures

QUIET = Counsel(offer_after=K_OFFER_AFTER, quiet_until=None)
"""No offer has said anything about this job yet."""

HOST = "http://127.0.0.1:63319"


def _evidence() -> dict[str, Gesture]:
    return {g.id: copy.deepcopy(g) for g in _gestures()}


def _typed(by_id: dict[str, Gesture]) -> Gesture:
    return next(
        g for g in by_id.values() if g.action.kind == "type" and g.action.value == "ACME-4471"
    )


def _saver(by_id: dict[str, Gesture]) -> Gesture:
    """The click on Save. By its control and not by position: half these tests
    put a gesture of their own into `by_id` first."""
    return next(
        g
        for g in by_id.values()
        if g.action.target
        and g.action.target.component
        and g.action.target.component.item_id == "saveButton"
    )


def _a_third_gesture(by_id: dict[str, Gesture]) -> Gesture:
    """The `select` in the committed batch, as this fixture's middle step.

    Three walkable gestures and not two, because `shape_of` refuses to serve a
    shape the matcher could never reach: `recognise.match` scans k down from
    `shape.length - 1` -- an offer leaves something to finish -- so a
    two-position shape has no k at or above `K_OFFER_AFTER`. Every test here
    that is not about that rule needs a job long enough to be offered.
    """
    return next(g for g in by_id.values() if g.action.kind == "select")


def _workflow(by_id: dict[str, Gesture], wid: str = "wfl_1") -> Workflow:
    return Workflow(
        id=wid,
        tenant="acme",
        title="create a client",
        narrative="n",
        systems=[HOST],
        steps=[
            Step(
                order=0,
                says="type the code",
                system=None,
                cites=[_typed(by_id).id],
                parameters=["clientCode"],
            ),
            Step(order=1, says="choose the depot", system=None, cites=[_a_third_gesture(by_id).id]),
            Step(order=2, says="save", system=None, cites=[_saver(by_id).id]),
        ],
        parameters=[{"name": "clientCode", "seen_values": ["ACME-4471"]}],
    )


def _served(
    workflow: Workflow,
    by_id: dict[str, Gesture],
    *,
    held: int = 0,
    advice: Counsel = QUIET,
) -> Shape | None:
    return shape_of(workflow, cited_pairs(workflow, by_id), held=held, advice=advice)


def _scroll(page_url: str = f"{HOST}/") -> Gesture:
    """A scroll as the recorder would have kept it. The committed batch holds
    none -- the browser test that produced it never scrolled -- and half the
    rules below are entirely about scrolls."""
    at = 1788165604.6
    return Gesture(
        id="ges_scroll",
        tenant="acme",
        stream_id="dev_browsertest",
        batch_id="bat_scrolled",
        at=at,
        url=f"{HOST}/",
        system=HOST,
        tab_id=1766715008,
        frame_url=f"{HOST}/",
        action=Action(kind="scroll", at=at, value="300", url=f"{HOST}/", target=None),
        page_url=page_url,
    )


def _scrolled_first(by_id: dict[str, Gesture]) -> Workflow:
    """The same workflow, with a scroll cited ahead of the gesture that types
    the parameter -- which is what a real recording looks like the moment the
    field is below the fold."""
    workflow = _workflow(by_id)
    scroll = _scroll()
    by_id[scroll.id] = scroll
    workflow.steps[0].cites = [scroll.id, *workflow.steps[0].cites]
    return workflow


def test_a_proven_workflow_is_served_as_its_shape_with_where_each_parameter_was_typed() -> None:
    by_id = _evidence()

    shape = _served(_workflow(by_id), by_id, held=0)

    assert shape is not None
    assert shape.id == "wfl_1" and shape.title == "create a client"
    assert shape.starts_on and shape.starts_on.startswith(HOST)
    assert HOST in shape.hosts
    assert len(shape.shape) == 3
    assert [triple[2] for triple in shape.shape] == ["type", "select", "click"]
    assert shape.parameters == [{"name": "clientCode", "at": 0}], (
        "the parameter was typed at shape index 0"
    )
    assert shape.held_runs == 0


def test_the_steps_are_read_in_their_own_order_and_not_the_order_they_arrived_in() -> None:
    """`Workflow.steps` is a list a repository filled, and nothing promises it
    came back sorted. `cited_pairs` sorts by `order`, so a parameter's `at`
    indexes the walk the extension makes; `shape_of` asks the lowest-order
    step where the job begins, not whichever step is written first. A list
    that happens to be in order proves neither."""
    by_id = _evidence()
    workflow = _workflow(by_id)
    # Two pages of one job, so "where it begins" has a wrong answer to give.
    _typed(by_id).page_url = f"{HOST}/clients/new"
    _saver(by_id).page_url = f"{HOST}/clients/saved"
    workflow.steps = list(reversed(workflow.steps))
    assert [step.order for step in workflow.steps] == [2, 1, 0], "the save is written first"

    pairs = cited_pairs(workflow, by_id)
    assert [step.order for _, step in pairs] == [0, 1, 2], "sorted by order, not by arrival"

    shape = shape_of(workflow, pairs, held=0, advice=QUIET)
    assert shape is not None
    assert shape.starts_on == f"{HOST}/clients/new", "the lowest-order step's own gesture"
    assert shape.parameters == [{"name": "clientCode", "at": 0}], "indexed into the sorted walk"


def test_the_page_a_job_begins_on_is_a_screen_and_not_one_visit_to_it() -> None:
    """What was served was the whole url of the first gesture of ONE
    demonstration. On the deployment, 2026-09-15, that put the message id of
    the mail an operator happened to read onto a job served to every browser in
    the tenant -- and on a warehouse job it would be a `libraryContext` session
    token, stale by the time anybody read it.

    Nothing loses anything: every consumer reduces this to host and path before
    comparing it, and `nudge.js` already documents it as "the same shape the
    miner records `starts_on` in" -- a sentence that was not true until now.
    """
    by_id = _evidence()
    workflow = _workflow(by_id)
    _typed(by_id).page_url = f"{HOST}/mail/u/0/?tab=rm&ogbl#inbox/FMfcgzQhWLSTRpPPfBFF"

    shape = shape_of(workflow, cited_pairs(workflow, by_id), held=0, advice=QUIET)

    assert shape is not None
    assert shape.starts_on == f"{HOST}/mail/u/0"
    assert "FMfcg" not in (shape.starts_on or ""), "a message id is not a screen"


def test_the_page_a_job_begins_on_keeps_the_screen_its_fragment_names() -> None:
    """QA 2026-09-29: `Create a Warehouse Equipment Type` was offered on the
    Transport Equipment page. Blue Yonder routes on the fragment, so both
    screens were served as `.../portal` and every arrival on the portal was
    "this job's page". The screen is the one `shape_key` already keys a step
    by: the fragment's route, without the site in the query or the empty
    positional tail."""
    by_id = _evidence()
    workflow = _workflow(by_id)
    by = "https://bf56-kms-wms-web-np2.jdadelivers.com"
    screen = "wm.config/wm.config.equipment.equipment.warehouseequipmenttype"
    _typed(by_id).page_url = f"{by}/portal?siteId=SG#{screen}////"
    for one in by_id.values():
        one.system = by

    shape = shape_of(workflow, cited_pairs(workflow, by_id), held=0, advice=QUIET)

    assert shape is not None
    assert shape.starts_on == f"{by}/portal#{screen}"


def test_the_hosts_a_job_names_are_where_somebody_stood() -> None:
    """Not everywhere their pages called. `hosts` came off `allowlist`, which
    carries the origin of every request a cited gesture made -- so a Gmail
    page's telemetry beacon put `https://play.google.com` on a warehouse job's
    shape. Those request origins are real evidence and `http.send` still needs
    them; they are just not answers to "which systems is this job done on"."""
    by_id = _evidence()
    workflow = _workflow(by_id)
    saver = _saver(by_id)
    saver.requests = [replace(saver.requests[0], url="https://play.google.com/log?id=1")]

    shape = shape_of(workflow, cited_pairs(workflow, by_id), held=0, advice=QUIET)

    assert shape is not None
    assert shape.hosts == [HOST]


# -- a shape entry is a gesture; from_step is a step ---------------------------
#
# `recognise.match` answers with how many SHAPE ENTRIES the operator's tail
# matched, and an entry is one cited gesture: a step of four gestures is four of
# them. The panel sent that number in as `from_step`, which the run reads as how
# many STEPS the operator finished. On the first real job this system mined they
# are 19 and 6.
#
# Under the step count it was silent -- every step below the number recorded
# `done_by_operator` and never sent, so at k=5 on a six-step job the step that
# types the code was skipped and the run went on to the description. At or above
# it the press was refused outright.


def _demonstrated_twice(by_id: dict[str, Gesture]) -> Workflow:
    """A job whose first step cites two gestures, which is what any job
    demonstrated more than once looks like -- and what the fixture, at one
    gesture per step, cannot be. Every step of the deployment's own `Create a
    Customer Type` cites two or more."""
    workflow = _workflow(by_id)
    first, *rest = sorted(workflow.steps, key=lambda step: step.order)
    spare = next(one for one in by_id if one not in first.cites)
    workflow.steps = [replace(first, cites=[*first.cites, spare]), *rest]
    return workflow


def test_the_step_a_browser_is_in_is_the_one_its_last_match_belongs_to() -> None:
    by_id = _evidence()
    workflow = _demonstrated_twice(by_id)
    walk = walkable(cited_pairs(workflow, by_id))
    assert len(walk) > len(workflow.steps), "this test is about the two counts differing"

    for matched, (_, step) in enumerate(walk, start=1):
        assert resumes_at(workflow, by_id, matched) == step.order


def test_a_step_half_matched_is_resumed_at_and_never_counted_done() -> None:
    """The conservative end, deliberately. A step marked done that was only
    half done is never sent and nothing notices; a step performed again that
    the operator had finished is caught -- `already_done` asks the warehouse
    whether the record is there before any live write goes out."""
    by_id = _evidence()
    workflow = _demonstrated_twice(by_id)
    first = min(workflow.steps, key=lambda step: step.order)
    assert len(first.cites) == 2

    assert resumes_at(workflow, by_id, 1) == first.order, "one of its two gestures is not done"


def test_a_job_the_model_numbered_from_one_resumes_at_its_own_first_step() -> None:
    """The fixture numbers its steps from zero, so `matched <= 0` and
    `matched <= 1` answer the same thing on it and a sweep found nothing
    standing between them. The deployment's own job runs 1..6 -- a model numbers
    its own steps and `umbrella` keeps that numbering -- so one match there is
    step ONE, not the top.
    """
    by_id = _evidence()
    workflow = _demonstrated_twice(by_id)
    workflow.steps = [replace(step, order=step.order + 1) for step in workflow.steps]
    walk = walkable(cited_pairs(workflow, by_id))

    assert resumes_at(workflow, by_id, 1) == walk[0][1].order == 1


def test_a_tail_that_matched_nothing_starts_from_the_top() -> None:
    by_id = _evidence()
    workflow = _workflow(by_id)

    assert resumes_at(workflow, by_id, 0) == 0
    assert resumes_at(workflow, by_id, -1) == 0


def test_more_matches_than_there_are_entries_is_clamped_rather_than_believed() -> None:
    """`match` scans k down from `len(shape) - 1` so it cannot overrun, but this
    is a number off the wire and the cost of believing a bad one is an
    IndexError in the middle of somebody's press."""
    by_id = _evidence()
    workflow = _workflow(by_id)
    walk = walkable(cited_pairs(workflow, by_id))

    assert resumes_at(workflow, by_id, 9_999) == walk[-1][1].order


def test_a_job_whose_evidence_is_gone_resumes_from_the_top() -> None:
    by_id = _evidence()
    workflow = _workflow(by_id)

    assert resumes_at(workflow, {}, 3) == 0


def test_a_parameter_no_cited_gesture_typed_has_no_index() -> None:
    by_id = _evidence()
    workflow = _workflow(by_id)
    workflow.parameters.append({"name": "description", "seen_values": ["never typed here"]})

    shape = _served(workflow, by_id)

    assert shape is not None
    assert {"name": "description", "at": None} in shape.parameters


def test_a_workflow_that_starts_somewhere_its_own_evidence_never_names_is_not_served() -> None:
    """The tab was on one origin while the frame that recorded the gesture was
    on another. Serving that sends the extension to an unproven host."""
    by_id = _evidence()
    workflow = _workflow(by_id)
    _typed(by_id).page_url = "https://other.example/x"

    assert _served(workflow, by_id) is None


def test_a_parameter_is_placed_by_the_step_that_declares_it_not_the_first_match() -> None:
    """Search-then-create types the same code twice. The first typing is the
    search box, which is not the control the workflow is filling."""
    by_id = _evidence()
    workflow = _workflow(by_id)
    searched = workflow.steps[0].cites[0]
    workflow.steps = [
        Step(order=0, says="search for it first", system=None, cites=[searched]),
        Step(
            order=1,
            says="type the code",
            system=None,
            cites=[searched],
            parameters=["clientCode"],
        ),
        *[
            Step(order=s.order + 1, says=s.says, system=s.system, cites=s.cites)
            for s in workflow.steps[1:]
        ],
    ]

    shape = _served(workflow, by_id)

    assert shape is not None
    assert len(shape.shape) == 4
    assert shape.parameters == [{"name": "clientCode", "at": 1}], (
        "index 0 is the search box the first value match would have bound"
    )


def test_a_scroll_is_not_part_of_the_shape_that_is_served() -> None:
    """`recognise.js` drops a scroll before the tail is ever written, so a
    served shape carrying one could not be matched at any k -- and a job whose
    first triple is a scroll could never be offered at all."""
    by_id = _evidence()
    workflow = _scrolled_first(by_id)

    shape = _served(workflow, by_id)

    assert shape is not None
    cited = [gesture for step in workflow.steps for gesture in step.cites]
    assert not any(triple[1] == "anon|scroll" for triple in shape.shape)
    assert len(shape.shape) == len(cited) - 1, "three cited gestures, one of them the scroll"


def test_a_parameter_typed_after_a_scroll_is_indexed_into_the_shape_as_served() -> None:
    """`at` is walked against the shape the extension is handed, which has no
    scroll in it. Counted against the unfiltered evidence it would point one
    control to the right and fill the wrong box."""
    by_id = _evidence()

    shape = _served(_scrolled_first(by_id), by_id)

    assert shape is not None
    assert shape.parameters == [{"name": "clientCode", "at": 0}], (
        "index 1 is where the scroll put it in the unfiltered list"
    )


def test_a_parameter_the_workflow_declares_badly_is_dropped_rather_than_served() -> None:
    """A parameter with no name is not a parameter the extension can fill, and
    one with no recorded values was simply never typed anywhere."""
    by_id = _evidence()
    workflow = _workflow(by_id)
    workflow.parameters = [
        {"seen_values": ["ACME-4471"]},
        {"name": "notes"},
        *workflow.parameters,
    ]

    shape = _served(workflow, by_id)

    assert shape is not None
    assert shape.parameters == [
        {"name": "notes", "at": None},
        {"name": "clientCode", "at": 0},
    ]


def test_a_job_whose_first_step_is_only_a_scroll_still_says_where_it_begins() -> None:
    """`primary_gesture` has nothing to return when every gesture the first
    step cites is a scroll, and the job still begins somewhere."""
    by_id = _evidence()
    workflow = _workflow(by_id)
    # Two pages, so the answer is the first step's and not the second's.
    scroll = _scroll(page_url=f"{HOST}/list")
    by_id[scroll.id] = scroll
    # Prepended rather than substituted: dropping the typing would leave one
    # walkable gesture, and `shape_of` refuses a walk `recognise.js` could
    # never match. What is under test is where the job begins, not how short
    # it is.
    workflow.steps.insert(0, Step(order=-1, says="scroll", system=None, cites=[scroll.id]))
    _saver(by_id).page_url = f"{HOST}/form"

    shape = _served(workflow, by_id)

    assert shape is not None
    assert shape.starts_on == f"{HOST}/list"


def test_a_resting_job_is_served_marked_for_the_browser_that_refused_it() -> None:
    """Refused three times running on this browser: still served, and marked.
    The list stays whole and cacheable, and `recognise.js` declines to offer
    the job until the hour the mark names."""
    by_id = _evidence()
    resting = Counsel(offer_after=2, quiet_until="2099-01-01T00:00:00+00:00")

    shape = _served(_workflow(by_id), by_id, advice=resting)

    assert shape is not None
    assert shape.quiet_until == "2099-01-01T00:00:00+00:00"
    assert shape.as_json()["quiet_until"] == shape.quiet_until


def test_a_later_offer_is_capped_at_the_last_gesture_but_one() -> None:
    """Diverged at k=5 on both jobs: counsel says 6 for each. Neither job can
    be offered that late, and the cap is the last gesture but one -- an offer
    has to leave something to finish."""
    by_id = _evidence()
    later = Counsel(offer_after=6, quiet_until=None)
    four = list(by_id.values())
    four_steps = Workflow(
        id="wfl_4",
        tenant="acme",
        title="four gestures",
        narrative="n",
        systems=[HOST],
        steps=[
            Step(order=i, says=f"step {i}", system=None, cites=[four[j].id])
            for i, j in enumerate((0, 1, 2, -1))
        ],
    )

    three_shape = _served(_workflow(by_id), by_id, advice=later)
    four_shape = _served(four_steps, by_id, advice=later)

    assert four_shape is not None and three_shape is not None
    assert len(four_shape.shape) == 4
    assert four_shape.offer_after == 3, "capped at the last gesture but one"
    assert three_shape.offer_after == K_OFFER_AFTER, "and never under the default"


def test_a_job_too_short_to_leave_anything_to_finish_is_never_served() -> None:
    """`recognise.match` scans k down from `shape.length - 1`, so the whole of
    a shape is never a prefix anybody is offered -- and a two-position shape
    therefore has no k at or above `K_OFFER_AFTER` at all.

    This was served until 2026-09-14, off by one against the matcher: every
    browser cached it, walked it on every gesture, and could never fire it.
    Nothing on this side could have caught it, because the offer replay only
    ever fed real mined jobs, all of them longer; it was found by watching a
    browser do a two-step job over and over with the panel open.

    The floor and the cap on `offer_after` are the same rule read from two
    ends: `max(K_OFFER_AFTER, min(advice, len(walk) - 1))` cannot be satisfied
    by a walk of `K_OFFER_AFTER` positions, so serving one is serving a shape
    whose own floor is above its own ceiling.
    """
    by_id = _evidence()
    workflow = _workflow(by_id)
    workflow.steps = [step for step in workflow.steps if step.order != 1]
    assert len(workflow.steps) == K_OFFER_AFTER

    assert _served(workflow, by_id) is None


def test_a_parameter_learned_across_doings_is_placed_by_the_control_that_typed_it() -> None:
    """`parameters_across` records a parameter on the workflow and on no step,
    named after the control it was typed into. Measured on the real corpus:
    four jobs learned eleven parameters in one pass, and every one was served
    with `at: None`."""
    by_id = _evidence()
    typed = _typed(by_id)
    target = typed.action.target
    assert target is not None and target.component is not None
    name = target.component.item_id
    assert name, "the fixture's typed control has a name to learn"
    workflow = Workflow(
        id="wfl_learned",
        tenant="acme",
        title="create a client",
        narrative="n",
        systems=[HOST],
        # No step declares the parameter: it was learned later.
        steps=[
            Step(order=0, says="type the code", system=None, cites=[typed.id]),
            Step(order=1, says="choose the depot", system=None, cites=[_a_third_gesture(by_id).id]),
            Step(order=2, says="save", system=None, cites=[_saver(by_id).id]),
        ],
        parameters=[{"name": name, "seen_values": ["ACME-4471", "ACME-9000"]}],
    )

    shape = _served(workflow, by_id)

    assert shape is not None
    assert shape.parameters == [{"name": name, "at": 0}]


# Left for plan 3, where the loop, its queries and rekeying live:
#   test_a_stored_workflow_is_served_because_storing_it_is_what_proved_it
#   test_the_held_gate_is_per_workflow_and_never_silences_one_that_never_ran
#   test_a_workflow_that_cannot_be_served_never_withdraws_the_ones_behind_it
#   test_a_stored_key_from_an_older_rule_is_recomputed_once
#   test_a_workflow_whose_evidence_is_partly_gone_keeps_its_key
#   test_a_workflow_that_cannot_be_rekeyed_does_not_stop_the_others
#   test_a_resting_job_is_served_marked_for_the_browser_that_refused_it
#     -- the counsel query behind it; the shape's own half is above.


def _picked(text: str, at: float = 1788165604.9) -> Gesture:
    """A click on a row of a floating list -- the WMS's ExtJS combo, whose
    answer is the row's text and whose `value` is nothing at all."""
    return Gesture(
        id=f"ges_picked_{text[:6]}",
        tenant="acme",
        stream_id="dev_browsertest",
        batch_id="bat_picked",
        at=at,
        url=f"{HOST}/",
        system=HOST,
        tab_id=1766715008,
        frame_url=f"{HOST}/",
        action=Action(
            kind="click",
            at=at,
            value=None,
            url=f"{HOST}/",
            target=Target(tag="li", text=text, component=Component(item_id="rpComboBoundList")),
        ),
        page_url=f"{HOST}/",
    )


def test_a_dropdown_pick_is_indexed_by_what_it_clicked_on() -> None:
    """Ten of the forty declared parameters across both real stores had no
    shape index, every one of them a dropdown: clicking a row of an ExtJS
    combo's floating list carries the choice in the row's TEXT and in no
    `value` anywhere, so an offer drew an empty box for `External System Name`
    however plainly the operator had just picked it."""
    by_id = _evidence()
    workflow = _workflow(by_id)
    picked = _picked("ConnectShip (TanData)")
    by_id[picked.id] = picked
    workflow.steps.append(
        Step(order=3, says="pick the system", system=None, cites=[picked.id], parameters=["system"])
    )
    workflow.parameters.append({"name": "system", "seen_values": ["ConnectShip (TanData)"]})

    shape = _served(workflow, by_id)

    assert shape is not None
    assert {"name": "system", "at": 3} in shape.parameters


def test_a_label_no_seen_value_matches_is_nobodys_answer() -> None:
    """Every click has a label, and the match against the parameter's own
    `seen_values` is the whole of what keeps this honest: the click on Save is
    still a click on Save."""
    by_id = _evidence()
    workflow = _workflow(by_id)
    saver = _saver(by_id)
    assert saver.action.target is not None
    saver.action = replace(saver.action, target=replace(saver.action.target, text="Save"))
    workflow.parameters.append({"name": "system", "seen_values": ["ConnectShip (TanData)"]})

    shape = _served(workflow, by_id)

    assert shape is not None
    assert {"name": "system", "at": None} in shape.parameters


def test_a_parameter_is_placed_where_its_own_value_was_put_and_nowhere_else() -> None:
    """`seen & put_by(gesture)` is an INTERSECTION, and that is the whole rule.

    Read as a union it is satisfied whenever either side is non-empty, which is
    every gesture that put anything and every parameter anybody declared -- so
    a parameter would be indexed at the first control in the walk whatever was
    typed into it, and the offer would lift somebody else's value off the tail.

    The step declaring the parameter is the right step here; what it typed is
    not one of the parameter's seen values, so there is no index to give.
    """
    by_id = _evidence()
    workflow = _workflow(by_id)
    workflow.parameters = [{"name": "clientCode", "seen_values": ["SOMETHING-ELSE"]}]

    shape = _served(workflow, by_id)

    assert shape is not None
    assert shape.parameters == [{"name": "clientCode", "at": None}]


def test_a_learned_parameter_needs_both_the_control_and_the_value() -> None:
    """The second scan is narrower than a value scan on purpose -- the search
    box is not named `workArea` -- and narrower than a name scan too: a control
    of the right name that put none of the parameter's values is not where it
    sits. `and`, read as `or`, makes either half enough."""
    by_id = _evidence()
    typed = _typed(by_id)
    target = typed.action.target
    assert target is not None and target.component is not None
    workflow = Workflow(
        id="wfl_learned_wrong",
        tenant="acme",
        title="create a client",
        narrative="n",
        # No step declares it, so only the control-and-value scan can place it.
        steps=[
            Step(order=0, says="type the code", system=None, cites=[typed.id]),
            Step(order=1, says="choose the depot", system=None, cites=[_a_third_gesture(by_id).id]),
            Step(order=2, says="save", system=None, cites=[_saver(by_id).id]),
        ],
        systems=[HOST],
        parameters=[{"name": target.component.item_id, "seen_values": ["NEVER-TYPED"]}],
    )

    shape = _served(workflow, by_id)

    assert shape is not None
    assert shape.parameters == [{"name": target.component.item_id, "at": None}]


def test_a_click_that_put_nothing_contributes_no_label() -> None:
    """`kind == "click" and target and target.text` -- all three, and the
    precedence matters: read as `(kind and target) or target.text`, a TYPE
    gesture on a control with a label would contribute that label as something
    the operator put, and "Save" would become a value the offer could fill in.
    """
    typed_in = _typed(_evidence())
    target = typed_in.action.target
    assert target is not None
    labelled = replace(typed_in.action, target=replace(target, text="Save"))

    put = put_by(replace(typed_in, action=labelled))

    assert put == {"ACME-4471"}, "a typed field puts its value, never its label"


def test_a_pick_on_a_struck_out_control_puts_nothing() -> None:
    """The rule `typed_values` and the browser's own tail already wear."""
    picked = _picked("ConnectShip (TanData)")
    assert picked.action.target is not None
    struck = replace(picked.action, target=replace(picked.action.target, secret=True))

    assert put_by(replace(picked, action=struck)) == set()


# --- a mailbox is where work is asked for, not work to repeat ----------------


def _in_a_mailbox(by_id: dict[str, Gesture], *, host: str = "mail.google.com") -> Workflow:
    """The same three-step job, done entirely in a mailbox -- which is what the
    miner makes of an operator who lives in their mail: this deployment holds
    four `Compose Email`, two `Reply to Email` and two `Forward an Email`."""
    for one in by_id.values():
        one.url = f"https://{host}/mail/u/0/#inbox"
        one.page_url = one.url
        one.system = f"https://{host}"
    return _workflow(by_id)


def test_a_job_done_entirely_in_a_mailbox_is_not_served() -> None:
    """The matcher offers a job when the last gestures look like its first, and
    in a mailbox that is most of the time. Measured 2026-09-19: an operator
    working through six requests was offered `Forward an Email` on nearly every
    screen, with the card that mattered underneath it -- and the mail reader
    hesitated between `Create a Customer Type` and `Forward an Email` for a
    mail that plainly asked for the first."""
    by_id = _evidence()

    assert _served(_in_a_mailbox(by_id), by_id) is None


def test_the_other_mailboxes_this_system_knows_about_count_too() -> None:
    """`K_MAILBOXES` is the named list `asked_by` reads requests out of, and
    both halves of the system have to mean the same thing by "a mailbox"."""
    by_id = _evidence()

    assert _served(_in_a_mailbox(by_id, host="outlook.office.com"), by_id) is None


def test_a_mailbox_host_with_an_explicit_port_still_counts() -> None:
    """The netloc is split on `:` before it is matched, so a host named with
    its port is still the same mailbox."""
    by_id = _evidence()

    assert _served(_in_a_mailbox(by_id, host="mail.google.com:443"), by_id) is None


def test_a_mailbox_system_still_counts_when_the_gesture_has_no_url() -> None:
    """A tool step in the mailbox names its `system` and never its own `url`;
    the fallback from `url` to `system` has to hold for it too."""
    by_id = _evidence()
    workflow = _in_a_mailbox(by_id)
    for gesture in by_id.values():
        gesture.url = None

    assert _served(workflow, by_id) is None


def test_the_gestures_own_url_decides_over_a_different_system() -> None:
    """`system` is the channel a gesture went out on, not where it happened.
    A job entirely inside the mailbox by its own `url`s counts even when
    every gesture's `system` names the warehouse instead."""
    by_id = _evidence()
    workflow = _in_a_mailbox(by_id)
    for gesture in by_id.values():
        gesture.system = HOST

    assert _served(workflow, by_id) is None


def test_a_gesture_with_neither_a_url_nor_a_system_is_not_a_mailbox() -> None:
    """`_all_in_a_mailbox` reads `url`, falling back to `system` -- and a
    gesture that names neither is not read as being in the mailbox, so one
    among an otherwise-mailbox job is enough to still serve it."""
    by_id = _evidence()
    workflow = _in_a_mailbox(by_id)
    stray = _saver(by_id)
    stray.url = None
    stray.system = None

    assert _served(workflow, by_id) is not None


def test_a_job_that_reads_a_mail_and_then_acts_is_still_served() -> None:
    """The shape this whole system is for. Every gesture, not any: a job that
    reads a request and then does it in the warehouse cites gestures on both,
    and refusing that would turn off the product."""
    by_id = _evidence()
    reads_first = _typed(by_id)
    reads_first.url = "https://mail.google.com/mail/u/0/#inbox"
    reads_first.page_url = reads_first.url
    reads_first.system = "https://mail.google.com"

    shape = _served(_workflow(by_id), by_id)

    assert shape is not None
    assert shape.id == "wfl_1"
