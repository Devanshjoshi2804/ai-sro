"""Reviewing the chat feedback a tenant's turns left (`python -m evals feedback ...`).

A row is evidence, not a verdict: `list` and `show` read it, `mark` records a person's reading of
it, and `promote` turns a row into a candidate chat case, the same file the `candidates` flow
writes (redacted by `evals/redact.py`, under `candidates/`), for a human to read and move to `ci/`
by hand. Nothing here writes into `ci/`, starts a job, or touches a prompt.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from evals.model import Case
from evals.redact import redacted
from evals.suggest import suggest
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.system import Clock
from sro.container import build_container
from sro.domain.chat.feedback import (
    DISMISSED,
    NEW,
    PROMOTED,
    REVIEWED,
    WITHHELD,
    Feedback,
    first_tool,
)
from sro.domain.shared.identifiers import TenantId

HERE = Path(__file__).parent

K_SHOWN = 50


def _line(row: Feedback) -> str:
    said = " ".join(row.said.split())
    said = said if len(said) <= K_SHOWN else said[: K_SHOWN - 1] + "…"
    return (
        f"{row.id:<22} {row.created_at:%Y-%m-%d} {row.kind:<13} {row.status:<9} "
        f"{first_tool(row) or '-':<12} {said}"
    )


async def listing(
    uow: UnitOfWork, tenant: str, *, status: str = NEW, kind: str = "", limit: int = 20
) -> str:
    async with uow as work:
        rows = await work.chat_feedback.newest(
            TenantId(tenant), statuses=(status,) if status else (), kind=kind, limit=limit
        )
    head = f"{'id':<22} {'when':<10} {'kind':<13} {'status':<9} {'tool':<12} said"
    return "\n".join([head, *(_line(one) for one in rows)]) if rows else "no feedback rows match"


async def _row(uow: UnitOfWork, tenant: str, feedback_id: str) -> Feedback:
    async with uow as work:
        row = await work.chat_feedback.get(TenantId(tenant), feedback_id)
    if row is None:
        raise SystemExit(f"no feedback row {feedback_id} for {tenant}")
    return row


async def showing(uow: UnitOfWork, tenant: str, feedback_id: str) -> str:
    row = await _row(uow, tenant, feedback_id)
    return json.dumps(_fields(row), indent=1, ensure_ascii=False)


def _fields(row: Feedback) -> dict[str, object]:
    return {
        "id": row.id,
        "kind": row.kind,
        "status": row.status,
        "note": row.note,
        "created_at": row.created_at.isoformat(),
        "operator": row.operator,
        "thread_id": row.thread_id,
        "message_id": row.message_id,
        "said": row.said,
        "brain": row.brain,
        "other": row.other,
    }


async def marking(uow: UnitOfWork, tenant: str, feedback_id: str, status: str, note: str) -> str:
    if status not in (REVIEWED, DISMISSED):
        raise SystemExit(f"mark takes {REVIEWED} or {DISMISSED}; promote makes a case")
    await _row(uow, tenant, feedback_id)
    async with uow as work:
        await work.chat_feedback.mark(TenantId(tenant), feedback_id, status=status, note=note)
        await work.commit()
    return f"{feedback_id} is {status}"


def _world(row: Feedback) -> list[dict[str, object]]:
    """The runs the case needs for the brain to see what the operator saw: the one this row
    is about, in the shape `run_status` gives it."""
    started = row.brain.get("started")
    if not isinstance(started, dict):
        return []
    return [
        {
            "id": started.get("run"),
            "job": started.get("job"),
            "values": started.get("values") or {},
            "state": str(row.other.get("state") or "done"),
            "stopped_because": str(row.other.get("reason") or ""),
            "from_mail": False,
            "question": "",
        }
    ]


async def promoting(
    uow: UnitOfWork,
    tenant: str,
    feedback_id: str,
    *,
    expect: str,
    args_json: str = "{}",
    root: Path = HERE,
) -> str:
    row = await _row(uow, tenant, feedback_id)
    if row.status == PROMOTED:
        raise SystemExit(f"{feedback_id} was already promoted: read its candidate before another")
    tools = [one.strip() for one in expect.split(",") if one.strip()]
    if not tools:
        raise SystemExit('--expect names the tools that are right, e.g. "find_jobs,start_job"')
    try:
        args = json.loads(args_json)
    except ValueError:
        args = None
    if not isinstance(args, dict):
        raise SystemExit("--args-json must be a JSON object: the arguments of the last tool")
    if not row.said.strip() or row.said == WITHHELD:
        raise SystemExit(f"{feedback_id} has no sentence kept to make a case of")
    case = Case(
        f"chat_fb_{row.id.removeprefix('fbk_')}",
        "chat",
        {"message": row.said, "origin": "chat", "runs": _world(row), "history": []},
        {"tools": tools, "args": args},
    )
    out = root / "candidates" / tenant / "chat"
    path = redacted(case, tenant=tenant).save(out)
    async with uow as work:
        await work.chat_feedback.mark(TenantId(tenant), feedback_id, status=PROMOTED, note=row.note)
        await work.commit()
    return f"wrote {path}: read it before moving it to ci/"


async def run_feedback(
    args: argparse.Namespace,
    *,
    uow: UnitOfWork | None = None,
    clock: Clock | None = None,
    root: Path = HERE,
) -> int:
    """The `feedback` subcommands; a test gives `uow` and `clock`, else the container's."""
    if uow is None or clock is None:
        container = build_container()
        uow, clock = uow or container.unit_of_work(), clock or container.clock
    store, now = uow, clock
    tenant = args.tenant
    try:
        if args.action == "list":
            out = await listing(store, tenant, status=args.status, kind=args.kind, limit=args.limit)
        elif args.action == "show":
            out = await showing(store, tenant, args.id)
        elif args.action == "mark":
            out = await marking(store, tenant, args.id, args.status, args.note)
        elif args.action == "suggest":
            out = await suggest(
                store, tenant, since=args.since, minimum=args.min, clock=now, root=root
            )
        else:
            out = await promoting(
                store, tenant, args.id, expect=args.expect, args_json=args.args_json, root=root
            )
    except SystemExit as stopped:
        print(stopped.code)  # noqa: T201
        return 1
    print(out)  # noqa: T201
    return 0
