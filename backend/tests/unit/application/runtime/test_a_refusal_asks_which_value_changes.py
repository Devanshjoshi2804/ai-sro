"""A refusal that names no value asks ONE plain question -- which value should
change? -- and a reply changing any one value starts one run with the rest kept.

Seen on QA 2026-09-30 (run_185c1a71...): "Record already exists." for a Voice
Code already in use asked for all four values, in a sentence ending "..", with
"takes N characters" lines for values that exceeded nothing.
"""

from __future__ import annotations

import asyncio
from dataclasses import replace

from sro.domain.chat.asking import NEEDS, Pending, refusal_question, standing
from tests.unit.application.runtime.test_a_refused_write import (
    CTX,
    _Asking,
    _chat,
    _refused_run,
    _saving,
)
from tests.unit.application.runtime.test_a_reply_to_a_refusal import (
    ENVELOPE,
    _new_runs,
    _replied,
)
from tests.unit.runtime_support import WORKFLOW, SteelRun

SAID = '{"message": "Record already exists."}'
KEPT = {"Customer Type": "GT2", "Description": "Vets"}


def _reading(name: str, value: str) -> dict[str, object]:
    return {
        "job": WORKFLOW.id,
        "values": [{"field": name, "value": value, "quote": value}],
        "missing": [],
        "sure": True,
    }


async def _unnamed() -> tuple[SteelRun, _Asking]:
    asking = _Asking()
    world, _ = await _saving((409, SAID), (404, ""), asking=asking, mail=ENVELOPE)
    await world.run_steps.step(CTX, world.run_id, stop=asyncio.Event())
    assert await world.run_steps.finish(CTX, world.run_id) == "failed"
    return world, asking


async def test_the_question_says_the_system_s_words_once_and_asks_which_value_changes() -> None:
    world, _ = await _unnamed()

    asked = standing((await _chat(world, ENVELOPE["thread"])).messages)

    assert asked is not None and (asked.decision or {}).get("kind") == NEEDS
    assert 'Record already exists"' in asked.text and ".." not in asked.text
    assert "takes" not in asked.text and "characters" not in asked.text
    assert "GT2" in asked.text and "Pet shops" in asked.text
    assert "Which value should change?" in asked.text
    assert "What should" not in asked.text


async def test_a_typed_answer_changing_one_value_starts_one_run_keeping_the_rest() -> None:
    world, asking = await _unnamed()
    chat = await _chat(world, ENVELOPE["thread"])

    await asking.converse(world).execute(CTX, thread_id=chat.id, text="Description: Vets")

    assert _new_runs(world) == [KEPT]


async def test_a_mail_reply_changing_one_value_starts_one_run_keeping_the_rest() -> None:
    world, asking = await _unnamed()
    await _chat(world, ENVELOPE["thread"])

    await _replied(world, asking, "Description :- Vets", _reading("Description", "Vets"))

    assert _new_runs(world) == [KEPT]


async def test_a_reply_that_changes_nothing_starts_nothing_and_the_question_stands() -> None:
    world, asking = await _unnamed()
    chat = await _chat(world, ENVELOPE["thread"])
    converse = asking.converse(world)

    await converse.execute(CTX, thread_id=chat.id, text="thanks a lot for looking into that")
    await converse.execute(CTX, thread_id=chat.id, text="Description: pet  SHOPS")
    await _replied(world, asking, "thanks")
    await _replied(world, asking, "Description :- Pet shops", _reading("Description", "Pet shops"))

    assert _new_runs(world) == []
    asked = standing((await _chat(world, ENVELOPE["thread"])).messages)
    assert asked is not None and "Which value should change?" in asked.text
    assert (asked.decision or {}).get("changing") is True

    await converse.execute(CTX, thread_id=chat.id, text="Description: Vets")
    assert _new_runs(world) == [KEPT]


async def test_the_mail_then_the_chat_answering_the_same_refusal_start_one_run() -> None:
    world, asking = await _unnamed()
    chat = await _chat(world, ENVELOPE["thread"])

    await _replied(world, asking, "Description :- Vets", _reading("Description", "Vets"))
    await asking.converse(world).execute(CTX, thread_id=chat.id, text="Description: Vets")

    assert len(_new_runs(world)) == 1


async def test_a_refusal_naming_a_field_still_asks_for_that_field_alone() -> None:
    world, _ = await _refused_run()

    asked = standing((await _chat(world, world.run_id)).messages)

    assert asked is not None
    assert "What should Description be?" in asked.text
    assert "Which value should change?" not in asked.text
    assert "characters" not in asked.text


def test_a_value_too_long_for_its_field_keeps_its_own_limit_line_only() -> None:
    pending = Pending(
        workflow_id="w",
        title="Create a Warehouse Equipment Type",
        values={"Voice Code": "123456789", "Description": "Pallet jack"},
        missing=("Voice Code",),
        limits={"Voice Code": 8, "Description": 250},
        refused={"Voice Code": "too long"},
    )

    text = refusal_question(pending, "Record already exists.")

    assert "Voice Code takes 8 characters" in text
    assert "Description takes" not in text and ".." not in text
    assert replace(pending, values={"Voice Code": "42"}) and "takes" not in refusal_question(
        replace(pending, values={"Voice Code": "42"}), "no."
    )
