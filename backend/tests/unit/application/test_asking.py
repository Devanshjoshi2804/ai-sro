from sro.application.shared.asking import ask
from sro.domain.prompts.write_mail import WRITE_MAIL
from sro.domain.shared.prices import Answer
from tests.unit.fakes import FakeAsker


async def test_an_answer_that_breaks_its_schema_is_no_answer() -> None:
    asker = FakeAsker(Answer(data={"to": "a@b.example"}, cost_usd=0.01))

    got = await ask(asker, WRITE_MAIL, trusted={"job": "x"}, untrusted={"conversation": "y"})

    assert got.data is None
    assert got.error is not None and "write_mail v1" in got.error
    assert got.cost_usd == 0.01


async def test_the_record_decides_model_thinking_instructions_and_schema() -> None:
    asker = FakeAsker(Answer(data={"to": "", "subject": "", "body": "b"}))

    got = await ask(asker, WRITE_MAIL, trusted={}, untrusted={"conversation": "hello"})

    asked = asker.asked[0]
    assert (asked["model"], asked["effort"]) == (WRITE_MAIL.model, WRITE_MAIL.thinking)
    assert asked["instructions"] == WRITE_MAIL.instructions
    assert asked["schema"] == dict(WRITE_MAIL.output_schema)
    assert '<untrusted name="conversation">' in str(asked["evidence"])
    assert got.data == {"to": "", "subject": "", "body": "b"}
