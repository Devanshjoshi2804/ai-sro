"""`feedback suggest`: groups of repeated problems become proposals, and nothing else changes."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from pathlib import Path
from tempfile import mkdtemp
from typing import Any

import pytest
from evals.__main__ import arguments
from evals.feedback import run_feedback
from evals.suggest import PROCESS, grouped, how_long, shape_of, suggest

from sro.domain.chat.feedback import Feedback
from tests.unit.fakes import FakeClock, FakeUnitOfWork

TENANT = "acme"
NOW = datetime(2026, 10, 1, 9, 0, tzinfo=UTC)
CLOCK = FakeClock(NOW)
SRC = Path(__file__).resolve().parents[3] / "src"
CI = Path(__file__).resolve().parents[3] / "evals" / "ci"


def _row(n: int, **over: Any) -> Feedback:
    fields: dict[str, Any] = {
        "id": f"fbk_{n}",
        "tenant": TENANT,
        "operator": "prn_a",
        "thread_id": "thr_1",
        "message_id": f"msg_{n}",
        "kind": "guard_refusal",
        "created_at": NOW - timedelta(days=1, minutes=n),
        "said": f"create customer type SR{n} with the description new",
        "brain": {"tools": [{"tool": "start_job", "ok": False}]},
        "other": {"refusal": f"the Customer Type you gave is longer than {n + 3}"},
    }
    fields.update(over)
    return Feedback(**fields)


async def _store(*rows: Feedback) -> FakeUnitOfWork:
    uow = FakeUnitOfWork()
    for one in rows:
        await uow.chat_feedback.add(one)
    return uow


def _tree(*roots: Path) -> dict[str, str]:
    return {
        str(path): hashlib.sha256(path.read_bytes()).hexdigest()
        for root in roots
        for path in sorted(root.rglob("*"))
        if path.is_file() and "__pycache__" not in path.parts
    }


def test_a_refusal_has_the_shape_of_what_was_wrong_not_its_field_or_its_limit() -> None:
    long_one = _row(1, other={"refusal": "the Customer Type you gave is longer than 4"})
    long_other = _row(2, other={"refusal": "the Voice Code you gave is longer than 8"})
    invented = _row(3, other={"refusal": "the Description you gave is not in what was said"})
    many = _row(
        4,
        other={
            "refusal": "this job can't set Foo; password is a secret: never give one; missing: A, B"
        },
    )

    assert shape_of(long_one) == shape_of(long_other) == "longer than N"
    assert shape_of(invented) == "not in what was said"
    assert shape_of(many) == "is a secret; missing; this job can't set"


def test_rows_group_by_kind_first_tool_and_shape() -> None:
    rows = [
        _row(1),
        _row(2, other={"refusal": "the Voice Code you gave is longer than 8"}),
        _row(3, other={"refusal": "the Description you gave is not in what was said"}),
        _row(4, kind="budget", other={"trouble": ["budget"]}),
        _row(5, brain={"tools": [{"tool": "find_jobs"}]}),
        _row(
            6,
            kind="disagreement",
            brain={"category": "ask", "tools": []},
            other={"category": "start"},
        ),
        _row(7, kind="undo", brain={"started": {"job": "wfl_x"}}, other={}),
    ]

    found = grouped(rows)

    assert {k: [r.id for r in v] for k, v in found.items()} == {
        ("guard_refusal", "start_job", "longer than N"): ["fbk_1", "fbk_2"],
        ("guard_refusal", "start_job", "not in what was said"): ["fbk_3"],
        ("budget", "start_job", "budget"): ["fbk_4"],
        ("guard_refusal", "find_jobs", "longer than N"): ["fbk_5"],
        ("disagreement", "", "chain start / brain ask"): ["fbk_6"],
        ("undo", "start_job", "wfl_x"): ["fbk_7"],
    }


async def test_a_group_below_the_minimum_gets_no_file_and_one_at_it_gets_one() -> None:
    uow = await _store(_row(1), _row(2), _row(3, kind="budget", other={"trouble": ["budget"]}))
    root = Path(mkdtemp())

    none = await suggest(uow, TENANT, minimum=3, clock=CLOCK, root=root)
    assert not (root / "proposals").exists()
    one = await suggest(uow, TENANT, minimum=2, clock=CLOCK, root=root)

    assert "nothing to propose" in none
    files = sorted((root / "proposals").glob("*.md"))
    assert len(files) == 1 and files[0].name.startswith("2026-10-01-guard-refusal-start-job-")
    assert one.splitlines()[-1] == PROCESS and str(files[0]) in one


async def test_only_open_recent_rows_count_and_reviewed_ones_do() -> None:
    uow = await _store(
        _row(1),
        _row(2, status="reviewed"),
        _row(3, status="dismissed"),
        _row(4, status="promoted"),
        _row(5, created_at=NOW - timedelta(days=30)),
    )
    root = Path(mkdtemp())

    await suggest(uow, TENANT, minimum=1, clock=CLOCK, root=root)

    (file,) = (root / "proposals").glob("*.md")
    text = file.read_text(encoding="utf-8")
    assert "fbk_1" in text and "fbk_2" in text
    assert not any(gone in text for gone in ("fbk_3", "fbk_4", "fbk_5"))
    assert "2 rows" in text


async def test_a_proposal_names_the_pattern_the_rows_the_cases_and_the_process() -> None:
    uow = await _store(_row(1), _row(2), _row(3))
    root = Path(mkdtemp())

    await suggest(uow, TENANT, minimum=3, clock=CLOCK, root=root)

    (file,) = (root / "proposals").glob("*.md")
    text = file.read_text(encoding="utf-8")
    assert f"> {PROCESS}." in text
    assert "a code guard refused a call the model made" in text
    assert "shape: longer than N" in text and "3 rows for acme" in text
    for n in (1, 2, 3):
        assert f"| fbk_{n} | new | create customer type SR{n} with the description new |" in text
        assert f"promote fbk_{n} --expect" in text
    assert "No rule is drafted here" in text and "ci/" in text


async def test_suggesting_edits_no_prompt_and_no_ci_case_and_no_row() -> None:
    uow = await _store(_row(1), _row(2), _row(3))
    before = _tree(SRC, CI)

    await suggest(uow, TENANT, minimum=3, clock=CLOCK, root=Path(mkdtemp()))

    assert _tree(SRC, CI) == before and {r.status for r in uow.chat_feedback.rows} == {"new"}


def test_since_is_days_or_hours_and_nothing_else() -> None:
    assert how_long("14d") == timedelta(days=14) and how_long("36h") == timedelta(hours=36)
    for bad in ("", "14", "2w", "d"):
        with pytest.raises(SystemExit):
            how_long(bad)


async def test_the_command_takes_since_and_min(capsys: pytest.CaptureFixture[str]) -> None:
    uow = await _store(_row(1))
    args = arguments(["feedback", "--tenant", TENANT, "suggest", "--since", "3d", "--min", "1"])

    code = await run_feedback(args, uow=uow, clock=CLOCK, root=Path(mkdtemp()))

    assert code == 0 and (args.since, args.min) == ("3d", 1)
    assert PROCESS in capsys.readouterr().out
