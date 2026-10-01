"""Reviewing chat feedback: list, show, mark, promote, over the fake store."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from tempfile import mkdtemp
from typing import Any, cast

import pytest
from evals.__main__ import arguments
from evals.feedback import listing, marking, promoting, run_feedback, showing
from evals.model import Case

from sro.domain.chat.feedback import WITHHELD, Feedback
from sro.domain.shared.identifiers import TenantId
from tests.unit.fakes import FakeUnitOfWork

TENANT = "acme"
JOB = "wfl_" + "a1" * 16


def _row(n: int, **over: Any) -> Feedback:
    fields: dict[str, Any] = {
        "id": f"fbk_{n}",
        "tenant": TENANT,
        "operator": "prn_a",
        "thread_id": "thr_1",
        "message_id": f"msg_{n}",
        "kind": "guard_refusal",
        "created_at": datetime(2026, 9, 30, 9, n, tzinfo=UTC),
        "said": "create customer type SR11 with the description new",
        "brain": {"tools": [{"tool": "start_job", "ok": False}]},
        "other": {"refusal": "the Customer Type you gave is longer than 4"},
    }
    fields.update(over)
    return Feedback(**fields)


async def _store(*rows: Feedback) -> FakeUnitOfWork:
    uow = FakeUnitOfWork()
    for one in rows:
        await uow.chat_feedback.add(one)
    return uow


async def test_list_is_a_compact_table_newest_first_of_the_new_rows_by_default() -> None:
    uow = await _store(
        _row(1),
        _row(2, kind="undo", brain={"started": {"run": "run_1"}}),
        _row(3, status="dismissed"),
        _row(4, said="x" * 200),
    )

    out = await listing(uow, TENANT)

    lines = out.splitlines()
    assert [one.split()[0] for one in lines] == ["id", "fbk_4", "fbk_2", "fbk_1"]
    assert "undo" in lines[2] and "start_job" in lines[2]
    assert "…" in lines[1] and len(lines[1]) < 130
    assert "fbk_3" not in out


async def test_list_filters_by_status_kind_and_limit() -> None:
    uow = await _store(_row(1), _row(2, kind="budget"), _row(3, status="reviewed"))

    assert (await listing(uow, TENANT, kind="budget")).count("fbk_") == 1
    assert "fbk_3" in await listing(uow, TENANT, status="reviewed")
    assert (await listing(uow, TENANT, limit=1)).count("fbk_") == 1
    assert await listing(uow, TENANT, status="promoted") == "no feedback rows match"


async def test_show_prints_the_whole_row_and_an_unknown_one_is_refused() -> None:
    uow = await _store(_row(1))

    shown = json.loads(await showing(uow, TENANT, "fbk_1"))

    assert shown["other"] == {"refusal": "the Customer Type you gave is longer than 4"}
    assert shown["said"].startswith("create customer type")
    with pytest.raises(SystemExit, match="no feedback row fbk_9"):
        await showing(uow, TENANT, "fbk_9")


async def test_mark_records_a_reading_and_nothing_else() -> None:
    uow = await _store(_row(1), _row(2))

    await marking(uow, TENANT, "fbk_1", "reviewed", "a real miss")
    await marking(uow, TENANT, "fbk_2", "dismissed", "")

    kept = {one.id: (one.status, one.note) for one in uow.chat_feedback.rows}
    assert kept == {"fbk_1": ("reviewed", "a real miss"), "fbk_2": ("dismissed", "")}
    with pytest.raises(SystemExit, match="promote makes a case"):
        await marking(uow, TENANT, "fbk_1", "promoted", "")
    with pytest.raises(SystemExit):
        await marking(uow, TENANT, "fbk_9", "reviewed", "")


async def test_promote_writes_a_redacted_candidate_chat_case_and_marks_the_row() -> None:
    uow = await _store(_row(1))
    root = Path(mkdtemp())

    out = await promoting(
        uow,
        TENANT,
        "fbk_1",
        expect="find_jobs,start_job",
        args_json=json.dumps({"job_id": JOB, "values": {"Customer Type": "SR11"}}),
        root=root,
    )

    path = root / "candidates" / TENANT / "chat" / "chat_fb_1.json"
    case = Case.load(path)
    assert str(path) in out
    assert (case.id, case.suite) == ("chat_fb_1", "chat")
    assert case.expected["tools"] == ["find_jobs", "start_job"]
    # The job's id stays, and the value is the same shape in the sentence and in the arguments.
    assert case.expected["args"] == {"job_id": JOB, "values": {"Customer Type": "AA99"}}
    assert "AA99" in str(case.input["message"])
    assert case.input["origin"] == "chat" and case.input["history"] == []
    # Redacted like every candidate: the operator's own values are shapes, not the values.
    assert "SR11" not in json.dumps(case.input)
    assert uow.chat_feedback.rows[0].status == "promoted"
    assert not (root / "ci").exists()


async def test_promote_carries_the_run_the_row_is_about_as_the_world_the_case_needs() -> None:
    uow = await _store(
        _row(
            1,
            kind="run_failed",
            brain={"started": {"run": "run_1", "job": "wfl_x", "values": {"Type": "SR11"}}},
            other={"run": "run_1", "state": "failed", "reason": "the save button was gone"},
        )
    )
    root = Path(mkdtemp())

    await promoting(uow, TENANT, "fbk_1", expect="run_status", root=root)

    case = Case.load(root / "candidates" / TENANT / "chat" / "chat_fb_1.json")
    (run,) = cast(list[dict[str, Any]], case.input["runs"])
    assert set(run) == {"id", "job", "values", "state", "stopped_because", "from_mail", "question"}
    assert run["state"] == "failed" and run["from_mail"] is False


async def test_promote_refuses_what_it_cannot_make_a_case_of_and_writes_nothing() -> None:
    uow = await _store(_row(1), _row(2, said=WITHHELD), _row(3, status="promoted"))
    root = Path(mkdtemp())

    for row_id, expect, args in (
        ("fbk_1", " , ", "{}"),
        ("fbk_1", "start_job", "[1]"),
        ("fbk_1", "start_job", "not json"),
        ("fbk_2", "start_job", "{}"),
        ("fbk_3", "start_job", "{}"),
        ("fbk_9", "start_job", "{}"),
    ):
        with pytest.raises(SystemExit):
            await promoting(uow, TENANT, row_id, expect=expect, args_json=args, root=root)

    assert not (root / "candidates").exists()
    assert [one.status for one in uow.chat_feedback.rows] == ["new", "new", "promoted"]


async def test_the_command_reads_the_arguments_and_prints(
    capsys: pytest.CaptureFixture[str],
) -> None:
    uow = await _store(_row(1))

    code = await run_feedback(arguments(["feedback", "--tenant", TENANT, "list"]), uow=uow)
    refused = await run_feedback(
        arguments(["feedback", "--tenant", TENANT, "show", "fbk_9"]), uow=uow
    )

    out = capsys.readouterr().out
    assert (code, refused) == (0, 1) and "fbk_1" in out and "no feedback row fbk_9" in out
    parsed = arguments(
        ["feedback", "--tenant", TENANT, "promote", "fbk_1", "--expect", "check_mail"]
    )
    assert (parsed.expect, parsed.args_json) == ("check_mail", "{}")
    assert TenantId(TENANT).value == TENANT
