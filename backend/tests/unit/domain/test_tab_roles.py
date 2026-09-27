from dataclasses import replace

from sro.domain.observation.gesture import Action, Gesture, PageMark, Target
from sro.domain.skill.tabs import MAIN, tab_roles, unresolved
from sro.domain.skill.workflow import Step, Workflow

WMS = "https://wms.example"


def _gesture(
    id_: str, at: float, tab: int, *, marks: tuple[PageMark, ...] = (), url: str = WMS
) -> Gesture:
    return Gesture(
        id=id_,
        tenant="acme",
        stream_id="s1",
        batch_id="b1",
        at=at,
        url=f"{url}/app",
        system=url,
        tab_id=tab,
        frame_url=None,
        action=Action(kind="click", at=at, target=Target(role="button", name=id_)),
        page_events=list(marks),
    )


def _job(*cites: str) -> Workflow:
    return Workflow(
        id="wfl_t",
        tenant="acme",
        title="t",
        narrative="",
        steps=[Step(order=n, says=one, system=WMS, cites=[one]) for n, one in enumerate(cites)],
    )


def test_a_one_tab_job_is_all_main() -> None:
    by_id = {one.id: one for one in (_gesture("a", 1, 7), _gesture("b", 2, 7))}
    assert tab_roles(_job("a", "b"), by_id) == {0: MAIN, 1: MAIN}


def test_a_tab_opened_by_a_click_is_opened_from_its_opener() -> None:
    opened = PageMark(at=1.5, page_kind="popup_opened", tab_id=9, opener_tab_id=7)
    by_id = {
        one.id: one
        for one in (_gesture("a", 1, 7, marks=(opened,)), _gesture("b", 2, 9), _gesture("c", 3, 7))
    }
    assert tab_roles(_job("a", "b", "c"), by_id) == {0: MAIN, 1: "opened_from:main", 2: MAIN}


def test_a_second_tab_the_operator_opened_is_tab_2() -> None:
    by_id = {one.id: one for one in (_gesture("a", 1, 7), _gesture("b", 2, 8))}
    assert tab_roles(_job("a", "b"), by_id) == {0: MAIN, 1: "tab_2"}


def test_a_mailbox_step_takes_no_tab_of_its_own() -> None:
    by_id = {
        one.id: one
        for one in (_gesture("m", 0, 3, url="https://mail.google.com"), _gesture("a", 1, 7))
    }
    assert tab_roles(_job("m", "a"), by_id) == {0: MAIN, 1: MAIN}


def test_a_role_whose_opener_never_came_first_is_unresolved() -> None:
    steps = [
        Step(order=0, says="x", system=WMS, tab="opened_from:tab_2"),
        Step(order=1, says="y", system=WMS),
    ]
    assert unresolved(steps) == [0]
    fine = [replace(steps[1], order=0), replace(steps[0], order=1, tab="opened_from:main")]
    assert unresolved(fine) == []
