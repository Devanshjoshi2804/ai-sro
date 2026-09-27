import logging

import pytest

from sro.application.shared.asking import ask
from sro.domain.prompts.gather import GATHER
from sro.domain.prompts.mine import MINE
from sro.domain.prompts.write_mail import WRITE_MAIL
from sro.domain.shared.prices import Answer
from tests.unit.fakes import FakeAsker


async def test_an_answer_that_breaks_its_schema_is_no_answer() -> None:
    asker = FakeAsker(Answer(data={"to": "a@b.example"}, cost_usd=0.01))

    got = await ask(asker, WRITE_MAIL, trusted={"job": "x"}, untrusted={"conversation": "y"})

    assert got.data is None
    assert got.error is not None and "write_mail v2" in got.error
    assert got.cost_usd == 0.01


async def test_the_record_decides_model_thinking_instructions_and_schema() -> None:
    asker = FakeAsker(Answer(data={"to": "", "subject": "", "body": "b", "cited": []}))

    got = await ask(asker, WRITE_MAIL, trusted={}, untrusted={"conversation": "hello"})

    asked = asker.asked[0]
    assert (asked["model"], asked["effort"]) == (WRITE_MAIL.model, WRITE_MAIL.thinking)
    assert asked["instructions"] == WRITE_MAIL.instructions
    assert asked["schema"] == dict(WRITE_MAIL.output_schema)
    assert '<untrusted name="conversation">' in str(asked["evidence"])
    assert got.data == {"to": "", "subject": "", "body": "b", "cited": []}


def _job(title: str, parameters: list[object]) -> dict[str, object]:
    return {
        "title": title,
        "steps": [{"order": 0, "cites": ["ges_1"], "says": "do it", "parameters": parameters}],
    }


async def test_one_bad_job_costs_only_itself_and_not_the_pass() -> None:
    good, bad = _job("create a supplier", ["code"]), _job("create a site", [7])
    asker = FakeAsker(Answer(data={"workflows": [good, bad], "unplaced": []}, cost_usd=0.2))

    got = await ask(asker, MINE, trusted={}, untrusted={"day": "[]"})

    assert got.data == {"workflows": [good], "unplaced": []}
    assert got.error is None and got.cost_usd == 0.2


async def test_one_value_without_its_message_costs_only_itself() -> None:
    kept = {"name": "code", "value": "GT2", "from_message": "m-1", "quoting": "use GT2"}
    lost = {"name": "description", "value": "a guess"}
    asker = FakeAsker(Answer(data={"action": "done", "values": [kept, lost], "why": "found"}))

    got = await ask(asker, GATHER, trusted={}, untrusted={"asked_for": "x"})

    assert got.data == {"action": "done", "values": [kept], "why": "found"}


async def test_a_unit_that_is_not_a_list_is_still_no_answer() -> None:
    asker = FakeAsker(Answer(data={"workflows": "not a list"}))

    got = await ask(asker, MINE, trusted={}, untrusted={"day": "[]"})

    assert got.data is None and got.error is not None and "mine v3" in got.error


async def test_an_error_already_on_the_answer_is_never_overwritten() -> None:
    asker = FakeAsker(Answer(data={}, error="the model returned nothing"))

    got = await ask(asker, WRITE_MAIL, trusted={}, untrusted={"conversation": "y"})

    assert got.data is None
    assert got.error == "the model returned nothing"


async def test_what_was_dropped_is_counted_and_logged_without_its_content(
    caplog: pytest.LogCaptureFixture,
) -> None:
    good, bad = _job("create a supplier", ["code"]), _job("create a site SECRET-9", [7])
    asker = FakeAsker(Answer(data={"workflows": [good, bad, bad]}))

    with caplog.at_level(logging.INFO, logger="sro.application.shared.asking"):
        got = await ask(asker, MINE, trusted={}, untrusted={"day": "[]"})

    assert got.dropped == 2
    assert "mine" in caplog.text and "2" in caplog.text
    assert "SECRET-9" not in caplog.text


async def test_nothing_dropped_is_a_zero() -> None:
    asker = FakeAsker(Answer(data={"workflows": [_job("create a supplier", ["code"])]}))

    got = await ask(asker, MINE, trusted={}, untrusted={"day": "[]"})

    assert got.dropped == 0
