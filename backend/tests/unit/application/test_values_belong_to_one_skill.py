"""Which values a follow-up sentence carries with it.

A thread is one conversation about many things. Somebody asks how many
suppliers there are, then goes on to create a client -- and the values
established for the first were merged into the parameters of the second. The
docstring on the gathering said "for the skill under discussion"; the code
merged every decision in the thread.

Values arriving from somewhere the operator never typed them is the worst way
for a write to be wrong: it looks answered.
"""

from __future__ import annotations

from sro.application.chat.converse import _gathered
from sro.domain.chat.thread import Message, MessageId, Speaker, Thread, ThreadId
from tests import factories as f


def _thread() -> Thread:
    return Thread(id=ThreadId("thr-1"), tenant_id=f.TENANT, opened_by=f.OPERATOR, opened_at=f.T0)


def _said(thread: Thread, skill_id: str, values: dict[str, str], *, waiting: bool) -> None:
    thread.say(
        Message(
            id=MessageId(f"msg-{len(thread.messages)}"),
            speaker=Speaker.ASSISTANT,
            text="...",
            said_at=f.at(10),
            decision={
                "matched_skill_id": skill_id,
                "missing_parameters": ["something"] if waiting else [],
                "items": [values],
            },
        )
    )


def test_a_value_given_for_one_skill_is_kept_for_that_skill() -> None:
    thread = _thread()
    _said(thread, "skl_client", {"client_name": "Acme"}, waiting=True)

    assert _gathered(thread, "skl_client") == {"client_name": "Acme"}


def test_it_does_not_follow_the_operator_to_the_next_skill() -> None:
    thread = _thread()
    _said(thread, "skl_supplier", {"supplier_number": "SUP-9"}, waiting=True)

    assert _gathered(thread, "skl_client") == {}


def test_nothing_is_carried_when_nothing_is_being_waited_on() -> None:
    """A fresh sentence brings its own values. The thread's older ones belong
    to whatever they were for."""
    thread = _thread()
    _said(thread, "skl_supplier", {"supplier_number": "SUP-9"}, waiting=False)

    assert _gathered(thread, None) == {}
