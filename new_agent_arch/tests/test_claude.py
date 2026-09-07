"""The Anthropic adapter, without asking Anthropic anything.

`AnthropicAsker` is the second implementation of the port the whole rig asks
through, and the bake-off it exists for spends real money at a vendor. What is
under test here is the adapter: that the schema is forced, that the answer is
found among the blocks rather than at a position, that a refusal and a cut-off
answer are told apart, and that every one of them still carries the bill.
"""

from typing import Any, Self

from rig.claude import K_MAX_OUTPUT_TOKENS, TOOL, AnthropicAsker

SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {"word": {"type": "string"}},
    "required": ["word"],
}


class _Block:
    def __init__(self, kind: str, **fields: Any) -> None:
        self.type = kind
        for name, value in fields.items():
            setattr(self, name, value)


class _Usage:
    def __init__(self, input_tokens: int | None, output_tokens: int | None) -> None:
        self.input_tokens, self.output_tokens = input_tokens, output_tokens


class _Message:
    def __init__(
        self,
        content: list[Any],
        *,
        usage: _Usage | None = None,
        stop_reason: str = "tool_use",
    ) -> None:
        self.content, self.usage, self.stop_reason = content, usage, stop_reason


class _Stream:
    def __init__(self, message: _Message) -> None:
        self.message = message

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *_: object) -> bool:
        return False

    async def get_final_message(self) -> _Message:
        return self.message


class _Messages:
    def __init__(self, message: _Message | None, problem: Exception | None = None) -> None:
        self.message, self.problem = message, problem
        self.asked: dict[str, Any] = {}

    def stream(self, **asked: Any) -> _Stream:
        self.asked = asked
        if self.problem is not None:
            raise self.problem
        assert self.message is not None
        return _Stream(self.message)


class _Client:
    def __init__(self, message: _Message | None, problem: Exception | None = None) -> None:
        self.messages = _Messages(message, problem)


def _answered(word: str = "yes", **over: Any) -> _Message:
    return _Message(
        [_Block("tool_use", input={"word": word})],
        usage=_Usage(1_000_000, 1_000_000),
        **over,
    )


async def test_the_answer_is_the_tool_input_and_the_bill_is_the_usage() -> None:
    client = _Client(_answered())
    asker = AnthropicAsker("", client=client)

    answer = await asker.ask(
        model="claude-haiku-4.5", instructions="read this", evidence="e", schema=SCHEMA
    )

    assert answer.data == {"word": "yes"}
    assert (answer.in_tokens, answer.out_tokens) == (1_000_000, 1_000_000)
    # $1 in and $5 out per million, which is what the table says for Haiku 4.5.
    assert answer.cost_usd == 6.0
    assert answer.unpriced is False
    assert answer.error is None


async def test_the_model_is_forced_into_the_schema_and_may_write_to_the_ceiling() -> None:
    """The guarantee that makes the comparison fair: both vendors are held to
    the schema, so what is measured is the model and not the harness."""
    client = _Client(_answered())

    await AnthropicAsker("", client=client).ask(
        model="claude-sonnet-5", instructions="", evidence="e", schema=SCHEMA
    )

    asked = client.messages.asked
    assert asked["tool_choice"] == {"type": "tool", "name": TOOL}
    assert asked["tools"][0]["input_schema"] == SCHEMA
    assert asked["max_tokens"] == K_MAX_OUTPUT_TOKENS


async def test_an_empty_instruction_is_not_sent_as_an_empty_system_prompt() -> None:
    """The mining door passes instructions="" on every call, and an empty
    system prompt is rejected by the API rather than ignored."""
    client = _Client(_answered())

    await AnthropicAsker("", client=client).ask(
        model="claude-sonnet-5", instructions="", evidence="e", schema=SCHEMA
    )

    assert "system" not in client.messages.asked


def test_an_instruction_that_exists_is_the_system_prompt() -> None:
    import asyncio

    client = _Client(_answered())

    asyncio.run(
        AnthropicAsker("", client=client).ask(
            model="claude-sonnet-5", instructions="read this", evidence="e", schema=SCHEMA
        )
    )

    assert client.messages.asked["system"] == "read this"


async def test_the_answer_is_found_by_kind_and_not_by_position() -> None:
    """A model that says something before it calls the tool is answering
    correctly. Reading content[0] files that as a refusal."""
    client = _Client(
        _Message(
            [_Block("text", text="here you go"), _Block("tool_use", input={"word": "yes"})],
            usage=_Usage(10, 2),
        )
    )

    answer = await AnthropicAsker("", client=client).ask(
        model="claude-haiku-4.5", instructions="", evidence="e", schema=SCHEMA
    )

    assert answer.data == {"word": "yes"}


async def test_an_answer_in_prose_is_an_error_that_still_carries_its_bill() -> None:
    client = _Client(_Message([_Block("text", text="I would rather not")], usage=_Usage(10, 3)))

    answer = await AnthropicAsker("", client=client).ask(
        model="claude-haiku-4.5", instructions="", evidence="e", schema=SCHEMA
    )

    assert answer.data is None
    assert answer.error is not None and "no tool call" in answer.error
    assert (answer.in_tokens, answer.out_tokens) == (10, 3)


async def test_an_answer_cut_off_by_the_ceiling_says_so_rather_than_refused() -> None:
    """A ceiling is a budget decision; a refusal is the model's. Filed as the
    same thing, the row that would tell you to raise the ceiling is gone."""
    client = _Client(_Message([], usage=_Usage(10, 64000), stop_reason="max_tokens"))

    answer = await AnthropicAsker("", client=client).ask(
        model="claude-haiku-4.5", instructions="", evidence="e", schema=SCHEMA
    )

    assert answer.error is not None
    assert "truncated" in answer.error
    assert str(K_MAX_OUTPUT_TOKENS) in answer.error


async def test_a_call_that_never_returned_does_not_claim_to_be_free() -> None:
    """It may or may not have been billed before it failed, and nothing here
    can tell -- so the zero in cost_usd is marked as not to be trusted."""
    client = _Client(None, problem=RuntimeError("no route to the vendor"))

    answer = await AnthropicAsker("", client=client).ask(
        model="claude-haiku-4.5", instructions="", evidence="e", schema=SCHEMA
    )

    assert answer.unpriced is True
    assert answer.error is not None and "RuntimeError: no route to the vendor" in answer.error


async def test_a_model_the_table_does_not_price_is_marked_unpriced() -> None:
    client = _Client(_answered())

    answer = await AnthropicAsker("", client=client).ask(
        model="claude-something-unreleased", instructions="", evidence="e", schema=SCHEMA
    )

    assert answer.data == {"word": "yes"}
    assert answer.cost_usd == 0.0
    assert answer.unpriced is True


async def test_usage_the_sdk_did_not_send_is_a_bill_nobody_can_trust() -> None:
    client = _Client(_Message([_Block("tool_use", input={"word": "yes"})], usage=None))

    answer = await AnthropicAsker("", client=client).ask(
        model="claude-haiku-4.5", instructions="", evidence="e", schema=SCHEMA
    )

    assert answer.unpriced is True


async def test_every_picture_is_carried_in_the_order_it_was_given() -> None:
    """A rescue shows the page as it is now and then the page the failed
    attempt left behind, and which is which is the order."""
    client = _Client(_answered())

    await AnthropicAsker("", client=client).ask(
        model="claude-haiku-4.5",
        instructions="",
        evidence="e",
        schema=SCHEMA,
        image=b"first",
        images=(b"second",),
    )

    import base64

    blocks = client.messages.asked["messages"][0]["content"]
    assert [block["type"] for block in blocks] == ["text", "image", "image"]
    assert blocks[1]["source"]["data"] == base64.b64encode(b"first").decode()
    assert blocks[2]["source"]["data"] == base64.b64encode(b"second").decode()


async def test_a_claude_row_carries_no_thinking_because_none_was_asked_for() -> None:
    """Forced structured output and extended thinking are not offered together.
    The zero is a fact about the harness, and the page says so rather than
    letting it read as a model that thought about nothing."""
    client = _Client(_answered())

    answer = await AnthropicAsker("", client=client).ask(
        model="claude-haiku-4.5", instructions="", evidence="e", schema=SCHEMA, effort="high"
    )

    assert answer.thought_tokens == 0
    assert "thinking" not in client.messages.asked
