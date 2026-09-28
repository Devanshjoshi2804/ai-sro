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
    assert got.error is not None and f"write_mail v{WRITE_MAIL.version}" in got.error
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

    assert got.data is None and got.error is not None and f"mine v{MINE.version}" in got.error


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


_DRAFT = {"to": "alex.r@example.com", "subject": "Re: x", "body": "Done.", "cited": []}
_EMPTY_DRAFT = {"to": "", "subject": "", "body": "", "cited": []}


async def test_an_empty_answer_on_the_primary_is_asked_again_on_the_fallback() -> None:
    """Measured on QA: WRITE_MAIL on 3.8-flash spent 1402 of 1414 output tokens
    thinking and wrote a draft with nothing in it."""
    asker = FakeAsker(Answer(data=_EMPTY_DRAFT, cost_usd=0.01), Answer(data=_DRAFT, cost_usd=0.02))

    got = await ask(asker, WRITE_MAIL, trusted={}, untrusted={"conversation": "y"})

    assert [one["model"] for one in asker.asked] == ["gemini-3.8-flash", "gemini-3.7-flash"]
    assert asker.asked[1]["instructions"] == asker.asked[0]["instructions"]
    assert asker.asked[1]["evidence"] == asker.asked[0]["evidence"]
    assert asker.asked[1]["schema"] == asker.asked[0]["schema"]
    assert got.data == _DRAFT and got.error is None and got.fell_back
    assert got.cost_usd == pytest.approx(0.03)


@pytest.mark.parametrize(
    "failed",
    [
        Answer(error="TimeoutError: the call timed out"),
        Answer(error="not json: Expecting value"),
        Answer(error="truncated: the answer hit the ceiling", truncated=True),
        Answer(data={"workflows": [_job("create a site", [7])], "unplaced": []}),
    ],
    ids=["raised", "not-json", "max-tokens", "every-item-dropped"],
)
async def test_each_kind_of_failure_falls_back(failed: Answer) -> None:
    good = {"workflows": [_job("create a supplier", ["code"])], "unplaced": []}
    asker = FakeAsker(failed, Answer(data=good))

    got = await ask(asker, MINE, trusted={}, untrusted={"day": "[]"})

    assert [one["model"] for one in asker.asked] == ["gemini-3.8-flash", "gemini-3.7-flash"]
    assert got.data == good


async def test_a_partly_valid_answer_is_used_and_not_asked_again() -> None:
    good, bad = _job("create a supplier", ["code"]), _job("create a site", [7])
    asker = FakeAsker(Answer(data={"workflows": [good, bad], "unplaced": []}))

    got = await ask(asker, MINE, trusted={}, untrusted={"day": "[]"})

    assert len(asker.asked) == 1
    assert got.data == {"workflows": [good], "unplaced": []} and not got.fell_back


async def test_nothing_found_is_an_answer_and_not_asked_again() -> None:
    asker = FakeAsker(Answer(data={"workflows": [], "unplaced": []}))

    await ask(asker, MINE, trusted={}, untrusted={"day": "[]"})

    assert len(asker.asked) == 1


async def test_when_both_fail_the_original_failure_comes_back(
    caplog: pytest.LogCaptureFixture,
) -> None:
    first = Answer(error="ServerError: 503 overloaded", cost_usd=0.01)
    asker = FakeAsker(first, Answer(error="ClientError: 429 quota", cost_usd=0.02))

    with caplog.at_level(logging.INFO, logger="sro.application.shared.asking"):
        got = await ask(
            asker, WRITE_MAIL, trusted={}, untrusted={"conversation": "SECRET-7 please"}
        )

    assert got.data is None and got.error == "ServerError: 503 overloaded"
    assert got.cost_usd == pytest.approx(0.03), "both calls were billed"
    assert "write_mail" in caplog.text and "gemini-3.7-flash" in caplog.text
    assert "ClientError: 429 quota" in caplog.text, "the fallback's own failure is logged"
    assert "SECRET-7" not in caplog.text


async def test_a_pro_record_never_falls_back() -> None:
    from sro.domain.prompts.interpret import INTERPRET

    asker = FakeAsker(Answer(error="ServerError: 503"), Answer(data={}))

    got = await ask(asker, INTERPRET, trusted={}, untrusted={})

    assert len(asker.asked) == 1 and got.error == "ServerError: 503"


async def test_other_thinking_is_sent_to_the_fallback_as_asked() -> None:
    asker = FakeAsker(Answer(error="not json"), Answer(data={"workflows": [], "unplaced": []}))

    await ask(asker, MINE, trusted={}, untrusted={"day": "[]"})

    assert [one["effort"] for one in asker.asked] == ["medium", "medium"]


async def test_a_body_of_only_whitespace_is_asked_again_on_the_fallback() -> None:
    """A model that spent its tokens thinking can write a lone newline; that is
    as empty as the empty body QA saw."""
    blank = {**_DRAFT, "body": " \n"}
    asker = FakeAsker(Answer(data=blank), Answer(data=_DRAFT))

    got = await ask(asker, WRITE_MAIL, trusted={}, untrusted={"conversation": "y"})

    assert [one["model"] for one in asker.asked] == ["gemini-3.8-flash", "gemini-3.7-flash"]
    assert got.data == _DRAFT
