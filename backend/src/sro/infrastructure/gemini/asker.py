"""Gemini, with structured output and a bill.

Every call records its tokens and what they cost. A model call with no cost row
is a model call nobody can defend at the end of the month.

Search grounding is never enabled: it voids zero data retention (thirty days of
storage, no opt-out), and this process reads live customer payloads.
"""

from __future__ import annotations

import json
from typing import Any

from sro.domain.shared.prices import Answer, Effort, is_priced, price

K_MAX_OUTPUT_TOKENS = 65536
"""What one answer may run to. A mining pass writes every workflow it found,
each step citing gestures by id; a day's worth is thousands of tokens and the
default ceiling cut one off.

Thinking is counted inside this on Gemini, not beside it, and that is a trap
worth knowing: Gemini 3.8 Flash at effort `high` spent 62,913 of the 65,536
thinking about one day of evidence and had 2,609 left to write its answer in --
truncated, three runs out of three, $0.38 each for nothing. A budget cannot fix
it (the API takes a level or a budget, never both, and this model ignores the
budget); the level is the knob, and a model that thinks too much for its own
ceiling needs a lower one. Anthropic bills thinking outside its ceiling and is
unaffected."""


def truncated(response: Any) -> bool:
    """Whether the model stopped because it hit the output ceiling. The SDK
    says so on the candidate's `finish_reason`; compared by name so a fake and
    the enum both read. A cut-off answer is not "not json": it is a page the
    model was not allowed to finish, and the row should say which."""
    candidates = getattr(response, "candidates", None) or []
    reason = getattr(candidates[0], "finish_reason", None) if candidates else None
    name = getattr(reason, "name", None) or (str(reason) if reason is not None else "")
    return "MAX_TOKENS" in name.upper()


def build_config(*, schema: dict[str, object], effort: Effort | None = None) -> Any:
    """The config every call uses. No tools, ever — see the module docstring."""
    from google.genai import types

    return types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=dict(schema),
        # The most the model may write back. Left to the default, a mining
        # pass over a whole day came back cut mid-string at 17,313 characters
        # and was filed as "not json": $1.16 for nothing, and nothing said
        # why. The models this rig names all write up to this.
        max_output_tokens=K_MAX_OUTPUT_TOKENS,
        # Self-consistency was measured at a 0.4% gain for 20x the cost, so
        # K_SAMPLES is 1 and this is the knob instead. None leaves the model's
        # own default alone, which is what the per-gesture reading wants.
        # ThinkingLevel(...) because the SDK types the field as its own enum,
        # and a plain str fails mypy. It takes "high" case-insensitively.
        thinking_config=None
        if effort is None
        else types.ThinkingConfig(thinking_level=types.ThinkingLevel(effort)),
    )


class GeminiAsker:
    def __init__(self, api_key: str, client: Any | None = None) -> None:
        """`client` is for tests; production passes an api_key and nothing else."""
        if client is not None:
            self._client = client
            return
        from google import genai

        self._client = genai.Client(api_key=api_key)

    async def ask(
        self,
        *,
        model: str,
        instructions: str,
        evidence: str,
        schema: dict[str, object],
        image: bytes | None = None,
        images: tuple[bytes, ...] = (),
        effort: Effort | None = None,
    ) -> Answer:
        from google.genai import types

        # A falsy instruction would otherwise ship as a leading Part(text=''):
        # benign in the SDK, and rejected by some endpoints. umbrella.py passes
        # instructions="" on every call.
        parts: list[Any] = [part for part in (instructions, evidence) if part]
        if image is not None:
            parts.append(types.Part.from_bytes(data=image, mime_type="image/png"))
        # Further pictures, in the order given: a rescue shows the page as it
        # is now and then the page the failed attempt left behind.
        for more in images:
            parts.append(types.Part.from_bytes(data=more, mime_type="image/png"))

        try:
            response = await self._client.aio.models.generate_content(
                model=model,
                contents=parts,
                config=build_config(schema=schema, effort=effort),
            )
        # Broad on purpose: a rig keeps going, and the row records why.
        except Exception as problem:
            # The call may or may not have been billed before it failed, and we
            # cannot tell -- so the cost figure (0.0 here) is not to be trusted.
            return Answer(unpriced=True, error=f"{type(problem).__name__}: {problem}")

        usage = getattr(response, "usage_metadata", None)
        raw_in = getattr(usage, "prompt_token_count", None)
        raw_out = getattr(usage, "candidates_token_count", None)
        # Thinking tokens are billed at the OUTPUT rate, with no discount tier,
        # and candidates_token_count does not include them -- the SDK carries
        # them separately. Reading only candidates_token_count understated every
        # figure this rig has ever produced, and understated them by more the
        # harder the prompt was. K_EFFORT = "high" exists to spend these, so a
        # short visible answer can carry thousands of billed tokens the bill
        # showed and we did not.
        thought_tokens = getattr(usage, "thoughts_token_count", None) or 0
        usage_missing = raw_in is None or raw_out is None
        in_tokens = raw_in or 0
        # Kept apart in the record and added together for the bill: one number
        # says what the model wrote, the other says what it cost.
        out_tokens = (raw_out or 0) + thought_tokens
        unpriced = usage_missing or not is_priced(model)
        cost = price(model, in_tokens, out_tokens)

        if response.text is None:
            # The SDK returns None rather than raising when a call is blocked or
            # comes back with no candidates. Parsing that as "{}" would file a
            # refusal as a confident empty answer.
            return Answer(
                in_tokens=in_tokens,
                out_tokens=out_tokens,
                thought_tokens=thought_tokens,
                cost_usd=cost,
                unpriced=unpriced,
                error="the model returned no text (blocked, or no candidates)",
            )

        try:
            data = json.loads(response.text)
        except ValueError as problem:
            why = (
                f"truncated: the answer hit the {K_MAX_OUTPUT_TOKENS} output-token ceiling"
                f" after {raw_out or 0} tokens"
                if truncated(response)
                else f"not json: {problem}"
            )
            return Answer(
                in_tokens=in_tokens,
                out_tokens=out_tokens,
                thought_tokens=thought_tokens,
                cost_usd=cost,
                unpriced=unpriced,
                error=why,
            )

        return Answer(
            data=data,
            in_tokens=in_tokens,
            out_tokens=out_tokens,
            thought_tokens=thought_tokens,
            cost_usd=cost,
            unpriced=unpriced,
        )
