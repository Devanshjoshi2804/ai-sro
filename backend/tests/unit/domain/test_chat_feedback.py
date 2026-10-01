"""The categories a turn is compared by, and what may be kept of it."""

from __future__ import annotations

import pytest

from sro.domain.chat.brain_turn import ToolCall, ToolResult
from sro.domain.chat.feedback import (
    ANSWER,
    ASK,
    K_SAID,
    NONE,
    START,
    WITHHELD,
    brain_category,
    chain_category,
    kept,
    said_of,
)


def _step(tool: str, ok: bool = True) -> tuple[ToolCall, ToolResult]:
    return ToolCall(tool, {}), ToolResult(ok)


@pytest.mark.parametrize(
    ("steps", "category"),
    [
        ([_step("find_jobs"), _step("start_job")], START),
        ([_step("undo_run")], START),
        ([_step("start_job", ok=False), _step("ask_operator")], ASK),
        ([_step("lookup")], ANSWER),
        ([_step("check_mail")], ANSWER),
        ([_step("run_status"), _step("start_job", ok=False)], ANSWER),
        ([_step("find_jobs")], NONE),
        ([], NONE),
    ],
)
def test_the_brain_turn_is_the_kind_of_thing_its_tools_that_went_through_did(
    steps: list[tuple[ToolCall, ToolResult]], category: str
) -> None:
    assert brain_category(steps) == category


@pytest.mark.parametrize(
    ("decision", "category"),
    [
        ({"kind": "run", "run_id": "run_1"}, START),
        ({"kind": "job", "missing": []}, START),
        ({"kind": "job", "missing": ["Description"]}, ASK),
        ({"kind": "needs_values"}, ASK),
        ({"kind": "which_job"}, ASK),
        ({"kind": "looked"}, ANSWER),
        ({"kind": "mail_looked"}, ANSWER),
        ({"kind": "note"}, NONE),
        ({"kind": "failure"}, NONE),
        ({"run_id": "run_1"}, START),
        ({"run_id": None, "derived": {"rows": 1}}, ANSWER),
        ({"run_id": None, "missing_parameters": ["x"]}, ASK),
        ({"run_id": None, "choices": ["a", "b"]}, ASK),
        ({}, NONE),
    ],
)
def test_the_old_chains_reply_is_the_kind_of_thing_its_decision_says(
    decision: dict[str, object], category: str
) -> None:
    assert chain_category(decision) == category


def test_words_are_kept_without_a_secrets_shape_and_bounded() -> None:
    token = "AKIA" + "ABCDEFGHIJKLMNOP"

    said = said_of(f"use {token} " + "x" * 600)

    assert "ABCDEFGH" not in said and len(said) == K_SAID


def test_a_sentence_that_names_a_secret_is_not_kept_at_all() -> None:
    assert said_of("the password is hunter2") == WITHHELD
    assert said_of("create customer type SR11") == "create customer type SR11"


def test_evidence_is_kept_without_secret_fields_and_each_text_bounded() -> None:
    got = kept({"values": {"password": "hunter2", "Type": "t" * 900}, "list": ["a" * 900]})

    assert got == {
        "values": {"password": "<secret>", "Type": "t" * K_SAID},
        "list": ["a" * K_SAID],
    }
