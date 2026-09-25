from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from urllib.parse import urlsplit

from sro.domain.observation.gesture import Gesture, Outline
from sro.domain.recording.sensitivity import redact_shapes, redact_url

K_OUTLINE_OPTIONS = 25
K_OUTLINE_FIELDS = 80
K_OUTLINE_TEXT = 120
K_OUTLINE_MESSAGES = 10
K_OUTLINES_PER_GESTURE = 3
K_OUTLINE_CHARS = 16384

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

_NOT_VOCABULARY = re.compile(r"://|\w=\S|[0-9a-f]{16,}|[\w-]{32,}", re.ASCII | re.IGNORECASE)


def _plain(text: str) -> str:
    return " ".join(text.split())


def _said(raw: object) -> str | None:
    if not isinstance(raw, str):
        return None
    plain = _plain(raw)
    if not plain or _NOT_VOCABULARY.search(plain):
        return None
    if redact_shapes(redact_url(plain)) != plain:
        return None
    return plain[:K_OUTLINE_TEXT]


def _items(raw: object) -> list[Mapping[str, object]]:
    return [one for one in raw if isinstance(one, Mapping)] if isinstance(raw, list) else []


def _texts(raw: object, cap: int) -> list[str]:
    items = raw if isinstance(raw, list) else []
    return [said for one in items[:cap] if (said := _said(one)) is not None]


def _role(one: Mapping[str, object], roles: frozenset[str]) -> str | None:
    role = one.get("role")
    return role if isinstance(role, str) and role in roles else None


def _size(value: object) -> int:
    return len(json.dumps(value, separators=(",", ":"), ensure_ascii=False))


def _fitted(outline: dict[str, object]) -> dict[str, object]:
    size = _size(outline)
    fields = outline["fields"]
    for field in reversed(fields) if isinstance(fields, list) else ():
        if size <= K_OUTLINE_CHARS:
            break
        if isinstance(field, dict) and field["options"] is not None:
            size -= _size(field["options"]) - _size(None)
            field["options"] = None
    for key in ("headings", "landmarks", "messages", "buttons", "fields"):
        items = outline[key]
        while isinstance(items, list) and items and size > K_OUTLINE_CHARS:
            size -= _size(items.pop()) + (1 if items else 0)
    return outline


def outline_kept(raw: object) -> dict[str, object] | None:
    if not isinstance(raw, Mapping):
        return None
    fields = []
    for one in _items(raw.get("fields"))[:K_OUTLINE_FIELDS]:
        role = _role(one, FIELD_ROLES)
        label = _said(one.get("label"))
        if role is None or label is None:
            continue
        options = one.get("options")
        required = one.get("required")
        fields.append(
            {
                "role": role,
                "label": label,
                "required": required if isinstance(required, bool) else None,
                "options": _texts(options, K_OUTLINE_OPTIONS)
                if isinstance(options, list) and len(options) <= K_OUTLINE_OPTIONS
                else None,
            }
        )
    return _fitted(
        {
            "headings": _texts(raw.get("headings"), K_OUTLINE_FIELDS),
            "landmarks": [
                {"role": role, "name": name}
                for one in _items(raw.get("landmarks"))[:K_OUTLINE_FIELDS]
                if (role := _role(one, LANDMARK_ROLES)) is not None
                and (name := _said(one.get("name"))) is not None
            ],
            "fields": fields,
            "buttons": _texts(raw.get("buttons"), K_OUTLINE_FIELDS),
            "messages": [
                {"role": role}
                for one in _items(raw.get("messages"))[:K_OUTLINE_MESSAGES]
                if (role := _role(one, MESSAGE_ROLES)) is not None
            ],
        }
    )


def _document(gesture: Gesture) -> tuple[str, str, str] | None:
    if gesture.url is None:
        return None
    parts = urlsplit(gesture.url)
    return parts.scheme, parts.netloc, parts.path


def last_outline(gesture: Gesture, earlier: Sequence[Gesture]) -> Outline | None:
    if gesture.action.outlines:
        return gesture.action.outlines[-1]
    here = (gesture.tab_id, gesture.action.frame_path, _document(gesture))
    for one in sorted(earlier, key=lambda one: one.at, reverse=True):
        if (one.tab_id, one.action.frame_path, _document(one)) == here and one.action.outlines:
            return one.action.outlines[-1]
    return None
