"""A15: the loop. Look, plan, refuse-or-perform, verify, escalate once, stop.

Flash plans; Pro rescues. A clean step never touches the expensive model, and
only the steps that surprise us cost what surprises cost. Between steps the
stop button and the budget are checked; after every step the run is saved, so
the page can watch it and so a crash mid-run leaves a record rather than a
mystery.

The first execution of any workflow is dry. Reads and navigations go out; a
step whose evidence carries a mutation is shown in full and withheld. A person
presses through to live.
"""

import base64
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any, ClassVar

from rig.channel import Answer as Reply
from rig.channel import Channel, DeviceUnreachable
from rig.correlate import system_of
from rig.locators import allowlist, origin_of, primary_gesture, recorded_call, writes
from rig.models import Answer, Asker
from rig.planner import Look, Planned, plan_step
from rig.records import Gesture
from rig.runs import Run, RunStep, load_run, new_run_id, save_run
from rig.store import Store
from rig.verify import Verdict, verify
from rig.workflows import Step, Workflow

K_STEP_SLACK = 3
"""Attempts a run may make beyond its step count before it stops. A model
looping on a form is money spent and a warehouse confused."""

K_WEAK_LOCATORS = frozenset({"css_path", None})
"""A step that only ever matches on the last fallback is a step about to break.
The run succeeds and the step is flagged stale."""


class Aborts:
    """The stop button. In-process, like the channel it belongs beside: a run
    does not survive a restart either."""

    _stopped: ClassVar[set[str]] = set()

    @classmethod
    def abort(cls, run_id: str) -> None:
        cls._stopped.add(run_id)

    @classmethod
    def is_aborted(cls, run_id: str) -> bool:
        return run_id in cls._stopped

    @classmethod
    def forget(cls, run_id: str) -> None:
        cls._stopped.discard(run_id)


def mark_stale(store: Store, workflow_id: str, step_order: int, matched_by: str | None) -> None:
    """This step's control was only found by the weakest rung of the ladder.

    A row rather than an entry appended to the workflow, because the workflow
    is what the mining pass writes and this is what a run learned: rewriting
    the workflow from here would race a re-mine and lose one of the two. One
    row per step, replaced, so a job run every morning reports its weak step
    once.
    """
    store.execute(
        "INSERT OR REPLACE INTO workflow_stale (workflow_id, ord, matched_by, noticed_at)"
        " VALUES (?, ?, ?, ?)",
        (workflow_id, step_order, matched_by, _now()),
    )


def _now() -> str:
    return datetime.now(tz=UTC).isoformat()


def _bill(step: RunStep, *answers: Answer | None) -> None:
    for answer in answers:
        if answer is None:
            continue
        step.in_tokens += answer.in_tokens
        step.out_tokens += answer.out_tokens
        step.thought_tokens += answer.thought_tokens
        step.cost_usd += answer.cost_usd
        step.unpriced = step.unpriced or answer.unpriced


def _total(run: Run) -> None:
    run.in_tokens = sum(s.in_tokens for s in run.steps)
    run.out_tokens = sum(s.out_tokens for s in run.steps)
    run.thought_tokens = sum(s.thought_tokens for s in run.steps)
    run.cost_usd = sum(s.cost_usd for s in run.steps)
    run.unpriced = any(s.unpriced for s in run.steps)


def _gestures_for(store: Store, workflow: Workflow) -> dict[str, Gesture]:
    from rig.api import _row_to_gesture  # deferred: api imports runner for the route

    wanted = sorted({c for s in workflow.steps for c in s.cites})
    if not wanted:
        return {}
    marks = ",".join("?" * len(wanted))
    rows = store.query(
        f"SELECT * FROM gestures WHERE tenant = ? AND id IN ({marks})",
        (workflow.tenant, *wanted),
    )
    return {row["id"]: _row_to_gesture(row) for row in rows}


def _target_origin(planned: Planned) -> str | None:
    """The origin a planned command would actually reach. For `http.send` and
    `navigate` that is the url's own host, not the step's: those two are the
    only ways a plan can leave the system the evidence was recorded on."""
    if planned.kind in ("http.send", "navigate"):
        return system_of(str(planned.payload.get("url")))
    origin = planned.payload.get("origin")
    return origin if isinstance(origin, str) else None


async def _look(
    channel: Channel, device_id: str, run_id: str, origin: str | None, allow_focus: bool
) -> Look:
    """Where the browser is and what is on the screen. A refused screenshot --
    `focus_not_permitted` -- is no picture, not a failure: the planner works
    from the url and the digest."""
    where = await channel.send(device_id, kind="ui.url", run_id=run_id, payload={"origin": origin})
    url = str(where.result.get("url")) if where.ok and where.result.get("url") else None
    payload: dict[str, Any] = {"inline": True, "origin": origin}
    if allow_focus:
        payload["allow_focus"] = True
    shot = await channel.send(device_id, kind="screenshot", run_id=run_id, payload=payload)
    image = None
    digest = ""
    if shot.ok:
        raw = shot.result.get("image_base64")
        if isinstance(raw, str) and raw:
            try:
                image = base64.b64decode(raw)
            except ValueError:
                image = None
        digest = str(shot.result.get("text_digest") or "")
    return Look(url=url, screenshot=image, digest=digest)


def _result(reply: Reply) -> dict[str, Any]:
    """What the extension answered -- not what it answered WITH.

    An `http.send` reply carries the response body and headers, and `verify`
    deliberately keeps those out of a prompt. A run record has no more business
    holding customer payload than a prompt does, and it holds it for longer, so
    only the three facts anything downstream reads are kept. `error_kind` stays
    its own field rather than `Answer.detail`, which concatenates kind and
    detail into prose nothing can branch on.
    """
    status = reply.result.get("status")
    matched = reply.result.get("matched_by")
    shown: dict[str, Any] = {
        "ok": reply.ok,
        "status": status if isinstance(status, int) else None,
        "matched_by": matched if isinstance(matched, str) else None,
    }
    if not reply.ok:
        shown["error_kind"] = reply.error_kind
    return shown


def _saw_nothing(step: Step, by_id: Mapping[str, Gesture]) -> bool:
    """Whether the capture recorded this step's gesture and none of the traffic
    it caused. A call that never completed is not traffic the recorder saw --
    the same completion guard `origin_of` and `expected_statuses` already
    wear."""
    for cited in step.cites:
        gesture = by_id.get(cited)
        if gesture is None:
            continue
        for request in gesture.requests:
            if request.status is not None and not request.failure_reason:
                return False
    return True


def _fell_over(run: Run, in_flight: RunStep | None, reason: str) -> None:
    """The run died. Whatever it was doing when it died is the step that
    failed, so the record says which one and why rather than stopping at
    `running` and leaving a reader to guess."""
    record = in_flight
    if record is None:
        record = RunStep(
            order=max((s.order for s in run.steps), default=-1) + 1, says="", verdict="failed"
        )
        run.steps.append(record)
    record.verdict, record.verdict_by, record.reason = "failed", "none", reason
    run.outcome = "failed"


def _withheld(step: Step, planned: Planned, by_id: Mapping[str, Gesture]) -> dict[str, Any]:
    """The write a dry run did not send, in full: what a person reads before
    pressing through to live."""
    call = recorded_call(step, by_id)
    shown: dict[str, Any] = {
        "step": step.order,
        "planned": {"kind": planned.kind, "payload": planned.payload},
    }
    if call is not None:
        shown.update(
            method=call.method.upper(),
            url=call.url,
            body=call.request_body.text if call.request_body else None,
        )
    return shown


async def run_workflow(
    store: Store,
    workflow: Workflow,
    *,
    values: Mapping[str, str],
    channel: Channel,
    device_id: str,
    asker: Asker,
    plan_model: str,
    rescue_model: str,
    live: bool,
    allow_focus: bool,
    started_by: str,
    run_id: str | None = None,
) -> Run:
    # A run the caller already claimed. `POST /v1/runs` writes the `running` row
    # itself, before it answers, so a second press for the same browser is
    # refused rather than landing in the window between `create_task` and this
    # task's first slice. That row is then the authority for what was asked
    # for -- read back here rather than rebuilt from the arguments, so there is
    # one answer to "what is this run doing" and not two that can drift.
    saved = load_run(store, workflow.tenant, run_id) if run_id else None
    # The two ways in have to agree. Reading the row's `device_id` back when it
    # disagrees with the argument would put a hand on a browser nobody asked
    # about, and its `workflow_id` would perform a different job under this
    # run's id -- both silent, and neither a thing to guess between. Refused
    # before anything is sent and before the row is touched: a run whose
    # arguments do not match it is not this caller's run to mark failed.
    if saved is not None and (saved.device_id != device_id or saved.workflow_id != workflow.id):
        raise ValueError(
            f"{saved.id} was saved for {saved.workflow_id} on {saved.device_id},"
            f" not {workflow.id} on {device_id}"
        )
    run = saved or Run(
        id=run_id or new_run_id(),
        tenant=workflow.tenant,
        workflow_id=workflow.id,
        device_id=device_id,
        values=dict(values),
        started_by=started_by,
        live=live,
        allow_focus=allow_focus,
        started_at=_now(),
    )
    values, live, allow_focus, device_id = run.values, run.live, run.allow_focus, run.device_id
    save_run(store, run)
    by_id = _gestures_for(store, workflow)
    allowed = allowlist(workflow, by_id)
    budget = len(workflow.steps) + K_STEP_SLACK
    attempts = 0
    starts_on = None
    first = primary_gesture(workflow.steps[0], by_id) if workflow.steps else None
    if first is not None:
        starts_on = first.page_url or first.url

    # The step being worked on, so a browser that goes away mid-step fails THAT
    # step -- with the tokens its plan already cost, and its own order -- rather
    # than a fabricated one whose order can collide on (run_id, ord).
    in_flight: RunStep | None = None
    try:
        for step in sorted(workflow.steps, key=lambda s: s.order):
            if Aborts.is_aborted(run.id):
                await channel.send(
                    device_id, kind="abort", run_id=run.id, payload={"run_id": run.id}
                )
                run.outcome = "aborted"
                break
            cited = [by_id[c] for c in step.cites if c in by_id]
            primary = primary_gesture(step, by_id)
            record = RunStep(order=step.order, says=step.says, verdict="skipped")
            in_flight = record
            run.steps.append(record)
            origin = origin_of(primary) if primary is not None else None
            mutates = writes(step, by_id)
            if primary is None:
                record.reason = "no cited gesture can be acted on"

            # Flash, then Pro once. A step with nothing actionable cited gets
            # neither: it is recorded skipped and the run carries on.
            rungs = (plan_model, rescue_model) if primary is not None else ()
            verdict: Verdict | None = None
            for model in rungs:
                # One rung of the ladder: plan, and plan again once if getting
                # to the right page was all the model asked for. Getting there
                # is not doing the step, so a navigate must not spend the one
                # Pro rescue -- it does spend budget, so a planner that only
                # ever navigates still runs out.
                planned: Planned | None = None
                navigated = False
                # What the record says was planned and sent, before this rung
                # touches it. A rung that ends without producing a command has
                # to give it back: the verdict on the record is still the
                # previous rung's, and a `planned_by` that disagrees with the
                # verdict beside it is a lie about who failed.
                previously = (record.planned_by, record.sent, record.result)
                while planned is None:
                    if attempts >= budget:
                        record.verdict = "refused"
                        record.reason = f"the step budget of {budget} attempts is spent"
                        run.outcome = "refused"
                        break
                    attempts += 1
                    before = await _look(channel, device_id, run.id, origin, allow_focus)
                    proposal = await plan_step(
                        step=step,
                        cited=cited,
                        values=values,
                        look=before,
                        origin=origin,
                        starts_on=starts_on,
                        allow_focus=allow_focus,
                        asker=asker,
                        model=model,
                        failure=verdict.reason if verdict else None,
                    )
                    record.planned_by = model
                    record.before_url = before.url
                    _bill(record, proposal.answer)
                    record.sent = {"kind": proposal.kind, "payload": proposal.payload}

                    if proposal.kind == "none":
                        verdict = Verdict("failed", "none", proposal.why)
                        break
                    off = _target_origin(proposal)
                    if off is not None and off not in allowed:
                        record.verdict = "refused"
                        record.reason = f"{off} is not a system this job's evidence names"
                        run.outcome = "refused"
                        break
                    if proposal.kind != "navigate":
                        planned = proposal
                    elif navigated:
                        verdict = Verdict(
                            "failed",
                            "none",
                            proposal.why or "still on the wrong page after navigating",
                        )
                        break
                    else:
                        moved = await channel.send(
                            device_id, kind="navigate", run_id=run.id, payload=proposal.payload
                        )
                        if not moved.ok:
                            verdict = Verdict(
                                "failed", "none", f"could not navigate: {moved.detail}"
                            )
                            break
                        navigated = True

                if planned is None and run.outcome == "running":
                    record.planned_by, record.sent, record.result = previously
                if run.outcome != "running":
                    break
                if planned is None:
                    continue

                # Still `writes()`, deliberately: withholding every click the
                # recorder heard nothing from would leave a dry run performing
                # almost none of the job, while not RESCUING one costs a
                # rescue. The asymmetry is the cheap side of each.
                if not live and mutates:
                    run.withheld.append(_withheld(step, planned, by_id))
                    record.verdict, record.verdict_by = "withheld", "dry"
                    record.reason = "a dry run does not send writes"
                    record.result = {"withheld": True}
                    break

                reply = await channel.send(
                    device_id, kind=planned.kind, run_id=run.id, payload=planned.payload
                )
                record.result = _result(reply)
                record.matched_by = record.result["matched_by"] if reply.ok else None
                after = await _look(channel, device_id, run.id, origin, allow_focus)
                record.after_url = after.url
                verdict = await verify(
                    step=step,
                    sent_kind=planned.kind,
                    answer=reply,
                    cited=cited,
                    values=values,
                    look_before=before,
                    look_after=after,
                    channel=channel,
                    device_id=device_id,
                    run_id=run.id,
                    origin=origin,
                    asker=asker,
                    model=plan_model,
                )
                _bill(record, verdict.answer)
                record.verdict, record.verdict_by = verdict.state, verdict.by
                record.reason = verdict.reason
                if verdict.state == "held":
                    if planned.kind == "ui.perform" and record.matched_by in K_WEAK_LOCATORS:
                        record.stale = True
                        mark_stale(store, workflow.id, step.order, record.matched_by)
                    break
                # A write that went out and was accepted, and then could not be
                # shown to have held, is not a step to try again: the second
                # attempt would create the order twice. Only a write the server
                # itself refused -- or one the browser never sent -- is safe to
                # rescue. A read is always safe.
                #
                # `writes()` is not the whole of it. It is False when the cited
                # evidence records no mutating call AT ALL, which is what a
                # click on Save looks like when the recorder never saw the
                # traffic -- a beacon, a worker, a frame nothing was attached
                # to. A click or a press on evidence that came back silent is
                # the same unknown state as an accepted write, so it does not
                # rescue either. A click that fired a completed read -- a menu,
                # a tab -- still does.
                unknown = mutates or (
                    planned.kind == "ui.perform"
                    and planned.payload.get("action") in ("click", "press")
                    and _saw_nothing(step, by_id)
                )
                if (
                    unknown
                    and reply.ok
                    and not (verdict.state == "failed" and verdict.by == "status")
                ):
                    record.reason = f"state unknown after a write; not retried: {record.reason}"
                    break

            # A rung that never reached a command -- an unplannable step, a
            # navigate that would not go -- left its reason on the local
            # verdict and nothing on the record, which then read `skipped` and
            # let the run walk past it.
            if record.verdict == "skipped" and verdict is not None:
                record.verdict, record.verdict_by = verdict.state, verdict.by
                record.reason = verdict.reason

            in_flight = None
            _total(run)
            save_run(store, run)
            if run.outcome != "running":
                break
            # Held, or deliberately withheld by a dry run. Anything else --
            # failed, unclear, or a step with nothing actionable to cite -- is
            # a step nobody watched succeed, and the rest of the job assumes it
            # did. Nothing runs unattended past one.
            if record.verdict not in ("held", "withheld"):
                run.outcome = "stopped"
                break
        else:
            run.outcome = "held"
    except DeviceUnreachable as gone:
        _fell_over(run, in_flight, str(gone))
    except Exception as broke:
        # Not handled, and not silently a run that says `running` forever
        # either. The record is finished and saved by the `finally` below, then
        # this goes on up.
        _fell_over(run, in_flight, f"{type(broke).__name__}: {broke}")
        raise
    finally:
        # In the finally, so an exception this function does not handle still
        # leaves a saved record rather than a row that says `running` forever.
        #
        # Still `running` here means neither `except` above ran, and the only
        # way out of the loop that skips both is a BaseException -- in practice
        # the CancelledError a shutdown delivers to this task. That is a run
        # nobody watched finish, so it says so rather than being read later as
        # one still in flight on a process that no longer exists.
        if run.outcome == "running":
            _fell_over(run, in_flight, "interrupted before finishing")
        run.finished_at = _now()
        _total(run)
        save_run(store, run)
        Aborts.forget(run.id)
    return run
