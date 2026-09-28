from collections.abc import Sequence
from dataclasses import replace

import pytest
from evals.model import Case, Scored, as_markdown, report
from evals.run import SUITES, reachable, run_ci
from evals.suites.repair import Repair, broken

from sro.application.context import RequestContext
from sro.application.ports.page import PageAnswer, PageGone
from sro.application.ports.vision import ProposedGesture, Screen
from sro.application.runtime.sight_lane import sight_goal
from sro.application.runtime.step import Held
from sro.application.runtime.ui_lane import ui_payload
from sro.domain.execution.account import Account
from sro.domain.execution.workflow_run import RunStep, WorkflowRun
from sro.domain.observation.gesture import Action, Call, Component, Gesture, Landmark, Target
from sro.domain.prompts.sight import SIGHT
from sro.domain.recording.events import ActionKind
from sro.domain.skill.workflow import Step, Workflow
from tests import factories as f
from tests.unit.fakes import FakeUnitOfWork
from tests.unit.runtime_support import lane_context, scripted_driver


class _Broker:
    """Only what the suite calls: the account's lease on the default tab, and its release."""

    def __init__(self) -> None:
        self.released: list[str] = []

    async def account_for(self, ctx: RequestContext, start_url: str) -> Account:
        return Account.of("acme", "https://wms.example", "clerk")

    async def acquire(
        self, ctx: RequestContext, account: Account, start_url: str, *, holder: str
    ) -> Held:
        held = lane_context({}).held
        assert held is not None
        return held

    async def release(self, ctx: RequestContext, held: Held) -> None:
        self.released.append(held.target_id)


class _Vision:
    def __init__(self, x: int | None = 10, y: int | None = 20) -> None:
        self.x, self.y = x, y

    async def propose(
        self,
        *,
        goal: str,
        screen: Screen,
        allowed: Sequence[ActionKind],
        history: Sequence[str] = (),
    ) -> ProposedGesture:
        return ProposedGesture(ActionKind.CLICK, x=self.x, y=self.y)


def _case(write: bool) -> Case:
    return Case(
        id="wfl_x:1",
        suite="repair-ui",
        input={
            "tenant": "acme",
            "page": "https://wms.example/app",
            "goal": "Open the Orders tab.",
            "write": write,
            "payload": {
                "action": "click",
                "value": None,
                "write": False,
                "target": {"role": "tab", "name": "Orders", "xpath": "/html/body/div[2]"},
                "learned": None,
                "frame_path": None,
            },
        },
        expected={},
    )


async def test_ui_repair_passes_when_it_finds_the_control_that_held_and_nothing_acted() -> None:
    driver = scripted_driver(
        url="https://wms.example/app",
        resolved=[
            PageAnswer(ok=True, candidates=1, matched_by="xpath", xpath="/html/body/div[2]"),
            PageAnswer(ok=True, candidates=1, matched_by="repair", xpath="/html/body/div[2]"),
        ],
    )

    scored = await Repair("ui", None, _Broker(), driver).run(_case(write=False), None)

    assert scored.passed
    assert driver.acted == [] and driver.pointed == []


async def test_a_page_that_does_not_show_the_recorded_control_is_unreachable_not_failed() -> None:
    driver = scripted_driver(
        url="https://wms.example/app", resolved=[PageAnswer(ok=False, candidates=0)]
    )

    scored = await Repair("ui", None, _Broker(), driver).run(_case(write=False), None)

    assert (scored.passed, scored.sure, scored.latency_s) == (False, False, -1.0)


async def test_sight_passes_when_its_point_resolves_to_the_control_that_held() -> None:
    driver = scripted_driver(
        url="https://wms.example/app",
        hit={"strategy": "text", "query": "Orders", "frame_path": []},
        resolved=[
            PageAnswer(ok=True, candidates=1, xpath="/html/body/div[2]"),
            PageAnswer(ok=True, candidates=1, xpath="/html/body/div[2]"),
        ],
    )

    scored = await Repair("sight", _Vision(), _Broker(), driver).run(_case(write=True), None)

    assert scored.passed and driver.acted == [] and driver.pointed == []


async def test_ui_repair_that_names_another_control_is_sure_and_wrong() -> None:
    driver = scripted_driver(
        url="https://wms.example/app",
        resolved=[
            PageAnswer(ok=True, candidates=1, matched_by="xpath", xpath="/html/body/div[2]"),
            PageAnswer(ok=True, candidates=1, matched_by="repair", xpath="/html/body/div[3]"),
        ],
    )

    scored = await Repair("ui", None, _Broker(), driver).run(_case(write=False), None)

    assert (scored.passed, scored.sure) == (False, True)


async def test_a_control_found_by_a_surviving_locator_is_not_a_repair() -> None:
    """The broken target must reach the page with nothing left to find it by,
    or the suite scores the locator that survived and calls it repair."""
    driver = scripted_driver(
        url="https://wms.example/app",
        resolved=[
            PageAnswer(ok=True, candidates=1, matched_by="xpath", xpath="/html/body/div[2]"),
            PageAnswer(ok=True, candidates=1, matched_by="text", xpath="/html/body/div[2]"),
        ],
    )

    scored = await Repair("ui", None, _Broker(), driver).run(_case(write=False), None)

    assert (scored.passed, scored.sure) == (False, True)


async def test_the_recorded_control_is_found_without_repair_and_the_broken_one_with() -> None:
    driver = scripted_driver(
        url="https://wms.example/app",
        resolved=[
            PageAnswer(ok=True, candidates=1, matched_by="xpath", xpath="/html/body/div[2]"),
            PageAnswer(ok=True, candidates=1, matched_by="repair", xpath="/html/body/div[2]"),
        ],
    )

    await Repair("ui", None, _Broker(), driver).run(_case(write=False), None)

    recorded, repaired = driver.resolved
    assert recorded.get("write") is not False
    assert repaired["write"] is False and repaired["learned"] is None


def test_a_broken_target_keeps_only_what_repair_scores_by() -> None:
    target = Target(
        tag="button",
        role="tab",
        name="Orders",
        text="Orders",
        test_id="orders",
        css_path="div > button",
        xpath="/html/body/div[2]",
        component=Component(item_id="orders-tab", chain=("tabpanel", "tab")),
        bounds={"x": 1.0, "y": 2.0, "width": 30.0, "height": 10.0},
        attributes={"name": "orders", "autocomplete": "off", "id": "t1", "placeholder": "Tab"},
        landmarks=(Landmark("navigation", "Main"),),
    )
    gesture = _gesture("g-1", target=target)
    payload = ui_payload(_step(["g-1"]), gesture, None, None, {"g-1": gesture})

    gone = broken(payload)["target"]

    assert isinstance(gone, dict)
    assert not {"text", "test_id", "css_path", "xpath", "component"} & set(gone)
    assert gone["attributes"] == {"placeholder": "Tab"}
    assert gone["name"] == "Orders (renamed)"
    assert (gone["role"], gone["tag"], gone["bounds"]) == ("tab", "button", target.bounds)
    assert list(gone["landmarks"]) == [{"role": "navigation", "name": "Main"}]


async def test_a_sight_point_is_resolved_back_through_the_hit_s_own_locator() -> None:
    driver = scripted_driver(
        url="https://wms.example/app",
        hit={"strategy": "role_and_name", "query": "tab|Orders", "frame_path": [{"index": 0}]},
        resolved=[
            PageAnswer(ok=True, candidates=1, xpath="/html/body/div[2]"),
            PageAnswer(ok=True, candidates=1, xpath="/html/body/div[3]"),
        ],
    )

    scored = await Repair("sight", _Vision(), _Broker(), driver).run(_case(write=True), None)

    again = driver.resolved[1]
    assert again["learned"] == {"strategy": "role_and_name", "query": "tab|Orders"}
    assert again["target"] == {} and again["frame_path"] == [{"index": 0}]
    assert (scored.passed, scored.sure) == (False, True)


async def test_a_model_that_names_no_point_is_unsure_not_unreachable() -> None:
    driver = scripted_driver(
        url="https://wms.example/app",
        resolved=[PageAnswer(ok=True, candidates=1, xpath="/html/body/div[2]")],
    )

    scored = await Repair("sight", _Vision(None, None), _Broker(), driver).run(
        _case(write=True),
        None,
    )

    assert (scored.passed, scored.sure) == (False, False) and scored.latency_s >= 0


async def test_the_lease_is_released_even_when_the_page_goes() -> None:
    broker = _Broker()
    driver = scripted_driver(
        url="https://wms.example/app",
        resolved=[PageAnswer(ok=True, candidates=1, xpath="/html/body/div[2]")],
    )
    driver.dead.add("sess-1")

    with pytest.raises(PageGone):
        await Repair("sight", _Vision(), broker, driver).run(_case(write=True), None)

    assert broker.released == ["tab-1"]


def _gesture(gesture_id: str, *, target: Target | None, page: str | None = None) -> Gesture:
    return Gesture(
        id=gesture_id,
        tenant="acme",
        stream_id="str-1",
        batch_id="bat-1",
        at=10.0,
        url="https://wms.example/app",
        system="https://wms.example",
        tab_id=1,
        frame_url=None,
        action=Action(kind="click", at=10.0, target=target),
        page_url=page,
    )


def _step(cites: list[str], order: int = 0) -> Step:
    return Step(order=order, says=f"Open the tab {order}", system=None, cites=cites)


def _run(workflow_id: str) -> WorkflowRun:
    return WorkflowRun(
        id=f"run-{workflow_id}",
        tenant="acme",
        workflow_id=workflow_id,
        device_id="dev-1",
        values={},
        started_by="offer",
        live=True,
        allow_focus=True,
        started_at="2026-09-01T09:00:00+00:00",
        outcome="held",
        steps=[RunStep(order=0, says="open", verdict="held", verdict_by="status")],
    )


async def _recorded() -> FakeUnitOfWork:
    """One held job: a read click with a page, a write click, a click with no
    xpath and one with no page; and a job that never held."""
    page = "https://wms.example/app"
    tab = Target(role="tab", name="Orders", xpath="/html/body/div[2]")
    gestures = [
        _gesture("g-read", target=tab, page=page),
        replace(
            _gesture("g-write", target=replace(tab, name="Save"), page=page),
            requests=[Call("POST", "https://wms.example/api/orders", started_at=10.0)],
        ),
        _gesture("g-no-xpath", target=replace(tab, xpath=None), page=page),
        _gesture("g-no-page", target=tab),
        _gesture("g-unheld", target=tab, page=page),
    ]
    held = Workflow(
        id="wfl_held",
        tenant="acme",
        title="Open orders",
        narrative="",
        steps=[
            _step(["g-read"], 0),
            _step(["g-write"], 1),
            _step(["g-no-xpath"], 2),
            _step(["g-no-page"], 3),
        ],
    )
    unheld = Workflow(
        id="wfl_unheld", tenant="acme", title="Never ran", narrative="", steps=[_step(["g-unheld"])]
    )
    uow = FakeUnitOfWork()
    async with uow:
        await uow.workflows.save(held)
        await uow.workflows.save(unheld)
        await uow.gestures.add_gestures(tuple(gestures))
        await uow.workflow_runs.save(_run("wfl_held"))
        await uow.commit()
    return uow


async def test_a_case_is_a_held_job_s_step_whose_recorded_control_has_a_page_and_an_xpath() -> None:
    uow = await _recorded()

    sight = await Repair("sight", _Vision(), _Broker(), scripted_driver()).cases(uow, f.TENANT)
    ui = await Repair("ui", None, _Broker(), scripted_driver()).cases(uow, f.TENANT)

    assert [one.id for one in sight] == ["wfl_held:0", "wfl_held:1"]
    assert [one.id for one in ui] == ["wfl_held:0"]
    assert [one.input["write"] for one in sight] == [False, True]


async def test_a_case_carries_the_lane_s_own_payload_and_goal() -> None:
    uow = await _recorded()
    workflow = next(one for one in await uow.workflows.known(f.TENANT) if one.id == "wfl_held")
    by_id = {one.id: one for one in await uow.gestures.gestures_for(f.TENANT, ids=("g-write",))}
    step, gesture = workflow.steps[1], by_id["g-write"]

    sight = await Repair("sight", _Vision(), _Broker(), scripted_driver()).cases(uow, f.TENANT)

    assert sight[1].input["payload"] == ui_payload(step, gesture, None, None, by_id)
    assert sight[1].input["goal"] == sight_goal(step, {}, gesture)
    assert sight[1].input["page"] == "https://wms.example/app"
    assert (sight[1].suite, sight[1].input["tenant"]) == ("repair-sight", "acme")


def test_unreachable_cases_are_counted_and_left_out_of_the_measure() -> None:
    scored = [
        Scored("a", passed=True, sure=True, cost_usd=0.0, latency_s=1.0),
        Scored("b", passed=False, sure=False, cost_usd=0.0, latency_s=-1.0),
    ]

    kept, unreachable = reachable(scored)
    now = report("repair-ui", SIGHT, kept, unreachable=unreachable)

    assert (now.cases, now.accuracy, now.unreachable, now.case_ids) == (1, 1.0, 1, ("a",))
    header, row = as_markdown(now, []).split("\n")[2:5:2]
    assert header.startswith("| cases | unreachable |") and row.startswith("| 1 | 1 |")


def test_the_repair_suites_are_run_by_name() -> None:
    assert {"mining", "reader", "repair-sight", "repair-ui"} <= set(SUITES)


def test_a_repair_suite_needs_the_live_stack() -> None:
    with pytest.raises(SystemExit):
        SUITES["repair-ui"](None)


async def test_ci_skips_a_suite_with_no_committed_folder(tmp_path) -> None:  # type: ignore[no-untyped-def]
    (tmp_path / "mining").mkdir()

    assert await run_ci(live=False, folder=tmp_path) == 1
