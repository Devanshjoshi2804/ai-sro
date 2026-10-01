"""`python -m evals feedback suggest`: what keeps going wrong, as proposals a person acts on.

It groups the rows still open (new or reviewed) by what the brain did and how it went wrong, and
for each group of enough rows writes one file under `proposals/` with the pattern, the rows and
the cases to add. It drafts no prompt text: three redacted sentences are thin ground for a rule,
and a model's draft of one would be a prompt change nobody ran the eval on. It edits no prompt,
changes no model, writes nothing to `ci/`, and starts nothing; a person adds the cases, changes
the prompt by hand, runs the chat eval, reviews, and merges.
"""

from __future__ import annotations

import hashlib
import re
from collections import defaultdict
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import cast

from sro.application.ports.repositories import UnitOfWork
from sro.domain.chat.feedback import (
    BUDGET,
    DISAGREEMENT,
    GUARD_REFUSAL,
    NEW,
    REVIEWED,
    Feedback,
    first_tool,
)
from sro.domain.shared.identifiers import TenantId

HERE = Path(__file__).parent

PROCESS = (
    "a proposal: add the cases, change the prompt by hand, run the chat eval "
    "(strict, repeat 3, >= 90%), review, then merge"
)

K_ROWS = 1000

_SINCE = re.compile(r"(\d+)([dh])")

_WHAT = {
    "undo": "the operator took back a run the brain started",
    "guard_refusal": "a code guard refused a call the model made",
    "run_failed": "a run the brain started ended failed or aborted",
    "disagreement": "the brain and the old chain did a different kind of thing",
    "budget": "the turn hit its budget, fell back to another model, or sent unreadable arguments",
}


def how_long(text: str) -> timedelta:
    found = _SINCE.fullmatch(text.strip())
    if found is None:
        raise SystemExit("--since is a number of days or hours, e.g. 14d or 36h")
    return timedelta(**{"days" if found[2] == "d" else "hours": int(found[1])})


def _clause(one: str) -> str:
    """One part of a refusal without its particulars: which field, which limit."""
    one = one.strip().lower()
    if "you gave is " in one:
        one = one.split("you gave is ", 1)[1]
    elif one.startswith("this job can't set"):
        one = "this job can't set"
    elif "is a secret" in one:
        one = "is a secret"
    elif one.startswith("missing:"):
        one = "missing"
    return re.sub(r"\d+", "N", one)


def shape_of(row: Feedback) -> str:
    """How a row went wrong, without the particulars (a field's name, a limit, a job's id)."""
    if row.kind == GUARD_REFUSAL:
        refusal = str(row.other.get("refusal") or "")
        return "; ".join(sorted({_clause(one) for one in refusal.split(";") if one.strip()}))
    if row.kind == DISAGREEMENT:
        return f"chain {row.other.get('category')} / brain {row.brain.get('category')}"
    if row.kind == BUDGET:
        trouble = cast(list[object], row.other.get("trouble") or [])
        return ", ".join(sorted(str(one) for one in trouble))
    started = row.brain.get("started")
    return str(started.get("job")) if isinstance(started, dict) else ""


Group = tuple[str, str, str]


def grouped(rows: Sequence[Feedback]) -> dict[Group, list[Feedback]]:
    found: dict[Group, list[Feedback]] = defaultdict(list)
    for row in rows:
        found[(row.kind, first_tool(row), shape_of(row))].append(row)
    return found


def _slug(group: Group) -> str:
    named = re.sub(r"[^a-z0-9]+", "-", "-".join(group).lower()).strip("-")[:48].strip("-")
    return f"{named}-{hashlib.sha256(repr(group).encode()).hexdigest()[:6]}"


def _proposal(group: Group, rows: Sequence[Feedback], tenant: str, since: str) -> str:
    kind, tool, shape = group
    ordered = sorted(rows, key=lambda one: one.created_at)
    lines = [
        f"# {kind}: the brain's first tool {tool or '-'}, {shape or 'no particular shape'}",
        "",
        f"> {PROCESS}.",
        "",
        "## The pattern",
        "",
        f"- what happened: {_WHAT[kind]}",
        f"- first tool the brain called: `{tool or '-'}`",
        f"- shape: {shape or '-'}",
        f"- {len(rows)} rows for {tenant} in the last {since}, "
        f"{ordered[0].created_at:%Y-%m-%d} to {ordered[-1].created_at:%Y-%m-%d}",
        "",
        "## The rows",
        "",
        "| id | status | the operator said (redacted) |",
        "|---|---|---|",
        *(
            f"| {r.id} | {r.status} | {' '.join(r.said.split()).replace('|', '/')} |"
            for r in ordered
        ),
        "",
        "## Cases to add",
        "",
        "Decide what the brain should have done for each, promote it, read the candidate, and move "
        "it to `ci/` by hand:",
        "",
        *(
            f"    uv run python -m evals feedback --tenant {tenant} promote {r.id} "
            '--expect "<the right tools>"'
            for r in ordered
        ),
        "",
        "## The prompt",
        "",
        "No rule is drafted here: read the rows, then change `domain/prompts/chat_brain.py` by "
        "hand if a rule or an edge case would have kept the brain from this, and run the chat "
        "eval before anything merges.",
        "",
    ]
    return "\n".join(lines)


async def suggest(
    uow: UnitOfWork,
    tenant: str,
    *,
    since: str = "14d",
    minimum: int = 3,
    now: datetime | None = None,
    root: Path = HERE,
) -> str:
    at = now or datetime.now(UTC)
    async with uow as work:
        rows = await work.chat_feedback.newest(
            TenantId(tenant),
            statuses=(NEW, REVIEWED),
            since=at - how_long(since),
            limit=K_ROWS,
        )
    groups = {group: found for group, found in grouped(rows).items() if len(found) >= minimum}
    out = root / "proposals"
    written = []
    for group, found in sorted(groups.items()):
        out.mkdir(parents=True, exist_ok=True)
        path = out / f"{at:%Y-%m-%d}-{_slug(group)}.md"
        path.write_text(_proposal(group, found, tenant, since), encoding="utf-8")
        written.append(path)
    if not written:
        return f"no group of {minimum} or more open rows in the last {since}: nothing to propose"
    return "\n".join([*(f"wrote {one}" for one in written), PROCESS])


__all__ = ["PROCESS", "grouped", "how_long", "shape_of", "suggest"]
