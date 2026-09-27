from dataclasses import replace

from sro.domain.observation.gesture import Action, Gesture, PageMark, Target
from sro.domain.skill.shape import keeping_fields
from sro.domain.skill.tabs import MAIN, tab_roles, unresolved
from sro.domain.skill.workflow import Step, Workflow

WMS = "https://wms.example"


def _gesture(
    id_: str,
    at: float,
    tab: int,
    *,
    marks: tuple[PageMark, ...] = (),
    url: str = WMS,
    kind: str = "click",
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
        action=Action(kind=kind, at=at, target=Target(role="button", name=id_)),
        page_events=list(marks),
    )


def _job(*cites: str | list[str]) -> Workflow:
    return Workflow(
        id="wfl_t",
        tenant="acme",
        title="t",
        narrative="",
        steps=[
            Step(order=n, says=str(one), system=WMS, cites=[one] if isinstance(one, str) else one)
            for n, one in enumerate(cites)
        ],
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


def _popup(at: float, *, tab: int = 9, opener: int = 7) -> PageMark:
    return PageMark(at=at, page_kind="popup_opened", tab_id=tab, opener_tab_id=opener)


def test_a_popup_mark_from_another_sitting_does_not_name_a_tab() -> None:
    """Tab ids repeat across browser sessions: a mark from an hour before the
    doing says nothing about the tab 9 of this one."""
    old = _gesture("old", 0, 7, marks=(_popup(0),))
    by_id = {one.id: one for one in (old, _gesture("a", 3600, 7), _gesture("b", 3601, 9))}
    assert tab_roles(_job("a", "b"), by_id) == {0: MAIN, 1: "tab_2"}


def test_a_steps_tab_is_the_tab_of_its_primary_gesture_not_its_first_cite() -> None:
    scrolled = _gesture("s", 1.5, 8, kind="scroll")
    by_id = {one.id: one for one in (_gesture("a", 1, 7), scrolled, _gesture("b", 2, 7))}
    assert tab_roles(_job("a", ["s", "b"]), by_id) == {0: MAIN, 1: MAIN}


def test_a_new_tab_on_another_system_with_no_opener_is_not_a_second_tab() -> None:
    """`tab_N` is a second tab of the same system; another system reached in a
    new tab is acted in where the step before it acted."""
    sap = "https://sap.example"
    by_id = {one.id: one for one in (_gesture("a", 1, 7), _gesture("b", 2, 8, url=sap))}
    assert tab_roles(_job("a", "b"), by_id) == {0: MAIN, 1: MAIN}


def test_a_popup_cited_before_its_opener_is_not_main() -> None:
    by_id = {
        one.id: one for one in (_gesture("a", 1, 7, marks=(_popup(1.5),)), _gesture("b", 2, 9))
    }
    roles = tab_roles(_job("b", "a"), by_id)
    assert roles == {0: "opened_from:main", 1: MAIN}
    steps = [Step(order=n, says="", system=WMS, tab=role) for n, role in roles.items()]
    assert unresolved(steps) == [0]


def test_an_undecided_step_reads_as_main_and_resolves() -> None:
    steps = [Step(order=0, says="x", system=WMS, tab=None), Step(order=1, says="y", system=WMS)]
    assert [one.role for one in steps] == [MAIN, MAIN]
    assert unresolved(steps) == []


def test_a_field_a_grown_job_carries_takes_the_tab_of_the_step_before_it() -> None:
    by_id = {one.id: one for one in (_gesture("a", 1, 7), _gesture("b", 2, 7))}
    was = replace(
        _job("a", "b"),
        steps=[
            Step(order=0, says="a", system=WMS, cites=["a"]),
            Step(order=1, says="Fill Department", system=WMS, parameters=["dept"]),
            Step(order=2, says="b", system=WMS, cites=["b"]),
        ],
        parameters=[{"name": "dept", "key": "dept"}],
    )
    now = [
        Step(order=0, says="a", system=WMS, cites=["a"], tab="tab_2"),
        Step(order=1, says="b", system=WMS, cites=["b"], tab="tab_2"),
    ]

    steps, _ = keeping_fields(was, now, by_id)

    assert [(one.says, one.tab) for one in steps] == [
        ("a", "tab_2"),
        ("Fill Department", "tab_2"),
        ("b", "tab_2"),
    ]
