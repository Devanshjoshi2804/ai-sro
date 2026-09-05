import asyncio
import copy
import json
from collections.abc import Mapping
from pathlib import Path

import pytest

from rig.api import save_batch
from rig.channel import Answer as Reply
from rig.channel import DeviceUnreachable, FakeChannel
from rig.models import Answer, FakeAsker
from rig.planner import PLAN_SCHEMA
from rig.runner import K_STEP_SLACK, Aborts, run_workflow
from rig.runs import Run, load_run, save_run
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


def _looks(n: int) -> dict[str, list[Reply]]:
    return {
        "ui.url": [Reply(ok=True, result={"url": "http://127.0.0.1:63319/form"})] * n,
        "screenshot": [Reply(ok=True, result={"image_base64": "aVBORw0=", "text_digest": "Save"})]
        * n,
    }


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
        allow_focus=True,
        started_by="form",
    )

    assert run.steps[0].verdict == "held" and run.steps[0].verdict_by == "status"
    assert run.steps[0].result == {"ok": True, "status": 200, "matched_by": None}


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
