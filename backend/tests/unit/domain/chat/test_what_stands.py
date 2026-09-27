"""What stands in a conversation, and what is said about it when asked."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sro.domain.chat.asking import NEEDS, Pending, of_the_question
from sro.domain.chat.standing import last_run, of_the_run, stands
from sro.domain.chat.thread import Message, MessageId, Speaker
from sro.domain.execution.workflow_run import WorkflowRun

AT = datetime(2026, 9, 27, 9, 0, tzinfo=UTC)


def _said(n: int, speaker: Speaker, decision: dict[str, object] | None = None) -> Message:
    return Message(
        id=MessageId(f"msg_{n}"),
        speaker=speaker,
        text=f"said {n}",
        said_at=AT,
        decision=decision or {},
    )


def _run(**changed: object) -> WorkflowRun:
    run = WorkflowRun(
        id="run_1",
        tenant="t",
        workflow_id="wfl_1",
        device_id="",
        values={"Customer Type": "GGD", "Password": "hunter2"},
        started_by="op",
        live=True,
        allow_focus=False,
        started_at=AT.isoformat(),
    )
    for name, value in changed.items():
        setattr(run, name, value)
    return run


def test_the_run_a_thread_is_about_is_the_last_one_it_named() -> None:
    said = (
        _said(1, Speaker.SYSTEM, {"kind": "run", "run_id": "run_old"}),
        _said(2, Speaker.ASSISTANT, {"kind": "run_asks", "run_id": "run_1"}),
        _said(3, Speaker.OPERATOR),
        _said(4, Speaker.ASSISTANT, {"kind": NEEDS, "workflow_id": "wfl_1"}),
    )

    assert last_run(said) == "run_1"
    assert last_run(said[2:]) is None


def test_a_running_run_stands_and_a_finished_one_does_not() -> None:
    assert stands(_run(), AT)
    assert not stands(_run(outcome="held"), AT)
    assert not stands(_run(outcome="failed"), AT)


def test_a_run_that_ended_still_stands_while_it_asks_or_waits() -> None:
    until = (AT + timedelta(days=1)).isoformat()

    assert stands(_run(outcome="failed", needs=["Customer Type"]), AT)
    assert stands(
        _run(outcome="stopped", awaiting={"server": "gmail", "thread": "t1", "until": until}), AT
    )
    assert not stands(
        _run(outcome="stopped", awaiting={"server": "gmail", "thread": "t1", "until": until}),
        AT + timedelta(days=2),
    ), "a wait past its deadline is not a wait"


def test_a_run_is_told_by_its_progress_its_wait_and_its_values() -> None:
    until = (AT + timedelta(days=7)).isoformat()
    run = _run(
        progress={"step": 2, "asking": {"id": "q_1", "kind": "value", "text": "What code?"}},
        awaiting={"server": "gmail", "thread": "t1", "until": until},
        gathered={"Customer Type": {"message": "m1", "quote": "GGD"}},
    )

    said = of_the_run(run, "Create a Customer Type", AT)

    assert said.startswith("Create a Customer Type is running, at step 3."), said
    assert "What code?" in said
    assert "No reply has answered it yet" in said
    assert "I have Customer Type: GGD (from the mail)." in said
    assert "Nothing new was started." in said


def test_a_run_never_says_a_secret_it_holds() -> None:
    """The rule broken on purpose: `Password` is in the run's values."""
    said = of_the_run(_run(), "Sign in", AT)

    assert "hunter2" not in said
    assert "Password" not in said


def test_a_run_that_is_gathering_says_what_it_is_doing() -> None:
    said = of_the_run(_run(doing="Reading your mail for Customer Type"), "Create", AT)

    assert said.startswith("Create is running — Reading your mail for Customer Type."), said


def test_a_question_is_told_by_what_it_still_waits_for() -> None:
    pending = Pending(
        workflow_id="wfl_1",
        title="Create a Customer Type",
        values={"Description": "north"},
        missing=("Customer Type",),
    )

    asked = of_the_question(pending, offered=False)
    offered = of_the_question(pending, offered=True)

    assert asked.startswith("Create a Customer Type is waiting for Customer Type."), asked
    assert "I have Description: north." in asked
    assert offered.startswith("Create a Customer Type is waiting on your word."), offered
    assert "Say yes to run it, or no to leave it." in offered
