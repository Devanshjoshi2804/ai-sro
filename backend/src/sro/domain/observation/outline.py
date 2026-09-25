from __future__ import annotations

import re
from collections.abc import Collection, Mapping, Sequence

from sro.domain.observation.gesture import Gesture, Outline
from sro.domain.recording.sensitivity import redact_shapes, redact_url

K_OUTLINE_OPTIONS = 25
K_OUTLINE_FIELDS = 80
K_OUTLINE_TEXT = 120
K_OUTLINE_MESSAGES = 10
K_OUTLINES_PER_GESTURE = 3
K_ECHO_MIN = 3
K_ECHO_SPAN = 8

FIELD_ROLES = frozenset(
    {
        "textbox",
        "searchbox",
        "combobox",
        "listbox",
        "checkbox",
        "radio",
        "switch",
        "spinbutton",
        "slider",
    }
)
MESSAGE_ROLES = frozenset({"alert", "status", "invalid"})
LANDMARK_ROLES = frozenset({"form", "dialog", "alertdialog"})

_NOT_VOCABULARY = re.compile(r"://|\w=\S")
_WORD_BREAK = re.compile(r"[\W_]+")


def _plain(text: str) -> str:
    return " ".join(text.split())


def _words(text: str) -> set[str]:
    return {word for word in _WORD_BREAK.split(text) if word}


def _echoes(lower: str, typed: Collection[str]) -> bool:
    words = _words(lower)
    for one in typed:
        if len(one) < K_ECHO_MIN:
            if _words(one) & words:
                return True
        elif one in lower or any(
            lower[at : at + K_ECHO_SPAN] in one for at in range(len(lower) - K_ECHO_SPAN + 1)
        ):
            return True
    return False


def _said(raw: object, typed: Collection[str]) -> str | None:
    if not isinstance(raw, str):
        return None
    plain = _plain(raw)
    if not plain or _NOT_VOCABULARY.search(plain) or _echoes(plain.lower(), typed):
        return None
    if redact_shapes(redact_url(plain)) != plain:
        return None
    return plain[:K_OUTLINE_TEXT]


def _items(raw: object) -> list[Mapping[str, object]]:
    return [one for one in raw if isinstance(one, Mapping)] if isinstance(raw, list) else []


def _texts(raw: object, typed: Collection[str], cap: int) -> list[str]:
    items = raw if isinstance(raw, list) else []
    return [said for one in items[:cap] if (said := _said(one, typed)) is not None]


def outline_kept(raw: object, typed: Collection[str]) -> dict[str, object] | None:
    if not isinstance(raw, Mapping):
        return None
    echoes = {plain for one in typed if (plain := _plain(one).lower())}
    fields = []
    for one in _items(raw.get("fields"))[:K_OUTLINE_FIELDS]:
        label = _said(one.get("label"), echoes)
        if one.get("role") not in FIELD_ROLES or label is None:
            continue
        options = one.get("options")
        required = one.get("required")
        fields.append(
            {
                "role": one["role"],
                "label": label,
                "required": required if isinstance(required, bool) else None,
                "options": _texts(options, echoes, K_OUTLINE_OPTIONS)
                if isinstance(options, list) and len(options) <= K_OUTLINE_OPTIONS
                else None,
            }
        )
    return {
        "headings": _texts(raw.get("headings"), echoes, K_OUTLINE_FIELDS),
        "landmarks": [
            {"role": one["role"], "name": name}
            for one in _items(raw.get("landmarks"))[:K_OUTLINE_FIELDS]
            if one.get("role") in LANDMARK_ROLES
            and (name := _said(one.get("name"), echoes)) is not None
        ],
        "fields": fields,
        "buttons": _texts(raw.get("buttons"), echoes, K_OUTLINE_FIELDS),
        "messages": [
            {"role": one["role"], "text": text}
            for one in _items(raw.get("messages"))[:K_OUTLINE_MESSAGES]
            if one.get("role") in MESSAGE_ROLES
            and (text := _said(one.get("text"), echoes)) is not None
        ],
    }


def last_outline(gesture: Gesture, earlier: Sequence[Gesture]) -> Outline | None:
    if gesture.action.outlines:
        return gesture.action.outlines[-1]
    here = (gesture.tab_id, gesture.action.frame_path)
    for one in sorted(earlier, key=lambda one: one.at, reverse=True):
        if (one.tab_id, one.action.frame_path) == here and one.action.outlines:
            return one.action.outlines[-1]
    return None
