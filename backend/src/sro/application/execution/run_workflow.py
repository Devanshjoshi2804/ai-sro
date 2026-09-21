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

import asyncio
import base64
import hashlib
import json
import logging
from collections.abc import Awaitable, Callable, Mapping, Sequence
from collections.abc import Set as AbstractSet
from contextlib import suppress
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from urllib.parse import urlparse

from sro.application.execution.approvals import K_APPROVAL_WAIT_S, Approvals
from sro.application.execution.declared import declared_keys, names_of, screen_for
from sro.application.execution.effects import earned, forget_effects, record_effect
from sro.application.execution.learn_from_rescue import learn_from_the_rescue
from sro.application.execution.plan_step import (
    SecretFor,
    plan_by_sight,
    plan_step,
    replay_without_asking,
)
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
from sro.domain.chat.asked_by import only_reads_the_mail
from sro.domain.execution.belts import K_WEAK_LOCATORS, StepVerdict
from sro.domain.execution.evidence import (
    allowlist,
    origin_of,
    primary_gesture,
    recorded_call,
    route_for,
    stood_on,
    writes,
)
from sro.domain.execution.field_notes import notes_on
from sro.domain.execution.gathering import Gathered
from sro.domain.execution.learned_step import LearnedStep, learned_from
from sro.domain.execution.planning import Look, Planned
from sro.domain.execution.secrets import secret_key_of, without_secrets
from sro.domain.execution.verified_writes import VerifiedWrite
from sro.domain.execution.workflow_run import RunStep, WorkflowRun, new_run_id
from sro.domain.execution.write_plan import scaffolding_for, seen_values
from sro.domain.observation.gesture import Gesture
from sro.domain.observation.trim import path_shape
from sro.domain.shared.hosts import (
    origin_of as origin_of_url,
)
from sro.domain.shared.hosts import same_screen, screen_of, system_of
from sro.domain.shared.identifiers import DeviceId, TenantId
from sro.domain.shared.prices import Answer
from sro.domain.skill.repeats import K_MOST_ITEMS, Repeat
from sro.domain.skill.signing_in import is_a_way_in, signs_in_at
from sro.domain.skill.workflow import Step, Workflow
from sro.whose import attribute

KnownFields = Callable[[tuple[str, ...], str], Awaitable[Mapping[str, Mapping[str, object]]]]
"""What the knowledge base says about these body keys, by key.

A callable rather than `Retrieve` itself, for `SecretFor`'s reason: this module
drives a run and does not learn what a vector store is. A deployment with an
empty knowledge base passes nothing and every step says nothing, which is what
happened before the claims were ever ingested -- 2,076 of them, and the store
on QA held none until 2026-09-16.
"""

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

K_STILL_COMING_S = 2.0
"""How long a step waits for a page that had not finished arriving.

Long enough for a panel to draw, short enough that it costs less than the rung
it replaces -- a model call about a half-drawn screen is seconds and money,
and this is neither. One wait per step: a screen still coming after this is
stuck, and waiting again turns a fault into a hang."""

GatherValues = Callable[[Sequence[str]], Awaitable[Gathered]]
"""Go and find the values this run was not given, or say which are missing.

A callable rather than `GatherContext` itself, for `SecretFor`'s reason: this
module drives a run and does not learn what a mailbox is. A deployment with no
connector passes nothing, and a run with missing values refuses exactly as it
always did."""

K_OPENINGS = 3
"""How many things one rung may open before it must answer the step.

A screen is answered with as many clicks as it takes -- open the menu, see the
item, click it -- and a rung that allowed exactly one was a rung that could not
reach a control under a menu nobody demonstrated. Measured on the deployment
across 2026-09-16 and 17: `Create a Customer Type` never once reached its form
on the screen, and that was why.

Three, because it is the depth a warehouse menu actually has and because a
planner that only ever opens things has to run out rather than loop. Each
costs a command and a picture; the step budget above bounds the rest.
"""

K_NOT_HERE = frozenset({"no_tab_for_system", "no_tab_for_origin"})
"""The two refusals that mean the browser is not where the step needs it.

Not a broken job and not a wrong plan: the tab was closed, or the system signed
the operator out and took the page with it. The same run would work a second
later with a person signed in, so the run asks for one rather than failing --
see `_let_in`.

Both are sent by the extension after looking: `no_tab_for_system` is nothing
open on the system at all, `no_tab_for_origin` is a tab that has been taken
somewhere else, which is what an identity provider does on the way to its login
page."""

K_NEVER_SENT = K_NOT_HERE | frozenset({"focus_not_permitted", "aborted"})
"""Refusals that mean the extension never reached the wire, so a write claimed
for this step can be given back.

`drivers._NO_BROWSER` is the same list with `timeout` in it, and the difference
is the whole of this constant. A timeout is the one case where the send may
well have landed -- it is the case `ToolCallRepository.remember` is written
around -- so it keeps its claim. These four are the extension refusing BEFORE
it acted: no tab on the system, no tab on the origin, focus it was not given,
a run already aborted. None of them touched the warehouse.

Found on the live deployment 2026-09-16: a run failed `no_tab_for_system`
because the operator's Blue Yonder session had expired, and every later run of
the same job with the same values was refused for half an hour on the grounds
that the first one might have landed. It could not have."""

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

    rescue: bool = False
    """Whether this step belongs to ANOTHER job, spliced in to get through an
    interruption -- signing back in, today.

    Every per-step decision this run made up front is keyed on `step.order`,
    and another job's steps start at 0 like everyone else's. Measured on the
    deployment 2026-09-19, run `run_d6e7a78`: the sign-in job's first click was
    recorded `not_needed -- this step only opened the request, which was read
    before the run began`, because the job being run has a mail-opening step 0
    and the orders collided. The run then tried the SECOND click on a page the
    first had never touched.

    So a rescue leg is exempt from all of them: what was already read, what was
    collapsed into a call, what the operator did before the offer. None of
    those were decided about this job."""


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


async def _the_way_back_in(
    uow: UnitOfWork,
    tenant_id: TenantId,
    workflow: Workflow,
    look: Look | None,
    values: Mapping[str, str],
    by_id: dict[str, Gesture],
) -> tuple[Workflow | None, list[_Leg]]:
    """The job that signs this run back in and its steps, where the tenant has
    shown them.

    A session expiring mid-flow is not an exception, it is a Tuesday: an
    operator works in a system all day and the system logs them out. Until this
    the run stopped and the request went nowhere until somebody noticed, which
    on a job started from a mailbox can be hours.

    **The way back in is mined evidence like anything else.** On the deployment
    the operator has clicked through `blueyonderalphaus.b2clogin.com` many
    times with the recorder on, and that is `Log in using Azure B2C SSO` --
    two clicks, both on that host. `signing_in.signs_in_at` is the lookup, by
    the host the browser actually sits on and never by a title.

    The steps come back as ordinary legs, spliced into the itinerary ahead of
    the step that met the page. Nothing here performs anything: they go through
    the same ladder, the same write gate and the same belts as any other step,
    and a password still comes out of the vault under `needs_secret` -- which
    means a tenant that has stored none gets the refusal that asks for one,
    rather than a run that guesses.

    **Not "this looks like a login" -- "the operator has been through this
    page".** `A_LOGIN` is `input[type=password]`, and the deployment's chooser
    has no password box at all: two SSO buttons, `Local WMS users` and
    `Kenco Management Services`. Measured 2026-09-19, run `run_db684040`, which
    landed there and read `signed_out: false`. A page recognised by its
    controls will always miss the next platform's idea of a login.

    What is not a guess is that the browser is somewhere this step's system is
    not, and that the tenant has a job whose every gesture is on that page. An
    operator does not mine a job on a host they were passing through; a job
    entirely there is the way through it, whatever it looks like.

    So: the step failed, the browser is off its own system -- or the page did
    say it was asking -- and exactly one job of this tenant's is entirely
    there. A step that failed on the right screen goes nowhere near this.
    """
    if look is None or not (look.signed_out or look.elsewhere):
        return None, []
    where = look.elsewhere or look.url or ""
    known = await uow.workflows.known(tenant_id)
    # Every job's evidence, in one read. The lookup is about WHERE the
    # gestures happened, so it cannot be made without them -- and this run has
    # loaded only its own job's cites. One query, and only ever on the failure
    # that met a sign-in page.
    cited = sorted({one for job in known for step in job.steps for one in step.cites})
    seen = (
        {one.id: one for one in await uow.gestures.gestures_for(tenant_id, ids=tuple(cited))}
        if cited
        else {}
    )
    back = signs_in_at(where, list(known), seen, not_this=workflow.id)
    if back is None:
        return None, []
    job = next((one for one in known if one.id == back), None)
    if job is None or not job.steps:
        return None, []
    # And into the run's own map, because everything downstream -- planning,
    # the locator ladder, the belts -- reads a step's evidence from there.
    by_id.update({one: seen[one] for step in job.steps for one in step.cites if one in seen})
    if not all(any(one in by_id for one in step.cites) for step in job.steps):
        return None, []
    logger.info("%s signing back in at %s with %s", workflow.id, where, job.title)
    legs = [
        _Leg(step, dict(values), rescue=True)
        for step in sorted(job.steps, key=lambda one: one.order)
    ]
    return job, legs


def _target_origin(planned: Planned) -> str | None:
    """The origin a planned command would actually reach. For `http.send` and
    `navigate` that is the url's own host, not the step's: those two are the
    only ways a plan can leave the system the evidence was recorded on."""
    if planned.kind in K_LEAVES:
        return system_of(str(planned.payload.get("url")))
    origin = planned.payload.get("origin")
    return origin if isinstance(origin, str) else None


def _refused_origin(
    kind: str, off: str | None, *, standing: AbstractSet[str], replayable: AbstractSet[str]
) -> bool:
    """Whether a planned command's target is one this job's evidence forbids.

    Two sets, because a plan can reach somewhere two different ways. `standing`
    is where the operator actually was, and it is what may take the BROWSER
    somewhere. `replayable` adds the origins their pages' own requests named,
    which `http.send` needs: a step's demonstrated call can be to an API origin
    the page itself never was, and refusing those refuses the step its own
    write.

    The difference is not hypothetical. A page calls whoever it likes -- a
    Gmail page calls Google's own infrastructure -- so one set for both
    questions made `https://play.google.com` somewhere a planner could have
    navigated an operator's browser to, on the evidence of a telemetry beacon,
    for a job about warehouse customer types.

    Named no origin at all -- `about:blank`, `file:`, a bare path -- is a
    refusal for the two kinds that choose their own target, and not for the
    rest: there `None` means the recorder saw no url, which the extension
    resolves itself.

    Lifted out of the run loop because that is the only way anything can ask
    it. Inside, it was three lines nothing could reach without driving a whole
    run, and the sets it compares had just been merged into one.
    """
    if off is None:
        return kind in K_LEAVES
    return off not in (replayable if kind == "http.send" else standing)


async def _let_in(
    uow: UnitOfWork,
    run: WorkflowRun,
    record: RunStep,
    *,
    where: str,
    approvals: Approvals,
    stops: Stops,
) -> bool:
    """Ask for a browser that is signed in, and wait for somebody to say there
    is one. True when the step may go again.

    The one refusal this system can do something about by asking. A job whose
    plan is wrong needs a demonstration and a value nobody typed needs a
    mailbox, but a session that has aged out needs a person who is already
    sitting in front of the panel -- and until now the run told them their job
    had failed on a sentence about a tab.

    The write gate's own machinery, because it is the same question asked in
    the same place: the record says `awaiting`, the panel draws the button off
    that, and the tap releases the wait. Nothing new to learn, on either side.

    Not a remedy that signs anybody in. `Remedy.REFRESH_SESSION` exists for the
    browsers this system owns; this is the operator's own Chrome, where the
    only thing that may type a password is the person sitting at it.
    """
    record.verdict, record.verdict_by = "awaiting", "none"
    record.reason = f"the browser is not on {where} — open it and sign in, then approve to carry on"
    # Registered before the save, for the write gate's reason: the save is what
    # puts this in front of a person, and a tap that lands before the wait
    # starts must find an event to set rather than a 409.
    approvals.register(run.id)
    await _save(uow, run)
    if not await approvals.wait_for(run.id, K_APPROVAL_WAIT_S):
        record.verdict, record.verdict_by = "failed", "none"
        record.reason = f"nobody signed in to {where} within {K_APPROVAL_WAIT_S / 60:.0f} minutes"
        run.outcome = "stopped"
        await _save(uow, run)
        return False
    if stops.asked(run.id):
        record.verdict, record.verdict_by = "failed", "none"
        record.reason = "stopped while waiting for a signed-in browser"
        run.outcome = "aborted"
        await _save(uow, run)
        return False
    # Back to what an in-flight step already says, for the reason the write
    # gate gives: a row left `awaiting` through the send is a row that lies for
    # as long as the step takes, and an operator who tapped Approve watches the
    # same paused card redraw with the same button.
    record.verdict, record.verdict_by = "skipped", "none"
    record.reason = "signed in; sending again"
    await _save(uow, run)
    return True


logger = logging.getLogger(__name__)
"""What the ladder did, said out loud.

The mining side has logged its reasoning since it was written -- "1 step(s)
repointed at the control the operator pressed" -- and the execution side had
2,251 lines and not one logger. What a run left behind was a truncated
sentence on a step row, read back through the console, and that sentence is
everything anybody has had to debug a run with.

Measured over 2026-09-15 to 17: four separate faults in one job (a frame
lookup that could not work, an unbounded viewport walk, an occluded window
with no frame to photograph, a step recorded as refused that the page had
taken) each arrived as the same few words. Every one of them took a
deploy-and-rerun cycle to tell apart, and three were diagnosed wrongly first.

So the ladder narrates: every rung it built, every rung it tried, what that
rung planned, what the browser answered, and what it concluded. One line each,
greppable by run and by step, and about the LADDER rather than about any job
-- a rule that reads "Customer Type" anywhere is a rule that helps one
workflow and lies about the rest.

Nothing here carries a value, a body or a header. `_said` keeps a command to
its kind and its shape, for the same reason `_result` keeps a reply to three
facts: a log outlives the run and a warehouse's payload has no business in it.
"""

K_ACTS = {
    "ui.perform": ("action", "value", "locators"),
    "ui.perform_at": ("action", "value", "x", "y"),
    "http.send": ("method", "url", "body"),
    "navigate": ("url",),
}
"""What identifies a command by WHAT IT DOES, per kind.

Not the whole payload. Two attempts at one step differ in fields that change
nothing about the page -- `starts_on` is carried by the first command a run
sends and by none after it -- so comparing payloads whole says two identical
clicks are different commands.
"""


def _command_key(kind: str, payload: Mapping[str, object]) -> str:
    """One command, as a string equal for two commands that do the same thing.

    For comparison and never for a log: `value` is what an operator typed, and
    on a sign-in step it is a password out of the vault. `_said` is the half
    that is safe to print.
    """
    acts = K_ACTS.get(kind)
    if acts is None:
        return f"{kind} {json.dumps(payload, sort_keys=True, default=str)}"
    return f"{kind} " + json.dumps(
        {part: payload.get(part) for part in acts}, sort_keys=True, default=str
    )


K_SAID = 120
"""How much of a plan's shape one line carries. A url and a method, not a body."""


def _said(kind: str, payload: Mapping[str, object]) -> str:
    """One command, in the few facts that identify it and none that reveal it.

    A url's path and nothing after it: the query holds session tokens and the
    fragment holds the screen, and neither belongs in a log that is kept.
    """
    if kind == "http.send":
        method = str(payload.get("method") or "")
        where = str(payload.get("url") or "")
        try:
            where = urlparse(where).path or where
        except ValueError:
            where = ""
        return f"{method} {where}"[:K_SAID]
    if kind in ("ui.perform", "ui.perform_at"):
        action = str(payload.get("action") or "")
        locators = payload.get("locators")
        if isinstance(locators, list) and locators:
            how = ",".join(str(one.get("strategy")) for one in locators if isinstance(one, dict))
            return f"{action} by {how}"[:K_SAID]
        at = (payload.get("x"), payload.get("y"))
        return f"{action} at {at[0]},{at[1]}"[:K_SAID]
    if kind == "navigate":
        where = str(payload.get("url") or "")
        try:
            place = urlparse(where)
            return f"{place.netloc}{place.path}"[:K_SAID]
        except ValueError:
            return ""
    return ""


async def _sign_in_here(
    *,
    channel: Channel,
    tenant_id: TenantId,
    device_id: DeviceId,
    run_id: str,
    origin: str | None,
    where: str,
    secret_for: SecretFor | None,
    record: RunStep,
) -> bool:
    """Fill this system's login page with what the vault holds. True if it went.

    The credential is read here and put in one command. It is not returned, not
    logged, and not written to the record -- `record.sent` keeps what the
    extension was asked to DO and never what it was given, which is the same
    rule `without_secrets` keeps for every other step that types one.

    False for every reason there is: no vault, nothing stored, a browser that
    refused, a page that took neither box. Each of them leaves the step exactly
    as it was -- failed, and about to ask for a password -- because a sign-in
    that did not happen must not read as one that did.
    """
    system = origin_of_url(where) or where
    if not system or secret_for is None:
        return False
    try:
        password = await secret_for(secret_key_of(tenant_id.value, system, "password"))
        username = await secret_for(secret_key_of(tenant_id.value, system, "username"))
    except Exception:
        logger.info("%s: the vault could not be asked to sign in", run_id)
        return False
    if not password:
        return False
    answered = await channel.send(
        tenant_id,
        device_id,
        kind="sign_in",
        run_id=run_id,
        payload={"origin": origin, "username": username or "", "password": password},
    )
    # What it DID, which is the half worth keeping. A run record read by a
    # person, by the panel and by the model asked to rescue the next step, and
    # none of those has any business holding a credential.
    steps = (answered.result or {}).get("did")
    did = ", ".join(str(one) for one in steps) if isinstance(steps, list) else ""
    logger.info(
        "%s: signing in to %s -- %s",
        run_id,
        system,
        did if answered.ok else f"refused: {answered.detail}",
    )
    if not answered.ok:
        record.reason = f"{record.reason}; the sign-in was refused: {answered.detail}"
        return False
    record.reason = f"{record.reason}; signed in again ({did})"
    return True


async def _ask_for_the_password(
    sent: Mapping[str, object] | None,
    where: str,
    tenant_id: TenantId,
    secret_for: SecretFor | None,
) -> dict[str, object] | None:
    """The refusal, carrying the vault key this system's password belongs under.

    Only where there is nothing stored yet: a run that stopped at a login page
    with a credential already in the vault has a different problem -- the
    password is wrong, or the system wants a second factor -- and asking for it
    again would be this system's answer to everything.

    Left exactly as it was on every other path, including when the vault cannot
    be reached. A refusal that grew a password box because a vault timed out
    would have somebody typing their credential to fix an outage.
    """
    system = origin_of_url(where) or where
    if not system or secret_for is None:
        return dict(sent) if sent else None
    key = secret_key_of(tenant_id.value, system, "password")
    try:
        if await secret_for(key):
            return dict(sent) if sent else None
    except Exception:
        logger.info("%s could not be looked up; not asking for it", key)
        return dict(sent) if sent else None
    kept: dict[str, object] = dict(sent) if sent else {"kind": "none"}
    was = kept.get("payload")
    payload: dict[str, object] = dict(was) if isinstance(was, Mapping) else {}
    payload["needs_secret"] = {"system": system, "field": "password", "key": key}
    kept["payload"] = payload
    return kept


def _what_earlier_steps_made(run: WorkflowRun, uses: Sequence[int]) -> dict[str, str]:
    """What the named steps created, keyed `step<order>.<field>`.

    Read off the run rather than held in a local, for `run.values`' reason: a
    resume re-reads the row and hands it back down, and anything kept only in
    this frame is a thing the second half of a run does not know.

    The LAST attempt of a step that ran more than once, which a repeating job
    does per item: the record this item is about is the one that step just
    made, not the one it made for the item before.

    Empty for a step that made nothing, which is most of them, and for one that
    has not run yet -- which the workflow checks refuse, and this must not
    depend on them having.
    """
    made: dict[str, str] = {}
    for order in uses:
        for record in run.steps:
            if record.of_step != order or not record.made:
                continue
            made.update({f"step{order}.{name}": value for name, value in record.made.items()})
    return made


async def _refused_by_the_system(
    *,
    channel: Channel,
    tenant_id: TenantId,
    device_id: DeviceId,
    run_id: str,
    since: float,
) -> str:
    """What the system itself refused during this step, if it refused anything.

    The last of the five, and the only one no amount of looking at a screen can
    answer: an operator who can reach a screen and not the action on it sees a
    page that looks exactly right and a control that does nothing. What says so
    is the status, and the calls the driven tab made are already asked for --
    `by_what_the_page_called` reads them to settle a step, but only for the
    step's own demonstrated endpoint and only where the evidence recorded a
    write. A 403 on anything else went unread.

    `401` and `403` told apart, because they are two different problems with
    two different fixes: nobody is signed in, and this account may not do this.

    Empty for everything else, including a browser that would not answer. A
    step that failed for an ordinary reason must not be told it was refused.
    """
    got = await channel.send(
        tenant_id, device_id, kind="calls.since", run_id=run_id, payload={"since": since}
    )
    if not got.ok:
        return ""
    made = got.result.get("calls") if isinstance(got.result, dict) else None
    for call in reversed(made if isinstance(made, list) else []):
        if not isinstance(call, dict):
            continue
        status = call.get("status")
        if status not in (401, 403):
            continue
        where = f"{str(call.get('method', '')).upper()} {path_shape(str(call.get('url', '')))}"
        return (
            f"this system refused the request: {where} returned 403. "
            "The screen is reachable and the action is not -- which is a fact "
            "about this account rather than about the job."
            if status == 403
            else f"this system answered {where} with 401 -- nobody is signed in."
        )
    return ""


def _said_what_is_there(
    verdict: StepVerdict,
    look: Look,
    screen: str | None = None,
    refused: str = "",
) -> StepVerdict:
    """The same verdict, saying what was on the screen instead.

    `control_not_found: no control matched` is true and says nothing about
    why, and the two things that most often put it there are both visible: a
    login page, and a dialog over the form. Neither renames the verdict -- a
    run that decided WHY a step failed would be a run guessing, and what this
    knows is only what is on the screen. The original reason is kept beside
    it, because the selector may be broken as well.

    Only for a failure. A step that held in front of a dialog is a step that
    held: plenty of screens confirm a save in one.
    """
    if verdict.state != "failed":
        return verdict
    if look.signed_out:
        return replace(
            verdict,
            reason=(
                "the browser is at a sign-in page -- this system's session has gone. "
                f"Sign in and start it again. ({verdict.reason})"
            ),
        )
    # What the system itself said, before anything read off the screen: a 403
    # is the whole answer, and the screen above it looks entirely normal.
    if refused:
        return replace(verdict, reason=f"{refused} ({verdict.reason})")
    if look.dialog.strip():
        # What it SAID, first and in full. A person reading this is looking for
        # the sentence the warehouse put on the screen, and every word this
        # wraps around it is a word between them and it.
        return replace(
            verdict,
            reason=f"the screen is showing: {look.dialog.strip()} ({verdict.reason})",
        )
    # And the plainest of the three: the browser is somewhere else.
    #
    # Not a login, no dialog, and a control nothing matched -- because the
    # screen this step was demonstrated on is not the screen in front of it.
    # A redirect, a half-finished navigation, an operator who clicked away.
    # Seen on the deployment 2026-09-18: a run reported a missing tab item
    # while the browser sat on the Warehouse configuration screen, after the
    # operator had signed back in and landed somewhere else.
    #
    # `same_screen` and not string equality, which is the comparison this
    # already makes everywhere else: a query string and a fragment's
    # particulars are not a different screen.
    # `elsewhere` when the browser is not on this system at all, which is what
    # every interruption looks like: the login host, a consent screen, an error
    # page a proxy served. Reading only `url` left the run saying nothing about
    # any of them.
    where = look.url or look.elsewhere
    if screen and where and not same_screen(where, screen):
        return replace(
            verdict,
            # The urls themselves. `screen_of` answers what a set of VISITS
            # agree on, which is not this question -- and a person reading a
            # step record wants the address they can go and look at.
            reason=(
                f"the browser is on {where}, and this step was demonstrated "
                f"on {screen} ({verdict.reason})"
            ),
        )
    return verdict


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
    return Look(
        url=url,
        screenshot=None,
        digest="",
        elsewhere=str(where.result.get("elsewhere") or "") if where.ok else "",
        elsewhere_is_ours=bool(where.ok and where.result.get("elsewhere_is_ours")),
        signed_out=bool(where.ok and where.result.get("signed_out")),
        dialog=str(where.result.get("dialog") or "") if where.ok else "",
        loading=bool(where.ok and where.result.get("loading")),
    )


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
    width = width if isinstance(width, int) else 0
    height = height if isinstance(height, int) else 0
    # Why there is no picture, kept rather than dropped. A browser that refused
    # the screen says so in its own words, and a picture that arrived with no
    # viewport beside it is a different fault again -- both used to reach the
    # step record as the same four words.
    refused = shot.detail if not shot.ok else ""
    if not refused and (image is None or not width or not height):
        refused = "the browser answered with no picture"
    return Look(
        url=url,
        screenshot=image,
        digest=digest,
        width=width,
        height=height,
        refused=refused,
        # Read off the same answer the url came in. Both readers carry it or
        # only route steps would ever notice a login page, and a route step is
        # the one kind that already knows where it is.
        elsewhere=str(where.result.get("elsewhere") or "") if where.ok else "",
        elsewhere_is_ours=bool(where.ok and where.result.get("elsewhere_is_ours")),
        signed_out=bool(where.ok and where.result.get("signed_out")),
        dialog=str(where.result.get("dialog") or "") if where.ok else "",
        loading=bool(where.ok and where.result.get("loading")),
    )


def _too_long_for(step: Step, values: Mapping[str, str], holds: int) -> list[str]:
    """Which of this step's parameters the box will not hold.

    The step says which parameters it fills and the run says what they are, so
    the name to ask about is arithmetic rather than a guess. Named rather than
    described, for the reason `run.needs` exists at all: a name parsed back out
    of an English sentence is a name that breaks the first time the sentence is
    reworded.
    """
    return [
        name
        for name in step.parameters
        if isinstance(values.get(name), str) and len(values[name]) > holds
    ]


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
    # What the box would not take, where the browser said so.
    #
    # Lengths and a flag, never the value: this is a run record and a log. The
    # browser truncates silently and BEFORE the request, so a field that stops
    # at 28 characters puts 28 into the body, the read-back returns 28, and
    # the photograph shows 28 -- every belt agreeing, because every one of them
    # compares the record to itself. This is the only fact that disagrees.
    short = reply.result.get("short")
    if isinstance(short, dict):
        shown["short"] = {
            "asked": short.get("asked"),
            "kept": short.get("kept"),
            "truncated": bool(short.get("truncated")),
        }
    if wrote:
        # The one fact the register of verified writes needs and cannot
        # recompute: SQL cannot ask `writes()`, and the evidence a later reader
        # would have to ask it about may have been re-mined by then.
        shown["wrote"] = True
    if not reply.ok:
        shown["error_kind"] = reply.error_kind
        # What was tried, and where it looked.
        #
        # `error_kind` alone says a control was not found and nothing about
        # which locators were attempted or which frames answered the probe --
        # and those are the whole diagnosis. The same step refused twice on the
        # deployment (KKYT 2026-09-20, SMK1 2026-09-21) and reading the second
        # one took five rounds of pasting into a console with the dialog held
        # open by hand, because the browser knew all of this at the time and
        # nothing kept it.
        #
        # This system's own selectors and frame ids. Not `error_detail`, which
        # carries near-miss control NAMES read off the page -- a run record has
        # no more business holding those than a prompt does, which is the rule
        # this function opens by stating.
        tried = reply.result.get("tried")
        if isinstance(tried, list):
            shown["tried"] = [str(one)[:120] for one in tried[:8]]
        claims = reply.result.get("claims")
        if isinstance(claims, list):
            shown["claims"] = [
                {
                    "frame": one.get("frame"),
                    "ok": bool(one.get("ok")),
                    "candidates": one.get("candidates"),
                }
                for one in claims[:12]
                if isinstance(one, dict)
            ]
        if "acted_in" in reply.result:
            shown["acted_in"] = reply.result["acted_in"]
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


def _not_given(workflow: Workflow, values: Mapping[str, str]) -> tuple[str, ...]:
    """The parameters this job declares that this run has no value for.

    Read off the JOB rather than off the steps: `Step.parameters` is what one
    step types, and a value typed by one step can be wanted by the body another
    sends. The job's own declaration is the whole set, in its own order.

    A blank counts as missing, for `typed_values`' reason: a parameter answered
    with an empty string is a parameter nobody answered.

    **Only the ones every doing reached.** A control two doings varied is a
    parameter and the job knows it -- but where a third doing never reached
    it, the job has a route that does not need it, and stopping a run of that
    route for want of a value nobody was going to type would make learning a
    field cost the job the ability to run without it. `in_all` is absent on
    every parameter stored before this existed, and absent reads as "yes":
    those were all learnt under the rule that required every doing.
    """
    declared = [
        str(name)
        for parameter in workflow.parameters
        if isinstance(name := parameter.get("name"), str) and name and parameter.get("in_all", True)
    ]
    return tuple(name for name in declared if not values.get(name, "").strip())


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
    shown: dict[str, object] = {
        "step": step.order,
        "planned": {"kind": planned.kind, "payload": planned.payload},
    }
    if planned.kind == "http.send":
        # The plan IS the write here, and it is not always the write the
        # demonstration made. `write_plan_for` re-aims the recorded body at
        # this run's values, so reading the recorded bytes would show a person
        # the code the operator typed on the day and have them press through
        # into a run that sends a different one. A dry run whose card cannot
        # be trusted to name what will go out is worse than no dry run.
        shown.update({key: planned.payload.get(key) for key in ("method", "url", "body")})
        return shown
    # A click, withheld because the evidence behind it writes. There is no
    # planned call to show, so the demonstration's is the only answer.
    call = recorded_call(step, by_id)
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
    watched: bool = False,
    started_by: str,
    stops: Stops,
    approvals: Approvals,
    run_id: str | None = None,
    from_step: int = 0,
    items: Sequence[Mapping[str, str]] = (),
    verified_writes: tuple[VerifiedWrite, ...] = (),
    secret_for: SecretFor | None = None,
    known_fields: KnownFields | None = None,
    gather_values: GatherValues | None = None,
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
    # Every line the rest of this run writes says which run it was, on whose
    # tenant, in whose browser. `attribute` rather than a block because the
    # work to attribute is the whole of what follows; see its own docstring for
    # why that is sound inside a task.
    attribute(
        tenant=tenant_id.value,
        device=device_id.value,
        workflow=workflow.id,
        run=run_id or "",
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
        watched=watched,
        started_at=_now(),
        # On the row, not just in this frame: it is what the check above
        # compares a re-press against, and a row that does not carry it would
        # refuse every resume as a disagreement with zero.
        from_step=from_step,
        items=[dict(item) for item in items],
    )
    values, live, allow_focus = run.values, run.live, run.allow_focus
    # And which of the two ways this run does the job, off the ROW like the
    # rest: a re-press that disagreed with the row about whether somebody is
    # watching would be a run that fills the form for one caller and posts for
    # the next.
    watched = run.watched
    device_id = DeviceId(run.device_id)
    await _save(uow, run)
    # The values nobody typed, found before anything is planned.
    #
    # A press carries what the person filled in. A job fired by a rule, or one
    # whose request arrived as a mail, has a parameter and no value -- and
    # until now that was the end of it. The live failure that named this was
    # step 1 of `Create a Customer Type` refusing with "the open email is for
    # customer type GPDP rather than the requested ZQ41": the mailbox held a
    # request and the run had no way to read it.
    #
    # Before the loop and once, not per step: a value is a fact about the run,
    # and a gather per step would read the same mailbox repeatedly and could
    # answer differently each time.
    #
    # What it finds is merged UNDER what the run was given. A person who typed
    # a value has said what they want and a mailbox does not overrule them --
    # the gather is only asked about what is missing, and this ordering says
    # the same thing a second time so the two cannot disagree.
    if gather_values is not None and (short := _not_given(workflow, values)):
        # Said on the row before it starts, because this is the one thing a run
        # does with no step to show for it -- and a card reading "Step 0" for
        # three and a half minutes while the mailbox is read is a run somebody
        # reasonably believes has hung.
        run.doing = "looking in your mail for " + ", ".join(short)
        await _save(uow, run)
        got = await gather_values(short)
        run.doing = ""
        values = {**{name: f.value for name, f in got.values.items()}, **values}
        # On the ROW and not only in this frame. `perform` re-reads the row and
        # hands its values back down, so a gather kept in a local is a gather
        # every resume does again -- against a mailbox that may answer
        # differently the second time -- and a console showing a run that typed
        # GPP into a form would show it running with no values at all.
        run.values = dict(values)
        run.gathered = {
            name: {"value": f.value, "from_message": f.from_message, "quoting": f.quoting}
            for name, f in got.values.items()
        }
        # What the mail asked for that this job cannot take.
        #
        # A job's parameters are what two doings proved VARY; the form has far
        # more fields than that. So a mail saying "code GV3, description X,
        # Department Inbound" is a perfectly reasonable request, and the run
        # makes a record with no Department in it -- silently, because `keep`
        # drops a name the job has no parameter for and said nothing about it.
        #
        # The dropping is right. The silence is the shape of every fault worth
        # having here: a request that asked for three things, a record that
        # holds two, and nothing anywhere naming the one that went missing.
        if got.unasked:
            run.unasked = list(got.unasked)
            logger.info(
                "%s: the mail also asked for %s, which this job has no parameter for",
                run.id,
                ", ".join(got.unasked),
            )
        await _save(uow, run)

        # A value nobody typed and nobody could find is not a value.
        #
        # The door lets a run start with a parameter unanswered ONLY because
        # something can go and look for it, and until this a look that came
        # back with nothing was read as permission to carry on. Measured on the
        # deployment 2026-09-16: the gather lost a round to a 5xx, came back
        # empty, and the run went on to press Save on a form somebody else had
        # half filled an hour earlier.
        #
        # Here rather than at the door, because the door cannot know what the
        # looking will find; and here rather than at the step, because the
        # answer is the same for every step and a person reading the row should
        # find one sentence rather than a verdict per step. Only on this path:
        # a deployment with no gather was refused at the door, as it always
        # was.
        if still := _not_given(workflow, values):
            run.outcome = "stopped"
            # And WHICH ones, machine-readably, beside the sentence. The
            # sentence is for the person reading the row; these are what the
            # question in their conversation is built from, one at a time, and
            # a name parsed back out of an English sentence is a name that
            # breaks the first time the sentence is reworded.
            run.needs = list(still)
            run.steps.append(
                RunStep(
                    order=0,
                    says=workflow.steps[0].says if workflow.steps else "",
                    verdict="failed",
                    verdict_by="none",
                    reason=(
                        "nobody gave a value for "
                        + ", ".join(still)
                        + ", and your mail does not say either — "
                        + got.why
                    ),
                )
            )
            await _save(uow, run)
            return run

    by_id = await _gestures_for(uow, tenant_id, workflow)
    # What earlier runs found out about this job's steps, by step order. Read
    # once: it is a handful of rows and every step of the loop would otherwise
    # ask for the same table.
    learned = {one.ord: one for one in await uow.workflows.learned_for(workflow.id)}
    # And what the operator taught it by hand since the last run failed, which
    # is a lesson nothing else in this system can learn: the ladder heals a
    # control that moved, and a step that fails the same way every time on a
    # control that never moved is repaired by the person who does it
    # themselves. See `sro.domain.execution.rescued`.
    taught = await learn_from_the_rescue(uow, tenant_id, workflow, by_id)
    if taught is not None:
        learned[taught.ord] = taught
    # Two sets, because they answer two questions. `standing` is where the
    # operator actually was and is where a plan may SEND the browser;
    # `replayable` adds the origins their page's own requests named, which is
    # what `http.send` replays a demonstrated call to.
    observed = seen_values(workflow)
    # Which body key each value this run holds is posted as, where the job
    # itself declares no parameter for it.
    #
    # A job's parameters are what two doings proved VARY, and the form posts
    # far more than that -- so a request naming one more had nowhere to put it.
    # `write_plan_for` fills the slot where the dictionary names it and the
    # record can be made to prove it landed; this is where that join is read,
    # once per run rather than once per step.
    #
    # Only the names the job does NOT declare. A parameter it does declare is
    # bound from the evidence, which is stronger than a declaration and is
    # `_assigned`'s own rule.
    placeable = await declared_keys(
        uow,
        tenant_id,
        [name for name in values if name not in set(names_of(workflow))],
        await screen_for(uow, tenant_id, workflow),
    )
    standing = stood_on(workflow, by_id)
    replayable = allowlist(workflow, by_id)
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
    # The steps that exist only to put a form on the screen, where the write
    # that form was for is going out as a call instead.
    #
    # Measured on the deployment's own row: of the six steps of `Create a
    # Customer Type`, only step 6 changes warehouse state. Steps 4 and 5 make
    # no network call at all -- they are keystrokes into a form that step 6
    # posts -- and step 2's thirty-four GETs are the screen loading. Replay the
    # write and there is nothing left for the other five to do, so doing them
    # is five plans, five commands and four screenshots spent to arrive where
    # the call was going to be sent from anyway.
    #
    # Decided here and once, because a scaffolding step comes BEFORE the write
    # it scaffolds: by the time the run reaches step 6 it has already performed
    # the five it did not need. Only the replay the EVIDENCE decides can be
    # known this early -- a model's `http.send` is chosen at the step, long
    # after step 2 has been done -- which is the second thing the deterministic
    # rung buys.
    #
    # Safe against a job whose values move per item: `write_plan_for` refuses
    # on the shape of the values, never on the values themselves (a slot is
    # claimed by comparing the DEMONSTRATED body against `seen_values`), so
    # every leg of a repeat answers this the same way.
    # Nothing is collapsed for a run somebody is watching.
    #
    # The two ways to do a job are not interchangeable and the choice is the
    # RUN's, not the step's: replaying the call is fast, deterministic and
    # invisible, and performing it is the one a person can see happen. A run
    # that skipped the typing because it was going to post, and then pressed
    # Save as if it had typed, is what deciding per step looks like.
    #
    # So a watched run performs every step: the fields fill, the button is
    # pressed, and somebody standing at the screen watches their job being
    # done. It costs a reading per step and the determinism of the replay, and
    # that is the trade being made on purpose rather than by accident.
    collapsed: set[int] = set()
    # What an unwatched run would have collapsed, held in reserve for a watched
    # one. See `_the_screen_gave_up` at the foot of the step loop: a run
    # somebody is watching performs the form-filling steps, and when the page
    # will not take one of them the job is not over -- the write those steps
    # were filling in is still a call this run knows how to make.
    in_reserve: set[int] = set()
    for leg in itinerary:
        if (
            replay_without_asking(
                step=leg.step,
                cited=[by_id[cited] for cited in leg.step.cites if cited in by_id],
                values=leg.values,
                verified_writes=verified_writes,
                seen=observed,
                keys=placeable,
            )
            is not None
        ):
            marks = scaffolding_for(workflow, by_id, write_step=leg.step.order)
            (in_reserve if run.watched else collapsed).update(marks)

    # The step that opens the mail, once the mail has been read.
    #
    # A job that starts in somebody's mailbox cites the gestures of them
    # finding that afternoon's message, so the plan clicks a link whose text is
    # that message: "a customer type :- GGD, description :- leaning new SRO
    # type 01". A job is asked for by a NEW mail every time. That link is not
    # on the screen and will not be again, and on 2026-09-16 a watched run
    # stopped at step 0 holding it -- `not_actionable: the page did not answer`
    # -- for a job whose values this same run had already read out of the right
    # mail, server-side, a second earlier.
    #
    # So it is not performed, in EITHER mode. This is not the collapse above:
    # that one is about a form whose write is going out as a call, and it is
    # off for a watched run on purpose. This is a step whose whole content was
    # done before the run began, and performing it is impossible rather than
    # merely unnecessary. A person watching wants to see the form fill; nobody
    # wants to watch their own mailbox be clicked.
    #
    # Whatever read it, and this was got wrong once.
    #
    # The first version of this rule asked whether the GATHER had read the mail
    # -- `run.gathered` -- and on 2026-09-16 at 21:11 a press failed anyway:
    # the panel's own look had already pulled the code out of the message and
    # the press carried it, so the run held every value it needed and had
    # gathered nothing. `gathered` says which of the two things read the mail,
    # and this step does not care. By the time a run exists the request has
    # been read -- by the gather, by a look, or by the person who typed the
    # values into the card -- because a run cannot start without its values.
    #
    # There is no state of this system in which opening that mail achieves
    # anything: the link the plan clicks names the message from the recording,
    # and that message will not be on the screen again.
    already_read: set[int] = {
        step.order for step in workflow.steps if only_reads_the_mail(step, by_id)
    }
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
    # Whether any command has gone out yet, which is what makes the next one
    # the run's first: `starts_on` belongs to that one alone.
    sent_nothing_yet = True

    # The page this run begins on, which is the page of the step it begins at
    # -- not the job's first page. The extension opens a tab at `starts_on`
    # when the operator's own tab is elsewhere, and aiming a run that starts at
    # step k there would abandon the progress the offer was made on.
    #
    # Not `page_of` the way `Shape.starts_on` is narrowed: that one is compared
    # and this one is NAVIGATED to, and no component of a url is particular or
    # general on its face. A warehouse addresses its screens BY fragment --
    # `…/portal?siteId=SG#wm.config/wm.config.partners.customers.types////` --
    # while Gmail puts a message id in the same place, so dropping either
    # component by rule lands a run on the portal root and plans every step
    # against the wrong page.
    #
    # So it is asked of the demonstrations instead. Every gesture this step
    # cites is a doing of it, and `screen_of` keeps what they agree on: what
    # varies between two doings of one step is the visit, and what does not is
    # the screen. No rule about queries or fragments is needed, and none is
    # right -- the evidence says which parts moved.
    #
    # With one doing it returns that url whole, which is the honest answer:
    # nothing has said which half of it was the job. It sharpens as the same
    # work is demonstrated again, with no re-mine and no new field.
    #
    # `primary_gesture` stays the anchor, so the origin and the choice of which
    # gesture speaks first are exactly what they were. What changes is that the
    # others are now allowed to disagree with it.
    #
    # Found the bug it fixes on this deployment's own row: step 2 of `Create a
    # Customer Type` is "Navigate to the Customer Types screen", and its two
    # cited gestures sit on `…inbound.receiving.optimaldoorassignment` and
    # `…warehouse.warehouse` -- the screens the operator happened to be on when
    # they reached for the menu, neither of them this step's. A run resuming
    # there opened whichever one `primary_gesture` picked. They agree on
    # `/portal?siteId=SG`, which is where that step actually starts.
    #
    # The first step the run will PERFORM, not the first one it has. A job
    # whose write goes out as a call collapses the steps that only opened the
    # form for it, and those are the ones at the front -- `Create a Customer
    # Type` collapses "Open an email" and "Navigate to the Customer Types
    # screen", so taking `starts_on` off the first step names the operator's
    # mail for a run whose only command is a warehouse call. `opensFor` in
    # `commands.js` drops a `starts_on` whose origin is not the command's, so
    # the browser is never driven into the wrong system -- but the tab is then
    # never opened either, and a run whose operator has no warehouse tab open
    # fails instead of opening one.
    def _next_after(steps: list[Step], step: Step) -> Step | None:
        """The step the job does next, by its own order."""
        later = [one for one in steps if one.order > step.order]
        return min(later, key=lambda one: one.order) if later else None

    def _screen_of(step: Step | None) -> str | None:
        """The screen this step's own demonstrations agree on."""
        anchor = primary_gesture(step, by_id) if step is not None else None
        if anchor is None or step is None:
            return None
        return screen_of(
            [
                anchor.page_url or anchor.url,
                *(
                    by_id[cited].page_url or by_id[cited].url
                    for cited in step.cites
                    if cited in by_id
                ),
            ]
        )

    # And `already_read` beside `collapsed`, for the same reason: the page this
    # run opens at is taken from the first step it will actually perform. A run
    # whose mail step is skipped would otherwise open the browser at the
    # mailbox and then send its first command to the warehouse.
    step_here = next(
        (
            one
            for one in ordered[from_step:]
            if one.order not in collapsed and one.order not in already_read
        ),
        None,
    )
    starts_on = _screen_of(step_here)

    # The step being worked on, so a browser that goes away mid-step fails THAT
    # step -- with the tokens its plan already cost, and its own order -- rather
    # than a fabricated one whose order can collide on (run_id, ord).
    in_flight: RunStep | None = None
    # A LIST walked by index rather than an iterator, because a run that meets
    # a sign-in page splices the way back in ahead of the step that met it --
    # see `_the_way_back_in`. Everything else about the walk is unchanged.
    itinerary = list(itinerary)
    signed_back_in = False
    try:
        position = -1
        while position + 1 < len(itinerary):
            position += 1
            leg = itinerary[position]
            step, values = leg.step, leg.values
            # What the steps this one NAMES have made, under their own names.
            #
            # `Step.uses` is CrewAI's `Task.context` and its argument: a step
            # that names the prior steps it depends on can be read, where an
            # implicit shared map means reading the whole job and guessing. The
            # binding is the other half of saying it.
            #
            # `step<order>.<field>`, never merged flat: a create answering
            # `{"id": ...}` and a job with a parameter called `id` would
            # otherwise silently be the same value.
            #
            # Under the run's own values, not over them: something a person
            # supplied or a mail said is what they asked for, and a job whose
            # wiring quietly replaced it would be doing something nobody could
            # see in the request.
            if step.uses:
                values = {**_what_earlier_steps_made(run, step.uses), **values}
            if not leg.rescue and step.order < from_step and leg.item in (None, 0):
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
            if not leg.rescue and (step.order in collapsed or step.order in already_read):
                # Recorded rather than dropped: the per-step audit trail is
                # what a reviewer reads, and a job that silently performed four
                # of its six steps would read as a job that lost two.
                run.steps.append(
                    RunStep(
                        order=position,
                        of_step=step.order,
                        item=leg.item,
                        says=step.says,
                        verdict="not_needed",
                        verdict_by="none",
                        reason=(
                            "this step only opened the request, which was read "
                            "before the run began; cites " + ", ".join(step.cites)
                            if step.order in already_read
                            else "this step put the form on the screen for a write "
                            "this run sends as a call; cites " + ", ".join(step.cites)
                        ),
                    )
                )
                await _save(uow, run)
                continue
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
            # Whether this job's own write is still ahead of this step.
            #
            # A click the recorder heard nothing from is a possible write --
            # a Save whose call was missed would otherwise be retried into a
            # second record. That is right for the step a job WRITES at, and
            # wrong for every step before it: opening a dropdown, pressing Add,
            # filling a field. The demonstration says which is which, because
            # it recorded the call on a later step.
            #
            # Measured on the deployment 2026-09-19, run `run_74a9a812`: the
            # operator pressed Undo, the delete started, and its first step --
            # "Opens the filter dropdown" -- failed `state unknown after a
            # write; not retried`. One dropdown click ended the run, took its
            # ladder away and suppressed the retry button, on a job whose
            # DELETE was four steps further on.
            writes_ahead = any(
                later.order > step.order and writes(later, by_id) for later in ordered
            )

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

            # A replay the evidence decides on its own, where there is one,
            # then the plan model, then the rescue model once, then -- only
            # when both missed the control by every recorded identity -- the
            # rescue model once more, by sight. A step with nothing actionable
            # cited gets none of them: it is recorded skipped and the run stops
            # below.
            #
            # First rather than instead. `replay_without_asking` covers exactly
            # the step the evidence fully determines -- a call in the ledger
            # whose body this run's values fit -- and a replay that comes back
            # refused is precisely when clicking Save is the right next move,
            # which is what the rungs behind it are.
            replay = (
                replay_without_asking(
                    step=step,
                    cited=cited,
                    values=values,
                    verified_writes=verified_writes,
                    seen=observed,
                    keys=placeable,
                    # THIS step's own screen, not the run's, and not only for
                    # the run's first command.
                    #
                    # Measured on the deployment's own row, 2026-09-16. `Create
                    # a Customer Type` step 1 is "Open an email" and carries 15
                    # writes -- Gmail's own -- so it is not scaffolding and is
                    # performed; steps 2 to 5 collapse; and the replay is the
                    # SECOND command, by which time `sent_nothing_yet` is false
                    # and the run-level `starts_on` has been spent on Gmail.
                    # The call then wants a Blue Yonder tab to read
                    # `CSRF-ENCRYPT-TOKEN` off, the browser is in the mail, and
                    # the step fails `no_tab_for_origin`.
                    #
                    # Safe where the run-level one was not, and the 2026-09-15
                    # failure says exactly why: what dragged a cross-system job
                    # back to its first system was sending every step the page
                    # the RUN began on. A step's own screen names its own
                    # system by construction, and `opensFor` refuses a
                    # `starts_on` whose origin is not the command's, so this
                    # can only ever open the page the call is going to.
                    starts_on=_screen_of(step),
                )
                if primary is not None
                else None
            )
            rungs: tuple[tuple[str, str], ...] = (
                (("evidence", plan_model), ("evidence", rescue_model), ("sight", rescue_model))
                if primary is not None
                else ()
            )
            # A step that is only arriving somewhere goes there, first and
            # without asking anybody.
            #
            # The application wrote down how to reach its screens in its own
            # urls, and the operator's visits recorded it: both demonstrations
            # of `Navigate to the Customer Types screen` carry the same route.
            # Measured across 2026-09-16 and 17, the alternative -- a model
            # shown a picture, working out that the screen is under a menu --
            # cost thirteen cents a run and landed about half the time.
            #
            # First, not instead: a route that no longer exists leaves the
            # rungs behind it to find the screen the hard way, which is what
            # they are for.
            # The step after this one in the job, which is where the evidence
            # says this one arrives: a gesture records the page it happened on,
            # never the page it led to.
            route = route_for(step, _next_after(ordered, step), by_id)
            if route is not None:
                rungs = (("route", ""), *rungs)
            # The form this write would have been typed into was never filled.
            #
            # A run whose write goes out as a CALL collapses the steps that
            # only put the form on the screen -- that is the whole point of
            # replaying it. The ladder's next rung after a failed replay is a
            # model planning from the evidence, and what the evidence says is
            # "click Save": right when the five steps before it were performed,
            # nonsense when this run skipped them on purpose.
            #
            # Measured on the deployment 2026-09-16: steps 0-4 `not_needed`
            # "this run sends as a call", then step 5 sent `ui.perform` click
            # on `toolbar button#saveButton`, against a form an operator had
            # half filled an hour earlier. The warehouse refused it for an
            # empty required field, which is the only reason it is not a wrong
            # record instead of a failed one.
            #
            # So a collapsed write has one rung. If the call will not go, the
            # step stops and says why -- and the job is still there to be run
            # again with the form filled, which is a decision for a person
            # rather than a fallback for a ladder.
            # Whether this step has already been signed in for. Per STEP, so a
            # run whose session dies twice can recover twice -- and once within
            # a step, so a wrong password cannot be spent over and over against
            # an account with a lockout policy.
            signed_in_here = False
            # And whether it has already been given a moment to finish drawing.
            waited_here = False
            never_filled = bool(
                replay is not None
                and collapsed
                and set(scaffolding_for(workflow, by_id, write_step=step.order)) & collapsed
            )
            if replay is not None and not run.watched:
                rungs = (("replay", ""),) if never_filled else (("replay", ""), *rungs)
            elif replay is not None and never_filled:
                # This run has already given up on the screen -- that is what
                # put this step's scaffolding in `collapsed` -- so the form in
                # front of the operator was never filled. Walking the screen
                # again to press its button would be pressing Save on a form
                # with nothing in it, and would spend the budget finding that
                # out. One rung: the call.
                rungs = (("replay", ""),)
            elif replay is not None:
                # Watched, and the screen would not take it.
                #
                # A watched run performs the job where somebody can see it, and
                # that is the whole of what `watched` buys. It must not also
                # mean "and if the page cannot be driven, do not do the job":
                # measured on the deployment 2026-09-16, every UI step ever
                # attempted on the warehouse host failed while the same write
                # went through as a call on the first try. The operator pressed
                # yes; a system that answers "I could not click it" while
                # holding a call it knows works is refusing for the wrong
                # reason.
                #
                # LAST, and that ordering is the decision. The screen is tried
                # first and fully -- plan from the evidence, plan again, then
                # look at a picture -- so a run somebody is watching is still a
                # run they watch whenever watching is possible. The call is
                # what happens instead of stopping.
                #
                # It cannot write twice. The step claims its write in
                # `tool_calls` before it goes out, keyed on the job, the step
                # and the values, so a click that actually landed leaves a
                # claim the replay then finds taken -- and a click that failed
                # left none. The safety here is the ledger's, not this
                # ordering's, which is why the fallback can be unconditional.
                rungs = (*rungs, ("replay", ""))
            logger.info(
                "%s step %d %r: rungs %s",
                run.id,
                step.order,
                step.says[:80],
                " then ".join(how for how, _ in rungs) or "none",
            )
            verdict: StepVerdict | None = None
            after_failed: Look | None = None
            # Commands this step has already sent and had refused.
            #
            # The rescue rung is handed `previous_attempt_failed` and exists to
            # plan something ELSE. Measured on the deployment, 2026-09-17 at
            # 17:32: `run_e1ff6362` step 3 planned `ui.perform click by
            # component,css_path`, was told `control_not_found` naming both
            # locators, and the rescue planned the same two locators again --
            # $0.0125 then $0.0453 to be refused twice in the same words,
            # before the ladder reached the rung that could have helped.
            #
            # A rule in the runner rather than a sentence in a prompt, because
            # a prompt is a request and this is arithmetic: a command this page
            # has just refused will be refused again, whatever model proposed
            # it and whatever job it belongs to.
            refused_already: set[str] = set()
            # Once per step. A session that ages out again three steps later is
            # a second question worth asking; the same step asking twice in a
            # row is a panel arguing with the person who just answered it.
            asked_for_a_browser = False
            for how, model in rungs:
                # The sight rung is for a page that moved, not for a plan that
                # was wrong: a control the browser could not find is the one
                # failure a picture can answer. Anything else stops here.
                if (
                    how == "sight"
                    and (record.result or {}).get("error_kind") != "control_not_found"
                ):
                    # `continue`, not `break`. Skipping the picture is right --
                    # it answers a control the browser could not find and
                    # nothing else -- but it must not skip what is behind it:
                    # on a watched run the rung after sight is the call, and a
                    # page that refuses to be driven at all is exactly when
                    # that call is the answer. With `break` the run stopped
                    # holding a write it knew how to make.
                    continue
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
                # same way a navigate is not the step.
                #
                # A screen is answered with as many as it takes, and that is
                # the difference between this and a rung that gives up. The
                # control for "click Customer Types" lives under a menu nobody
                # demonstrated: one click opens the menu, a fresh picture shows
                # it, the next click is the step. Measured on the deployment
                # across two days -- that job never once reached its form on
                # the screen, and the reason was a ladder that allowed exactly
                # one thing to happen before the answer.
                #
                # Bounded, because a planner that only ever opens things must
                # run out rather than loop: `K_OPENINGS` of them per rung, and
                # the step budget above still bounds the whole step.
                openings = 0
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
                    if how == "route" and route is not None:
                        # No model, no picture: the evidence says where this
                        # step ends up and the browser is told to be there.
                        before = await _where(channel, tenant_id, device_id, run.id, origin)
                        proposal = Planned(
                            "navigate",
                            {
                                "url": route,
                                "origin": origin,
                                "allow_focus": allow_focus,
                                "starts_on": route,
                            },
                            f"going to the page this step's doings agree on: {route}",
                            Answer(),
                        )
                    elif replay is not None and how == "replay":
                        # No picture: nobody is being shown one. The url is
                        # still wanted -- `before_url` is on the record -- and
                        # that is a message rather than a camera.
                        before = await _where(channel, tenant_id, device_id, run.id, origin)
                        proposal = replay
                    elif how == "sight":
                        before = await _look(
                            channel, tenant_id, device_id, run.id, origin, allow_focus
                        )
                        proposal = await plan_by_sight(
                            step=step,
                            cited=cited,
                            values=values,
                            look=before,
                            origin=origin,
                            asker=asker,
                            model=model,
                            failure=verdict.reason if verdict else None,
                            # The same guard the dropdown's two clicks use: one
                            # opening is allowed per rung, so a planner that
                            # only ever opens menus spends its budget instead
                            # of looping.
                            opened=openings > 0,
                        )
                    else:
                        before = await _look(
                            channel, tenant_id, device_id, run.id, origin, allow_focus
                        )
                        proposal = await plan_step(
                            step=step,
                            # What a previous run found when this step's own
                            # recorded identity did not match. Tried first, and
                            # the recorded ladder still underneath it.
                            learned=learned.get(step.order),
                            cited=cited,
                            values=values,
                            look=before,
                            origin=origin,
                            # Only for the first step this run performs.
                            #
                            # `starts_on` is where a tab is OPENED when the
                            # operator's own is elsewhere, and it is a fact
                            # about beginning the run -- which is what the
                            # comment where it is computed has always said.
                            # Attached to every step instead, it dragged a
                            # cross-system job back to the first system on
                            # every leg: measured 2026-09-15, step 2 of `Create
                            # a Customer Type` went out with `origin` naming the
                            # warehouse and `starts_on` naming the operator's
                            # mail, so the extension found their warehouse tab,
                            # threw it away because it was not on that page, and
                            # clicked a warehouse control in Gmail. The step
                            # failed `not_actionable: the page did not answer`.
                            #
                            # After the first, the run has a tab pinned to it
                            # and `commands.js` keeps it while it is on the
                            # step's own origin, which is the whole of what the
                            # later steps need.
                            starts_on=starts_on if sent_nothing_yet else None,
                            allow_focus=allow_focus,
                            asker=asker,
                            model=model,
                            failure=verdict.reason if verdict else None,
                            failed_look=after_failed,
                            verified_writes=verified_writes,
                            # What each declared parameter has been seen taking,
                            # which is how a value this run supplies finds its
                            # slot in a recorded body. Read off the stored job
                            # once, before the loop.
                            seen=observed,
                            keys=placeable,
                            tenant_id=tenant_id.value,
                            secret_for=secret_for,
                            opened=openings > 0,
                        )
                    # Who actually planned it. A replay asks nobody, and
                    # writing a model's name beside a step it never saw is a
                    # lie in the one field a reviewer reads to know who to
                    # blame.
                    record.planned_by = proposal.by or model
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
                    if _refused_origin(
                        proposal.kind, off, standing=standing, replayable=replayable
                    ):
                        record.verdict = "refused"
                        record.reason = (
                            f"{off} is not a system this job's evidence names"
                            if off is not None
                            else f"{proposal.payload.get('url')!r} names no system at all"
                        )
                        run.outcome = "refused"
                        break
                    if proposal.opens and openings < K_OPENINGS and not mutates:
                        # Sent from here, ahead of the gate that withholds a
                        # write and parks one on a person -- and only for a
                        # step that changes nothing, which is what makes this
                        # the same safe position `navigate` sends from.
                        #
                        # `not mutates` is said here as well as in the
                        # planners. A step whose evidence shows a write may
                        # need a menu opened to reach its button, and reaching
                        # it is not the writing -- but an opening click is a
                        # click the model chose, and the gate that parks those
                        # on a person is BELOW this line. Until that ordering
                        # is worth rearranging, a write step climbs the ladder
                        # as it always did.
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
                        openings += 1
                    elif _command_key(proposal.kind, proposal.payload) in refused_already:
                        # Already sent, already refused. `break`, not a fall
                        # through: this is inside the loop that lets a rung
                        # open a menu and ask again, and leaving `planned`
                        # unset there re-asks THIS rung rather than moving to
                        # the next one -- which buys the same answer
                        # `K_OPENINGS` times instead of twice. The rung is
                        # spent; the ladder has another.
                        proposal = Planned(
                            proposal.kind,
                            proposal.payload,
                            "the same command this step has already had refused",
                            proposal.answer,
                        )
                        break
                    elif proposal.kind != "navigate" or how == "route":
                        # A navigate is normally the way to the step and not
                        # the step -- except on this rung, where arriving IS
                        # what the step says it does.
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

                if planned is not None:
                    logger.info(
                        "%s step %d rung %s planned %s %s",
                        run.id,
                        step.order,
                        how,
                        planned.kind,
                        _said(planned.kind, planned.payload),
                    )
                elif proposal is not None:
                    # A rung that answered and was not taken. This is the half
                    # nothing recorded: the step's reason keeps the LAST rung's
                    # words, so a rung that proposed something the runner would
                    # not use left no trace at all.
                    logger.info(
                        "%s step %d rung %s proposed %s, not taken: %s",
                        run.id,
                        step.order,
                        how,
                        proposal.kind,
                        (proposal.why or "")[:120],
                    )
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
                # A step that signs back in is not a step that writes.
                #
                # `may_write` is deliberately wide -- every silent click is a
                # possible write, because a click whose demonstration showed no
                # traffic could be a Save. That rule is about the JOB's own
                # steps. A spliced sign-in click is on the login host, cannot
                # create a warehouse record, and paying the write rules for it
                # costs the run twice: the approval gate parks on it, and a
                # click that could not be confirmed ends the run with "state
                # unknown after a write; not retried".
                #
                # Measured on the deployment 2026-09-19, run `run_d6e7a78`:
                # the SSO button click ended the run that way, and the result
                # card then offered no "Try it again" either -- because a run
                # whose write may have landed must not be pressed twice.
                pressing = planned.payload.get("action") in ("click", "press")
                may_write = (not leg.rescue) and (
                    mutates
                    # A click at a point the MODEL chose is a click on whatever
                    # is there now, on a page that has already moved under the
                    # job: what the demonstrated control's traffic showed says
                    # nothing about it. Every sight click is a possible write,
                    # whatever the job does later.
                    or (pressing and planned.kind == "ui.perform_at")
                    # A click the recorder heard nothing from is a possible
                    # write too -- unless this job's own write is still ahead
                    # of it. Then the demonstration says what this step is:
                    # scaffolding, opening a dropdown or a form, on the way to
                    # a call it recorded somewhere later.
                    or (
                        pressing
                        and planned.kind == "ui.perform"
                        and _saw_nothing(step, by_id)
                        and not writes_ahead
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

                # What is already known about the fields this write fills,
                # asked once, for every write that is about to go out.
                #
                # Not inside the approval branch below, and the difference is
                # the point: a job that has EARNED the right to write unasked
                # is exactly the one nobody is watching, and the note belongs
                # in its audit too. The dictionary is the vendor's own
                # documentation and the question it answers is "will this value
                # fit" -- the sharpest instance of the one failure the ladder
                # cannot see, because a column that keeps four characters of
                # six still answers 201 and the read-back shows the record the
                # system actually made.
                #
                # A note and never a refusal: see `field_notes`. The two
                # sources disagree by construction -- the dictionary says
                # `customerType` holds 60, the ledger's own gotcha says
                # `csttyp truncates at 4 chars` -- and refusing on the
                # documented one would stop correct runs against a system that
                # behaves differently from its manual.
                if known_fields is not None and planned.filled:
                    writing = {
                        slot: values[name]
                        for slot, name in planned.filled.items()
                        if name in values
                    }
                    # The screen as well as the keys. A body key does not name
                    # a form -- `customerType` is posted by both Customer Types
                    # and Existing Customers on this deployment -- so a lookup
                    # by key alone would lend one screen's required fields to
                    # another screen's write.
                    record.notes = list(
                        notes_on(
                            writing,
                            await known_fields(
                                tuple(sorted(writing)), _screen_of(step) or origin or ""
                            ),
                        )
                    )

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
                # A step this same job would SKIP is not a write to ask about.
                #
                # `may_write` is deliberately wide: a click whose demonstration
                # showed no traffic might be a write, so it asks. But a step in
                # the reserve is one an unwatched run of this very job does not
                # perform at all -- it is scaffolding for a write that is in
                # the ledger, and the ledger's write is the Save at the end of
                # it. Asking a person to approve doing what the same job would
                # otherwise not do is incoherent, and it cost three approval
                # windows on 2026-09-17: every watched run parked on "Click the
                # Add button", which opens a form.
                #
                # The write itself still asks. `in_reserve` never holds the
                # step that carries the call -- `scaffolding_for` returns what
                # comes BEFORE it -- so this narrows the question to the one
                # step that changes the warehouse.
                opening_the_form = not leg.rescue and step.order in in_reserve
                if (
                    live
                    and may_write
                    and not approved_here
                    and not opening_the_form
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

                # The row stops saying it is waiting on a person, before the
                # command goes out rather than after it comes back.
                #
                # `awaiting` is what the panel draws the Approve button from.
                # Left standing through the send it is a row that lies for as
                # long as the step takes -- the call, the read-back, and on the
                # ladder's third rung a screenshot and a vision call -- so an
                # operator taps Approve, the tap is recorded, the wait really
                # is released, and the panel redraws the same paused row with
                # the same button. Reported as "I clicked approve and nothing
                # happened" on the live deployment, 2026-09-16, against a run
                # whose approval had in fact landed every time (`resumed:
                # true`, three taps).
                #
                # Back to `skipped`, which is what an in-flight step already
                # says: it is this record's starting value, the panel draws it
                # `○`, and the real verdict overwrites it a few lines below.
                # Not a new word for "sending" -- the vocabulary is closed and
                # a state that exists only between two statements of the same
                # function is not a disposition anybody needs to read about.
                if record.verdict == "awaiting":
                    record.verdict, record.verdict_by = "skipped", "none"
                    record.reason = "approved; sending the write"
                    await _save(uow, run)
                # `before` and `planned` are set by the same pass of the while
                # above: a command to send is a command something was looked at
                # before planning.
                assert before is not None  # noqa: S101 -- see the comment above
                # The moment the command went out, so the calls the page makes
                # because of it can be told from the ones it was already
                # making. Taken here and not after the reply: a form submit
                # posts before the click's own answer comes back.
                # A box already known not to take this does not get filled.
                #
                # The limit was learnt by a run that found it the hard way: it
                # typed, the browser silently kept a prefix, and the run
                # stopped. Knowing that and typing anyway would half-fill a
                # form in front of somebody to reach the same conclusion --
                # which is the difference between a system that learns and one
                # that repeats, and the whole point of writing the limit down.
                #
                # Checked here rather than at the door, because the value for
                # a step is not known until it is planned: a run may supply it,
                # a mailbox may, and a body may carry it.
                holds = (learned.get(step.order) or LearnedStep(step.order, "", "", "")).holds
                asked_for = planned.payload.get("value")
                if holds is not None and isinstance(asked_for, str) and len(asked_for) > holds:
                    # Asked about, not merely refused. The same road a value
                    # nobody could find takes: the names go on the row, and the
                    # conversation turns them into a question somebody answers
                    # -- and the run starts again on the yes they already gave.
                    # A run that stops dead here is an operator who pressed
                    # once and got a dead card, which is the thing
                    # `_ask_for_values` was built to end.
                    run.needs = _too_long_for(step, values, holds)
                    verdict = StepVerdict(
                        "failed",
                        "read",
                        f"this field holds {holds} characters and was given "
                        f"{len(asked_for)}, so the record would not say what was "
                        "asked for",
                    )
                    record.verdict, record.verdict_by = verdict.state, verdict.by
                    record.reason = verdict.reason
                    logger.info("%s step %d %s", run.id, step.order, verdict.reason)
                    await _save(uow, run)
                    break
                sent_at = datetime.now(tz=UTC).timestamp()
                reply = await channel.send(
                    tenant_id, device_id, kind=planned.kind, run_id=run.id, payload=planned.payload
                )
                # Whatever came back, a command has now gone out and a tab is
                # pinned to this run: `starts_on` has done its one job and the
                # next step is driven by its own origin.
                sent_nothing_yet = False
                record.result = _result(reply, wrote=may_write)
                # A field that would not take what it was given stops the run,
                # here, before the Save.
                #
                # The browser truncates silently and BEFORE the request. On
                # this deployment `Warehouse.Description` stops at about 28
                # characters with no error and no warning -- so 28 characters
                # go into the body, 28 come back from the read, and 28 are in
                # the photograph. Every belt this run has agrees, because every
                # one of them compares the record to ITSELF, and the record it
                # makes is not the record the request asked for.
                #
                # Stopped rather than noted, and this is the one place in the
                # ladder that judges a step the page performed perfectly well.
                # The rule is the same one the blank-value gate is built on: a
                # write with the wrong thing in it is a wrong record, and a
                # warehouse record cannot be un-created. Somebody shortening
                # the description themselves is a minute; a wrong record in a
                # warehouse is not.
                #
                # Only a truncation. A field that trimmed a space or fixed a
                # case changed what was asked for and did not LOSE any of it,
                # and stopping for that would stop correct runs on a hundred
                # ordinary forms.
                cut = record.result.get("short")
                if isinstance(cut, dict) and cut.get("truncated"):
                    # Learnt, not merely reported. A limit found once and
                    # forgotten is this job discovering the same fact every
                    # run -- which is what `learned_step.py` calls repeating
                    # rather than learning, and it says what that cost when
                    # the fact was a locator.
                    kept = cut.get("kept")
                    if isinstance(kept, int):
                        await uow.workflows.remember_limit(
                            workflow.id, step.order, kept, by_run=run.id
                        )
                        run.needs = _too_long_for(step, values, kept)
                    verdict = StepVerdict(
                        "failed",
                        "read",
                        f"the field kept {cut.get('kept')} of the "
                        f"{cut.get('asked')} characters it was given, so the record "
                        "would not say what was asked for",
                    )
                    record.verdict, record.verdict_by = verdict.state, verdict.by
                    record.reason = verdict.reason
                    logger.info("%s step %d %s", run.id, step.order, verdict.reason)
                    await _save(uow, run)
                    break
                if not reply.ok:
                    refused_already.add(_command_key(planned.kind, planned.payload))
                logger.info(
                    "%s step %d sent %s -> %s",
                    run.id,
                    step.order,
                    planned.kind,
                    f"ok matched_by={reply.result.get('matched_by')}"
                    if reply.ok
                    else f"FAILED {reply.detail[:120]}",
                )
                # The browser is not where this step needs it, and that is a
                # question for a person rather than a verdict about the job.
                #
                # Measured on the live deployment 2026-09-16: a run failed
                # `no_tab_for_system` because the operator's Blue Yonder
                # session had expired. The job was right, the plan was right,
                # the values were right, and the run died on a sentence naming
                # a tab. The system signs people out on its own schedule and
                # takes the tab to an identity provider when it does, which is
                # `no_tab_for_origin` -- the same thing with the page still
                # open.
                #
                # So the panel asks, in the one place the operator is already
                # watching, and the same command goes again when they say they
                # are back. Live only: an unattended dry run has nobody to ask,
                # and parking one for half an hour is a hang rather than a
                # question.
                #
                # The claim is not given back before the second send. The
                # release below reads the FINAL reply, which is what decides
                # whether anything left the browser.
                # There WAS a rule here that read this as "already signed in",
                # and it was wrong. It said: a job that does nothing but sign
                # in, a step that cannot find its tab, and an earlier step that
                # held -- so the page went away because the sign-in completed.
                #
                # On a job that IS the sign-in, an earlier step holding means
                # the LOGIN FORM was being filled. It is the strongest evidence
                # in the run that nobody is signed in yet, and it was read as
                # the opposite. Measured on the deployment 2026-09-20, run
                # `run_28f14216`: step 0 typed `RKUCHIYAGM` into the Keycloak
                # username box and held, step 1 was skipped as "already signed
                # in", the run ended `held` -- and the operator was sitting in
                # front of that same form with the password box empty and
                # nothing on screen asking them for anything.
                #
                # What it was built for -- `run_83efedf5` -- has the same shape
                # and a different cause: the browser lost the tab it had pinned
                # when this worker was evicted between two commands, which
                # `commands.js` now carries through storage. A failure read as
                # a success is how a fault gets a coat of paint instead of a
                # fix, and this one painted over the password card: a skipped
                # step asks for nothing.
                #
                # So the question is not what held. It is WHERE THE BROWSER
                # IS, which is a thing this can go and ask.
                #
                # A sign-in page that is gone because the sign-in worked leaves
                # the browser somewhere else and not asking anybody to sign in.
                # A sign-in page that is gone because this run lost its tab
                # leaves the browser on that page still, with the form in front
                # of the operator. Those are two different answers to `ui.url`
                # and they were one answer to this.
                #
                # Measured on the deployment 2026-09-20, both halves:
                #
                #   run_28f14216  step 0 typed the username and held; the
                #                 operator was looking at the Keycloak form
                #                 with the password box empty. `signed_out`.
                #                 -> ask, which is what this now does.
                #   run_1dd7e8..  step 0 typed the username, the sign-in went
                #                 through, and the browser was in the WMS
                #                 portal saying "Hello Rudy". Step 1 failed
                #                 `no_tab_for_system` on a page that no longer
                #                 exists because the job had SUCCEEDED, and the
                #                 card said "The run stopped".
                #                 -> nothing left to do, which is this.
                #
                # `elsewhere_is_ours`, so the page read is the tab this run
                # pinned and not whatever window happened to be in front. And
                # only for a job that does nothing BUT sign in: a bigger job
                # whose sign-in completed has the rest of itself to do, and
                # ending its run here would be this same mistake wearing the
                # other coat.
                if not reply.ok and reply.error_kind in K_NOT_HERE and is_a_way_in(workflow, by_id):
                    went = await _where(channel, tenant_id, device_id, run.id, origin)
                    if went.elsewhere_is_ours and not went.signed_out:
                        record.verdict, record.verdict_by = "skipped", "none"
                        record.reason = (
                            f"the page this signs in at is gone and the browser is on"
                            f" {went.elsewhere} -- signed in"
                        )
                        run.outcome = "held"
                        await _save(uow, run)
                        return run
                # Otherwise a sign-in that cannot find its page asks. The
                # operator can see the screen and this cannot.
                if (
                    live
                    and not asked_for_a_browser
                    and not reply.ok
                    and reply.error_kind in K_NOT_HERE
                ):
                    asked_for_a_browser = True
                    if not await _let_in(
                        uow,
                        run,
                        record,
                        where=origin or _screen_of(step) or "the system",
                        approvals=approvals,
                        stops=stops,
                    ):
                        verdict = StepVerdict("failed", "none", record.reason)
                        break
                    sent_at = datetime.now(tz=UTC).timestamp()
                    reply = await channel.send(
                        tenant_id,
                        device_id,
                        kind=planned.kind,
                        run_id=run.id,
                        payload=planned.payload,
                    )
                    record.result = _result(reply, wrote=may_write)
                # A write whose command never left the browser gives its claim
                # back. Kept for everything else, including a timeout: see
                # `K_NEVER_SENT`.
                if key and not reply.ok and reply.error_kind in K_NEVER_SENT:
                    async with uow:
                        await uow.tool_calls.forget(tenant_id, key)
                        await uow.commit()
                    claimed_here.discard(key)
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
                # Never for a replay, and for two separate reasons.
                #
                # It cannot work: the extension sends an `http.send` through the
                # page's own `fetch` in the ISOLATED world specifically so the
                # replay does NOT re-enter the evidence plane as the operator's
                # own action, so `calls.since` can never see it. The round trip
                # is spent to be told nothing.
                #
                # And it must not work. This rung settles a step by STATUS, and
                # `settled or await verify(...)` means a verdict here is a
                # verdict instead of the ladder -- so a call the page happened
                # to make to the same endpoint shape would hold the step on its
                # status and skip the read-back that `rewrote` exists to reach.
                # The one belt that can tell a truncated record from the record
                # this run asked for would be bypassed by a coincidence.
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
                    if reply.ok and planned.kind != "http.send"
                    else None
                )
                # Where the status settled it, the url is still wanted -- the
                # record says where the step left the browser -- and that is a
                # question the browser answers without a camera.
                #
                # And for a replay, where there was never a picture to take. An
                # `http.send` is a `fetch`: no click, no navigation, no repaint,
                # so the "after" screen IS the before screen and the screen rung
                # would ask a model whether an unchanged page proves a record
                # was created. That is not a weak answer, it is a meaningless
                # one -- and it can come back `held`. Without a picture the
                # rung refuses instead: a step that writes cannot reach the
                # "changes nothing" hold, so an odd status ends `unclear` and
                # stops the run, which is the honest end for a write nothing
                # could confirm.
                after = (
                    await _where(channel, tenant_id, device_id, run.id, origin)
                    if settled is not None or planned.kind == "http.send"
                    else await _look(channel, tenant_id, device_id, run.id, origin, allow_focus)
                )
                record.after_url = after.url
                # Kept for the rescue: if this attempt does not hold, the next
                # rung is shown the page it left behind beside the page as it
                # is when it plans.
                after_failed = after
                # A step that was only arriving is judged by where the
                # browser is, which is a fact this side can read: no status to
                # weigh, no picture to interpret, and nothing for a model to be
                # confident about. `page_of` drops the query and the fragment's
                # particulars, so the same screen reached twice compares equal.
                arrived = (
                    StepVerdict(
                        "held" if same_screen(after.url, route) else "failed",
                        "read",
                        (
                            f"the browser is on {after.url}"
                            if same_screen(after.url, route)
                            # `elsewhere` where the browser is not on this
                            # system at all: without it this said "the browser
                            # is on None", which is the sentence a person read
                            # on the deployment while looking at a sign-in
                            # page.
                            else f"the browser is on {after.url}, not {route}"
                        ),
                    )
                    if how == "route" and route is not None
                    else None
                )
                verdict = (
                    arrived
                    or settled
                    or await verify(
                        step=step,
                        sent_kind=planned.kind,
                        rewrote=planned.rewrote,
                        confirm=planned.confirm,
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
                        # What this screen has to be good enough for. A step
                        # that changes nothing is judged on whether the job can
                        # go on, and the next leg is what going on means.
                        next_says=(
                            itinerary[position + 1].step.says
                            if position + 1 < len(itinerary)
                            else None
                        ),
                    )
                )
                # A step that failed in front of a login page failed for one
                # reason, and it is not the one it was about to report.
                #
                # `control_not_found: no control matched` is true and says
                # nothing: somebody reading it goes looking for a broken
                # selector. Measured on the deployment 2026-09-18 -- a session
                # expired, the operator spent minutes signing back in, and
                # every run in between blamed a missing tab item. The page in
                # front of it was a login form the whole time.
                #
                # The verdict stands; what changes is what it SAYS. A run that
                # renamed the failure would be a run deciding it knows why the
                # step failed, and what this knows is only what is on screen.
                # Asked only of a step that failed, and only once: a round
                # trip per failure is cheap, and one per step is not.
                refused = (
                    await _refused_by_the_system(
                        channel=channel,
                        tenant_id=tenant_id,
                        device_id=device_id,
                        run_id=run.id,
                        since=sent_at,
                    )
                    if verdict.state == "failed"
                    else ""
                )
                verdict = _said_what_is_there(verdict, after, route, refused)
                # And where nothing is stored to sign in WITH, the refusal
                # carries the key, so the panel can ask for it.
                #
                # The box already exists: a step that types a password and
                # finds the vault empty refuses with `needs_secret`, and the
                # run card draws "this job needs your password for <system>"
                # and a field. What never reached it is this case -- a job
                # mined from an already-signed-in session has no login step at
                # all, so nothing ever asked, and the operator was left with a
                # run that stopped and a sentence about a session.
                #
                # Same key either way. `secret_key_of` and `secret_key_for`
                # normalise the field identically for exactly this reason: the
                # side asking and the side storing have to spell it the same or
                # the value is invisible to the one thing that needs it.
                # A page that had not finished arriving gets a moment, and the
                # same rung again.
                #
                # This is the one of the screen's answers a run can DO
                # something about rather than only report. A step that failed
                # against a half-drawn screen otherwise spends the rest of its
                # ladder on it -- a model call about a page that was not there
                # yet, then a sight rung photographing a spinner -- and reports
                # a missing control that appeared a second after it gave up.
                #
                # Once per step, like the sign-in. A screen that is still
                # coming after one wait is a screen that is stuck, and a run
                # that waited again would turn a fault into a hang.
                if verdict.state == "failed" and after.loading and not waited_here:
                    waited_here = True
                    logger.info(
                        "%s step %d: the page had not finished; waiting %.1fs and trying again",
                        run.id,
                        step.order,
                        K_STILL_COMING_S,
                    )
                    await asyncio.sleep(K_STILL_COMING_S)
                    continue
                if verdict.state == "failed" and after.signed_out:
                    # Sign in and try the step again, where there IS something
                    # to sign in with.
                    #
                    # `KeepSessionsOpen` has done this for years against a
                    # hosted browser, and the runs that matter drive the
                    # operator's own Chrome, which nothing could sign in. So a
                    # session that died mid-shift left a stopped run and a
                    # person whose only way on was to do the whole job by hand.
                    #
                    # Once per step and no more. A login that did not take is a
                    # wrong password or a second factor, and a run that tried
                    # again would spend an account's lockout budget on a
                    # credential that is not going to start working.
                    # The page the browser is ACTUALLY in front of, and only
                    # then the one the recording named.
                    #
                    # A credential belongs to the system whose box it is typed
                    # into. `after.url` is empty whenever the step's own origin
                    # is not where the tab got to -- which is every sign-in
                    # that bounced -- so this used to fall back to the
                    # RECORDING's origin and ask for that system's password
                    # while the operator looked at another system's form.
                    #
                    # Measured on the deployment 2026-09-20, run
                    # `run_b949148d`: `Log in using Azure B2C SSO` is mined
                    # entirely on `blueyonderalphaus.b2clogin.com`, the live
                    # sign-in bounced to Keycloak, and the b2clogin password
                    # went into the Keycloak form. The page said *Invalid
                    # username or password*. A credential in the wrong
                    # system's box is worse than a step that fails: it spends
                    # an account's lockout budget, and it is the operator's
                    # account.
                    #
                    # `elsewhere_is_ours` and not `elsewhere`: the browser
                    # answers with the tab in front when this run pinned none,
                    # and "your password for <whatever window was open>" is a
                    # credential prompt for a system nobody named.
                    here = after.url or (after.elsewhere if after.elsewhere_is_ours else "")
                    # And a credential goes out only where this run can say
                    # which page it is for. `sign_in` fills the run's own tab
                    # WHEREVER it has got to -- it has to, a sign-in page is on
                    # another host by design -- so the origin in the command is
                    # not a guard on where the typing lands. This is: with no
                    # reading of where the browser is, the honest answer is to
                    # ask rather than to send somebody's password somewhere
                    # nothing looked at.
                    if (
                        here
                        and not signed_in_here
                        and await _sign_in_here(
                            channel=channel,
                            tenant_id=tenant_id,
                            device_id=device_id,
                            run_id=run.id,
                            origin=origin,
                            where=here,
                            secret_for=secret_for,
                            record=record,
                        )
                    ):
                        signed_in_here = True
                        continue
                    record.sent = await _ask_for_the_password(
                        record.sent, here or origin or "", tenant_id, secret_for
                    )
                _bill(record, verdict.answer)
                record.verdict, record.verdict_by = verdict.state, verdict.by
                record.reason = verdict.reason
                logger.info(
                    "%s step %d %s by %s (%s): %s",
                    run.id,
                    step.order,
                    verdict.state,
                    verdict.by,
                    f"${record.cost_usd:.4f}",
                    (verdict.reason or "")[:160],
                )
                if verdict.made:
                    # What the warehouse called the record this step made. On
                    # the row because it is the only place it exists: the panel
                    # says which records a run created, and an undo -- the day
                    # the evidence for one exists -- addresses them by it.
                    record.made = dict(verdict.made)
                if verdict.called:
                    # On the RESULT, where `_remember_the_write` looks, and on
                    # its OWN condition: `made` is the fields that name the
                    # record and a create whose answer carries none leaves it
                    # empty, which has nothing to do with whether a call was
                    # watched. Nested under `made`, this stored nothing for
                    # exactly the writes it exists to learn from.
                    record.result = {**(record.result or {}), "called": dict(verdict.called)}
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
                        # And WHAT it found, which is the half that was
                        # missing. Marking the step stale says it is about to
                        # break; this says what worked instead, so the next
                        # run tries that first rather than climbing the same
                        # ladder and paying for the same model call to reach
                        # the same control.
                        # The REPLY, not the record: `_result` keeps the three
                        # facts a row needs and the control the browser named
                        # is not one of them -- it is for the job, not for the
                        # audit of this run.
                        found = learned_from(
                            step.order,
                            "sight" if planned.kind == "ui.perform_at" else record.matched_by,
                            reply.result,
                        )
                        if found is not None:
                            await uow.workflows.remember_locator(workflow.id, found, by_run=run.id)
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

            # Said once the rungs are spent, because it explains what was NOT
            # tried: the interface. A person reading "the call would not go"
            # would otherwise reasonably ask why it did not just press the
            # button, and the answer is that this run never filled the form.
            if never_filled and record.verdict not in ("held", "withheld", "awaiting"):
                record.reason = (
                    record.reason
                    + " — and the form was never filled for this run, so the button was not"
                    " pressed either; run it again to have it typed in front of you"
                ).strip()

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
            # **A step the page TOOK is not a step the page refused.**
            #
            # The collapse below exists for one premise -- "the page would not
            # take this step" -- and when the browser answered `ok` that
            # premise is false. run_7ebafa8f, the deployment, 2026-09-17 at
            # 22:17: step 3 typed `GS7` into Customer Type and the browser said
            # `ok: true, matched_by: component`. It came back `unclear` only
            # because there was no screen to confirm it against, the reserve
            # collapsed it as a refusal, and the card told the operator "the
            # form was never filled for this run" over a form holding GS7.
            #
            # That is the worst of both: a half-filled form left in front of
            # somebody who might press Save on it, and the same write going out
            # as a call beside it. So a step the page took stops the run
            # instead, with the form as it is and a reason that matches it --
            # which is a decision for a person, and the reserve is for the case
            # where the page did nothing.
            took_it = bool(isinstance(record.result, dict) and record.result.get("ok"))
            in_the_reserve = (
                not leg.rescue
                and record.verdict not in ("held", "withheld")
                and step.order in in_reserve
            )
            if in_the_reserve and not took_it:
                # Only a step the BROWSER would not do reaches here, and that
                # is by construction rather than by a check: a step in the
                # reserve is never parked on a person (see the approval gate),
                # and a wait nobody answers ends the run before this. A
                # timeout read as "the page refused" would collapse the job
                # and walk past the thing somebody was being asked about,
                # which is what happened on 2026-09-17 while both were true.
                # The screen would not take it, and the job is not over.
                #
                # A watched run performs the steps that put the form on the
                # screen, and this is one of them. Measured on the deployment,
                # 2026-09-17 at 10:40: the run stopped on "Navigate to the
                # Customer Types screen" -- a step with no call of its own --
                # while the write it was on its way to was a call this run knew
                # how to make, three steps later and never reached. The
                # fallback built for the write step could not help, because a
                # run stops at its first failed step.
                #
                # So the run gives up on the SCREEN rather than on the job: the
                # steps that were only ever scaffolding for the write are
                # collapsed, exactly as an unwatched run would have had them
                # from the start, and the write goes out as a call. Once --
                # `in_reserve` is emptied -- so a job that fails again fails.
                logger.info(
                    "%s step %d collapsing the reserve %s: %s",
                    run.id,
                    step.order,
                    sorted(in_reserve),
                    record.reason[:120],
                )
                record.verdict, record.verdict_by = "not_needed", "none"
                record.reason = (
                    "the page would not take this step, so the form is not being "
                    "filled and the write it was for is going out as a call: " + record.reason
                )
                collapsed |= in_reserve
                in_reserve = set()
                await _save(uow, run)
                continue
            if record.verdict not in ("held", "withheld"):
                # A session that went is not a job that failed.
                #
                # The browser is at a sign-in page, the tenant has shown how to
                # get through it, and the steps for that go in ahead of the one
                # that met it -- so the run signs itself back in and tries
                # again, through the same ladder as everything else.
                #
                # Once per run, and never twice: a second sign-in page after
                # signing in is a system this run cannot get into, and a loop
                # that kept trying would spend a budget it cannot see the end
                # of on somebody's credentials.
                _signing_in, back = (
                    (None, [])
                    if signed_back_in
                    else await _the_way_back_in(
                        uow, tenant_id, workflow, after_failed, values, by_id
                    )
                )
                if signed_back_in and after_failed is not None and after_failed.signed_out:
                    # Signed in once and the system is still asking. That is
                    # not a session that went, it is one this run cannot get
                    # into -- wrong credential, a second factor, an account
                    # locked -- and trying again would spend somebody's
                    # attempts on it.
                    record.reason = (
                        record.reason
                        + " — the run signed back in and this system is still asking, so a"
                        " person has to sign in here"
                    ).strip()
                if back and _signing_in is not None:
                    signed_back_in = True
                    # Where those steps may act: the sign-in job's OWN
                    # evidence, and nothing wider. The run's allowlist is built
                    # from the job being run, so without this the spliced steps
                    # are refused for reaching a host this job never stood on
                    # -- which is the right rule for the job and the wrong one
                    # for the page it has been bounced to.
                    standing = standing | stood_on(_signing_in, by_id)
                    replayable = replayable | allowlist(_signing_in, by_id)
                    itinerary[position + 1 : position + 1] = [*back, leg]
                    # The rescue's own steps, and the retry. Without this the
                    # budget below ends the run part way through signing in.
                    budget += len(back) + 1
                    record.verdict, record.verdict_by = "not_needed", "none"
                    record.reason = (
                        "this system's session had gone, so the run is signing back in "
                        "and trying this step again: " + record.reason
                    )
                    await _save(uow, run)
                    continue
                run.outcome = "stopped"
                break
        else:
            # Every step skipped is not a job done.
            #
            # A run whose steps were all `not_needed` performed nothing, sent
            # nothing and made nothing, and until this it reported `held` --
            # measured on the deployment 2026-09-17 at 03:59, where a job made
            # entirely of steps in a mailbox had all five skipped and said it
            # had worked. A run that claims the job is done and did not do it
            # is worse than one that fails, because nobody goes looking.
            #
            # `not_needed` and not the rest: `withheld` is a dry run, which
            # deliberately does nothing and says so in its own word, and a run
            # with no steps at all never reaches here.
            if run.steps and all(one.verdict == "not_needed" for one in run.steps):
                run.outcome = "stopped"
                run.steps[-1].reason = (
                    "every step of this job was skipped, so nothing was done — "
                    + run.steps[-1].reason
                ).strip()
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
