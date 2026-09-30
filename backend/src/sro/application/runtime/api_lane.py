from __future__ import annotations

import asyncio
from collections.abc import Mapping, Sequence
from dataclasses import replace
from typing import Literal
from urllib.parse import quote, unquote, urlsplit, urlunsplit

from sro.application.connection.check_session import is_login
from sro.application.context import RequestContext
from sro.application.execution.plan_step import replay_without_asking
from sro.application.ports.http import HttpResponse
from sro.application.runtime.broker import K_HEADERS_WAIT_S, SessionBroker
from sro.application.runtime.step import Held, LaneContext, Stopped
from sro.domain.execution.belts import carries_in_slot, confirming_read, expected_statuses
from sro.domain.execution.evidence import recorded_call
from sro.domain.execution.lanes import (
    K_CONFLICT,
    Lane,
    SeenCall,
    StepResult,
    Verdict,
    fingerprint_of,
    write_confirmed,
)
from sro.domain.execution.planning import Planned
from sro.domain.execution.records import made_by, told_by
from sro.domain.execution.write_plan import learned_slots, seen_values
from sro.domain.observation.trim import path_shape
from sro.domain.recording.sensitivity import K_TOKENS, classify_header
from sro.domain.shared.hosts import REDACTED
from sro.domain.skill.workflow import Step

K_AUTH_REFUSED = frozenset({401, 403, 419})

K_REPRESENTATION = frozenset({"content-type", "accept"})


_GONE = frozenset({404, 410})

Found = Literal["ours", "other", "absent"]


class ApiLane:
    lane = Lane.API

    def __init__(self, broker: SessionBroker) -> None:
        self._broker = broker

    async def execute(self, step: Step, values: Mapping[str, str], ctx: LaneContext) -> StepResult:
        planned = replay_of(step, values, ctx)
        recorded = recorded_call(step, ctx.by_id)
        held = ctx.held
        if planned is None or recorded is None or held is None:
            return _unsent("no verified replay for this step", "no_replay")
        method, url = str(planned.payload["method"]), str(planned.payload["url"])
        body = planned.payload.get("body")
        needs = needs_of(recorded.request_headers)
        headers = await session_headers(
            self._broker,
            ctx.ctx,
            held,
            url,
            recorded.request_headers,
            fresh=ctx.reauthed,
            needs=needs,
        )
        carried = {name.lower() for name in headers}
        missing = [name for name in needs if name not in carried]
        if missing:
            return StepResult(
                "failed",
                Lane.API,
                f"the session has no {', '.join(missing)} for this write",
                never_left=True,
                expired=True,
            )
        if not _sendable(url, headers):
            return _unsent("the call cannot be built as recorded", "unsendable", path_shape(url))
        ctx.check_stop()
        await ctx.about_to_write(self.lane)
        try:
            answered = await self._broker.send(
                ctx.ctx,
                held,
                method,
                url,
                headers=headers,
                body=body if isinstance(body, str) else None,
            )
        except (Stopped, asyncio.CancelledError):
            raise
        except Exception as lost:
            return StepResult(
                "unknown", Lane.API, f"the call may have arrived: {type(lost).__name__}"
            )
        status = answered.status_code
        told = told_by(status, answered.text, _content_type(answered.headers))
        if status in K_AUTH_REFUSED and ctx.reauthed:
            return StepResult(
                "failed",
                Lane.API,
                f"the system refused this account ({status})",
                fingerprint=fingerprint_of(Lane.API, str(status), path_shape(url)),
                answered=told,
            )
        if status in K_AUTH_REFUSED:
            return StepResult(
                "failed",
                Lane.API,
                f"the session was refused ({status})",
                expired=True,
                answered=told,
            )
        if is_login(status, answered.headers.get("location"), url, answered.text):
            return StepResult(
                "unknown",
                Lane.API,
                f"the system sent the call to sign in ({status})",
                expired=True,
                answered=told,
            )
        verdict = write_confirmed(
            recorded=replace(recorded, url=url),
            wanted=expected_statuses(step, ctx.by_id),
            calls=[SeenCall(method, url, status)],
        )
        if verdict == "failed":
            return StepResult(
                "failed",
                Lane.API,
                f"the system answered {status}",
                never_left=True,
                fingerprint=fingerprint_of(Lane.API, str(status), path_shape(url)),
                answered=told,
            )
        made = made_by({"status": status, "body": answered.text})
        if verdict is None or (verdict == "unknown" and method.upper() == "DELETE"):
            return StepResult(
                "unknown", Lane.API, f"the system answered {status}", read=made, answered=told
            )
        if method.upper() == "DELETE":
            # A delete leaves no values to read back: its record's own address
            # answering that it is gone is what confirms it.
            try:
                after = await self._broker.send(ctx.ctx, held, "GET", url, headers=headers)
            except (Stopped, asyncio.CancelledError):
                raise
            except Exception as lost:
                return StepResult(
                    "unknown",
                    Lane.API,
                    f"the read-back was lost: {type(lost).__name__}",
                    read=made,
                    answered=told,
                )
            if after.status_code in _GONE:
                return StepResult("done", Lane.API, "a read-back finds the record gone", read=made)
            return StepResult(
                "unknown",
                Lane.API,
                f"the record still answers {after.status_code} after the delete",
                answered=told,
            )
        try:
            confirmed = await self._its_record(planned, ctx, held, headers, made) or (
                await self._confirmed(step, planned, ctx, held, fresh=False)
            )
            found = None if confirmed else await self._by_key(planned, ctx, held, headers)
        except (Stopped, asyncio.CancelledError):
            raise
        except Exception as lost:
            return StepResult(
                "unknown",
                Lane.API,
                f"the read-back was lost: {type(lost).__name__}",
                read=made,
                answered=told,
            )
        # Absent at a guessed address is a refusal only after the system's own
        # rejection (409); after a 5xx the record may live at an id we cannot guess.
        refused = (
            verdict == "unknown"
            and found is not None
            and (found[0] == "other" or (found[0] == "absent" and status == K_CONFLICT))
        )
        if refused and found is not None:
            said = told["said"] or f"it answered {status}"
            return StepResult(
                "failed",
                Lane.API,
                f"{found[1]} already exists with different values"
                if found[0] == "other"
                else f"the system refused it: {said}",
                never_left=True,
                refused=True,
                answered=told,
            )
        if not confirmed and (found is None or found[0] != "ours"):
            return StepResult(
                "unknown",
                Lane.API,
                "no read-back shows the values written"
                if verdict == "done"
                else f"the system answered {status}",
                read=made,
                answered=told,
            )
        return StepResult(
            "done",
            Lane.API,
            "a read-back shows the values written",
            read=made,
            keyed=confirmed_keys(step, values, ctx, planned),
        )

    async def read_back(
        self, step: Step, values: Mapping[str, str], ctx: LaneContext
    ) -> Verdict | None:
        planned = replay_of(step, values, ctx)
        if planned is None or ctx.held is None:
            return None
        if await self._confirmed(step, planned, ctx, ctx.held, fresh=ctx.reauthed):
            return "done"
        headers = await session_headers(
            self._broker, ctx.ctx, ctx.held, str(planned.payload["url"]), {}, fresh=ctx.reauthed
        )
        found = await self._by_key(planned, ctx, ctx.held, headers)
        return "done" if found is not None and found[0] == "ours" else None

    async def _its_record(
        self,
        planned: Planned,
        ctx: LaneContext,
        held: Held,
        headers: Mapping[str, str],
        made: Mapping[str, str],
    ) -> bool:
        """A create that answered with its record's id is read back there: the
        recording's own confirming read can be a list that never holds the new
        record (greyorange's transport job read its dock access groups)."""
        record = str(made.get("resourceId") or "").strip()
        if not record or not planned.confirm:
            return False
        got = await self._read_at(planned, ctx, held, headers, record)
        return got.succeeded and carries_in_slot(got.text, planned.confirm)

    async def _by_key(
        self, planned: Planned, ctx: LaneContext, held: Held, headers: Mapping[str, str]
    ) -> tuple[Found, str] | None:
        key = _key_of(ctx.workflow.parameters, planned)
        if key is None:
            return None
        slot, value = key
        got = await self._read_at(planned, ctx, held, headers, value)
        if got.status_code in _GONE:
            return "absent", value
        if not got.succeeded:
            return None
        if carries_in_slot(got.text, planned.confirm):
            return "ours", value
        return ("other", value) if carries_in_slot(got.text, {slot: value}) else None

    async def _read_at(
        self,
        planned: Planned,
        ctx: LaneContext,
        held: Held,
        headers: Mapping[str, str],
        record: str,
    ) -> HttpResponse:
        parts = urlsplit(str(planned.payload["url"]))
        url = urlunsplit(parts._replace(path=f"{parts.path.rstrip('/')}/{quote(record, safe='')}"))
        reading = {k: v for k, v in headers.items() if k.lower() != "content-type"}
        return await self._broker.send(ctx.ctx, held, "GET", url, headers=reading)

    async def _confirmed(
        self, step: Step, planned: Planned, ctx: LaneContext, held: Held, *, fresh: bool
    ) -> bool:
        probe = confirming_read(step, ctx.by_id)
        if probe is None or not planned.confirm or REDACTED in probe.url:
            return False
        if _origin(probe.url) != _origin(str(planned.payload["url"])):
            return False
        url = _aimed(probe.url, planned, seen_values(ctx.workflow, ctx.by_id))
        if url is None:
            return False
        headers = await session_headers(
            self._broker,
            ctx.ctx,
            held,
            url,
            probe.request_headers,
            fresh=fresh,
            needs=needs_of(probe.request_headers),
        )
        if not _sendable(url, headers):
            return False
        got = await self._broker.send(ctx.ctx, held, "GET", url, headers=headers)
        return got.succeeded and carries_in_slot(got.text, planned.confirm)


def needs_of(recorded: Mapping[str, str]) -> list[str]:
    return sorted(
        {
            name.lower()
            for name, value in recorded.items()
            if REDACTED in value and classify_header(name) in K_TOKENS
        }
    )


async def session_headers(
    broker: SessionBroker,
    ctx: RequestContext,
    held: Held,
    url: str,
    recorded: Mapping[str, str],
    *,
    fresh: bool = False,
    needs: Sequence[str] = (),
    wait_s: float = K_HEADERS_WAIT_S,
) -> dict[str, str]:
    said = await broker.headers(ctx, held, url, fresh=fresh, needs=needs, wait_s=wait_s)
    named = {name.lower() for name in said}
    return {
        **{
            name: value
            for name, value in recorded.items()
            if name.lower() in K_REPRESENTATION
            and name.lower() not in named
            and REDACTED not in value
        },
        **said,
    }


def replay_of(step: Step, values: Mapping[str, str], ctx: LaneContext) -> Planned | None:
    return replay_without_asking(
        step=step,
        cited=[ctx.by_id[one] for one in step.cites if one in ctx.by_id],
        values=values,
        verified_writes=ctx.ledger,
        seen=seen_values(ctx.workflow, ctx.by_id),
        learned=learned_slots(ctx.workflow, step),
    )


def confirmed_keys(
    step: Step, values: Mapping[str, str], ctx: LaneContext, planned: Planned | None = None
) -> dict[str, str]:
    planned = planned or replay_of(step, values, ctx)
    if planned is None:
        return {}
    return {
        name: key
        for name, key in learned_slots(ctx.workflow, step).items()
        if key in planned.confirm
    }


def _unsent(reason: str, kind: str, evidence: str = "") -> StepResult:
    return StepResult(
        "failed",
        Lane.API,
        reason,
        never_left=True,
        fingerprint=fingerprint_of(Lane.API, kind, evidence),
    )


def _key_of(parameters: Sequence[Mapping[str, object]], planned: Planned) -> tuple[str, str] | None:
    slots = {name: slot for slot, name in planned.filled.items() if slot in planned.confirm}
    name = next((str(one.get("name")) for one in parameters if one.get("name") in slots), None)
    return None if name is None else (slots[name], planned.confirm[slots[name]])


def _content_type(headers: Mapping[str, str]) -> str | None:
    return next((value for name, value in headers.items() if name.lower() == "content-type"), None)


def _origin(url: str) -> tuple[str, str]:
    parts = urlsplit(url)
    return parts.scheme.lower(), parts.netloc.lower()


def _sendable(url: str, headers: Mapping[str, str]) -> bool:
    scheme, host = _origin(url)
    if scheme not in ("http", "https") or not host:
        return False
    return all(
        (name + value).isascii() and (name + value).isprintable() for name, value in headers.items()
    )


def _aimed(url: str, planned: Planned, seen: Mapping[str, frozenset[str]]) -> str | None:
    run = {
        recorded: planned.confirm[slot]
        for slot, parameter in planned.filled.items()
        if slot in planned.confirm
        for recorded in seen.get(parameter, frozenset())
    }
    parts = urlsplit(url)
    segments = parts.path.split("/")
    rest = unquote("/".join(one for one in segments if unquote(one) not in run) + "?" + parts.query)
    if any(recorded in rest for recorded in run):
        return None
    aimed = [quote(run[unquote(one)], safe="") if unquote(one) in run else one for one in segments]
    return urlunsplit(parts._replace(path="/".join(aimed)))
