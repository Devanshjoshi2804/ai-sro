import asyncio
import base64
import copy
import json
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

import pytest

from rig.api import save_batch
from rig.channel import Answer as Reply
from rig.channel import DeviceUnreachable, FakeChannel
from rig.effects import record_effect
from rig.models import Answer, FakeAsker
from rig.planner import PLAN_SCHEMA, Look, Planned
from rig.runner import (
    K_STEP_SLACK,
    Aborts,
    Approvals,
    _bill,
    _fell_over,
    _gestures_for,
    _look,
    _now,
    _result,
    _saw_nothing,
    _target_origin,
    _withheld,
    clear_stale,
    mark_stale,
    run_workflow,
)
from rig.runs import Run, RunStep, load_run, save_run
from rig.store import Store
from rig.wire import Batch
from rig.workflows import Step, Workflow, save_workflow
from tests.fixtures import BATCH


def _store(tmp_path: Path) -> Store:
    store = Store(tmp_path / "rig.db")
    store.migrate()
    save_batch(store, Batch.model_validate(BATCH), "acme")
    return store


def _ids(store: Store) -> list[str]:
    return [r["id"] for r in store.query("SELECT id FROM gestures ORDER BY at")]


def _workflow(store: Store) -> Workflow:
    ids = _ids(store)
    typed, saver = ids[0], ids[-1]
    wf = Workflow(
        id="wfl_1",
        tenant="acme",
        title="create a client",
        narrative="n",
        systems=["http://127.0.0.1:63319"],
        steps=[
            Step(
                order=0, says="type the code", system=None, cites=[typed], parameters=["clientCode"]
            ),
            Step(order=1, says="save", system=None, cites=[saver]),
        ],
        parameters=[{"name": "clientCode", "seen_values": ["A", "B"]}],
    )
    save_workflow(store, wf)
    return wf


def _plan(action: str, value: str | None = None) -> Answer:
    return Answer(
        data={"kind": "ui.perform", "action": action, "value": value, "url": None, "why": "w"},
        cost_usd=0.001,
    )


def _earned(_workflow_id: str) -> bool:
    """These tests predate the approval pause, and are about the loop rather
    than about the tap. They run as a job that has earned the right to write
    unasked; the tests that are about the pause take the default."""
    return True


def _looks(n: int) -> dict[str, list[Reply]]:
    return {
        "ui.url": [Reply(ok=True, result={"url": "http://127.0.0.1:63319/form"})] * n,
        "screenshot": [Reply(ok=True, result={"image_base64": "aVBORw0=", "text_digest": "Save"})]
        * n,
    }


class _per_schema_asker(FakeAsker):
    """`FakeAsker`, answered by schema rather than by call order.

    A run that starts mid-job asks a different number of questions than one
    that starts at the top, and a positional queue has to be rewritten every
    time that number moves. This one answers `verdict` to a verification and
    `plan` to everything else -- the same split `scripts/dry_run.py` makes --
    and still records every call in `.asked`.
    """

    def __init__(self, plan: Answer, verdict: Answer) -> None:
        super().__init__()
        self.plan, self.verdict = plan, verdict

    async def ask(self, **asked: Any) -> Answer:
        await super().ask(**asked)
        return self.verdict if "held" in asked["schema"]["properties"] else self.plan


def _navigate() -> Answer:
    return Answer(
        data={
            "kind": "navigate",
            "action": None,
            "value": None,
            "url": "http://127.0.0.1:63319/form",
            "why": "wrong page",
        }
    )


def _repeated(store: Store, steps: int) -> Workflow:
    """One workflow of `steps` identical read steps, all citing the same typed
    gesture. Nothing here writes, so every step is performable in a live run."""
    typed = _ids(store)[0]
    wf = Workflow(
        id="wfl_n",
        tenant="acme",
        title="type it again",
        narrative="n",
        systems=["http://127.0.0.1:63319"],
        steps=[
            Step(
                order=i, says="type the code", system=None, cites=[typed], parameters=["clientCode"]
            )
            for i in range(steps)
        ],
    )
    save_workflow(store, wf)
    return wf


def _silent_click(store: Store) -> str:
    """A click the recorder saw and heard no traffic from -- what a Save looks
    like when its call went out somewhere the recorder was not attached."""
    rows = store.query("SELECT id, gesture_json FROM gestures WHERE requests = '[]' ORDER BY at")
    return next(r["id"] for r in rows if json.loads(r["gesture_json"])["kind"] == "click")


def _only_run(store: Store) -> str:
    return str(store.query("SELECT id FROM runs")[0]["id"])


def _one_step(store: Store, cite: str, says: str = "save") -> Workflow:
    wf = Workflow(
        id="wfl_one",
        tenant="acme",
        title=says,
        narrative="n",
        systems=["http://127.0.0.1:63319"],
        steps=[Step(order=0, says=says, system=None, cites=[cite])],
    )
    save_workflow(store, wf)
    return wf


async def test_a_dry_run_sends_the_reads_and_withholds_the_write_in_full(tmp_path: Path) -> None:
    store = _store(tmp_path)
    wf = _workflow(store)
    channel = FakeChannel(
        {
            **_looks(4),
            "ui.perform": [
                Reply(
                    ok=True, result={"performed": True, "matched_by": "component", "candidates": 1}
                )
            ],
        }
    )
    asker = FakeAsker(
        _plan("type", "THIRD"), Answer(data={"held": True, "why": "typed"}), _plan("click")
    )

    run = await run_workflow(
        store,
        wf,
        values={"clientCode": "THIRD"},
        channel=channel,
        device_id="dev_test",
        asker=asker,
        plan_model="flash",
        rescue_model="pro",
        live=False,
        allow_focus=True,
        started_by="form",
    )

    assert run.outcome == "held"
    assert [s.verdict for s in run.steps] == ["held", "withheld"]
    performed = [s for s in channel.sent if s["kind"] == "ui.perform"]
    assert len(performed) == 1 and performed[0]["payload"]["value"] == "THIRD", (
        "the typing went out"
    )
    assert run.withheld and run.withheld[0]["method"] == "POST", "the write is shown, in full"
    assert load_run(store, "acme", run.id) == run, "saved"


async def test_a_live_run_sends_the_write(tmp_path: Path) -> None:
    store = _store(tmp_path)
    wf = _workflow(store)
    channel = FakeChannel(
        {
            **_looks(4),
            "ui.perform": [
                Reply(
                    ok=True, result={"performed": True, "matched_by": "component", "candidates": 1}
                ),
                Reply(
                    ok=True, result={"performed": True, "matched_by": "component", "candidates": 1}
                ),
            ],
        }
    )
    asker = FakeAsker(
        _plan("type", "THIRD"),
        Answer(data={"held": True, "why": ""}),
        _plan("click"),
        Answer(data={"held": True, "why": ""}),
    )

    run = await run_workflow(
        store,
        wf,
        values={"clientCode": "THIRD"},
        channel=channel,
        device_id="dev_test",
        asker=asker,
        plan_model="flash",
        rescue_model="pro",
        live=True,
        earned=_earned,
        allow_focus=True,
        started_by="form",
    )

    assert [s.verdict for s in run.steps] == ["held", "held"] and not run.withheld


async def test_an_origin_outside_the_evidence_is_refused_before_it_is_sent(tmp_path: Path) -> None:
    store = _store(tmp_path)
    wf = _workflow(store)
    channel = FakeChannel(_looks(2))
    asker = FakeAsker(
        Answer(
            data={
                "kind": "navigate",
                "action": None,
                "value": None,
                "url": "https://evil.example/x",
                "why": "",
            }
        )
    )

    run = await run_workflow(
        store,
        wf,
        values={},
        channel=channel,
        device_id="dev_test",
        asker=asker,
        plan_model="flash",
        rescue_model="pro",
        live=True,
        earned=_earned,
        allow_focus=True,
        started_by="form",
    )

    assert run.outcome == "refused" and run.steps[0].verdict == "refused"
    assert not [s for s in channel.sent if s["kind"] == "navigate"], "nothing left the process"


async def test_a_failed_step_is_retried_once_with_pro_then_the_run_stops_and_asks(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    wf = _workflow(store)
    channel = FakeChannel(
        {
            **_looks(6),
            "ui.perform": [
                Reply(ok=False, error_kind="control_not_found", error_detail="gone"),
                Reply(ok=False, error_kind="control_not_found", error_detail="still gone"),
            ],
        }
    )
    asker = FakeAsker(_plan("type", "x"), _plan("type", "x"))

    run = await run_workflow(
        store,
        wf,
        values={"clientCode": "x"},
        channel=channel,
        device_id="dev_test",
        asker=asker,
        plan_model="flash",
        rescue_model="pro",
        live=True,
        earned=_earned,
        allow_focus=True,
        started_by="form",
    )

    assert run.outcome == "stopped"
    assert run.steps[0].verdict == "failed" and run.steps[0].planned_by == "pro", (
        "the second attempt was Pro's"
    )
    assert [a["model"] for a in asker.asked] == ["flash", "pro"]
    assert len(run.steps) == 1, "it stopped rather than carrying on to save"


async def test_a_navigate_gets_to_the_page_and_does_not_spend_the_rescue(tmp_path: Path) -> None:
    """A deep job was demonstrated across several screens. Moving to the next
    one is not doing the step: after the navigate the same step is planned
    again on the same rung, so a step that needed a page change and then went
    wrong still has its one Pro rescue."""
    store = _store(tmp_path)
    wf = _workflow(store)
    channel = FakeChannel(
        {
            **_looks(6),
            "navigate": [Reply(ok=True, result={"navigated": True})],
            "ui.perform": [
                Reply(
                    ok=True, result={"performed": True, "matched_by": "component", "candidates": 1}
                )
            ],
        }
    )
    asker = FakeAsker(
        Answer(
            data={
                "kind": "navigate",
                "action": None,
                "value": None,
                "url": "http://127.0.0.1:63319/form",
                "why": "wrong page",
            }
        ),
        _plan("type", "x"),
        Answer(data={"held": True, "why": ""}),
        _plan("click"),
    )

    run = await run_workflow(
        store,
        wf,
        values={"clientCode": "x"},
        channel=channel,
        device_id="dev_test",
        asker=asker,
        plan_model="flash",
        rescue_model="pro",
        live=False,
        allow_focus=True,
        started_by="form",
    )

    assert [s["kind"] for s in channel.sent if s["kind"] in ("navigate", "ui.perform")] == [
        "navigate",
        "ui.perform",
    ]
    assert run.steps[0].verdict == "held" and run.steps[0].planned_by == "flash", (
        "the rescue was never needed"
    )


async def test_a_weak_locator_match_succeeds_and_flags_the_step_stale(tmp_path: Path) -> None:
    store = _store(tmp_path)
    wf = _workflow(store)
    channel = FakeChannel(
        {
            **_looks(4),
            "ui.perform": [
                Reply(
                    ok=True, result={"performed": True, "matched_by": "css_path", "candidates": 1}
                )
            ],
        }
    )
    asker = FakeAsker(_plan("type", "x"), Answer(data={"held": True, "why": ""}), _plan("click"))

    run = await run_workflow(
        store,
        wf,
        values={"clientCode": "x"},
        channel=channel,
        device_id="dev_test",
        asker=asker,
        plan_model="flash",
        rescue_model="pro",
        live=False,
        allow_focus=True,
        started_by="form",
    )

    assert (
        run.steps[0].verdict == "held"
        and run.steps[0].stale is True
        and run.steps[0].matched_by == "css_path"
    )


async def test_the_stop_button_is_honoured_between_steps(tmp_path: Path) -> None:
    store = _store(tmp_path)
    wf = _workflow(store)
    channel = FakeChannel(
        {
            **_looks(4),
            "ui.perform": [
                Reply(
                    ok=True, result={"performed": True, "matched_by": "component", "candidates": 1}
                )
            ],
            "abort": [Reply(ok=True, result={"aborted": True})],
        }
    )
    asker = FakeAsker(_plan("type", "x"), Answer(data={"held": True, "why": ""}))
    Aborts.abort("run_stop")

    run = await run_workflow(
        store,
        wf,
        values={"clientCode": "x"},
        channel=channel,
        device_id="dev_test",
        asker=asker,
        plan_model="flash",
        rescue_model="pro",
        live=True,
        earned=_earned,
        allow_focus=True,
        started_by="form",
        run_id="run_stop",
    )

    assert run.outcome == "aborted" and run.steps == []


async def test_the_step_budget_is_the_workflows_steps_plus_slack(tmp_path: Path) -> None:
    """Every attempt counts against it, including the ones that only moved the
    browser, so a planner that navigates its way around a job runs out before
    it has spent the day."""
    store = _store(tmp_path)
    wf = _repeated(store, 4)
    assert K_STEP_SLACK == 3
    budget = len(wf.steps) + K_STEP_SLACK
    channel = FakeChannel(
        {
            **_looks(budget * 2),
            "navigate": [Reply(ok=True, result={"navigated": True})] * len(wf.steps),
            "ui.perform": [Reply(ok=True, result={"performed": True, "matched_by": "component"})]
            * len(wf.steps),
        }
    )
    # Every rung is asked twice: once for the navigate that gets to the page,
    # once for the command itself. Three steps at two attempts each spends six
    # of the seven, and the fourth step's navigate spends the last.
    asker = FakeAsker(
        *[
            answer
            for _ in range(3)
            for answer in (_navigate(), _plan("type", "x"), Answer(data={"held": True, "why": ""}))
        ],
        _navigate(),
    )

    run = await run_workflow(
        store,
        wf,
        values={"clientCode": "x"},
        channel=channel,
        device_id="dev_test",
        asker=asker,
        plan_model="flash",
        rescue_model="pro",
        live=True,
        earned=_earned,
        allow_focus=True,
        started_by="form",
    )

    assert run.outcome == "refused"
    last = run.steps[-1]
    assert last.order == 3 and last.verdict == "refused", "the budget stopped the last step"
    assert str(budget) in last.reason and "budget" in last.reason
    assert len([a for a in asker.asked if a["schema"] is PLAN_SCHEMA]) == budget


async def test_every_model_call_on_a_run_is_billed_to_its_step(tmp_path: Path) -> None:
    store = _store(tmp_path)
    wf = _workflow(store)
    channel = FakeChannel(
        {
            **_looks(4),
            "ui.perform": [
                Reply(
                    ok=True, result={"performed": True, "matched_by": "component", "candidates": 1}
                )
            ],
        }
    )
    asker = FakeAsker(
        Answer(
            data={"kind": "ui.perform", "action": "type", "value": "x", "url": None, "why": ""},
            cost_usd=0.002,
            in_tokens=100,
            out_tokens=10,
        ),
        Answer(data={"held": True, "why": ""}, cost_usd=0.001, in_tokens=50, out_tokens=5),
        _plan("click"),
    )

    run = await run_workflow(
        store,
        wf,
        values={"clientCode": "x"},
        channel=channel,
        device_id="dev_test",
        asker=asker,
        plan_model="flash",
        rescue_model="pro",
        live=False,
        allow_focus=True,
        started_by="form",
    )

    assert run.steps[0].cost_usd == 0.003 and run.steps[0].in_tokens == 150
    assert run.cost_usd == sum(s.cost_usd for s in run.steps)


async def test_a_browser_that_went_away_fails_the_run_and_says_so(tmp_path: Path) -> None:
    from rig.channel import DeviceChannel

    store = _store(tmp_path)
    wf = _workflow(store)
    run = await run_workflow(
        store,
        wf,
        values={},
        channel=DeviceChannel(),
        device_id="dev_gone",
        asker=FakeAsker(),
        plan_model="flash",
        rescue_model="pro",
        live=False,
        allow_focus=True,
        started_by="form",
    )
    assert run.outcome == "failed" and "dev_gone" in run.steps[0].reason


def test_a_stale_step_is_recorded_once_per_step_not_once_per_run(tmp_path: Path) -> None:
    """`mark_stale` writes a row a re-mine cannot race, and a job run every
    morning reports its weak step once rather than every morning."""
    from rig.runner import mark_stale

    store = _store(tmp_path)
    mark_stale(store, "wfl_1", 0, "css_path")
    mark_stale(store, "wfl_1", 0, None)

    rows = store.query("SELECT * FROM workflow_stale WHERE workflow_id = ?", ("wfl_1",))
    assert len(rows) == 1 and rows[0]["ord"] == 0 and rows[0]["matched_by"] is None


async def test_a_step_the_planner_could_not_plan_stops_the_run(tmp_path: Path) -> None:
    """A rung that never reached a command left its reason on nothing but a
    local, and the run walked past the step as if it had been skipped."""
    store = _store(tmp_path)
    wf = _workflow(store)
    channel = FakeChannel(_looks(4))
    asker = FakeAsker(
        Answer(data={"kind": "nope", "why": "no idea"}),
        Answer(data={"kind": "nope", "why": "still no idea"}),
    )

    run = await run_workflow(
        store,
        wf,
        values={"clientCode": "x"},
        channel=channel,
        device_id="dev_test",
        asker=asker,
        plan_model="flash",
        rescue_model="pro",
        live=True,
        earned=_earned,
        allow_focus=True,
        started_by="form",
    )

    assert run.outcome == "stopped"
    assert len(asker.asked) == 2, "step 1 was never planned"
    assert not [s for s in channel.sent if s["kind"] == "ui.perform"], "nothing was performed"
    assert run.steps[0].verdict == "failed" and run.steps[0].reason, "it says why"


async def test_a_step_with_nothing_actionable_to_cite_stops_the_run(tmp_path: Path) -> None:
    """You scroll a page, not a control. A step whose whole evidence is a
    scroll cannot be performed, and a job that carries on past it is a job
    doing its later steps on an assumption nobody checked."""
    store = _store(tmp_path)
    raw = copy.deepcopy(BATCH)
    raw["batch_id"] = "bat_scroll"
    event = next(e for e in raw["events"] if e["kind"] == "gesture")
    event["gesture"] = {**event["gesture"], "kind": "scroll", "target": None, "value": None}
    raw["events"] = [event]
    save_batch(store, Batch.model_validate(raw), "acme")
    scrolled = store.query("SELECT id FROM gestures WHERE batch_id = ?", ("bat_scroll",))[0]["id"]

    wf = _workflow(store)
    wf.steps[0].cites = [scrolled]
    save_workflow(store, wf)
    channel = FakeChannel(_looks(4))
    asker = FakeAsker(_plan("click"))

    run = await run_workflow(
        store,
        wf,
        values={},
        channel=channel,
        device_id="dev_test",
        asker=asker,
        plan_model="flash",
        rescue_model="pro",
        live=True,
        earned=_earned,
        allow_focus=True,
        started_by="form",
    )

    assert run.outcome == "stopped"
    assert len(run.steps) == 1 and run.steps[0].verdict == "skipped"
    assert not asker.asked and not channel.sent, "nothing was planned and nothing was sent"


async def test_the_record_keeps_what_the_browser_answered_not_what_it_answered_with(
    tmp_path: Path,
) -> None:
    """`verify` keeps a response body out of a prompt; the run record holds it
    for far longer than a prompt does, so it does not hold it at all."""
    store = _store(tmp_path)
    wf = _one_step(store, _ids(store)[-1])
    channel = FakeChannel(
        {
            **_looks(2),
            "http.send": [
                Reply(
                    ok=True,
                    result={
                        "status": 200,
                        "body": '{"id": 41, "clientCode": "ACME-4471"}',
                        "headers": {"set-cookie": "session=secret"},
                    },
                )
            ],
        }
    )
    asker = FakeAsker(
        Answer(data={"kind": "http.send", "action": None, "value": None, "url": None, "why": ""})
    )

    run = await run_workflow(
        store,
        wf,
        values={},
        channel=channel,
        device_id="dev_test",
        asker=asker,
        plan_model="flash",
        rescue_model="pro",
        live=True,
        earned=_earned,
        allow_focus=True,
        started_by="form",
    )

    assert run.steps[0].verdict == "held" and run.steps[0].verdict_by == "status"
    assert run.steps[0].result == {
        "ok": True,
        "status": 200,
        "matched_by": None,
        "wrote": True,
    }, "the three facts and the write marker; not the body, not the cookie"


async def test_a_failed_reply_keeps_the_error_kind_as_its_own_field(tmp_path: Path) -> None:
    store = _store(tmp_path)
    wf = _workflow(store)
    channel = FakeChannel(
        {
            **_looks(6),
            "ui.perform": [Reply(ok=False, error_kind="control_not_found", error_detail="gone")]
            * 2,
        }
    )
    asker = FakeAsker(_plan("type", "x"), _plan("type", "x"))

    run = await run_workflow(
        store,
        wf,
        values={"clientCode": "x"},
        channel=channel,
        device_id="dev_test",
        asker=asker,
        plan_model="flash",
        rescue_model="pro",
        live=True,
        earned=_earned,
        allow_focus=True,
        started_by="form",
    )

    assert run.steps[0].result == {
        "ok": False,
        "status": None,
        "matched_by": None,
        "error_kind": "control_not_found",
    }
    assert "gone" in run.steps[0].reason, (
        "the detail is in the reason, not concatenated into a kind"
    )


class _GoesAway(FakeChannel):
    """A browser that stops listening on the nth `ui.perform`."""

    def __init__(self, script: dict[str, list[Reply]], on_perform: int) -> None:
        super().__init__(script)
        self.on_perform = on_perform
        self.performs = 0

    async def send(
        self,
        device_id: str,
        *,
        kind: str,
        payload: Mapping[str, object],
        run_id: str | None = None,
        deadline_s: float | None = None,
    ) -> Reply:
        if kind == "ui.perform":
            self.performs += 1
            if self.performs >= self.on_perform:
                raise DeviceUnreachable(f"{device_id} stopped listening")
        return await super().send(
            device_id, kind=kind, payload=payload, run_id=run_id, deadline_s=deadline_s
        )


async def test_a_browser_that_goes_away_mid_step_fails_that_step(tmp_path: Path) -> None:
    """The step in flight is the one that failed -- with the order the workflow
    gave it and the tokens its plan already cost -- not a fabricated one whose
    order collides with a real step's."""
    store = _store(tmp_path)
    typed = _ids(store)[0]
    wf = Workflow(
        id="wfl_ordered",
        tenant="acme",
        title="two",
        narrative="n",
        systems=["http://127.0.0.1:63319"],
        steps=[
            Step(order=1, says="type the code", system=None, cites=[typed]),
            Step(order=2, says="type it again", system=None, cites=[typed]),
        ],
    )
    save_workflow(store, wf)
    channel = _GoesAway(
        {
            **_looks(4),
            "ui.perform": [Reply(ok=True, result={"performed": True, "matched_by": "component"})],
        },
        on_perform=2,
    )
    asker = FakeAsker(
        _plan("type", "x"),
        Answer(data={"held": True, "why": ""}),
        Answer(
            data={"kind": "ui.perform", "action": "type", "value": "x", "url": None, "why": ""},
            in_tokens=11,
        ),
    )

    run = await run_workflow(
        store,
        wf,
        values={"clientCode": "x"},
        channel=channel,
        device_id="dev_test",
        asker=asker,
        plan_model="flash",
        rescue_model="pro",
        live=True,
        earned=_earned,
        allow_focus=True,
        started_by="form",
    )

    assert run.outcome == "failed"
    assert [s.order for s in run.steps] == [1, 2], "the step in flight kept its own order"
    assert run.steps[1].verdict == "failed" and "dev_test" in run.steps[1].reason
    assert run.steps[1].in_tokens == 11, "the plan it already paid for is still billed"
    saved = load_run(store, "acme", run.id)
    assert saved is not None and saved.outcome == "failed", "and it was saved"


async def test_a_write_that_went_out_is_not_performed_a_second_time(tmp_path: Path) -> None:
    """The rescue exists for a step that did not happen. A write the browser
    sent and the server accepted, which then could not be shown to have held,
    is not that: retrying it creates the order twice."""
    store = _store(tmp_path)
    wf = _one_step(store, _ids(store)[-1])
    channel = FakeChannel(
        {
            **_looks(4),
            "ui.perform": [Reply(ok=True, result={"performed": True, "matched_by": "component"})],
        }
    )
    asker = FakeAsker(_plan("click"), Answer(data={"held": False, "why": "no confirmation"}))

    run = await run_workflow(
        store,
        wf,
        values={"clientCode": "x"},
        channel=channel,
        device_id="dev_test",
        asker=asker,
        plan_model="flash",
        rescue_model="pro",
        live=True,
        earned=_earned,
        allow_focus=True,
        started_by="form",
    )

    assert run.outcome == "stopped"
    assert len([s for s in channel.sent if s["kind"] == "ui.perform"]) == 1, "sent once"
    assert [a["model"] for a in asker.asked] == ["flash", "flash"], "Pro was never asked"
    assert run.steps[0].reason.startswith("state unknown after a write; not retried: ")


async def test_a_read_that_failed_is_still_rescued(tmp_path: Path) -> None:
    """The write rule must not cost every step its rescue."""
    store = _store(tmp_path)
    wf = _one_step(store, _ids(store)[0], says="type the code")
    channel = FakeChannel(
        {
            **_looks(8),
            "ui.perform": [Reply(ok=True, result={"performed": True, "matched_by": "component"})]
            * 2,
        }
    )
    asker = FakeAsker(
        _plan("type", "x"),
        Answer(data={"held": False, "why": "nothing typed"}),
        _plan("type", "x"),
        Answer(data={"held": True, "why": "typed"}),
    )

    run = await run_workflow(
        store,
        wf,
        values={"clientCode": "x"},
        channel=channel,
        device_id="dev_test",
        asker=asker,
        plan_model="flash",
        rescue_model="pro",
        live=True,
        earned=_earned,
        allow_focus=True,
        started_by="form",
    )

    assert run.outcome == "held" and run.steps[0].planned_by == "pro"
    assert [a["model"] for a in asker.asked] == ["flash", "flash", "pro", "flash"]


class _Breaks(FakeChannel):
    """A channel that raises something nobody planned for."""

    async def send(
        self,
        device_id: str,
        *,
        kind: str,
        payload: Mapping[str, object],
        run_id: str | None = None,
        deadline_s: float | None = None,
    ) -> Reply:
        if kind == "ui.perform":
            raise RuntimeError("boom")
        return await super().send(
            device_id, kind=kind, payload=payload, run_id=run_id, deadline_s=deadline_s
        )


async def test_a_run_that_dies_of_something_unexpected_is_not_left_saying_running(
    tmp_path: Path,
) -> None:
    """The exception is nobody's to swallow; the record is nobody's to lose."""
    store = _store(tmp_path)
    wf = _workflow(store)
    channel = _Breaks(_looks(4))
    asker = FakeAsker(_plan("type", "x"))

    with pytest.raises(RuntimeError):
        await run_workflow(
            store,
            wf,
            values={"clientCode": "x"},
            channel=channel,
            device_id="dev_test",
            asker=asker,
            plan_model="flash",
            rescue_model="pro",
            live=True,
            earned=_earned,
            allow_focus=True,
            started_by="form",
        )

    saved = load_run(store, "acme", _only_run(store))
    assert saved is not None and saved.outcome == "failed"
    assert "RuntimeError" in saved.steps[-1].reason and "boom" in saved.steps[-1].reason


async def test_a_click_the_capture_heard_nothing_from_is_not_clicked_twice(
    tmp_path: Path,
) -> None:
    """`writes()` is False for a Save whose call the recorder never saw, and a
    rescue of that click submits the order a second time."""
    store = _store(tmp_path)
    wf = _one_step(store, _silent_click(store), says="press Save")
    channel = FakeChannel(
        {
            **_looks(4),
            "ui.perform": [Reply(ok=True, result={"performed": True, "matched_by": "component"})],
        }
    )
    asker = FakeAsker(_plan("click"), Answer(data={"held": False, "why": "no confirmation"}))

    run = await run_workflow(
        store,
        wf,
        values={"clientCode": "x"},
        channel=channel,
        device_id="dev_test",
        asker=asker,
        plan_model="flash",
        rescue_model="pro",
        live=True,
        earned=_earned,
        allow_focus=True,
        started_by="form",
    )

    assert run.outcome == "stopped"
    assert len([s for s in channel.sent if s["kind"] == "ui.perform"]) == 1, "clicked once"
    assert [a["model"] for a in asker.asked] == ["flash", "flash"], "Pro was never asked"
    assert "state unknown" in run.steps[0].reason


async def test_a_click_that_fired_a_read_still_gets_its_rescue(tmp_path: Path) -> None:
    """A menu or a tab click that the recorder DID see traffic from changed
    nothing, and the write rule must not cost it its second attempt."""
    store = _store(tmp_path)
    raw = copy.deepcopy(BATCH)
    raw["batch_id"] = "bat_reads"
    raw["events"] = [
        e for e in raw["events"] if e["kind"] != "request" or e["request"]["method"] == "GET"
    ]
    save_batch(store, Batch.model_validate(raw), "acme")
    clicked = store.query("SELECT id FROM gestures WHERE batch_id = ? ORDER BY at", ("bat_reads",))[
        -1
    ]["id"]

    wf = _one_step(store, clicked, says="open the tab")
    channel = FakeChannel(
        {
            **_looks(8),
            "ui.perform": [Reply(ok=True, result={"performed": True, "matched_by": "component"})]
            * 2,
        }
    )
    asker = FakeAsker(
        _plan("click"),
        Answer(data={"held": False, "why": "the panel did not open"}),
        _plan("click"),
        Answer(data={"held": True, "why": "the panel is open"}),
    )

    run = await run_workflow(
        store,
        wf,
        values={"clientCode": "x"},
        channel=channel,
        device_id="dev_test",
        asker=asker,
        plan_model="flash",
        rescue_model="pro",
        live=True,
        earned=_earned,
        allow_focus=True,
        started_by="form",
    )

    assert run.outcome == "held" and run.steps[0].planned_by == "pro"
    assert len([s for s in channel.sent if s["kind"] == "ui.perform"]) == 2


async def test_a_rung_that_reached_no_command_leaves_the_previous_rungs_plan_standing(
    tmp_path: Path,
) -> None:
    """Flash failed AT a command and Pro failed BEFORE one. The record's
    verdict is Flash's, so its `planned_by` and `sent` must be too."""
    store = _store(tmp_path)
    wf = _one_step(store, _ids(store)[0], says="type the code")
    channel = FakeChannel(
        {
            **_looks(6),
            "ui.perform": [Reply(ok=False, error_kind="control_not_found", error_detail="gone")],
        }
    )
    asker = FakeAsker(_plan("type", "x"), Answer(data={"kind": "nope", "why": "lost"}))

    run = await run_workflow(
        store,
        wf,
        values={"clientCode": "x"},
        channel=channel,
        device_id="dev_test",
        asker=asker,
        plan_model="flash",
        rescue_model="pro",
        live=True,
        earned=_earned,
        allow_focus=True,
        started_by="form",
    )

    step = run.steps[0]
    assert step.verdict == "failed" and "control_not_found" in step.reason
    assert step.planned_by == "flash", "Pro never got as far as a command"
    assert step.sent is not None and step.sent["kind"] == "ui.perform"
    assert step.result == {
        "ok": False,
        "status": None,
        "matched_by": None,
        "error_kind": "control_not_found",
    }
    assert [a["model"] for a in asker.asked] == ["flash", "pro"], "Pro was still asked"


async def test_a_run_cancelled_mid_step_is_not_left_saying_running(tmp_path: Path) -> None:
    """Shutdown cancels the task. `CancelledError` is a BaseException, so
    neither `except` clause runs -- only the `finally`, which must still finish
    the record rather than leave a row that says `running` for good."""
    store = _store(tmp_path)
    wf = _workflow(store)

    class _Hangs(FakeChannel):
        def __init__(self) -> None:
            super().__init__({})
            self.reached = asyncio.Event()

        async def send(
            self,
            device_id: str,
            *,
            kind: str,
            payload: Mapping[str, object],
            run_id: str | None = None,
            deadline_s: float | None = None,
        ) -> Reply:
            self.reached.set()
            await asyncio.Event().wait()
            raise AssertionError("never reached")

    channel = _Hangs()
    task = asyncio.create_task(
        run_workflow(
            store,
            wf,
            values={"clientCode": "x"},
            channel=channel,
            device_id="dev_test",
            asker=FakeAsker(),
            plan_model="flash",
            rescue_model="pro",
            live=False,
            allow_focus=True,
            started_by="form",
        )
    )
    await channel.reached.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    saved = load_run(store, "acme", _only_run(store))
    assert saved is not None and saved.outcome == "failed"
    assert saved.steps[-1].reason == "interrupted before finishing"
    assert saved.steps[-1].order == 0, "the step it was working on, not a fabricated one"


def _claimed(store: Store, **fields: str) -> Run:
    """The row `POST /v1/runs` writes before it answers."""
    run = Run(
        id="run_claimed",
        tenant="acme",
        workflow_id="wfl_1",
        device_id="dev_test",
        values={},
        started_by="form",
        live=False,
        allow_focus=True,
        started_at="2026-01-01T00:00:00+00:00",
    )
    for name, value in fields.items():
        setattr(run, name, value)
    save_run(store, run)
    return run


@pytest.mark.parametrize(
    ("field", "value"),
    [("device_id", "dev_other"), ("workflow_id", "wfl_other")],
)
async def test_a_claimed_run_that_disagrees_with_its_arguments_is_refused(
    tmp_path: Path, field: str, value: str
) -> None:
    """The saved row is the authority for what a run is doing, so the two ways
    into this function must agree. Driving the row's browser instead of the
    caller's would put a hand on a window nobody asked about; driving the row's
    workflow would perform a different job under this one's id. Neither is a
    thing to guess between, and neither marks the row failed -- it belongs to
    whoever saved it."""
    store = _store(tmp_path)
    wf = _workflow(store)
    _claimed(store, **{field: value})
    channel = FakeChannel(_looks(4))

    with pytest.raises(ValueError, match="run_claimed"):
        await run_workflow(
            store,
            wf,
            values={},
            channel=channel,
            device_id="dev_test",
            asker=FakeAsker(),
            plan_model="flash",
            rescue_model="pro",
            live=False,
            allow_focus=True,
            started_by="form",
            run_id="run_claimed",
        )

    assert channel.sent == [], "refused before anything reached a browser"
    still = load_run(store, "acme", "run_claimed")
    assert still is not None and still.outcome == "running" and still.finished_at is None
    assert getattr(still, field) == value, "the row is left exactly as its owner saved it"


async def test_a_navigate_to_a_url_that_names_no_system_is_refused(tmp_path: Path) -> None:
    store = _store(tmp_path)
    wf = _workflow(store)
    channel = FakeChannel(_looks(2))
    asker = FakeAsker(
        Answer(
            data={
                "kind": "navigate",
                "action": None,
                "value": None,
                "url": "about:blank",
                "why": "",
            }
        )
    )

    run = await run_workflow(
        store,
        wf,
        values={},
        channel=channel,
        device_id="dev_test",
        asker=asker,
        plan_model="flash",
        rescue_model="pro",
        live=True,
        earned=_earned,
        allow_focus=True,
        started_by="form",
    )

    assert run.outcome == "refused" and run.steps[0].verdict == "refused"
    assert "about:blank" in run.steps[0].reason
    assert not [s for s in channel.sent if s["kind"] == "navigate"], "no origin is not permission"


async def test_a_run_started_mid_job_records_the_operators_steps_and_performs_the_rest(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    wf = _workflow(store)
    channel = FakeChannel(
        {
            **_looks(2),
            "ui.perform": [Reply(ok=True, result={"performed": True, "matched_by": "component"})],
        }
    )
    asker = _per_schema_asker(_plan("click"), Answer(data={"held": True, "why": "saved"}))

    run = await run_workflow(
        store,
        wf,
        values={"clientCode": "THIRD"},
        channel=channel,
        device_id="dev_test",
        asker=asker,
        plan_model="flash",
        rescue_model="pro",
        live=True,
        earned=_earned,
        allow_focus=True,
        started_by="offer",
        from_step=1,
    )

    assert [s.verdict for s in run.steps] == ["done_by_operator", "held"]
    assert run.steps[0].verdict_by == "none" and wf.steps[0].cites[0] in run.steps[0].reason
    assert run.steps[0].sent is None and run.steps[0].in_tokens == 0, "nothing asked, nothing sent"
    assert [s["kind"] for s in channel.sent].count("ui.perform") == 1
    assert run.outcome == "held"


async def test_a_run_started_mid_job_starts_on_the_page_of_the_step_it_starts_at(
    tmp_path: Path,
) -> None:
    """`starts_on` is what the extension opens a tab at when the operator's own
    tab is elsewhere. Aimed at step 0 for a run that starts at step 1, it would
    abandon the very progress the offer was made on."""
    store = _store(tmp_path)
    wf = _workflow(store)
    saved_on = "http://127.0.0.1:63319/client/new"
    store.execute("UPDATE gestures SET page_url = ? WHERE id = ?", (saved_on, wf.steps[1].cites[0]))
    channel = FakeChannel(
        {
            **_looks(2),
            "ui.perform": [Reply(ok=True, result={"performed": True, "matched_by": "component"})],
        }
    )

    await run_workflow(
        store,
        wf,
        values={"clientCode": "THIRD"},
        channel=channel,
        device_id="dev_test",
        asker=_per_schema_asker(_plan("click"), Answer(data={"held": True, "why": "saved"})),
        plan_model="flash",
        rescue_model="pro",
        live=True,
        earned=_earned,
        allow_focus=True,
        started_by="offer",
        from_step=1,
    )

    [performed] = [s for s in channel.sent if s["kind"] == "ui.perform"]
    assert performed["payload"]["starts_on"] == saved_on


async def test_the_steps_the_operator_did_buy_no_budget(tmp_path: Path) -> None:
    """A run that starts at step k attempts fewer steps, so it gets fewer
    attempts. The slack is for the job that is left."""
    store = _store(tmp_path)
    wf = _repeated(store, 5)
    budget = len(wf.steps) - 1 + K_STEP_SLACK
    channel = FakeChannel(
        {
            **_looks(budget * 2),
            "navigate": [Reply(ok=True, result={"navigated": True})] * len(wf.steps),
            "ui.perform": [Reply(ok=True, result={"performed": True, "matched_by": "component"})]
            * len(wf.steps),
        }
    )
    # Three of the four steps left take a navigate and a command each, which is
    # six of the seven; the fourth's navigate spends the last.
    asker = FakeAsker(
        *[
            answer
            for _ in range(3)
            for answer in (_navigate(), _plan("type", "x"), Answer(data={"held": True, "why": ""}))
        ],
        _navigate(),
    )

    run = await run_workflow(
        store,
        wf,
        values={"clientCode": "x"},
        channel=channel,
        device_id="dev_test",
        asker=asker,
        plan_model="flash",
        rescue_model="pro",
        live=True,
        earned=_earned,
        allow_focus=True,
        started_by="offer",
        from_step=1,
    )

    assert run.outcome == "refused"
    last = run.steps[-1]
    assert last.order == 4 and last.verdict == "refused"
    assert str(budget) in last.reason, "the operator's step is not slack for the rig"
    assert len([a for a in asker.asked if a["schema"] is PLAN_SCHEMA]) == budget


async def test_a_live_write_waits_for_approval_and_goes_out_when_it_comes(tmp_path: Path) -> None:
    store = _store(tmp_path)
    wf = _workflow(store)
    channel = FakeChannel(
        {
            **_looks(4),
            "ui.perform": [
                Reply(ok=True, result={"performed": True, "matched_by": "component"}),
                Reply(ok=True, result={"performed": True, "matched_by": "component"}),
            ],
        }
    )
    asker = _per_schema_asker(
        plan=_plan("type", "THIRD"), verdict=Answer(data={"held": True, "why": "ok"})
    )

    task = asyncio.create_task(
        run_workflow(
            store,
            wf,
            values={"clientCode": "THIRD"},
            channel=channel,
            device_id="dev_test",
            asker=asker,
            plan_model="flash",
            rescue_model="pro",
            live=True,
            allow_focus=True,
            started_by="offer",
        )
    )
    for _ in range(200):
        await asyncio.sleep(0.01)
        if Approvals.awaiting_any():
            break
    else:
        raise AssertionError("the write never paused")

    run_id = next(iter(Approvals.waiting()))
    saved = load_run(store, "acme", run_id)
    assert saved is not None and saved.steps[-1].verdict == "awaiting"
    assert saved.steps[-1].sent is not None, "the panel shows what would go out"
    assert [s["kind"] for s in channel.sent].count("ui.perform") == 1, (
        "the read step went; the write waits"
    )

    assert Approvals.approve(run_id) is True
    run = await task
    assert run.outcome == "held"
    assert [s["kind"] for s in channel.sent].count("ui.perform") == 2


async def test_a_write_nobody_approves_stops_the_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import rig.runner as runner_module

    monkeypatch.setattr(runner_module, "K_APPROVAL_WAIT_S", 0.05)
    store = _store(tmp_path)
    wf = _workflow(store)
    channel = FakeChannel({**_looks(4), "ui.perform": [Reply(ok=True, result={"performed": True})]})
    asker = _per_schema_asker(
        plan=_plan("type", "THIRD"), verdict=Answer(data={"held": True, "why": "ok"})
    )

    run = await run_workflow(
        store,
        wf,
        values={"clientCode": "THIRD"},
        channel=channel,
        device_id="dev_test",
        asker=asker,
        plan_model="flash",
        rescue_model="pro",
        live=True,
        allow_focus=True,
        started_by="offer",
    )

    assert run.outcome == "stopped"
    assert "nobody approved" in run.steps[-1].reason
    assert [s["kind"] for s in channel.sent].count("ui.perform") == 1


async def test_a_stop_pressed_during_the_wait_aborts_the_run(tmp_path: Path) -> None:
    store = _store(tmp_path)
    wf = _workflow(store)
    channel = FakeChannel({**_looks(4), "ui.perform": [Reply(ok=True, result={"performed": True})]})
    asker = _per_schema_asker(
        plan=_plan("type", "THIRD"), verdict=Answer(data={"held": True, "why": "ok"})
    )

    task = asyncio.create_task(
        run_workflow(
            store,
            wf,
            values={"clientCode": "THIRD"},
            channel=channel,
            device_id="dev_test",
            asker=asker,
            plan_model="flash",
            rescue_model="pro",
            live=True,
            allow_focus=True,
            started_by="offer",
        )
    )
    for _ in range(200):
        await asyncio.sleep(0.01)
        if Approvals.awaiting_any():
            break
    else:  # pragma: no cover - the pause is asserted above
        raise AssertionError("the write never paused")

    run_id = next(iter(Approvals.waiting()))
    Aborts.abort(run_id)
    Approvals.approve(run_id)
    run = await task
    assert run.outcome == "aborted"
    assert [s["kind"] for s in channel.sent].count("ui.perform") == 1


async def test_a_dry_run_never_pauses(tmp_path: Path) -> None:
    store = _store(tmp_path)
    wf = _workflow(store)
    channel = FakeChannel({**_looks(4), "ui.perform": [Reply(ok=True, result={"performed": True})]})
    asker = _per_schema_asker(
        plan=_plan("type", "THIRD"), verdict=Answer(data={"held": True, "why": "ok"})
    )
    run = await asyncio.wait_for(
        run_workflow(
            store,
            wf,
            values={"clientCode": "THIRD"},
            channel=channel,
            device_id="dev_test",
            asker=asker,
            plan_model="flash",
            rescue_model="pro",
            live=False,
            allow_focus=True,
            started_by="form",
        ),
        timeout=5,
    )
    assert [s.verdict for s in run.steps] == ["held", "withheld"]


async def test_an_earned_workflow_writes_without_asking(tmp_path: Path) -> None:
    store = _store(tmp_path)
    wf = _workflow(store)
    channel = FakeChannel(
        {
            **_looks(4),
            "ui.perform": [
                Reply(ok=True, result={"performed": True}),
                Reply(ok=True, result={"performed": True}),
            ],
        }
    )
    asker = _per_schema_asker(
        plan=_plan("type", "THIRD"), verdict=Answer(data={"held": True, "why": "ok"})
    )
    run = await asyncio.wait_for(
        run_workflow(
            store,
            wf,
            values={"clientCode": "THIRD"},
            channel=channel,
            device_id="dev_test",
            asker=asker,
            plan_model="flash",
            rescue_model="pro",
            live=True,
            allow_focus=True,
            started_by="offer",
            earned=lambda _wid: True,
        ),
        timeout=5,
    )
    assert run.outcome == "held" and not Approvals.awaiting_any()


async def test_a_click_the_capture_heard_nothing_from_also_waits(tmp_path: Path) -> None:
    """`writes()` is False for a Save whose call the recorder never saw, and
    the rescue gate below already refuses to retry it. A step nobody may retry
    is a step nobody may send unasked either, so it waits for the tap too."""
    store = _store(tmp_path)
    wf = _one_step(store, _silent_click(store), says="press Save")
    channel = FakeChannel({**_looks(2), "ui.perform": [Reply(ok=True, result={"performed": True})]})
    asker = _per_schema_asker(plan=_plan("click"), verdict=Answer(data={"held": True, "why": "ok"}))

    task = asyncio.create_task(
        run_workflow(
            store,
            wf,
            values={"clientCode": "THIRD"},
            channel=channel,
            device_id="dev_test",
            asker=asker,
            plan_model="flash",
            rescue_model="pro",
            live=True,
            allow_focus=True,
            started_by="offer",
        )
    )
    for _ in range(200):
        await asyncio.sleep(0.01)
        if Approvals.awaiting_any():
            break
    else:  # pragma: no cover - the pause is asserted below
        raise AssertionError("the silent click never paused")

    run_id = next(iter(Approvals.waiting()))
    saved = load_run(store, "acme", run_id)
    assert saved is not None and saved.steps[-1].verdict == "awaiting"
    assert not [s for s in channel.sent if s["kind"] == "ui.perform"], "nothing went out"

    assert Approvals.approve(run_id) is True
    run = await task
    assert run.outcome == "held"
    assert len([s for s in channel.sent if s["kind"] == "ui.perform"]) == 1


def _replay() -> Answer:
    """The planner's one way to send a write as a call: replay the recorded
    one. The url is never the model's -- `plan_step` takes it off the
    evidence -- so `url: None` here is the honest shape of that answer."""
    return Answer(
        data={"kind": "http.send", "action": None, "value": None, "url": None, "why": "w"}
    )


async def test_a_held_write_verified_by_state_is_recorded_as_an_effect(tmp_path: Path) -> None:
    store = _store(tmp_path)
    wf = _one_step(store, _ids(store)[-1])
    channel = FakeChannel(
        {
            **_looks(4),
            # 200 is what the capture's POST returned, and `expected_statuses`
            # is what "held by status" is measured against.
            "http.send": [Reply(ok=True, result={"status": 200, "body": "{}", "headers": {}})],
        }
    )
    asker = _per_schema_asker(plan=_replay(), verdict=Answer(data={"held": True, "why": "ok"}))

    run = await run_workflow(
        store,
        wf,
        values={"clientCode": "THIRD"},
        channel=channel,
        device_id="dev_test",
        asker=asker,
        plan_model="flash",
        rescue_model="pro",
        live=True,
        allow_focus=True,
        started_by="offer",
        earned=lambda _wid: True,
    )

    assert run.outcome == "held"
    assert run.steps[-1].result is not None and run.steps[-1].result.get("wrote") is True
    rows = store.query(
        "SELECT run_id, ord, verified_by FROM workflow_effects WHERE workflow_id = ?", (wf.id,)
    )
    assert [tuple(r) for r in rows] == [(run.id, 0, "status")]


async def test_a_failed_write_forgets_the_effects_the_workflow_had_earned(tmp_path: Path) -> None:
    store = _store(tmp_path)
    wf = _one_step(store, _ids(store)[-1])
    record_effect(store, workflow_id=wf.id, run_id="run_old", order=0, verified_by="status", at="t")
    channel = FakeChannel(
        {
            # Two rungs: a write the server refused is the one write that is
            # safe to plan again, so Pro gets its rescue and fails too.
            **_looks(8),
            "http.send": [Reply(ok=True, result={"status": 500, "body": "", "headers": {}})] * 2,
        }
    )
    asker = _per_schema_asker(plan=_replay(), verdict=Answer(data={"held": True, "why": "ok"}))

    await run_workflow(
        store,
        wf,
        values={"clientCode": "THIRD"},
        channel=channel,
        device_id="dev_test",
        asker=asker,
        plan_model="flash",
        rescue_model="pro",
        live=True,
        allow_focus=True,
        started_by="offer",
        earned=lambda _wid: True,
    )

    assert store.query("SELECT 1 FROM workflow_effects WHERE workflow_id = ?", (wf.id,)) == []


class _GoesAwayAfterTheWrite(FakeChannel):
    """A browser that answers the write and is gone before anyone can look."""

    async def send(
        self,
        device_id: str,
        *,
        kind: str,
        payload: Mapping[str, object],
        run_id: str | None = None,
        deadline_s: float | None = None,
    ) -> Reply:
        if any(s["kind"] == "http.send" for s in self.sent):
            raise DeviceUnreachable(f"{device_id} stopped listening")
        return await super().send(
            device_id, kind=kind, payload=payload, run_id=run_id, deadline_s=deadline_s
        )


async def test_a_browser_that_goes_away_after_the_write_forgets_the_effects(
    tmp_path: Path,
) -> None:
    """The step body never runs again after the browser goes: the write went
    out, nobody could show it held, and the job kept its autonomy."""
    store = _store(tmp_path)
    wf = _one_step(store, _ids(store)[-1])
    record_effect(store, workflow_id=wf.id, run_id="run_old", order=0, verified_by="status", at="t")
    channel = _GoesAwayAfterTheWrite(
        {**_looks(2), "http.send": [Reply(ok=True, result={"status": 200, "body": "{}"})]}
    )
    asker = _per_schema_asker(plan=_replay(), verdict=Answer(data={"held": True, "why": "ok"}))

    run = await run_workflow(
        store,
        wf,
        values={},
        channel=channel,
        device_id="dev_test",
        asker=asker,
        plan_model="flash",
        rescue_model="pro",
        live=True,
        allow_focus=True,
        started_by="offer",
        earned=lambda _wid: True,
    )

    assert run.outcome == "failed" and run.steps[0].result is not None
    assert run.steps[0].result.get("wrote") is True, "the write went out"
    assert store.query("SELECT 1 FROM workflow_effects WHERE workflow_id = ?", (wf.id,)) == []


async def test_a_write_that_ends_unclear_forgets_the_effects(tmp_path: Path) -> None:
    """No status the evidence knows, no read to make, no screen to look at:
    the write went out and nothing can say whether it held."""
    store = _store(tmp_path)
    wf = _one_step(store, _ids(store)[-1])
    record_effect(store, workflow_id=wf.id, run_id="run_old", order=0, verified_by="status", at="t")
    channel = FakeChannel(
        {
            "ui.url": [Reply(ok=True, result={"url": "http://127.0.0.1:63319/form"})] * 2,
            "screenshot": [Reply(ok=False, error_kind="focus_not_permitted")] * 2,
            # 300: not a refusal, and not a status the capture's POST returned.
            "http.send": [Reply(ok=True, result={"status": 300, "body": "{}"})],
        }
    )
    asker = _per_schema_asker(plan=_replay(), verdict=Answer(data={"held": True, "why": "ok"}))

    run = await run_workflow(
        store,
        wf,
        # No values, so there is no proposition a confirming read could check.
        values={},
        channel=channel,
        device_id="dev_test",
        asker=asker,
        plan_model="flash",
        rescue_model="pro",
        live=True,
        allow_focus=True,
        started_by="offer",
        earned=lambda _wid: True,
    )

    assert [s.verdict for s in run.steps] == ["unclear"]
    assert store.query("SELECT 1 FROM workflow_effects WHERE workflow_id = ?", (wf.id,)) == []


async def test_a_dry_run_records_no_effect_even_for_a_click_it_does_send(tmp_path: Path) -> None:
    """`writes()` is False for a Save whose call the recorder never saw, so a
    dry run performs it -- and a dry run's evidence earns nothing."""
    store = _store(tmp_path)
    wf = _one_step(store, _silent_click(store), says="press Save")
    channel = FakeChannel({**_looks(2), "ui.perform": [Reply(ok=True, result={"performed": True})]})
    asker = _per_schema_asker(plan=_plan("click"), verdict=Answer(data={"held": True, "why": "ok"}))

    run = await run_workflow(
        store,
        wf,
        values={"clientCode": "THIRD"},
        channel=channel,
        device_id="dev_test",
        asker=asker,
        plan_model="flash",
        rescue_model="pro",
        live=False,
        allow_focus=True,
        started_by="form",
    )

    assert run.outcome == "held", "the click was sent, not withheld"
    assert len([s for s in channel.sent if s["kind"] == "ui.perform"]) == 1
    assert store.query("SELECT 1 FROM workflow_effects WHERE workflow_id = ?", (wf.id,)) == []


def _bare_run(**over) -> Run:
    base: dict[str, Any] = {
        "id": "run_1",
        "tenant": "acme",
        "workflow_id": "wfl_1",
        "device_id": "dev_1",
        "values": {},
        "started_by": "form",
        "live": False,
        "allow_focus": True,
        "started_at": "2026-09-06T10:00:00+00:00",
    }
    return Run(**{**base, **over})


def _step_record(**over) -> RunStep:
    return RunStep(**{"order": 0, "says": "s", "verdict": "skipped", **over})


def test_a_step_is_billed_for_every_reading_it_took_and_for_none_it_did_not() -> None:
    """A step is planned once and verified once, and both readings are its
    cost. One unpriced reading makes the whole step's number untrustworthy."""
    record = _step_record()

    _bill(
        record,
        None,
        Answer(in_tokens=10, out_tokens=2, thought_tokens=1, cost_usd=0.001),
        Answer(in_tokens=5, out_tokens=3, thought_tokens=2, cost_usd=0.002, unpriced=True),
    )

    assert (record.in_tokens, record.out_tokens, record.thought_tokens) == (15, 5, 3)
    assert record.cost_usd == pytest.approx(0.003)
    assert record.unpriced is True, "one unpriced reading is an unpriced step"


def test_what_the_browser_answered_is_kept_and_what_it_answered_with_is_not() -> None:
    reply = Reply(
        ok=True,
        result={
            "status": 201,
            "matched_by": "component",
            "body": '{"clientCode":"ACME-4471"}',
            "headers": {"Set-Cookie": "session=abc"},
        },
    )

    assert _result(reply) == {"ok": True, "status": 201, "matched_by": "component"}
    assert _result(reply, wrote=True)["wrote"] is True

    refused = Reply(ok=False, error_kind="control_not_found", error_detail="no visible match")
    assert _result(refused) == {
        "ok": False,
        "status": None,
        "matched_by": None,
        "error_kind": "control_not_found",
    }


def test_a_step_whose_evidence_shows_no_completed_traffic_saw_nothing(tmp_path: Path) -> None:
    store = _store(tmp_path)
    by_id = _gestures_for(store, _workflow(store))
    saver = next(g for g in by_id.values() if g.requests)
    typed = next(g for g in by_id.values() if not g.requests)

    assert not _saw_nothing(Step(order=0, says="s", system=None, cites=[saver.id]), by_id)
    assert _saw_nothing(Step(order=0, says="s", system=None, cites=[typed.id]), by_id)
    assert not _saw_nothing(
        Step(order=0, says="s", system=None, cites=["ges_gone", saver.id]), by_id
    ), "a cited gesture the store lost does not hide the evidence behind it"

    dead = copy.deepcopy(saver)
    dead.requests = [
        r.model_copy(update={"status": 502, "failure_reason": "Failed to fetch"})
        for r in saver.requests
    ]
    assert _saw_nothing(Step(order=0, says="s", system=None, cites=[dead.id]), {dead.id: dead}), (
        "a call that never landed is not traffic the recorder saw"
    )


def test_the_origin_a_plan_would_reach_is_the_urls_for_the_two_kinds_that_leave() -> None:
    def _p(kind: str, payload: dict[str, Any]) -> Planned:
        return Planned(kind, payload, "w", Answer())

    assert (
        _target_origin(_p("http.send", {"url": "https://wms.example/x"})) == "https://wms.example"
    )
    assert _target_origin(_p("navigate", {"url": "https://wms.example/x"})) == "https://wms.example"
    assert _target_origin(_p("navigate", {"url": "about:blank"})) is None
    assert (
        _target_origin(_p("ui.perform", {"origin": "https://wms.example", "url": "https://evil/x"}))
        == "https://wms.example"
    ), "ui.perform keeps the origin the evidence gave it"
    assert _target_origin(_p("ui.perform", {})) is None
    assert _target_origin(_p("ui.perform", {"origin": 7})) is None


def test_a_run_that_died_between_steps_gets_a_step_of_its_own_to_say_so() -> None:
    run = _bare_run(steps=[_step_record(order=0), _step_record(order=1)])

    _fell_over(run, None, "the browser went away")

    assert run.outcome == "failed" and len(run.steps) == 3
    fresh = run.steps[-1]
    assert (fresh.order, fresh.says) == (2, ""), "past the last one, so (run_id, ord) cannot clash"
    assert (fresh.verdict, fresh.verdict_by, fresh.reason) == (
        "failed",
        "none",
        "the browser went away",
    )


def test_a_run_that_died_before_its_first_step_still_gets_step_zero() -> None:
    run = _bare_run(steps=[])
    _fell_over(run, None, "interrupted before finishing")
    assert [s.order for s in run.steps] == [0]


def test_a_run_that_died_mid_step_fails_that_step_and_keeps_what_it_cost() -> None:
    """Not a fabricated step: the one in flight, with its own order and the
    tokens its plan already spent."""
    in_flight = _step_record(order=4, says="save", in_tokens=300, cost_usd=0.0004)
    run = _bare_run(steps=[_step_record(order=3, verdict="held"), in_flight])

    _fell_over(run, in_flight, "the browser went away")

    assert len(run.steps) == 2 and run.steps[-1] is in_flight
    assert (in_flight.order, in_flight.in_tokens) == (4, 300)
    assert (in_flight.verdict, in_flight.verdict_by) == ("failed", "none")


def test_the_rig_stamps_its_times_in_utc() -> None:
    """Every other writer here produces UTC. A naive local stamp beside them
    reads as a run that finished hours before it started."""
    assert _now().endswith("+00:00")


def test_what_a_dry_run_withholds_is_the_write_in_full(tmp_path: Path) -> None:
    """What a person reads before pressing through to live: the command the
    planner chose, and the call the operator's own demonstration made."""
    store = _store(tmp_path)
    by_id = _gestures_for(store, _workflow(store))
    saver = next(g for g in by_id.values() if g.requests)
    post = next(r for r in saver.requests if r.method == "POST")
    step = Step(order=1, says="save", system=None, cites=[saver.id])
    planned = Planned("ui.perform", {"action": "click"}, "w", Answer())

    assert _withheld(step, planned, by_id) == {
        "step": 1,
        "planned": {"kind": "ui.perform", "payload": {"action": "click"}},
        "method": "POST",
        "url": post.url,
        "body": post.request_body.text,
    }

    typed = next(g for g in by_id.values() if not g.requests)
    quiet = _withheld(Step(order=0, says="type", system=None, cites=[typed.id]), planned, by_id)
    assert quiet == {"step": 0, "planned": {"kind": "ui.perform", "payload": {"action": "click"}}}


async def test_a_look_is_where_the_browser_is_and_what_is_on_the_screen() -> None:
    channel = FakeChannel(
        {
            "ui.url": [Reply(ok=True, result={"url": "http://127.0.0.1:63319/form"})],
            "screenshot": [
                Reply(
                    ok=True,
                    result={
                        "image_base64": base64.b64encode(b"png-bytes").decode(),
                        "text_digest": "Save",
                    },
                )
            ],
        }
    )

    look = await _look(channel, "dev_1", "run_1", "http://127.0.0.1:63319", True)

    assert look == Look("http://127.0.0.1:63319/form", b"png-bytes", "Save")
    assert channel.sent == [
        {
            "device_id": "dev_1",
            "kind": "ui.url",
            "run_id": "run_1",
            "payload": {"origin": "http://127.0.0.1:63319"},
        },
        {
            "device_id": "dev_1",
            "kind": "screenshot",
            "run_id": "run_1",
            # inline, or the picture comes back as a url the rig would have to
            # fetch; allow_focus only when the run was given it.
            "payload": {
                "inline": True,
                "origin": "http://127.0.0.1:63319",
                "allow_focus": True,
            },
        },
    ]


async def test_a_look_a_run_may_not_take_focus_for_never_asks_for_it() -> None:
    channel = FakeChannel({"ui.url": [Reply(ok=True, result={"url": "http://x/"})]})
    await _look(channel, "dev_1", "run_1", None, False)
    assert channel.sent[1]["payload"] == {"inline": True, "origin": None}


async def test_a_refused_screenshot_is_no_picture_rather_than_a_failure() -> None:
    """`focus_not_permitted` is the extension declining to steal the tab. The
    planner works from the url and the digest."""
    channel = FakeChannel(
        {
            "ui.url": [Reply(ok=True, result={"url": "http://127.0.0.1:63319/form"})],
            "screenshot": [Reply(ok=False, error_kind="focus_not_permitted", error_detail="no")],
        }
    )

    look = await _look(channel, "dev_1", "run_1", None, True)

    assert look == Look("http://127.0.0.1:63319/form", None, "")


async def test_a_url_the_browser_did_not_actually_answer_is_not_where_it_is() -> None:
    for reply in (
        Reply(ok=False, error_kind="no_tab", error_detail="x", result={"url": "http://stale/"}),
        Reply(ok=True, result={}),
    ):
        channel = FakeChannel({"ui.url": [reply]})
        assert (await _look(channel, "dev_1", "run_1", None, False)).url is None


async def test_a_picture_that_will_not_decode_is_no_picture_either() -> None:
    for raw in ("!!!not base64!!!", "", 17):
        channel = FakeChannel(
            {
                "ui.url": [Reply(ok=True, result={"url": "http://x/"})],
                "screenshot": [Reply(ok=True, result={"image_base64": raw, "text_digest": "d"})],
            }
        )
        look = await _look(channel, "dev_1", "run_1", None, False)
        assert look.screenshot is None, raw
        assert look.digest == "d", "the text still reads even when the picture does not"


def test_a_step_found_the_strong_way_again_clears_its_stale_mark(tmp_path: Path) -> None:
    store = _store(tmp_path)
    mark_stale(store, "wfl_1", 0, "css_path")
    mark_stale(store, "wfl_1", 1, "css_path")
    clear_stale(store, "wfl_1", 0)
    rows = store.query("SELECT ord FROM workflow_stale WHERE workflow_id = 'wfl_1' ORDER BY ord")
    assert [r["ord"] for r in rows] == [1], "only the step that matched strongly is cleared"


async def test_the_pro_rescue_sees_the_page_the_flash_attempt_left_behind(tmp_path: Path) -> None:
    store = _store(tmp_path)
    wf = _workflow(store)
    channel = FakeChannel(
        {
            **_looks(6),
            "ui.perform": [Reply(ok=True, result={"performed": True})] * 3,
        }
    )
    # Step 0 is a read, so a failed verdict is rescued once by Pro.
    asker = _per_schema_asker(
        plan=_plan("type", "THIRD"), verdict=Answer(data={"held": False, "why": "still blank"})
    )

    await run_workflow(
        store,
        wf,
        values={"clientCode": "THIRD"},
        channel=channel,
        device_id="dev_test",
        asker=asker,
        plan_model="flash",
        rescue_model="pro",
        live=False,
        allow_focus=True,
        started_by="form",
        earned=_earned,
    )

    plans = [a for a in asker.asked if a["schema"] is PLAN_SCHEMA]
    assert [p["model"] for p in plans][:2] == ["flash", "pro"]
    assert plans[0]["images"] == (), "the first attempt has no failed attempt to show"
    assert len(plans[1]["images"]) == 1, "the rescue is shown the page the first attempt left"
    assert isinstance(plans[1]["images"][0], bytes), "a real picture, not a placeholder"


async def test_a_run_stopped_by_the_flag_is_forgotten_by_the_registers_when_it_ends(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    wf = _workflow(store)
    channel = FakeChannel(_looks(2))
    asker = _per_schema_asker(
        plan=_plan("type", "THIRD"), verdict=Answer(data={"held": True, "why": "ok"})
    )
    # Flagged before it starts: the loop sees the flag at its first step and
    # ends aborted. What matters here is what the run leaves behind in the
    # in-process registers -- nothing, or the next run under that id would
    # inherit a stop it never asked for.
    Aborts.abort("run_forget_me")
    run = await run_workflow(
        store,
        wf,
        values={"clientCode": "THIRD"},
        channel=channel,
        device_id="dev_test",
        asker=asker,
        plan_model="flash",
        rescue_model="pro",
        live=True,
        allow_focus=True,
        started_by="form",
        earned=_earned,
        run_id="run_forget_me",
    )
    assert run.outcome == "aborted"
    assert not Aborts.is_aborted("run_forget_me"), "the finally forgets the flag"
    assert "run_forget_me" not in Approvals.waiting()


async def test_an_approved_wait_leaves_nothing_waiting() -> None:
    task = asyncio.create_task(Approvals.wait_for("run_w2", timeout=2))
    await asyncio.sleep(0)
    assert "run_w2" in Approvals.waiting()
    assert Approvals.approve("run_w2") is True
    assert await task is True
    assert "run_w2" not in Approvals.waiting(), "the register is popped on the way out"


async def test_a_run_started_past_its_last_step_performs_nothing_and_holds(tmp_path: Path) -> None:
    store = _store(tmp_path)
    wf = _workflow(store)
    channel = FakeChannel(_looks(2))
    asker = _per_schema_asker(
        plan=_plan("type", "x"), verdict=Answer(data={"held": True, "why": "ok"})
    )
    run = await run_workflow(
        store,
        wf,
        values={"clientCode": "THIRD"},
        channel=channel,
        device_id="dev_test",
        asker=asker,
        plan_model="flash",
        rescue_model="pro",
        live=False,
        allow_focus=True,
        started_by="form",
        from_step=len(wf.steps),
    )
    assert [s.verdict for s in run.steps] == ["done_by_operator", "done_by_operator"]
    assert run.outcome == "held" and channel.sent == [] and asker.asked == []


def _sight(x: int = 40, y: int = 30, action: str = "type", value: str | None = "x") -> Answer:
    return Answer(
        data={"found": True, "x": x, "y": y, "action": action, "value": value, "why": "there"},
        cost_usd=0.002,
    )


def _looks_with_size(n: int) -> dict[str, list[Reply]]:
    looks = _looks(n)
    for reply in looks["screenshot"]:
        reply.result.update({"width": 800, "height": 600})
    return looks


class _by_rung_asker(FakeAsker):
    """Answers the evidence planner, the sight planner and the verifier each
    from their own queue, by schema, and records every call."""

    def __init__(self, plans: list[Answer], sights: list[Answer], verdict: Answer) -> None:
        super().__init__()
        self.plans, self.sights, self.verdict = list(plans), list(sights), verdict

    async def ask(self, **asked: Any) -> Answer:
        await super().ask(**asked)
        props = asked["schema"]["properties"]
        if "held" in props:
            return self.verdict
        if "found" in props:
            return self.sights.pop(0)
        return self.plans.pop(0)


async def _run_by_sight(
    tmp_path: Path,
    *,
    sights: list[Answer],
    perform_at: list[Reply],
    performs: list[Reply] | None = None,
    live: bool = True,
    looks: dict[str, list[Reply]] | None = None,
    earned: Callable[[str], bool] = _earned,
) -> tuple[Run, FakeChannel, _by_rung_asker]:
    store = _store(tmp_path)
    wf = _workflow(store)
    channel = FakeChannel(
        {
            **(looks or _looks_with_size(12)),
            # Two misses on the first step; the save then matches by evidence.
            "ui.perform": performs
            or [
                Reply(ok=False, error_kind="control_not_found", error_detail="gone"),
                Reply(ok=False, error_kind="control_not_found", error_detail="gone"),
                Reply(ok=True, result={"performed": True, "matched_by": "role_and_name"}),
            ],
            "ui.perform_at": perform_at,
        }
    )
    asker = _by_rung_asker(
        [_plan("type", "x")] * 4, sights, Answer(data={"held": True, "why": "typed"})
    )
    run = await run_workflow(
        store,
        wf,
        values={"clientCode": "x"},
        channel=channel,
        device_id="dev_test",
        asker=asker,
        plan_model="flash",
        rescue_model="pro",
        live=live,
        earned=earned,
        allow_focus=True,
        started_by="form",
    )
    return run, channel, asker


async def test_a_control_neither_rung_could_find_is_found_by_sight_and_the_job_marked_stale(
    tmp_path: Path,
) -> None:
    run, channel, asker = await _run_by_sight(
        tmp_path,
        sights=[_sight()],
        perform_at=[Reply(ok=True, result={"performed": True})],
    )
    first = run.steps[0]
    assert first.verdict == "held", first.reason
    assert first.matched_by == "sight" and first.stale is True
    assert first.result == {"ok": True, "status": None, "matched_by": "sight"}
    assert [a["model"] for a in asker.asked if "found" in a["schema"]["properties"]] == ["pro"]
    [sent] = [s for s in channel.sent if s["kind"] == "ui.perform_at"]
    assert sent["payload"] == {
        "origin": "http://127.0.0.1:63319",
        "x": 40,
        "y": 30,
        "action": "type",
        "value": "x",
    }
    assert first.planned_by == "pro"
    assert run.outcome == "held", "the run carried on to the save and held"


async def test_the_sight_rung_is_for_a_control_that_was_not_found_and_nothing_else(
    tmp_path: Path,
) -> None:
    """A plan the browser refused for another reason -- the page did not
    answer, the tab is gone -- is not a page that moved, and a picture answers
    nothing about it."""
    run, channel, asker = await _run_by_sight(
        tmp_path,
        sights=[_sight()],
        perform_at=[Reply(ok=True, result={"performed": True})],
        performs=[Reply(ok=False, error_kind="not_actionable", error_detail="no answer")] * 2,
    )
    assert run.outcome == "stopped" and run.steps[0].verdict == "failed"
    assert not [s for s in channel.sent if s["kind"] == "ui.perform_at"]
    assert not [a for a in asker.asked if "found" in a["schema"]["properties"]]


async def test_a_point_off_the_screen_or_a_control_not_seen_is_a_step_that_stops(
    tmp_path: Path,
) -> None:
    for sight in (
        _sight(x=900, y=30),
        Answer(data={"found": False, "x": 0, "y": 0, "action": "click", "why": "not here"}),
    ):
        run, channel, _ = await _run_by_sight(
            tmp_path, sights=[sight], perform_at=[Reply(ok=True, result={"performed": True})]
        )
        assert run.outcome == "stopped" and run.steps[0].verdict == "failed", sight.data
        assert not [s for s in channel.sent if s["kind"] == "ui.perform_at"], "nothing was sent"
        assert "then by sight: " in run.steps[0].reason
        assert "not on the screen" in run.steps[0].reason or "not here" in run.steps[0].reason
        assert run.steps[0].result == {
            "ok": False,
            "status": None,
            "matched_by": None,
            "error_kind": "control_not_found",
        }, "the record keeps the last command that went out"


async def test_without_a_picture_there_is_no_sight_rung(tmp_path: Path) -> None:
    """A screenshot the browser refused -- `focus_not_permitted` -- is no
    picture, and a rung that looks has nothing to look at."""
    run, channel, asker = await _run_by_sight(
        tmp_path,
        sights=[_sight()],
        perform_at=[Reply(ok=True, result={"performed": True})],
        looks={
            "ui.url": [Reply(ok=True, result={"url": "http://127.0.0.1:63319/form"})] * 12,
            "screenshot": [Reply(ok=False, error_kind="focus_not_permitted", error_detail="no")]
            * 12,
        },
    )
    assert run.outcome == "stopped" and "no screen to look at" in run.steps[0].reason
    assert not [a for a in asker.asked if "found" in a["schema"]["properties"]], (
        "the model was not asked to look at nothing"
    )
    assert not [s for s in channel.sent if s["kind"] == "ui.perform_at"]


async def test_a_dry_run_reads_by_sight_too_and_its_writes_never_reach_the_rung(
    tmp_path: Path,
) -> None:
    """A dry run performs reads, so a read neither evidence rung could find is
    found by sight the same way. Its writes are withheld before any rung
    could miss them: the save below is withheld by evidence, and the sight
    rung is never asked about it."""
    run, channel, asker = await _run_by_sight(
        tmp_path,
        sights=[_sight()],
        perform_at=[Reply(ok=True, result={"performed": True})],
        live=False,
    )
    assert [s.verdict for s in run.steps] == ["held", "withheld"], [s.reason for s in run.steps]
    assert run.steps[0].matched_by == "sight" and run.steps[0].stale is True
    assert len([s for s in channel.sent if s["kind"] == "ui.perform_at"]) == 1
    assert len([a for a in asker.asked if "found" in a["schema"]["properties"]]) == 1
    assert run.withheld[0]["planned"]["kind"] == "ui.perform", "withheld by evidence, unasked"


async def test_a_click_by_sight_is_a_write_until_a_person_says_otherwise(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The first step's evidence is a typed field, not a silent click: by
    evidence, a click there would not be a possible write. By sight it is --
    the point is on a page that has moved, and what is there now is unknown --
    so on a job that has not earned it, the click waits for a tap. Nobody
    taps, and it never goes out."""
    import rig.runner as runner_module

    monkeypatch.setattr(runner_module, "K_APPROVAL_WAIT_S", 0.05)
    run, channel, _ = await _run_by_sight(
        tmp_path,
        sights=[_sight(action="click", value=None)],
        perform_at=[Reply(ok=True, result={"performed": True})],
        earned=lambda _workflow_id: False,
    )
    assert run.steps[0].verdict == "failed" and "nobody approved" in run.steps[0].reason
    assert not [s for s in channel.sent if s["kind"] == "ui.perform_at"], "it waited, then stopped"
    assert run.steps[0].sent == {
        "kind": "ui.perform_at",
        "payload": {"origin": "http://127.0.0.1:63319", "x": 40, "y": 30, "action": "click"},
    }, "what would have gone out was shown"


async def test_an_action_a_point_cannot_take_is_a_step_that_stops(tmp_path: Path) -> None:
    run, channel, _ = await _run_by_sight(
        tmp_path,
        sights=[Answer(data={"found": True, "x": 1, "y": 1, "action": "select", "why": "w"})],
        perform_at=[Reply(ok=True, result={"performed": True})],
    )
    assert run.outcome == "stopped" and "'select' is not an action" in run.steps[0].reason
    assert not [s for s in channel.sent if s["kind"] == "ui.perform_at"]


async def test_an_evidence_rung_with_no_plan_is_not_blamed_on_sight(tmp_path: Path) -> None:
    """The reason append is the sight rung's alone: an evidence rung whose
    planner had no answer keeps its own reason, unadorned."""
    store = _store(tmp_path)
    wf = _workflow(store)
    channel = FakeChannel(_looks(6))
    asker = FakeAsker(Answer(error="503 UNAVAILABLE"), Answer(error="503 UNAVAILABLE"))
    run = await run_workflow(
        store,
        wf,
        values={"clientCode": "x"},
        channel=channel,
        device_id="dev_test",
        asker=asker,
        plan_model="flash",
        rescue_model="pro",
        live=True,
        earned=_earned,
        allow_focus=True,
        started_by="form",
    )
    assert run.steps[0].verdict == "failed" and run.steps[0].reason == "503 UNAVAILABLE"
    assert "by sight" not in run.steps[0].reason
