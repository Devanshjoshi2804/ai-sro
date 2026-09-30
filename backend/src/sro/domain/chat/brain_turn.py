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
class ToolCall:
    tool: str
    args: dict[str, object]
    why: str = ""


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


@dataclass(frozen=True, slots=True)
class BrainReply:
    said: str
    decisions: tuple[dict[str, object], ...] = ()
    steps: tuple[tuple[ToolCall, ToolResult], ...] = ()


def _args_of(raw: object) -> dict[str, object]:
    """The model writes its arguments as a JSON string (Gemini drops a free-form object)."""
    if isinstance(raw, str):
        try:
            raw = json.loads(raw) if raw.strip() else {}
        except ValueError:
            return {}
    return dict(raw) if isinstance(raw, Mapping) else {}


def step_of(data: Mapping[str, object] | None) -> BrainStep:
    if not isinstance(data, Mapping):
        return BrainStep(call=None, say=None)
    if data.get("action") == "call" and isinstance(data.get("tool"), str) and data["tool"]:
        args = _args_of(data.get("args"))
        return BrainStep(
            call=ToolCall(
                str(data["tool"]),
                args,
                str(data.get("why") or ""),
            ),
            say=None,
        )
    if data.get("action") == "say" and str(data.get("text") or "").strip():
        return BrainStep(call=None, say=str(data["text"]).strip())
    return BrainStep(call=None, say=None)


def fenced_result(call: ToolCall, result: ToolResult) -> str:
    body = {"ok": result.ok, "data": result.data, "error": result.error}
    return fenced(f"result of {call.tool}", json.dumps(body, ensure_ascii=False, default=str))
