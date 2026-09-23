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
from urllib.parse import urlparse, urlsplit

from sro.application.execution.approvals import K_APPROVAL_WAIT_S, Approvals
from sro.application.execution.declared import declared_keys, names_of, screen_for
from sro.application.execution.effects import earned, forget_effects, record_effect
from sro.application.execution.learn_from_rescue import learn_from_the_rescue
from sro.application.execution.mail_job import MailHand
from sro.application.execution.plan_step import (
    SecretFor,
    plan_by_sight,
    plan_step,
    replay_without_asking,
)
from sro.application.execution.stops import Stops
from sro.application.execution.verify import (
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
    PUTS_A_VALUE,
    READ_METHODS,
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
from sro.domain.execution.mail_job import MAILBOXES, on_the_mailbox, sends_mail
from sro.domain.execution.planning import Look, Planned
from sro.domain.execution.secrets import secret_key_of, without_secrets
from sro.domain.execution.verified_writes import VerifiedWrite
from sro.domain.execution.waiting import read_wait
from sro.domain.execution.workflow_run import RunStep, WorkflowRun, new_run_id
from sro.domain.execution.write_plan import (
    demonstrated_writes,
    scaffolding_for,
    seen_values,
    write_plan_for,
)
from sro.domain.observation.gesture import Gesture
from sro.domain.observation.trim import path_shape
from sro.domain.shared.hosts import (
    origin_of as origin_of_url,
)
from sro.domain.shared.hosts import same_screen, screen_of, system_of
from sro.domain.shared.identifiers import DeviceId, TenantId
from sro.domain.shared.prices import Answer
from sro.domain.skill.learned import demanded
from sro.domain.skill.repeats import K_MOST_ITEMS, Repeat
from sro.domain.skill.signing_in import is_a_way_in, is_sign_in_page, signs_in_at
from sro.domain.skill.workflow import Step, Workflow
from sro.whose import attribute

KnownFields = Callable[[tuple[str, ...], str], Awaitable[Mapping[str, Mapping[str, object]]]]

K_SAME_WRITE_WINDOW = timedelta(minutes=30)


def write_key(workflow_id: str, step: Step, values: Mapping[str, str]) -> str:
    said = json.dumps(dict(sorted(values.items())), separators=(",", ":"))
    return f"{workflow_id}:{step.order}:{hashlib.sha256(said.encode()).hexdigest()[:16]}"


K_CAP_EVERY = 10

K_STEP_SLACK = 3

K_STILL_COMING_S = 2.0

GatherValues = Callable[[Sequence[str]], Awaitable[Gathered]]

K_OPENINGS = 3

K_LOOKS = 4

K_NOT_HERE = frozenset({"no_tab_for_system", "no_tab_for_origin"})

K_MIGHT_BE_BEHIND = K_NOT_HERE | frozenset({"control_not_found"})

K_NEVER_SENT = K_NOT_HERE | frozenset({"focus_not_permitted", "aborted"})

K_LEAVES = ("http.send", "navigate")


@dataclass(frozen=True, slots=True)
class _Leg:
    step: Step
    values: Mapping[str, str]
    item: int | None = None

    rescue: bool = False


def _itinerary(
    ordered: Sequence[Step],
    repeat: Repeat | None,
    values: Mapping[str, str],
    items: Sequence[Mapping[str, str]],
) -> list[_Leg]:
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
    if look is None or not (look.signed_out or look.elsewhere):
        return None, []
    where = look.elsewhere or look.url or ""
    known = await uow.workflows.known(tenant_id)
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
    if planned.kind in K_LEAVES:
        return system_of(str(planned.payload.get("url")))
    origin = planned.payload.get("origin")
    return origin if isinstance(origin, str) else None


def _refused_origin(
    kind: str, off: str | None, *, standing: AbstractSet[str], replayable: AbstractSet[str]
) -> bool:
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
    record.verdict, record.verdict_by = "awaiting", "none"
    record.reason = f"the browser is not on {where} — open it and sign in, then approve to carry on"
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
    record.verdict, record.verdict_by = "skipped", "none"
    record.reason = "signed in; sending again"
    await _save(uow, run)
    return True


logger = logging.getLogger(__name__)

K_ACTS = {
    "ui.perform": ("action", "value", "locators"),
    "ui.perform_at": ("action", "value", "x", "y"),
    "http.send": ("method", "url", "body"),
    "navigate": ("url",),
}


def _command_key(kind: str, payload: Mapping[str, object]) -> str:
    acts = K_ACTS.get(kind)
    if acts is None:
        return f"{kind} {json.dumps(payload, sort_keys=True, default=str)}"
    return f"{kind} " + json.dumps(
        {part: payload.get(part) for part in acts}, sort_keys=True, default=str
    )


K_SAID = 120


def _said(kind: str, payload: Mapping[str, object]) -> str:
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
    made: dict[str, str] = {}
    for order in uses:
        for record in run.steps:
            if record.of_step != order or not record.made:
                continue
            made.update({f"step{order}.{name}": value for name, value in record.made.items()})
    return made


async def _a_write_went_out(
    *,
    channel: Channel,
    tenant_id: TenantId,
    device_id: DeviceId,
    run_id: str,
    origin: str | None,
) -> str:
    got = await channel.send(
        tenant_id, device_id, kind="calls.since", run_id=run_id, payload={"since": 0}
    )
    if not got.ok:
        return "a move whose traffic the browser could not report"
    made = got.result.get("calls") if isinstance(got.result, dict) else None
    for call in made if isinstance(made, list) else []:
        if not isinstance(call, dict):
            continue
        method = str(call.get("method", "")).upper()
        url = str(call.get("url", ""))
        if method in READ_METHODS or (origin is not None and system_of(url) != origin):
            continue
        return f"{method} {path_shape(url)}"
    return ""


async def _refused_by_the_system(
    *,
    channel: Channel,
    tenant_id: TenantId,
    device_id: DeviceId,
    run_id: str,
    since: float,
) -> str:
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
    if refused:
        return replace(verdict, reason=f"{refused} ({verdict.reason})")
    if look.dialog.strip():
        return replace(
            verdict,
            reason=f"the screen is showing: {look.dialog.strip()} ({verdict.reason})",
        )
    where = look.url or look.elsewhere
    if screen and where and not same_screen(where, screen):
        return replace(
            verdict,
            reason=(
                f"the browser is on {where}, and this step was demonstrated "
                f"on {screen} ({verdict.reason})"
            ),
        )
    return verdict


async def _ahead_of_here(
    channel: Channel,
    tenant_id: TenantId,
    device_id: DeviceId,
    run_id: str,
    origin: str | None,
    *,
    ordered: list[Step],
    after: Step,
    by_id: Mapping[str, Gesture],
    screen_of_step: Callable[[Step | None], str | None],
) -> int | None:
    look = await _where(channel, tenant_id, device_id, run_id, origin)
    on = look.url or look.elsewhere or ""
    logger.info(
        "%s step %d: is the browser ahead? it is on %r (asked about %r)",
        run_id,
        after.order,
        on,
        origin,
    )
    if not on:
        return None
    after_screen = screen_of_step(after)
    for one in ordered:
        if one.order <= after.order:
            continue
        screen = screen_of_step(one)
        same = bool(screen) and (
            same_screen(screen, on)
            or (_host_of(screen) != _host_of(after_screen) and _host_path(screen) == _host_path(on))
        )
        logger.info(
            "%s step %d: step %d's screen is %r -- %s",
            run_id,
            after.order,
            one.order,
            screen,
            "the same" if same else "not this one",
        )
        if not same:
            continue
        passed = [before for before in ordered if after.order <= before.order < one.order]
        if any(
            writes(before, by_id)
            or (_puts_a_value(before, by_id) and _host_of(screen_of_step(before)) == _host_of(on))
            for before in passed
        ):
            return None
        return one.order
    return None


async def _through_the_mailbox(
    uow: UnitOfWork,
    run: WorkflowRun,
    record: RunStep,
    workflow: Workflow,
    values: Mapping[str, str],
    mail: MailHand,
    *,
    approvals: Approvals,
    stops: Stops,
) -> None:
    waiting = read_wait(run.awaiting) if run.awaiting else None
    written = await mail.write(workflow, values, waiting.thread if waiting else "")
    if isinstance(written, str):
        record.verdict, record.verdict_by, record.reason = "failed", "none", written
        return
    record.sent = {
        "kind": "mail.send",
        "payload": {"to": written.to, "subject": written.subject, "body": written.body},
    }
    if not run.live:
        record.verdict, record.verdict_by = "withheld", "none"
        record.reason = f"a dry run: the mail to {written.to} was written and not sent"
        return
    record.verdict, record.verdict_by = "awaiting", "none"
    record.reason = f"waiting for a person to read the mail to {written.to} and approve it"
    approvals.register(run.id)
    await _save(uow, run)
    if not await approvals.wait_for(run.id, K_APPROVAL_WAIT_S):
        record.verdict, record.verdict_by = "failed", "none"
        record.reason = f"nobody approved the mail within {K_APPROVAL_WAIT_S / 60:.0f} minutes"
        return
    if stops.asked(run.id):
        record.verdict, record.verdict_by = "failed", "none"
        record.reason = "stopped while waiting for approval; the mail was not sent"
        run.outcome = "aborted"
        return
    sent_id, why = await mail.send(written)
    if not sent_id:
        record.verdict, record.verdict_by, record.reason = "failed", "none", why
        return
    record.verdict, record.verdict_by = "held", "status"
    record.reason = f"Gmail took the mail to {written.to} (id {sent_id})"
    record.made = {"message": sent_id}


def _puts_a_value(step: Step, by_id: Mapping[str, Gesture]) -> bool:
    primary = primary_gesture(step, by_id)
    return primary is not None and primary.action.kind in PUTS_A_VALUE


def _host_of(url: str | None) -> str:
    return urlsplit(url or "").netloc.lower()


def _host_path(url: str | None) -> tuple[str, str]:
    parts = urlsplit(url or "")
    return (parts.netloc.lower(), parts.path.rstrip("/").lower())


async def _where(
    channel: Channel,
    tenant_id: TenantId,
    device_id: DeviceId,
    run_id: str,
    origin: str | None,
) -> Look:
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
        elsewhere=str(where.result.get("elsewhere") or "") if where.ok else "",
        elsewhere_is_ours=bool(where.ok and where.result.get("elsewhere_is_ours")),
        signed_out=bool(where.ok and where.result.get("signed_out")),
        dialog=str(where.result.get("dialog") or "") if where.ok else "",
        loading=bool(where.ok and where.result.get("loading")),
    )


def _too_long_for(step: Step, values: Mapping[str, str], holds: int) -> list[str]:
    return [
        name
        for name in step.parameters
        if isinstance(values.get(name), str) and len(values[name]) > holds
    ]


def _result(reply: Reply, *, wrote: bool = False) -> dict[str, object]:
    status = reply.result.get("status")
    matched = reply.result.get("matched_by")
    shown: dict[str, object] = {
        "ok": reply.ok,
        "status": status if isinstance(status, int) else None,
        "matched_by": matched if isinstance(matched, str) else None,
    }
    short = reply.result.get("short")
    if isinstance(short, dict):
        shown["short"] = {
            "asked": short.get("asked"),
            "kept": short.get("kept"),
            "truncated": bool(short.get("truncated")),
        }
    if wrote:
        shown["wrote"] = True
    if not reply.ok:
        shown["error_kind"] = reply.error_kind
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
    for cited in step.cites:
        gesture = by_id.get(cited)
        if gesture is None:
            continue
        for request in gesture.requests:
            if request.status is not None and not request.failure_reason:
                return False
    return True


def _not_given(workflow: Workflow, values: Mapping[str, str]) -> tuple[str, ...]:
    declared = [
        str(name)
        for parameter in workflow.parameters
        if isinstance(name := parameter.get("name"), str)
        and name
        and parameter.get("in_all", True)
        and demanded(parameter)
    ]
    return tuple(name for name in declared if not values.get(name, "").strip())


def _optional_of(step: Step, workflow: Workflow) -> tuple[str, ...]:
    return tuple(
        name
        for name in step.parameters
        if (declared := _by_alias(workflow).get(str(name))) is not None and not demanded(declared)
    )


def _by_alias(workflow: Workflow) -> dict[str, dict[str, object]]:
    by_alias: dict[str, dict[str, object]] = {}
    seen_tail: dict[str, int] = {}
    for one in workflow.parameters:
        names = one.get("names")
        aliases = {
            str(alias)
            for alias in (
                one.get("name"),
                one.get("key"),
                *(names if isinstance(names, list | tuple) else ()),
            )
            if isinstance(alias, str) and alias
        }
        for alias in aliases:
            by_alias.setdefault(alias, one)
            tail = alias.rsplit("-", 1)[-1]
            if tail != alias:
                seen_tail[tail] = seen_tail.get(tail, 0) + 1
                by_alias.setdefault(tail, one)
    for tail, count in seen_tail.items():
        if count > 1:
            by_alias.pop(tail, None)
    return by_alias


def _under_every_name(workflow: Workflow, values: Mapping[str, str]) -> dict[str, str]:
    known = dict(values)
    for alias, parameter in _by_alias(workflow).items():
        name = parameter.get("name")
        if alias in known or not isinstance(name, str):
            continue
        if (value := values.get(name, "")).strip():
            known[alias] = value
    return known


def _skippable(step: Step, workflow: Workflow, values: Mapping[str, str]) -> bool:
    wanted = tuple(str(name) for name in step.parameters)
    if not wanted:
        return False
    declared = [
        str(name)
        for one in workflow.parameters
        if isinstance(name := one.get("name"), str) and name
    ]
    if declared and not any(values.get(name, "").strip() for name in declared):
        return False
    optional = set(_optional_of(step, workflow))
    return all(name in optional and not values.get(name, "").strip() for name in wanted)


def _fell_over(run: WorkflowRun, in_flight: RunStep | None, reason: str) -> None:
    record = in_flight
    if record is None:
        record = RunStep(
            order=max((s.order for s in run.steps), default=-1) + 1, says="", verdict="failed"
        )
        run.steps.append(record)
    record.verdict, record.verdict_by, record.reason = "failed", "none", reason
    run.outcome = "failed"


def _withheld(step: Step, planned: Planned, by_id: Mapping[str, Gesture]) -> dict[str, object]:
    shown: dict[str, object] = {
        "step": step.order,
        "planned": {"kind": planned.kind, "payload": planned.payload},
    }
    if planned.kind == "http.send":
        shown.update({key: planned.payload.get(key) for key in ("method", "url", "body")})
        return shown
    call = recorded_call(step, by_id)
    if call is not None:
        shown.update(
            method=call.method.upper(),
            url=call.url,
            body=call.request_body.text if call.request_body else None,
        )
    return shown


async def fail_orphans(uow: UnitOfWork, reason: str) -> int:
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
    mail: MailHand | None = None,
    cap_usd: float,
) -> WorkflowRun:
    saved = await uow.workflow_runs.get(tenant_id, run_id) if run_id else None
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
        from_step=from_step,
        items=[dict(item) for item in items],
    )
    values, live, allow_focus = run.values, run.live, run.allow_focus
    watched = run.watched
    device_id = DeviceId(run.device_id)
    await _save(uow, run)
    if gather_values is not None and (short := _not_given(workflow, values)):
        run.doing = "looking in your mail for " + ", ".join(short)
        await _save(uow, run)
        got = await gather_values(short)
        run.doing = ""
        values = {**{name: f.value for name, f in got.values.items()}, **values}
        run.values = dict(values)
        run.gathered = {
            name: {"value": f.value, "from_message": f.from_message, "quoting": f.quoting}
            for name, f in got.values.items()
        }
        if got.unasked:
            run.unasked = list(got.unasked)
            logger.info(
                "%s: the mail also asked for %s, which this job has no parameter for",
                run.id,
                ", ".join(got.unasked),
            )
        await _save(uow, run)

        if still := _not_given(workflow, values):
            run.outcome = "stopped"
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

    values = _under_every_name(workflow, values)
    by_id = await _gestures_for(uow, tenant_id, workflow)
    verified_writes = (*verified_writes, *demonstrated_writes(workflow, by_id))
    learned = {one.ord: one for one in await uow.workflows.learned_for(workflow.id)}
    taught = await learn_from_the_rescue(uow, tenant_id, workflow, by_id)
    if taught is not None:
        learned[taught.ord] = taught
    observed = seen_values(workflow)
    placeable = await declared_keys(
        uow,
        tenant_id,
        [name for name in values if name not in set(names_of(workflow))],
        await screen_for(uow, tenant_id, workflow),
    )
    standing = stood_on(workflow, by_id)
    replayable = allowlist(workflow, by_id)
    ordered = sorted(workflow.steps, key=lambda s: s.order)
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
    collapsed: set[int] = set()
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

    already_read: set[int] = {
        step.order for step in workflow.steps if only_reads_the_mail(step, by_id)
    }
    mail_sends: set[int] = (
        {
            step.order
            for step in workflow.steps
            if sends_mail(step, by_id)
            and all(
                (urlsplit(by_id[one].url or "").hostname or "") in MAILBOXES
                for one in step.cites
                if one in by_id and on_the_mailbox(by_id[one])
            )
        }
        if mail is not None
        else set()
    )
    claimed_here: set[str] = set()
    approved_for_the_list: set[int] = set()
    proved_the_first = False
    already_done = [step for step in ordered if step.order < from_step]
    budget = len(itinerary) - len(already_done) + K_STEP_SLACK
    attempts = 0
    starts_on = None
    sent_nothing_yet = True

    def _next_after(steps: list[Step], step: Step) -> Step | None:
        later = [one for one in steps if one.order > step.order]
        return min(later, key=lambda one: one.order) if later else None

    def _screen_of(step: Step | None) -> str | None:
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

    step_here = next(
        (
            one
            for one in ordered[from_step:]
            if one.order not in collapsed and one.order not in already_read
        ),
        None,
    )
    starts_on = _screen_of(step_here)

    in_flight: RunStep | None = None
    itinerary = list(itinerary)
    signed_back_in = False
    joined_at: int | None = None
    try:
        position = -1
        while position + 1 < len(itinerary):
            position += 1
            leg = itinerary[position]
            step, values = leg.step, leg.values
            if (
                joined_at is not None
                and step.order < joined_at
                and leg.item in (None, 0)
                and not leg.rescue
            ):
                run.steps.append(
                    RunStep(
                        order=position,
                        of_step=step.order,
                        item=leg.item,
                        says=step.says,
                        verdict="not_needed",
                        verdict_by="none",
                        reason=(
                            "the browser is already past this: it is on the screen"
                            f" step {joined_at} starts from"
                        ),
                    )
                )
                await _save(uow, run)
                continue
            if step.uses:
                values = {**_what_earlier_steps_made(run, step.uses), **values}
            if not leg.rescue and step.order < from_step and leg.item in (None, 0):
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
            if not leg.rescue and _skippable(step, workflow, leg.values):
                run.steps.append(
                    RunStep(
                        order=position,
                        of_step=step.order,
                        item=leg.item,
                        says=step.says,
                        verdict="not_needed",
                        verdict_by="none",
                        reason=(
                            "this step fills "
                            + ", ".join(_optional_of(step, workflow))
                            + ", which the page does not ask for and this run"
                            " was given no value for"
                        ),
                    )
                )
                await _save(uow, run)
                continue
            if not leg.rescue and (step.order in collapsed or step.order in already_read):
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
            if mail is not None and not leg.rescue and step.order in mail_sends:
                record = RunStep(
                    order=position,
                    of_step=step.order,
                    item=leg.item,
                    says=step.says,
                    verdict="skipped",
                )
                in_flight = record
                run.steps.append(record)
                await _through_the_mailbox(
                    uow, run, record, workflow, values, mail, approvals=approvals, stops=stops
                )
                in_flight = None
                await _save(uow, run)
                if run.outcome != "running":
                    break
                if record.verdict not in ("held", "withheld"):
                    run.outcome = "stopped"
                    break
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
            writes_ahead = any(
                later.order > step.order and writes(later, by_id) for later in ordered
            )

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
                record.verdict, record.verdict_by = "skipped", "none"
                record.reason = ""
                if workflow.repeat is not None:
                    approved_for_the_list.update(
                        range(workflow.repeat.first_step, workflow.repeat.last_step + 1)
                    )
            if primary is None:
                record.reason = "no cited gesture can be acted on"

            replay = (
                replay_without_asking(
                    step=step,
                    cited=cited,
                    values=values,
                    verified_writes=verified_writes,
                    seen=observed,
                    keys=placeable,
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
            route = route_for(step, _next_after(ordered, step), by_id)
            if route is not None:
                rungs = (("route", ""), *rungs)
            signed_in_here = False
            waited_here = False
            never_filled = bool(
                replay is not None
                and collapsed
                and set(scaffolding_for(workflow, by_id, write_step=step.order)) & collapsed
            )
            if replay is not None and not run.watched:
                rungs = (("replay", ""),) if never_filled else (("replay", ""), *rungs)
            elif replay is not None and never_filled:
                rungs = (("replay", ""),)
            elif replay is not None:
                rungs = (*rungs, ("replay", ""))
            if primary is not None and not mutates:
                rungs = (*rungs, *((("look", rescue_model),) * K_LOOKS))
            logger.info(
                "%s step %d %r: rungs %s",
                run.id,
                step.order,
                step.says[:80],
                " then ".join(how for how, _ in rungs) or "none",
            )
            verdict: StepVerdict | None = None
            after_failed: Look | None = None
            refused_already: set[str] = set()
            asked_for_a_browser = False
            stepped_over = False
            for how, model in rungs:
                if stepped_over:
                    break
                if how == "look" and (
                    verdict is None or verdict.state != "failed" or verdict.by != "screen"
                ):
                    continue
                if (
                    how == "sight"
                    and (record.result or {}).get("error_kind") != "control_not_found"
                ):
                    continue
                planned: Planned | None = None
                before: Look | None = None
                navigated = False
                openings = 0
                previously = (record.planned_by, record.sent, record.result)
                while planned is None:
                    if how != "look" and attempts >= budget:
                        record.verdict = "refused"
                        record.reason = f"the step budget of {budget} attempts is spent"
                        run.outcome = "refused"
                        break
                    if how != "look":
                        attempts += 1
                    if how == "route" and route is not None:
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
                        before = await _where(channel, tenant_id, device_id, run.id, origin)
                        proposal = replay
                    elif how in ("sight", "look"):
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
                            opened=openings > 0,
                        )
                    else:
                        before = await _look(
                            channel, tenant_id, device_id, run.id, origin, allow_focus
                        )
                        proposal = await plan_step(
                            step=step,
                            learned=learned.get(step.order),
                            cited=cited,
                            values=values,
                            look=before,
                            origin=origin,
                            starts_on=starts_on if sent_nothing_yet else None,
                            allow_focus=allow_focus,
                            asker=asker,
                            model=model,
                            failure=verdict.reason if verdict else None,
                            failed_look=after_failed,
                            verified_writes=verified_writes,
                            seen=observed,
                            keys=placeable,
                            tenant_id=tenant_id.value,
                            secret_for=secret_for,
                            opened=openings > 0,
                        )
                    record.planned_by = proposal.by or model
                    record.before_url = before.url
                    _bill(record, proposal.answer)
                    record.sent = {
                        "kind": proposal.kind,
                        "payload": without_secrets(proposal.payload),
                    }

                    if proposal.kind == "none":
                        if live:
                            ahead = await _ahead_of_here(
                                channel,
                                tenant_id,
                                device_id,
                                run.id,
                                origin,
                                ordered=ordered,
                                after=step,
                                by_id=by_id,
                                screen_of_step=_screen_of,
                            )
                            if ahead is not None:
                                joined_at = ahead
                                stepped_over = True
                                never_filled = False
                                record.verdict, record.verdict_by = "not_needed", "none"
                                record.reason = (
                                    "the browser is already past this: it is on the"
                                    f" screen step {ahead} starts from"
                                )
                                break
                        verdict = StepVerdict("failed", "none", proposal.why)
                        break
                    off = _target_origin(proposal)
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
                    if proposal.opens and openings < K_OPENINGS and not mutates and how != "look":
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
                        proposal = Planned(
                            proposal.kind,
                            proposal.payload,
                            "the same command this step has already had refused",
                            proposal.answer,
                        )
                        break
                    elif proposal.kind != "navigate" or how == "route":
                        planned = proposal
                    elif navigated:
                        verdict = StepVerdict(
                            "failed",
                            "none",
                            proposal.why or "still on the wrong page after navigating",
                        )
                        break
                    else:
                        if live:
                            ahead = await _ahead_of_here(
                                channel,
                                tenant_id,
                                device_id,
                                run.id,
                                origin,
                                ordered=ordered,
                                after=step,
                                by_id=by_id,
                                screen_of_step=_screen_of,
                            )
                            if ahead is not None:
                                joined_at = ahead
                                stepped_over = True
                                never_filled = False
                                record.verdict, record.verdict_by = "not_needed", "none"
                                record.reason = (
                                    "the browser is already past this: it is on the"
                                    f" screen step {ahead} starts from"
                                )
                                break
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
                    logger.info(
                        "%s step %d rung %s proposed %s, not taken: %s",
                        run.id,
                        step.order,
                        how,
                        proposal.kind,
                        (proposal.why or "")[:120],
                    )
                if planned is None and run.outcome == "running":
                    refusal = record.sent if (record.sent or {}).get("payload") else None
                    record.planned_by, record.sent, record.result = previously
                    if refusal and refusal.get("kind") == "none":
                        record.sent = refusal
                    if how == "sight" and verdict is not None:
                        record.reason = f"{record.reason}; then by sight: {verdict.reason}"
                        verdict = StepVerdict(verdict.state, verdict.by, record.reason)
                if run.outcome != "running":
                    break
                if planned is None:
                    continue

                if not live and mutates:
                    run.withheld.append(_withheld(step, planned, by_id))
                    record.verdict, record.verdict_by = "withheld", "dry"
                    record.reason = "a dry run does not send writes"
                    record.result = {"withheld": True}
                    break

                pressing = planned.payload.get("action") in ("click", "press")
                signing_in = is_sign_in_page(primary.url if primary is not None else None)
                may_write = (not leg.rescue) and (
                    mutates
                    or (
                        pressing
                        and planned.kind == "ui.perform_at"
                        and how != "look"
                        and not signing_in
                    )
                    or (
                        pressing
                        and planned.kind == "ui.perform"
                        and _saw_nothing(step, by_id)
                        and not writes_ahead
                        and not signing_in
                    )
                )

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
                        record.result = {"skipped": True, "already": True}
                        verdict = StepVerdict("held", "read", settled_already)
                        break

                key = write_key(workflow.id, step, values) if live and mutates else ""
                if live and mutates and key not in claimed_here:
                    async with uow:
                        claimed = await uow.tool_calls.remember(
                            tenant_id,
                            key,
                            tool=f"{planned.kind} {step.says}"[:200],
                            at=datetime.now(tz=UTC),
                            stale_after=K_SAME_WRITE_WINDOW,
                        )
                        await uow.commit()
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

                if known_fields is not None and planned.filled:
                    writing = {
                        slot: values[name]
                        for slot, name in planned.filled.items()
                        if name in values
                    }
                    record.notes = list(
                        notes_on(
                            writing,
                            await known_fields(
                                tuple(sorted(writing)), _screen_of(step) or origin or ""
                            ),
                        )
                    )

                approved_here = leg.item is not None and step.order in approved_for_the_list
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
                    record.sent = {
                        "kind": planned.kind,
                        "payload": without_secrets(planned.payload),
                    }
                    approvals.register(run.id)
                    await _save(uow, run)
                    if not await approvals.wait_for(run.id, K_APPROVAL_WAIT_S):
                        waited = f"{K_APPROVAL_WAIT_S / 60:.0f} minutes"
                        record.verdict, record.verdict_by = "failed", "none"
                        record.reason = f"nobody approved the write within {waited}"
                        verdict = StepVerdict("failed", "none", record.reason)
                        break
                    if stops.asked(run.id):
                        record.verdict, record.verdict_by = "failed", "none"
                        record.reason = "stopped while waiting for approval"
                        run.outcome = "aborted"
                        with suppress(DeviceUnreachable):
                            await channel.send(
                                tenant_id,
                                device_id,
                                kind="abort",
                                run_id=run.id,
                                payload={"run_id": run.id},
                            )
                        break
                    if leg.item is not None:
                        approved_for_the_list.add(step.order)

                if record.verdict == "awaiting":
                    record.verdict, record.verdict_by = "skipped", "none"
                    record.reason = "approved; sending the write"
                    await _save(uow, run)
                assert before is not None  # noqa: S101 -- see the comment above
                holds = (learned.get(step.order) or LearnedStep(step.order, "", "", "")).holds
                asked_for = planned.payload.get("value")
                if holds is not None and isinstance(asked_for, str) and len(asked_for) > holds:
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
                sent_nothing_yet = False
                record.result = _result(reply, wrote=may_write)
                if how == "look" and reply.ok:
                    wrote_by_looking = await _a_write_went_out(
                        channel=channel,
                        tenant_id=tenant_id,
                        device_id=device_id,
                        run_id=run.id,
                        origin=origin,
                    )
                    if wrote_by_looking:
                        record.result = {**record.result, "wrote": True}
                        record.verdict, record.verdict_by = "failed", "none"
                        record.reason = (
                            f"working this step out on the screen sent {wrote_by_looking}; "
                            "state unknown after a write; not retried"
                        )
                        verdict = StepVerdict("failed", "none", record.reason)
                        logger.info("%s step %d %s", run.id, step.order, record.reason)
                        break
                cut = record.result.get("short")
                if isinstance(cut, dict) and cut.get("truncated"):
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
                if live and not reply.ok and reply.error_kind in K_MIGHT_BE_BEHIND:
                    ahead = await _ahead_of_here(
                        channel,
                        tenant_id,
                        device_id,
                        run.id,
                        origin,
                        ordered=ordered,
                        after=step,
                        by_id=by_id,
                        screen_of_step=_screen_of,
                    )
                    if ahead is not None:
                        joined_at = ahead
                        stepped_over = True
                        never_filled = False
                        record.verdict, record.verdict_by = "not_needed", "none"
                        record.reason = (
                            "the browser is already past this: it is on the screen"
                            f" step {ahead} starts from"
                        )
                        logger.info(
                            "%s: joining the job at step %s, where the browser is",
                            run.id,
                            ahead,
                        )
                        break
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
                if key and not reply.ok and reply.error_kind in K_NEVER_SENT:
                    async with uow:
                        await uow.tool_calls.forget(tenant_id, key)
                        await uow.commit()
                    claimed_here.discard(key)
                if reply.ok and planned.kind == "ui.perform_at":
                    record.result["matched_by"] = "sight"
                matched = record.result["matched_by"]
                record.matched_by = matched if reply.ok and isinstance(matched, str) else None
                settled = (
                    await by_what_the_page_called(
                        step=step,
                        cited=cited,
                        since=sent_at,
                        channel=channel,
                        tenant_id=tenant_id,
                        device_id=device_id,
                        run_id=run.id,
                        aimed_url=(
                            aimed.url
                            if mutates
                            and (
                                aimed := write_plan_for(
                                    step, by_id, values, verified_writes, observed, placeable
                                )
                            )
                            is not None
                            else None
                        ),
                    )
                    if reply.ok and planned.kind != "http.send"
                    else None
                )
                after = (
                    await _where(channel, tenant_id, device_id, run.id, origin)
                    if settled is not None or planned.kind == "http.send"
                    else await _look(channel, tenant_id, device_id, run.id, origin, allow_focus)
                )
                record.after_url = after.url
                after_failed = after
                arrived = (
                    StepVerdict(
                        "held" if same_screen(after.url, route) else "failed",
                        "read",
                        (
                            f"the browser is on {after.url}"
                            if same_screen(after.url, route)
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
                        next_says=(
                            itinerary[position + 1].step.says
                            if position + 1 < len(itinerary)
                            else None
                        ),
                    )
                )
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
                    here = after.url or (after.elsewhere if after.elsewhere_is_ours else "")
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
                    record.made = dict(verdict.made)
                if verdict.called:
                    record.result = {**(record.result or {}), "called": dict(verdict.called)}
                if verdict.refuted:
                    record.result = {**(record.result or {}), "refuted": True}
                if verdict.state == "held":
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
                        found = learned_from(
                            step.order,
                            "sight" if planned.kind == "ui.perform_at" else record.matched_by,
                            reply.result,
                        )
                        if found is not None:
                            await uow.workflows.remember_locator(workflow.id, found, by_run=run.id)
                    elif planned.kind == "ui.perform":
                        await uow.workflows.clear_stale(workflow.id, step.order)
                    await record_effect(uow.workflows, run, record, at=_now())
                    break
                if (
                    may_write
                    and reply.ok
                    and not (verdict.state == "failed" and verdict.by == "status")
                ):
                    record.reason = f"state unknown after a write; not retried: {record.reason}"
                    break

            if stepped_over:
                in_flight = None
                await _save(uow, run)
                continue
            if never_filled and record.verdict not in ("held", "withheld", "awaiting"):
                record.reason = (
                    record.reason
                    + " — and the form was never filled for this run, so the button was not"
                    " pressed either; run it again to have it typed in front of you"
                ).strip()

            if record.verdict == "skipped" and verdict is not None:
                record.verdict, record.verdict_by = verdict.state, verdict.by
                record.reason = verdict.reason

            in_flight = None
            await _save(uow, run)
            if run.outcome != "running":
                break
            took_it = bool(isinstance(record.result, dict) and record.result.get("ok"))
            in_the_reserve = (
                not leg.rescue
                and record.verdict not in ("held", "withheld")
                and step.order in in_reserve
            )
            if in_the_reserve and not took_it:
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
                _signing_in, back = (
                    (None, [])
                    if signed_back_in or is_sign_in_page(primary.url if primary else None)
                    else await _the_way_back_in(
                        uow, tenant_id, workflow, after_failed, values, by_id
                    )
                )
                if signed_back_in and after_failed is not None and after_failed.signed_out:
                    record.reason = (
                        record.reason
                        + " — the run signed back in and this system is still asking, so a"
                        " person has to sign in here"
                    ).strip()
                if back and _signing_in is not None:
                    signed_back_in = True
                    standing = standing | stood_on(_signing_in, by_id)
                    replayable = replayable | allowlist(_signing_in, by_id)
                    itinerary[position + 1 : position + 1] = [*back, leg]
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
        _fell_over(run, in_flight, f"{type(broke).__name__}: {broke}")
        raise
    finally:
        if run.outcome == "running":
            _fell_over(run, in_flight, "interrupted before finishing")
        await forget_effects(uow.workflows, run)
        run.finished_at = _now()
        await _save(uow, run)
        stops.forget(run.id)
        approvals.forget(run.id)
    return run
