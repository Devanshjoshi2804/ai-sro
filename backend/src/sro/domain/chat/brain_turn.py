from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Literal

from sro.domain.prompts.record import fenced

K_HISTORY = 12


@dataclass(frozen=True)
class Origin:
    kind: Literal["chat", "mail"]
    sender: str = ""
    subject: str = ""


@dataclass(frozen=True, slots=True)
class Turn:
    """What a tool may know of the turn it runs in, never from the model: the words the
    person said (a value must come from them) and the offer the caller makes a run under."""

    said: str = ""
    offer: str = ""


@dataclass(frozen=True, slots=True)
class ToolCall:
    tool: str
    args: dict[str, object]
    why: str = ""
    # The arguments were not a JSON object: the tool is not run, the model is told.
    unreadable: bool = False


@dataclass(frozen=True, slots=True)
class BrainStep:
    call: ToolCall | None
    say: str | None


@dataclass(frozen=True, slots=True)
class ToolResult:
    ok: bool
    data: dict[str, object] = field(default_factory=dict)
    error: str = ""
    ends_turn: bool = False
    decision: dict[str, object] | None = None
    # What the operator is told of this result, when it has a card of its own.
    said: str = ""
    # A code guard refused the call (not the world): the model's own mistake.
    guard: bool = False


@dataclass(frozen=True, slots=True)
class BrainReply:
    said: str
    decisions: tuple[dict[str, object], ...] = ()
    steps: tuple[tuple[ToolCall, ToolResult], ...] = ()
    # What went wrong on the way that the operator is not told of: "budget" (the turn hit its
    # steps, calls or spend), "fell_back" (a second model answered), "unreadable_args".
    trouble: tuple[str, ...] = ()


def _args_of(raw: object) -> dict[str, object] | None:
    """The model writes its arguments as a JSON string (Gemini drops a free-form object).
    None when what it wrote is not an object: that is an error to tell it, not no arguments."""
    if raw is None:
        return {}
    if isinstance(raw, str):
        try:
            raw = json.loads(raw) if raw.strip() else {}
        except ValueError:
            return None
    return dict(raw) if isinstance(raw, Mapping) else None


def step_of(data: Mapping[str, object] | None) -> BrainStep:
    if not isinstance(data, Mapping):
        return BrainStep(call=None, say=None)
    if data.get("action") == "call" and isinstance(data.get("tool"), str) and data["tool"]:
        args = _args_of(data.get("args"))
        return BrainStep(
            call=ToolCall(
                str(data["tool"]), args or {}, str(data.get("why") or ""), unreadable=args is None
            ),
            say=None,
        )
    if data.get("action") == "say" and str(data.get("text") or "").strip():
        return BrainStep(call=None, say=str(data["text"]).strip())
    return BrainStep(call=None, say=None)


def fenced_result(call: ToolCall, result: ToolResult) -> str:
    body = {"ok": result.ok, "data": result.data, "error": result.error}
    return fenced(f"result of {call.tool}", json.dumps(body, ensure_ascii=False, default=str))
