"""What the operator did after a step failed, taken as the repair for it.

The deployment's own shape, 2026-09-19: `Delete a Customer Type` failed four
times in twenty minutes, every time on step 0 -- *"the filter dropdown is not
open on the screen"* -- and every time the operator opened that dropdown by
hand a moment later. All four repairs were captured and none of them reached
the job.
"""

from __future__ import annotations

from sro.domain.execution.rescued import BY_HAND, K_SOON, rescued_by
from sro.domain.observation.gesture import Action, Gesture, Target
from sro.domain.skill.workflow import Step

WMS = "https://bf56-kms-wms-web-np2.jdadelivers.com"
MAIL = "https://mail.google.com"

FINISHED = 1_000.0
"""When the run that failed ended, on the browser's clock."""


def _gesture(gesture_id: str, at: float, url: str, target: Target | None) -> Gesture:
    return Gesture(
        id=gesture_id,
        tenant="greyorange",
        stream_id="s",
        batch_id="b",
        at=at,
        url=f"{url}/wms/customerTypes",
        system=url,
        tab_id=1,
        frame_url=None,
        action=Action(kind="click", at=at, url=f"{url}/wms/customerTypes", target=target),
    )


DROPDOWN = Target(role="button", name="Filter", text="Filter", css_path="div.f > button")
SOMETHING_ELSE = Target(role="button", name="Export", text="Export")

STEP = Step(order=0, says="Opens the filter dropdown", system=None, cites=["g-old"])
CITED = {"g-old": _gesture("g-old", 1.0, WMS, Target(test_id="filter-btn"))}


def test_the_control_the_operator_used_is_what_the_step_should_have_used() -> None:
    found = rescued_by(
        STEP,
        f"{WMS}/wms/customerTypes",
        FINISHED,
        [_gesture("g-fix", FINISHED + 4.0, WMS, DROPDOWN)],
        CITED,
    )

    assert found is not None
    assert (found.ord, found.strategy, found.query) == (0, "role_and_name", "button|Filter")
    assert found.found_by == BY_HAND


def test_what_the_run_itself_drove_is_not_the_operator_repairing_it() -> None:
    """A run drives the browser and what it drives is recorded like anything
    else. Only what happened after the run ended can be somebody's own."""
    found = rescued_by(
        STEP,
        f"{WMS}/wms/customerTypes",
        FINISHED,
        [_gesture("g-run", FINISHED - 2.0, WMS, DROPDOWN)],
        CITED,
    )

    assert found is None


def test_tomorrows_work_is_not_a_correction_to_last_nights_failure() -> None:
    found = rescued_by(
        STEP,
        f"{WMS}/wms/customerTypes",
        FINISHED,
        [_gesture("g-late", FINISHED + K_SOON + 1.0, WMS, DROPDOWN)],
        CITED,
    )

    assert found is None


def test_a_gesture_in_another_system_is_somebody_getting_on_with_something() -> None:
    found = rescued_by(
        STEP,
        f"{WMS}/wms/customerTypes",
        FINISHED,
        [_gesture("g-mail", FINISHED + 3.0, MAIL, DROPDOWN)],
        CITED,
    )

    assert found is None


def test_the_first_thing_they_did_is_the_answer_not_the_next_one() -> None:
    found = rescued_by(
        STEP,
        f"{WMS}/wms/customerTypes",
        FINISHED,
        [
            _gesture("g-later", FINISHED + 9.0, WMS, SOMETHING_ELSE),
            _gesture("g-fix", FINISHED + 4.0, WMS, DROPDOWN),
        ],
        CITED,
    )

    assert found is not None
    assert found.query == "button|Filter"


def test_a_gesture_that_names_no_control_teaches_nothing() -> None:
    """A scroll has no target and so has no ladder."""
    found = rescued_by(
        STEP,
        f"{WMS}/wms/customerTypes",
        FINISHED,
        [_gesture("g-scroll", FINISHED + 2.0, WMS, None)],
        CITED,
    )

    assert found is None


def test_the_job_is_not_taught_what_its_own_evidence_already_says() -> None:
    """The step knew the control and failed for another reason; writing it down
    would be the job telling itself what it already says."""
    found = rescued_by(
        STEP,
        f"{WMS}/wms/customerTypes",
        FINISHED,
        [_gesture("g-fix", FINISHED + 4.0, WMS, DROPDOWN)],
        {"g-old": _gesture("g-old", 1.0, WMS, DROPDOWN)},
    )

    assert found is None


def test_the_scroll_on_the_way_to_the_repair_is_not_the_repair() -> None:
    """Somebody scrolls to the control before they press it. The first gesture
    that NAMES something is the answer, not the first gesture."""
    found = rescued_by(
        STEP,
        f"{WMS}/wms/customerTypes",
        FINISHED,
        [
            _gesture("g-scroll", FINISHED + 2.0, WMS, None),
            _gesture("g-fix", FINISHED + 4.0, WMS, DROPDOWN),
        ],
        CITED,
    )

    assert found is not None
    assert found.query == "button|Filter"


def test_a_step_that_was_on_no_page_has_nothing_to_learn_from() -> None:
    """And nothing a page-less gesture did is "the same page" as no page: both
    sides reduce to the empty origin, and an equality between them would teach
    a step on no screen from a gesture on no screen."""
    nowhere = _gesture("g-nowhere", FINISHED + 4.0, WMS, DROPDOWN)
    nowhere.url = None
    nowhere.system = None

    assert rescued_by(STEP, "", FINISHED, [nowhere], CITED) is None
    assert rescued_by(STEP, f"{WMS}/wms/customerTypes", FINISHED, [nowhere], CITED) is None
