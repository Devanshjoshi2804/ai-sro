"""Anthropic, behind the same port Gemini sits behind.

The rig runs on Gemini. This exists so the question "would another model do
this better, cheaper or faster" can be answered with the rig's own evidence and
the rig's own arithmetic instead of a vendor's benchmark table. It is asked by
`rig.bakeoff` and by nothing else, and the rig runs with no Anthropic key at
all.

Structured output is a forced tool call rather than a JSON instruction: the
schema goes in as the tool's `input_schema` and the answer comes back as the
tool's input, already parsed, so a model that would have wrapped its JSON in
prose cannot. That is the same guarantee `response_schema` gives on the Gemini
side, which is what makes the comparison fair.

No extended thinking. Forced tool use and extended thinking are not offered
together, and a comparison where one side is forced into the schema and the
other is free to narrate would measure the harness rather than the models. So
`effort` is accepted, recorded, and not sent -- and `thought_tokens` is 0 for
every Claude row, which the page says out loud rather than letting a zero read
as "thought about nothing".
"""

import json
from typing import Any

from rig.models import Answer, Effort, is_priced, price

K_MAX_OUTPUT_TOKENS = 64000
"""What one answer may run to. Claude's ceiling, which is lower than Gemini's
65,536 -- 64,000 on both Haiku 4.5 and Sonnet 5. Named separately rather than
sharing the Gemini constant, because a shared one would silently be whichever
vendor's limit was edited last."""

TOOL = "answer"
"""The one tool, and the model is forced into it. Its name is never shown to
the model as a choice, so it carries no meaning; it is here so the reply can be
found among the content blocks by something other than its position."""


def _blocks(evidence: str, image: bytes | None, images: tuple[bytes, ...]) -> list[Any]:
    """The user turn: the evidence, then every picture in the order given.

    A falsy evidence string is dropped rather than sent as an empty text block,
    which the API rejects -- the same rule the Gemini side keeps for a falsy
    instruction.
    """
    import base64

    parts: list[Any] = []
    if evidence:
        parts.append({"type": "text", "text": evidence})
    for picture in ((image,) if image is not None else ()) + images:
        parts.append(
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/png",
                    "data": base64.b64encode(picture).decode(),
                },
            }
        )
    if not parts:
        # Every door sends evidence; a call with neither text nor picture is a
        # caller bug, and an empty content list is a 400 that says nothing.
        parts.append({"type": "text", "text": " "})
    return parts


def _answered(message: Any) -> dict[str, Any] | None:
    """The tool input the model filled in, or None if it did not call the tool.

    Read by block type rather than by position: a model that emits a text block
    first and the tool call second is answering correctly, and indexing [0]
    would file that as a refusal.
    """
    for block in getattr(message, "content", None) or []:
        if getattr(block, "type", None) == "tool_use":
            data = getattr(block, "input", None)
            if isinstance(data, dict):
                return data
            if isinstance(data, str):
                try:
                    parsed = json.loads(data)
                except ValueError:
                    return None
                return parsed if isinstance(parsed, dict) else None
    return None


def _truncated(message: Any) -> bool:
    """Whether the model stopped because it hit the output ceiling. Compared by
    name so a fake and the SDK's own literal both read."""
    return str(getattr(message, "stop_reason", "") or "").lower() == "max_tokens"


class AnthropicAsker:
    def __init__(self, api_key: str, client: Any | None = None) -> None:
        """`client` is for tests; production passes an api_key and nothing else."""
        if client is not None:
            self._client = client
            return
        import anthropic

        self._client = anthropic.AsyncAnthropic(api_key=api_key)

    async def ask(
        self,
        *,
        model: str,
        instructions: str,
        evidence: str,
        schema: dict[str, Any],
        image: bytes | None = None,
        images: tuple[bytes, ...] = (),
        effort: Effort | None = None,
    ) -> Answer:
        try:
            message = await self._client.messages.create(
                model=model,
                max_tokens=K_MAX_OUTPUT_TOKENS,
                # The instruction is the system prompt, which is where it
                # belongs on this API -- and an empty one is omitted rather
                # than sent blank, as `umbrella.py` passes instructions="".
                **({"system": instructions} if instructions else {}),
                tools=[
                    {
                        "name": TOOL,
                        "description": "Answer in this shape. Call this and nothing else.",
                        "input_schema": schema,
                    }
                ],
                tool_choice={"type": "tool", "name": TOOL},
                messages=[{"role": "user", "content": _blocks(evidence, image, images)}],
            )
        except Exception as problem:  # noqa: BLE001 -- a rig keeps going; the row records why
            # The call may or may not have been billed before it failed, and we
            # cannot tell -- so the cost figure (0.0 here) is not to be trusted.
            return Answer(unpriced=True, error=f"{type(problem).__name__}: {problem}")

        usage = getattr(message, "usage", None)
        raw_in = getattr(usage, "input_tokens", None)
        raw_out = getattr(usage, "output_tokens", None)
        usage_missing = raw_in is None or raw_out is None
        in_tokens = raw_in or 0
        out_tokens = raw_out or 0
        unpriced = usage_missing or not is_priced(model)
        cost = price(model, in_tokens, out_tokens)

        data = _answered(message)
        if data is None:
            why = (
                f"truncated: the answer hit the {K_MAX_OUTPUT_TOKENS} output-token ceiling"
                if _truncated(message)
                else "the model returned no tool call (refused, or answered in prose)"
            )
            return Answer(
                in_tokens=in_tokens,
                out_tokens=out_tokens,
                cost_usd=cost,
                unpriced=unpriced,
                error=why,
            )

        return Answer(
            data=data,
            in_tokens=in_tokens,
            out_tokens=out_tokens,
            # Always 0: see the module docstring. Not billed separately either,
            # so the bill above is whole.
            thought_tokens=0,
            cost_usd=cost,
            unpriced=unpriced,
        )
