from pathlib import Path

from rig.api import save_batch
from rig.channel import Answer as Reply
from rig.channel import FakeChannel
from rig.models import Answer, FakeAsker
from rig.runner import K_STEP_SLACK, Aborts, run_workflow
from rig.runs import load_run
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
    """Every attempt counts against it, so a model looping on a form runs out."""
    store = _store(tmp_path)
    wf = _workflow(store)
    assert K_STEP_SLACK == 3
    attempts = len(wf.steps) + K_STEP_SLACK + 2
    channel = FakeChannel(
        {
            **_looks(attempts * 2),
            "ui.perform": [Reply(ok=False, error_kind="not_visible", error_detail="")] * attempts,
        }
    )
    asker = FakeAsker(*[_plan("type", "x")] * attempts)

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

    assert run.outcome in ("stopped", "refused")
    assert (
        len([s for s in channel.sent if s["kind"] == "ui.perform"]) <= len(wf.steps) + K_STEP_SLACK
    )


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
