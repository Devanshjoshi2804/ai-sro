"""The loop. Look, plan, refuse-or-perform, verify, escalate once, stop.

Ported from `run_workflow` in `new_agent_arch/src/rig/runner.py`. Between steps
the stop button and the budget are checked; after every step the run is saved,
so the page can watch it and so a crash mid-run leaves a record rather than a
mystery.

Nothing here drives a browser or calls a vendor: `Channel` sends the command the
demonstration recorded, `Asker` plans it, and the repositories behind
`UnitOfWork` are where the run is written down.

The plan model plans; the rescue model rescues. A clean step never touches the
expensive one, and only the steps that surprise us cost what surprises cost.
Below both rungs, and only for a control neither of them could find, one rung
that looks at the picture.

The first execution of any workflow is dry. Reads and navigations go out; a
step whose evidence carries a mutation is shown in full and withheld. That
reading is `writes()`, the narrow one, and the gap is deliberate: a Save click
the recorder heard no traffic from carries no mutation the evidence knows
about, so a dry run SENDS it, against a real warehouse, unwithheld and
unapproved. It is the only live write that escapes this gate, and it escapes
because withholding every click nothing was heard from would leave a dry run
performing almost none of the job. `may_write` below is the wider reading, and
it guards the two places where being wrong costs more than that: the tap, and
the rescue.

A person presses through to live -- and until the job has earned it by verified
effect, every live write that goes out stops and waits for a tap first.

The stop button is `Stops`, shared with the backend's own runs -- there is one
register of "somebody pressed stop" and no second one to build. It is checked
between steps and never mid-command: a gesture already sent cannot be recalled
from a warehouse. It is checked once more on the way out of an approval wait,
because a release says only that the wait ended and a stop releases it too.
"""

from __future__ import annotations

import base64
import hashlib
import json
from collections.abc import Mapping, Sequence
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sro.application.execution.approvals import K_APPROVAL_WAIT_S, Approvals
from sro.application.execution.effects import earned, forget_effects, record_effect
from sro.application.execution.plan_step import SecretFor, plan_by_sight, plan_step
from sro.application.execution.stops import Stops
from sro.application.execution.verify import (
    # `already_done` is taken in this module: the steps an operator did
    # themselves before the run picked it up. Two true meanings of one name,
    # and mypy caught the collision the moment the import landed.
    already_done as effect_already_holds,
)
from sro.application.execution.verify import (
    by_what_the_page_called,
    verify,
)
from sro.application.intent.spend import over_cap
from sro.application.ports.agent import DeviceUnreachable
from sro.application.ports.channel import Channel, Reply
from sro.application.ports.model import Asker
from sro.application.ports.repositories import UnitOfWork
from sro.domain.execution.belts import K_WEAK_LOCATORS, StepVerdict
from sro.domain.execution.evidence import (
    allowlist,
    origin_of,
    primary_gesture,
    recorded_call,
    writes,
)
from sro.domain.execution.planning import Look, Planned
from sro.domain.execution.secrets import without_secrets
from sro.domain.execution.verified_writes import VerifiedWrite
from sro.domain.execution.workflow_run import RunStep, WorkflowRun, new_run_id
from sro.domain.observation.gesture import Gesture
from sro.domain.shared.hosts import system_of
from sro.domain.shared.identifiers import DeviceId, TenantId
from sro.domain.shared.prices import Answer
from sro.domain.skill.repeats import K_MOST_ITEMS, Repeat
from sro.domain.skill.workflow import Step, Workflow

K_SAME_WRITE_WINDOW = timedelta(minutes=30)
"""How long one job's write stays claimed against a second run making it again.

Not forever, which is right for a connector call keyed by run and step and
wrong here: this key is the JOB, the step and the values, so a claim that never
expired would mean a tenant could create one supplier with a given code, ever.
Long enough to cover the case this exists for -- a rule that fires twice, two
browsers taking one job, a card answered while another run of it is still
going -- and short enough that "do that again" after lunch just works."""


def write_key(workflow_id: str, step: Step, values: Mapping[str, str]) -> str:
    """What makes two writes the same write.

    The job, the step within it, and the values the run was given -- not the
    run id, because two runs are exactly what this is about. The values are
    hashed rather than spelled: they are a customer's data and this key is
    stored, and a row in `tool_calls` is not a place to keep a supplier's name.
    """
    said = json.dumps(dict(sorted(values.items())), separators=(",", ":"))
    return f"{workflow_id}:{step.order}:{hashlib.sha256(said.encode()).hexdigest()[:16]}"


K_CAP_EVERY = 10
"""How many legs a run may perform between two readings of the day's bill.

The cap was read once, at the press, and never again -- `over_cap` appears
nowhere in this module's history. One press on a 25-item list is about a
hundred legs, and at this deployment's measured $0.0118 a step that is $1.20
against a $5 day, spent after a check that saw $0. Ten is small enough that
the overspend is a rounding error and large enough that a four-step job pays
for no extra query at all: the day's bill is a sum over four tables.

A new thing on the list is always a reading, whatever this says. That is where
a run can still be stopped having done whole records rather than half of one.
"""

K_STEP_SLACK = 3
"""Attempts a run may make beyond its step count before it stops. A model
looping on a form is money spent and a warehouse confused."""

K_LEAVES = ("http.send", "navigate")
"""The two kinds whose target the model chooses, and so the only two ways a
plan can leave the system the evidence was recorded on. For everything else the
origin comes off the evidence."""


@dataclass(frozen=True, slots=True)
class _Leg:
    """One step of a run, and which thing on the list it is being done for."""

    step: Step
    values: Mapping[str, str]
    item: int | None = None


def _itinerary(
    ordered: Sequence[Step],
    repeat: Repeat | None,
    values: Mapping[str, str],
    items: Sequence[Mapping[str, str]],
) -> list[_Leg]:
    """The steps this run will actually perform, in the order it will do them.

    A job that does one thing once answers with its own steps and nothing else
    -- and so does a repeating job handed no items, or one item, which is what
    keeps every other rule in this loop from having to learn about repeats.

    Where there is a list, the body is laid out once per thing on it, with that
    thing's values over the run's own. The item's values win: a run carrying a
    `facility` for the whole job and an item carrying its own is a run where
    the item is the more specific answer.

    Nothing is interleaved. The body is done for the first thing and then for
    the second, because that is the order an operator does them in and the
    order a half-finished run has to be readable in: three records made and two
    not, rather than five records each missing their last field.
    """
    if repeat is None or len(items) <= 1:
        only = dict(items[0]) if items else {}
        return [_Leg(step, {**values, **only}) for step in ordered]
    legs: list[_Leg] = []
    for step in ordered:
        if not repeat.covers(step.order):
            legs.append(_Leg(step, values))
            continue
        if step.order != repeat.first_step:
            continue
        for index, item in enumerate(items):
            for inner in ordered:
                if repeat.covers(inner.order):
                    legs.append(_Leg(inner, {**values, **item}, index))
    return legs


def _worth_asking(position: int, leg: _Leg, itinerary: Sequence[_Leg]) -> bool:
    """Whether the day's bill is worth a query before this leg.

    Never at the first: the press just asked, and a run refused on its own
    opening leg would be a 429 wearing a run's clothes.

    Otherwise at the start of each new thing on the list -- the one boundary
    where stopping leaves whole records rather than half of one -- and every
    `K_CAP_EVERY` legs for a job that is long without being a list.
    """
    if position == 0:
        return False
    if leg.item is not None and leg.item != itinerary[position - 1].item:
        return True
    return position % K_CAP_EVERY == 0


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


def _total(run: WorkflowRun) -> None:
    run.in_tokens = sum(s.in_tokens for s in run.steps)
    run.out_tokens = sum(s.out_tokens for s in run.steps)
    run.thought_tokens = sum(s.thought_tokens for s in run.steps)
    run.cost_usd = sum(s.cost_usd for s in run.steps)
    run.unpriced = any(s.unpriced for s in run.steps)


async def _save(uow: UnitOfWork, run: WorkflowRun) -> None:
    """The run as it stands, totalled and committed.

    Totalling and saving are one call because they were never two: a run saved
    without its steps summed is a row whose bill disagrees with the steps
    underneath it, and the panel reads the row.
    """
    _total(run)
    await uow.workflow_runs.save(run)
    await uow.commit()


async def _gestures_for(
    uow: UnitOfWork, tenant_id: TenantId, workflow: Workflow
) -> dict[str, Gesture]:
    wanted = sorted({cited for step in workflow.steps for cited in step.cites})
    if not wanted:
        return {}
    found = await uow.gestures.gestures_for(tenant_id, ids=tuple(wanted))
    return {gesture.id: gesture for gesture in found}


def _target_origin(planned: Planned) -> str | None:
    """The origin a planned command would actually reach. For `http.send` and
    `navigate` that is the url's own host, not the step's: those two are the
    only ways a plan can leave the system the evidence was recorded on."""
    if planned.kind in K_LEAVES:
        return system_of(str(planned.payload.get("url")))
    origin = planned.payload.get("origin")
    return origin if isinstance(origin, str) else None


async def _where(
    channel: Channel,
    tenant_id: TenantId,
    device_id: DeviceId,
    run_id: str,
    origin: str | None,
) -> Look:
    """Where the browser is, and no picture.

    For the step a status already settled. The record still says where the
    step left the browser -- that is what `after_url` is -- and asking for it
    costs a message rather than a screenshot, an upload and a vision call.
    """
    where = await channel.send(
        tenant_id, device_id, kind="ui.url", run_id=run_id, payload={"origin": origin}
    )
    url = str(where.result.get("url")) if where.ok and where.result.get("url") else None
    return Look(url=url, screenshot=None, digest="")


async def _look(
    channel: Channel,
    tenant_id: TenantId,
    device_id: DeviceId,
    run_id: str,
    origin: str | None,
    allow_focus: bool,
) -> Look:
    """Where the browser is and what is on the screen. A refused screenshot --
    `focus_not_permitted` -- is no picture, not a failure: the planner works
    from the url and the digest."""
    where = await channel.send(
        tenant_id, device_id, kind="ui.url", run_id=run_id, payload={"origin": origin}
    )
    url = str(where.result.get("url")) if where.ok and where.result.get("url") else None
    payload: dict[str, object] = {"inline": True, "origin": origin}
    if allow_focus:
        payload["allow_focus"] = True
    shot = await channel.send(
        tenant_id, device_id, kind="screenshot", run_id=run_id, payload=payload
    )
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
    width, height = shot.result.get("width"), shot.result.get("height")
    return Look(
        url=url,
        screenshot=image,
        digest=digest,
        width=width if isinstance(width, int) else 0,
        height=height if isinstance(height, int) else 0,
    )


def _result(reply: Reply, *, wrote: bool = False) -> dict[str, object]:
    """What the extension answered -- not what it answered WITH.

    An `http.send` reply carries the response body and headers, and `verify`
    deliberately keeps those out of a prompt. A run record has no more business
    holding customer payload than a prompt does, and it holds it for longer, so
    only the three facts anything downstream reads are kept. `error_kind` stays
    its own field rather than `Reply.detail`, which concatenates kind and detail
    into prose nothing can branch on.
    """
    status = reply.result.get("status")
    matched = reply.result.get("matched_by")
    shown: dict[str, object] = {
        "ok": reply.ok,
        "status": status if isinstance(status, int) else None,
        "matched_by": matched if isinstance(matched, str) else None,
    }
    if wrote:
        # The one fact the register of verified writes needs and cannot
        # recompute: SQL cannot ask `writes()`, and the evidence a later reader
        # would have to ask it about may have been re-mined by then.
        shown["wrote"] = True
    if not reply.ok:
        shown["error_kind"] = reply.error_kind
    return shown


def _saw_nothing(step: Step, by_id: Mapping[str, Gesture]) -> bool:
    """Whether the capture recorded this step's gesture and no traffic at all
    beside it. A call that never completed is not traffic the recorder saw --
    the same completion guard `origin_of` and `expected_statuses` already wear.

    Any completed call counts, including one `recorded_call` now discards as
    the page's own timer (`K_CAUSED_S`). That looks like an oversight and is
    not: the question here is not "did this gesture write", it is "was the
    recorder listening when this gesture happened" -- and a keep-alive captured
    beside a click is evidence about the recorder, not about the click. Where
    the capture was working and heard nothing from a Save, nothing silently
    wrote.

    It is the weaker half of that evidence, and worth naming: six steps across
    both real stores have completed traffic of which none is theirs -- acme's
    `Create a Work Operation` step 3 and its `Create a Carrier Cross Reference`
    step 2, and four in `new`. Widening `may_write` to cover them would park
    step 1 of every cross-system job on a person's approval, since "Read the
    details in an email" is a Gmail click beside Gmail's own chatter, and that
    is the friction the `earned` ladder exists to retire rather than to feed.
    """
    for cited in step.cites:
        gesture = by_id.get(cited)
        if gesture is None:
            continue
        for request in gesture.requests:
            if request.status is not None and not request.failure_reason:
                return False
    return True


def _fell_over(run: WorkflowRun, in_flight: RunStep | None, reason: str) -> None:
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


def _withheld(step: Step, planned: Planned, by_id: Mapping[str, Gesture]) -> dict[str, object]:
    """The write a dry run did not send, in full: what a person reads before
    pressing through to live."""
    call = recorded_call(step, by_id)
    shown: dict[str, object] = {
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


async def fail_orphans(uow: UnitOfWork, reason: str) -> int:
    """Every run still `running` marked failed, and how many there were.

    Called once at startup, across tenants -- nobody is making the request. One
    worker owns every run, so a row that says `running` when the process starts
    is a run nobody is driving: the process that was driving it died mid-step.
    Left alone it would 409 its browser forever and keep the extension asking
    after it on every heartbeat.

    The sweep itself is the repository's, which is where the "on the last step,
    or on a new step when the run never reached one" rule lives. What is here
    is the commit: a startup that sweeps and does not commit has done nothing.
    """
    swept = await uow.workflow_runs.fail_orphans(reason)
    if swept:
        await uow.commit()
    return swept


async def run_workflow(
    uow: UnitOfWork,
    workflow: Workflow,
    *,
    tenant_id: TenantId,
    values: Mapping[str, str],
    channel: Channel,
    device_id: DeviceId,
    asker: Asker,
    plan_model: str,
    rescue_model: str,
    live: bool,
    allow_focus: bool,
    started_by: str,
    stops: Stops,
    approvals: Approvals,
    run_id: str | None = None,
    from_step: int = 0,
    items: Sequence[Mapping[str, str]] = (),
    verified_writes: tuple[VerifiedWrite, ...] = (),
    secret_for: SecretFor | None = None,
    cap_usd: float,
) -> WorkflowRun:
    # A run the caller already claimed. `POST /v1/runs` writes the `running` row
    # itself, before it answers, so a second press for the same browser is
    # refused rather than landing in the window between `create_task` and this
    # task's first slice. That row is then the authority for what was asked
    # for -- read back here rather than rebuilt from the arguments, so there is
    # one answer to "what is this run doing" and not two that can drift.
    saved = await uow.workflow_runs.get(tenant_id, run_id) if run_id else None
    # The two ways in have to agree. Reading the row's `device_id` back when it
    # disagrees with the argument would put a hand on a browser nobody asked
    # about, and its `workflow_id` would perform a different job under this
    # run's id -- both silent, and neither a thing to guess between. Refused
    # before anything is sent and before the row is touched: a run whose
    # arguments do not match it is not this caller's run to mark failed.
    #
    # And `outcome`, which the rig does not check and we do -- a deliberate
    # divergence, not a port regression. If the row is the authority for what
    # this run is doing, `outcome` is the one field that says whether there is
    # anything left to do: a row already `held`, `failed` or `aborted` picked
    # up here plans step zero, pays for the model call, has the send blocked
    # further down, saves the step `skipped` and then breaks out carrying the
    # stale outcome plus a step that never happened. The rig gets away with it
    # because nothing re-presses a finished run; phase 4's route will, and the
    # cheapest place to say no is the same refusal that already reads the row.
    #
    # And `from_step`, the fourth thing the press asked for: how many steps the
    # operator did themselves before the offer. A re-press that moves it
    # finishes a different job under this run's id -- steps the operator never
    # performed recorded `done_by_operator` and skipped, or steps they did
    # perform redone against a live warehouse. Silent, because the other three
    # checks all pass; and the only one of the four the row could not answer
    # until it had a column.
    if saved is not None and (
        saved.device_id != device_id.value
        or saved.workflow_id != workflow.id
        or saved.outcome != "running"
        or saved.from_step != from_step
    ):
        raise ValueError(
            f"{saved.id} was saved {saved.outcome} for {saved.workflow_id} on"
            f" {saved.device_id} from step {saved.from_step}, not running for"
            f" {workflow.id} on {device_id.value} from step {from_step}"
        )
    run = saved or WorkflowRun(
        id=run_id or new_run_id(),
        tenant=tenant_id.value,
        workflow_id=workflow.id,
        device_id=device_id.value,
        values=dict(values),
        started_by=started_by,
        live=live,
        allow_focus=allow_focus,
        started_at=_now(),
        # On the row, not just in this frame: it is what the check above
        # compares a re-press against, and a row that does not carry it would
        # refuse every resume as a disagreement with zero.
        from_step=from_step,
        items=[dict(item) for item in items],
    )
    values, live, allow_focus = run.values, run.live, run.allow_focus
    device_id = DeviceId(run.device_id)
    await _save(uow, run)
    by_id = await _gestures_for(uow, tenant_id, workflow)
    allowed = allowlist(workflow, by_id)
    ordered = sorted(workflow.steps, key=lambda s: s.order)
    # A list longer than one press can mean.
    #
    # Refused before anything is sent and before the first record is made: an
    # operator pressing yes on "add these" has read a mail with a handful of
    # rows in it, and two hundred is either a mistake or a decision they have
    # not made. Whoever wants the two hundred can say so twice.
    if len(run.items) > K_MOST_ITEMS:
        run.outcome = "refused"
        run.steps.append(
            RunStep(
                order=0,
                of_step=0,
                says=ordered[0].says if ordered else "",
                verdict="refused",
                verdict_by="none",
                reason=(
                    f"this asks for the job to be done {len(run.items)} times, and one press "
                    f"may mean at most {K_MOST_ITEMS}. Ask again for the rest"
                ),
            )
        )
        run.finished_at = _now()
        await _save(uow, run)
        return run
    itinerary = _itinerary(ordered, workflow.repeat, values, run.items)
    # The steps the operator already did cost nothing and are not attempted, so
    # they buy no slack either: the budget is what is left to perform.
    # Which writes this run has claimed the right to make, so a rescue of a
    # refused write is not stopped by its own first attempt.
    #
    # Write keys, not step numbers. A repeating job performs one step.order
    # once per thing on its list, so a set of step numbers claimed the first
    # item and let every other one past `tool_calls.remember` entirely -- two
    # runs whose lists overlap then created the overlap twice, which is the
    # accident the ledger exists to stop. The key already carries the values,
    # so a retry of the same leg still finds its own claim and is still let
    # through.
    claimed_here: set[str] = set()
    # Which steps a person has already approved for this list. One tap answers
    # for every thing on it: they read the rows and pressed once.
    approved_for_the_list: set[int] = set()
    # Whether the person has seen the first thing done and said to do the rest.
    proved_the_first = False
    already_done = [step for step in ordered if step.order < from_step]
    budget = len(itinerary) - len(already_done) + K_STEP_SLACK
    attempts = 0
    starts_on = None
    # The page this run begins on, which is the page of the step it begins at
    # -- not the job's first page. The extension opens a tab at `starts_on`
    # when the operator's own tab is elsewhere, and aiming a run that starts at
    # step k there would abandon the progress the offer was made on.
    first = primary_gesture(ordered[from_step], by_id) if from_step < len(ordered) else None
    if first is not None:
        starts_on = first.page_url or first.url

    # The step being worked on, so a browser that goes away mid-step fails THAT
    # step -- with the tokens its plan already cost, and its own order -- rather
    # than a fabricated one whose order can collide on (run_id, ord).
    in_flight: RunStep | None = None
    try:
        for position, leg in enumerate(itinerary):
            step, values = leg.step, leg.values
            if step.order < from_step and leg.item in (None, 0):
                # The operator did this one before the offer was made. Recorded
                # so the run reads whole, cited so a reviewer can see what it
                # was, and never sent: the job is being finished, not redone.
                #
                # `leg.item in (None, 0)`, because what they did, they did
                # once. A repeating job performs this same step.order again for
                # every other thing on the list, and skipping those was the
                # run filling the form for the first item and then pressing
                # Save for the second and the third against whatever was left
                # on the screen -- reported `held`, with the fill steps marked
                # "performed by the operator" for items nobody had touched.
                run.steps.append(
                    RunStep(
                        order=position,
                        of_step=step.order,
                        item=leg.item,
                        says=step.says,
                        verdict="done_by_operator",
                        verdict_by="none",
                        reason="performed by the operator before the offer; cites "
                        + ", ".join(step.cites),
                    )
                )
                await _save(uow, run)
                continue
            if stops.asked(run.id):
                await channel.send(
                    tenant_id, device_id, kind="abort", run_id=run.id, payload={"run_id": run.id}
                )
                run.outcome = "aborted"
                break
            # The day's bill, again. Read at the press and then never, a run
            # that passed the check at $0 could spend the rest of the tenant's
            # day inside one press -- and the longer the list, the more it
            # spends before anything asks. Asked at the start of each new thing
            # on the list, and otherwise every `K_CAP_EVERY` legs.
            if _worth_asking(position, leg, itinerary) and (
                why := await over_cap(uow, tenant_id, now=datetime.now(tz=UTC), cap_usd=cap_usd)
            ):
                run.steps.append(
                    RunStep(
                        order=position,
                        of_step=step.order,
                        item=leg.item,
                        says=step.says,
                        verdict="failed",
                        verdict_by="none",
                        reason=why,
                    )
                )
                run.outcome = "stopped"
                await _save(uow, run)
                break
            cited = [by_id[c] for c in step.cites if c in by_id]
            primary = primary_gesture(step, by_id)
            record = RunStep(
                order=position,
                of_step=step.order,
                item=leg.item,
                says=step.says,
                verdict="skipped",
            )
            in_flight = record
            run.steps.append(record)
            origin = origin_of(primary) if primary is not None else None
            mutates = writes(step, by_id)

            # The first thing is the proof.
            #
            # A tap on "add these twenty" is one decision made before anything
            # happened. It is a good decision about a job that does what the
            # person thinks it does -- and the way to find out is to do one and
            # show them. A job read out of a sentence can be the wrong job: an
            # operator asking for a warehouse equipment type was once answered
            # with a customer type, and the same guess against a list is a list
            # of wrong records.
            #
            # So the run stops once, before the second thing, with the first
            # one's result in front of them. Two taps for a list of any length,
            # and the second one is informed by something real.
            #
            # Asked even of a job that has earned the right to write unasked,
            # which is the one place this system does not let earning through.
            # Earning says the job's writes have been watched to hold over
            # runs; it says nothing about whether this is the right job for
            # what somebody just asked for, and that is the question a list
            # makes expensive. A job cannot earn its way out of being the wrong
            # job twenty times.
            if live and leg.item == 1 and not proved_the_first:
                proved_the_first = True
                did = ", ".join(str(one) for one in run.items[0].values()) or "the first one"
                rest = len(run.items) - 1
                record.verdict, record.verdict_by = "awaiting", "none"
                record.reason = (
                    f"the first of {len(run.items)} is done — {did}. Approve to do the other {rest}"
                )
                approvals.register(run.id)
                await _save(uow, run)
                if not await approvals.wait_for(run.id, K_APPROVAL_WAIT_S):
                    waited = f"{K_APPROVAL_WAIT_S / 60:.0f} minutes"
                    record.verdict, record.verdict_by = "failed", "none"
                    record.reason = f"nobody said whether to do the rest within {waited}"
                    run.outcome = "stopped"
                    await _save(uow, run)
                    break
                if stops.asked(run.id):
                    record.verdict, record.verdict_by = "failed", "none"
                    record.reason = "stopped after the first one"
                    run.outcome = "aborted"
                    await _save(uow, run)
                    with suppress(DeviceUnreachable):
                        await channel.send(
                            tenant_id,
                            device_id,
                            kind="abort",
                            run_id=run.id,
                            payload={"run_id": run.id},
                        )
                    break
                # Said yes to the rest, so the write gate is not asked again
                # for them either: they answered about this list twice already.
                record.verdict, record.verdict_by = "skipped", "none"
                record.reason = ""
                if workflow.repeat is not None:
                    approved_for_the_list.update(
                        range(workflow.repeat.first_step, workflow.repeat.last_step + 1)
                    )
            if primary is None:
                # A step with nothing actionable cited gets no model call at
                # all: it is recorded skipped and the run stops below rather
                # than doing its later steps on an assumption nobody checked.
                record.reason = "no cited gesture can be acted on"

            # The plan model, then the rescue model once, then -- only when
            # both missed the control by every recorded identity -- the rescue
            # model once more, by sight. A step with nothing actionable cited
            # gets none of them: it is recorded skipped and the run stops below.
            rungs = (
                (("evidence", plan_model), ("evidence", rescue_model), ("sight", rescue_model))
                if primary is not None
                else ()
            )
            verdict: StepVerdict | None = None
            after_failed: Look | None = None
            for how, model in rungs:
                # The sight rung is for a page that moved, not for a plan that
                # was wrong: a control the browser could not find is the one
                # failure a picture can answer. Anything else stops here.
                if (
                    how == "sight"
                    and (record.result or {}).get("error_kind") != "control_not_found"
                ):
                    break
                # One rung of the ladder: plan, and plan again once if getting
                # to the right page was all the model asked for. Getting there
                # is not doing the step, so a navigate must not spend the one
                # rescue -- it does spend budget, so a planner that only ever
                # navigates still runs out.
                planned: Planned | None = None
                before: Look | None = None
                navigated = False
                # A dropdown is answered with two clicks: one to open the list
                # and one to choose the row. The first is not the step, the
                # same way a navigate is not the step -- and like a navigate it
                # is allowed once, so a planner that only ever opens lists runs
                # out of budget rather than looping.
                opened = False
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
                    before = await _look(channel, tenant_id, device_id, run.id, origin, allow_focus)
                    if how == "sight":
                        proposal = await plan_by_sight(
                            step=step,
                            cited=cited,
                            values=values,
                            look=before,
                            origin=origin,
                            asker=asker,
                            model=model,
                            failure=verdict.reason if verdict else None,
                        )
                    else:
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
                            failed_look=after_failed,
                            verified_writes=verified_writes,
                            tenant_id=tenant_id.value,
                            secret_for=secret_for,
                            opened=opened,
                        )
                    record.planned_by = model
                    record.before_url = before.url
                    _bill(record, proposal.answer)
                    record.sent = {
                        "kind": proposal.kind,
                        "payload": without_secrets(proposal.payload),
                    }

                    if proposal.kind == "none":
                        verdict = StepVerdict("failed", "none", proposal.why)
                        break
                    off = _target_origin(proposal)
                    # For the two kinds whose target the model chooses, a url
                    # that names no origin at all -- about:blank, file:, a bare
                    # path -- is a refusal, not permission. `ui.perform` keeps
                    # its origin from the evidence and None there means the
                    # recorder saw no url, which the extension resolves itself.
                    leaves = proposal.kind in K_LEAVES
                    if (off is None and leaves) or (off is not None and off not in allowed):
                        record.verdict = "refused"
                        record.reason = (
                            f"{off} is not a system this job's evidence names"
                            if off is not None
                            else f"{proposal.payload.get('url')!r} names no system at all"
                        )
                        run.outcome = "refused"
                        break
                    if proposal.opens and not opened:
                        # Sent from here, ahead of the gate that withholds a
                        # write and parks one on a person. `plan_step` only
                        # marks a command `opens` for a step that changes
                        # nothing, which is what makes this the same safe
                        # position `navigate` sends from.
                        shown = await channel.send(
                            tenant_id,
                            device_id,
                            kind=proposal.kind,
                            run_id=run.id,
                            payload=proposal.payload,
                        )
                        if not shown.ok:
                            verdict = StepVerdict(
                                "failed", "none", f"could not open the list: {shown.detail}"
                            )
                            break
                        opened = True
                    elif proposal.kind != "navigate":
                        planned = proposal
                    elif navigated:
                        verdict = StepVerdict(
                            "failed",
                            "none",
                            proposal.why or "still on the wrong page after navigating",
                        )
                        break
                    else:
                        moved = await channel.send(
                            tenant_id,
                            device_id,
                            kind="navigate",
                            run_id=run.id,
                            payload=proposal.payload,
                        )
                        if not moved.ok:
                            verdict = StepVerdict(
                                "failed", "none", f"could not navigate: {moved.detail}"
                            )
                            break
                        navigated = True

                if planned is None and run.outcome == "running":
                    # A refusal that carries STRUCTURE is kept, because it is
                    # not "no command" -- it is the one thing a person can act
                    # on. `needs_secret` names the system and field a step
                    # wanted a password for, and the panel draws a box from it;
                    # rolling it back to the previous rung's command left the
                    # operator with a step marked ✗ and nothing to do about it,
                    # which is the whole defect this payload exists to fix.
                    refusal = record.sent if (record.sent or {}).get("payload") else None
                    record.planned_by, record.sent, record.result = previously
                    if refusal and refusal.get("kind") == "none":
                        record.sent = refusal
                    # The sight rung's answer, when it had none: the record
                    # keeps the last command that went out, and says beside it
                    # what the picture said -- "not on this screen" is the fact
                    # a person acts on, and it was about to be lost.
                    if how == "sight" and verdict is not None:
                        record.reason = f"{record.reason}; then by sight: {verdict.reason}"
                        verdict = StepVerdict(verdict.state, verdict.by, record.reason)
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

                # `writes()` is not the whole of a write. It is False when the
                # cited evidence records no mutating call AT ALL, which is what
                # a click on Save looks like when the recorder never saw the
                # traffic -- a beacon, a worker, a frame nothing was attached
                # to. A click or a press on evidence that came back silent is
                # the same unknown state as an accepted write; a click that
                # fired a completed read -- a menu, a tab -- is not.
                #
                # One predicate, both gates below: a step nobody may retry
                # afterwards is a step nobody may send unasked either.
                # A click at a point the model chose is a click on whatever is
                # there now, on a page that has already moved under the job:
                # what the demonstrated control's traffic showed says nothing
                # about it. Every sight click is a possible write.
                may_write = mutates or (
                    planned.payload.get("action") in ("click", "press")
                    and (
                        planned.kind == "ui.perform_at"
                        or (planned.kind == "ui.perform" and _saw_nothing(step, by_id))
                    )
                )

                # Already true, so there is nothing to do.
                #
                # Before the approval gate on purpose: a person asked to
                # approve a write that has already happened is a person being
                # asked to make a duplicate. The run that made this worth
                # writing signed an operator in who was already signed in, and
                # the class behind it is wider -- a rule that fires twice, two
                # browsers on one job, a card answered a day late -- and every
                # one of those ends in a second record a warehouse wanted one
                # of.
                #
                # Only where the step's own evidence shows the page reading its
                # effect back and this run carries the value to look for. None
                # of the run's other steps are touched: a step that opens a
                # form or picks a row has no read and is done the way it always
                # was.
                if live and may_write:
                    settled_already = await effect_already_holds(
                        step=step,
                        cited=cited,
                        values=values,
                        channel=channel,
                        tenant_id=tenant_id,
                        device_id=device_id,
                        run_id=run.id,
                    )
                    if settled_already is not None:
                        record.verdict, record.verdict_by = "held", "read"
                        record.reason = settled_already
                        # Not a write this run made. `record_effect` is what
                        # earns a job the right to write unasked, and a step
                        # that sent nothing has not demonstrated anything about
                        # this job's ability to write correctly.
                        record.result = {"skipped": True, "already": True}
                        verdict = StepVerdict("held", "read", settled_already)
                        break

                # And the same write, claimed before it is sent.
                #
                # `already_done` above asks the warehouse whether the record is
                # there; this asks our own store whether we are already making
                # it. They catch different halves: a read cannot see a write
                # that is in flight in another run right now, and a claim
                # cannot see a record somebody made by hand.
                #
                # Claimed and kept, never released on failure -- the reason
                # `tool_calls` gives for connector calls holds here word for
                # word: a timeout is the one case where the send may well have
                # landed, and releasing the key would retry it into a second
                # write.
                # `mutates` and not `may_write`, which is the wider of the
                # two on purpose. `may_write` includes a click whose evidence
                # recorded no traffic at all -- a Sign In that submits a form
                # the recorder cannot see is one -- and there the evidence says
                # nothing was created, so refusing a second attempt would stop
                # an operator retrying a login that failed. A step whose
                # evidence carries a real mutating call is the one that can
                # leave a second record behind.
                key = write_key(workflow.id, step, values) if live and mutates else ""
                if live and mutates and key not in claimed_here:
                    async with uow:
                        # Not `first`: that name is a gesture in this function.
                        claimed = await uow.tool_calls.remember(
                            tenant_id,
                            key,
                            tool=f"{planned.kind} {step.says}"[:200],
                            at=datetime.now(tz=UTC),
                            stale_after=K_SAME_WRITE_WINDOW,
                        )
                        await uow.commit()
                    # Once per step per run, not once per attempt. A write the
                    # server itself refused is the one write this loop is
                    # allowed to plan again, and a claim made by the first
                    # attempt must not refuse the second -- that is this run
                    # colliding with itself.
                    claimed_here.add(key)
                    if not claimed:
                        record.verdict, record.verdict_by = "failed", "none"
                        record.reason = (
                            "another run of this job made this write with these values in the "
                            "last half hour, and it may have landed. Nothing is sent twice on a "
                            "guess -- start a new run if it did not"
                        )
                        verdict = StepVerdict("failed", "none", record.reason)
                        break

                # A live write, on a job that has not yet earned the right to
                # write unasked: shown in the panel with what would go out, and
                # held until somebody taps. `live` is checked here rather than
                # inherited from the block above, whose narrower `mutates` lets
                # a dry run walk past it: a dry run withholds, never waits.
                # Once for the list, not once per thing.
                #
                # A person answering "add these three" read three rows and
                # pressed one button. Asking them again for the second and the
                # third is asking them to authorise what they have already
                # authorised -- and a card per thing on a list of ten is a
                # panel nobody reads by the fourth. So the tap on one step
                # covers that step for the rest of the list, and only for the
                # rest of THIS list: a second run asks again, because a second
                # press is a second decision.
                #
                # Not the same as earning the right to write unasked. That is
                # a job proving itself over runs, and this is one person
                # answering about one list they have in front of them.
                approved_here = leg.item is not None and step.order in approved_for_the_list
                if (
                    live
                    and may_write
                    and not approved_here
                    and not await earned(uow.workflows, tenant_id, workflow.id)
                ):
                    record.verdict, record.verdict_by = "awaiting", "none"
                    record.reason = (
                        "waiting for a person to approve the write"
                        if not run.items
                        else (
                            "waiting for a person to approve the write, for this and the "
                            f"{len(run.items) - 1} other thing(s) on the list"
                        )
                    )
                    # `without_secrets`: this row is read by the panel, by an
                    # operator reviewing what happened, and by the model asked
                    # to rescue a failed step. A password typed from the vault
                    # would otherwise reach all three and outlive the run.
                    record.sent = {
                        "kind": planned.kind,
                        "payload": without_secrets(planned.payload),
                    }
                    # Registered before the save, not by the wait below: the
                    # save is what puts this step in front of a person, and a
                    # tap that lands before the wait starts must find an event
                    # to set rather than a 409.
                    approvals.register(run.id)
                    await _save(uow, run)
                    if not await approvals.wait_for(run.id, K_APPROVAL_WAIT_S):
                        waited = f"{K_APPROVAL_WAIT_S / 60:.0f} minutes"
                        record.verdict, record.verdict_by = "failed", "none"
                        record.reason = f"nobody approved the write within {waited}"
                        verdict = StepVerdict("failed", "none", record.reason)
                        break
                    # A released wait is not a yes. The stop button releases it
                    # as well as setting the flag, so a person who pressed Stop
                    # rather than Approve gets an aborted run and not a write.
                    if stops.asked(run.id):
                        record.verdict, record.verdict_by = "failed", "none"
                        record.reason = "stopped while waiting for approval"
                        run.outcome = "aborted"
                        # The browser is told here too, and not only between
                        # steps. This is the path where somebody is WATCHING:
                        # they pressed Stop on a panel showing a write, and
                        # until the extension hears the abort its band goes on
                        # claiming the run for up to `RUN_QUIET_MS`. The route
                        # sends nothing itself -- `AbortWorkflowRun` releases
                        # the wait and the loop is what talks to the browser.
                        #
                        # Suppressed where the between-steps send at the top of
                        # this loop is bare, which is a deliberate difference
                        # and the rig's own shape (`api.py:1250`). There, a
                        # send that raises is a browser that went away and the
                        # run honestly failed. Here the person's intention is
                        # already recorded and the row already says `aborted`,
                        # and letting this raise would hand it to `_fell_over`
                        # -- which rewrites the outcome to `failed` and the
                        # reason to the socket error, reporting "the browser
                        # went away" for a run a person deliberately stopped.
                        # A browser that has gone is also the commonest reason
                        # to press Stop.
                        with suppress(DeviceUnreachable):
                            await channel.send(
                                tenant_id,
                                device_id,
                                kind="abort",
                                run_id=run.id,
                                payload={"run_id": run.id},
                            )
                        break
                    # Answered yes, and the answer stands for the rest of the
                    # list. Recorded after both refusals above, so a wait that
                    # timed out or a Stop cannot be mistaken for a tap.
                    if leg.item is not None:
                        approved_for_the_list.add(step.order)

                # `before` and `planned` are set by the same pass of the while
                # above: a command to send is a command something was looked at
                # before planning.
                assert before is not None  # noqa: S101 -- see the comment above
                # The moment the command went out, so the calls the page makes
                # because of it can be told from the ones it was already
                # making. Taken here and not after the reply: a form submit
                # posts before the click's own answer comes back.
                sent_at = datetime.now(tz=UTC).timestamp()
                reply = await channel.send(
                    tenant_id, device_id, kind=planned.kind, run_id=run.id, payload=planned.payload
                )
                record.result = _result(reply, wrote=may_write)
                # A point has no locator: the record says the control was found
                # by sight, in both places a reader looks.
                if reply.ok and planned.kind == "ui.perform_at":
                    record.result["matched_by"] = "sight"
                matched = record.result["matched_by"]
                record.matched_by = matched if reply.ok and isinstance(matched, str) else None
                # The cheap rung first, and the picture only if it cannot
                # answer. A step whose demonstrated endpoint has just answered
                # 201 is done, and photographing the screen to ask a model
                # whether it looks done costs a screenshot, a vision call and
                # most of the step's wall clock to reach a worse answer -- the
                # verifier's own docstring puts the status first and the screen
                # "last and least", and until the browser could be asked what
                # it called, a UI step could never reach the first rung.
                settled = (
                    await by_what_the_page_called(
                        step=step,
                        cited=cited,
                        since=sent_at,
                        channel=channel,
                        tenant_id=tenant_id,
                        device_id=device_id,
                        run_id=run.id,
                    )
                    if reply.ok
                    else None
                )
                # Where the status settled it, the url is still wanted -- the
                # record says where the step left the browser -- and that is a
                # question the browser answers without a camera.
                after = (
                    await _where(channel, tenant_id, device_id, run.id, origin)
                    if settled is not None
                    else await _look(channel, tenant_id, device_id, run.id, origin, allow_focus)
                )
                record.after_url = after.url
                # Kept for the rescue: if this attempt does not hold, the next
                # rung is shown the page it left behind beside the page as it
                # is when it plans.
                after_failed = after
                verdict = settled or await verify(
                    step=step,
                    sent_kind=planned.kind,
                    answer=reply,
                    cited=cited,
                    values=values,
                    look_before=before,
                    look_after=after,
                    channel=channel,
                    tenant_id=tenant_id,
                    device_id=device_id,
                    run_id=run.id,
                    origin=origin,
                    asker=asker,
                    model=plan_model,
                )
                _bill(record, verdict.answer)
                record.verdict, record.verdict_by = verdict.state, verdict.by
                record.reason = verdict.reason
                if verdict.made:
                    # What the warehouse called the record this step made. On
                    # the row because it is the only place it exists: the panel
                    # says which records a run created, and an undo -- the day
                    # the evidence for one exists -- addresses them by it.
                    record.made = dict(verdict.made)
                if verdict.state == "held":
                    # Found by sight, or by the last locator: the page moved
                    # under the job, and the job is flagged before it breaks.
                    if planned.kind == "ui.perform_at" or (
                        planned.kind == "ui.perform" and record.matched_by in K_WEAK_LOCATORS
                    ):
                        record.stale = True
                        await uow.workflows.mark_stale(
                            workflow.id,
                            step.order,
                            matched_by=record.matched_by,
                            noticed_at=_now(),
                        )
                    elif planned.kind == "ui.perform":
                        # The step was found the strong way again: a warning
                        # that never clears is a warning nobody reads.
                        await uow.workflows.clear_stale(workflow.id, step.order)
                    # A write this run made that the verifier saw hold by
                    # state. The three gates -- live, held, wrote -- are
                    # `record_effect`'s own, read off the record rather than
                    # off these locals so a second caller cannot forget one.
                    await record_effect(uow.workflows, run, record, at=_now())
                    break
                # A write that went out and was accepted, and then could not be
                # shown to have held, is not a step to try again: the second
                # attempt would create the order twice. Only a write the server
                # itself refused -- or one the browser never sent -- is safe to
                # rescue. A read is always safe. `may_write` above is the same
                # reading of "this may have changed something" the tap uses.
                if (
                    may_write
                    and reply.ok
                    and not (verdict.state == "failed" and verdict.by == "status")
                ):
                    record.reason = f"state unknown after a write; not retried: {record.reason}"
                    break

            # A rung that never reached a command -- an unplannable step, a
            # navigate that would not go -- left its reason on the local verdict
            # and nothing on the record, which then read `skipped` and let the
            # run walk past it.
            if record.verdict == "skipped" and verdict is not None:
                record.verdict, record.verdict_by = verdict.state, verdict.by
                record.reason = verdict.reason

            in_flight = None
            await _save(uow, run)
            if run.outcome != "running":
                break
            # Held, or deliberately withheld by a dry run. Anything else --
            # failed, unclear, refused, or a step with nothing actionable to
            # cite -- is a step nobody watched succeed, and the rest of the job
            # assumes it did. Nothing runs unattended past one.
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
        # A write that went out and did not hold un-earns the whole job: the
        # next runs ask for a tap again. Here rather than in the step body,
        # because the step body is not reached when a browser goes away
        # mid-write -- and that run wrote, was never shown to have held, and
        # would have kept its autonomy.
        await forget_effects(uow.workflows, run)
        run.finished_at = _now()
        await _save(uow, run)
        stops.forget(run.id)
        approvals.forget(run.id)
    return run
