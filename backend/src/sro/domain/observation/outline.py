from __future__ import annotations

import json
import re
import unicodedata
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


K_SAID_INPUT = K_OUTLINE_TEXT * 4
K_RANDOM_TOKEN = 10

_STOPS = (
    "required|invalid|incorrect|missing|empty|wrong|expired|too|must|not|cannot|can|should|"
    "failed|mismatch|does|did|has|needed"
)
_NOT_PERSONAL = re.compile(
    r"\S\s*(?:@|\[at\]|\(at\))\s*\S"
    r"|\bat\s+[\w-]+(?:\.|\s+dot\s+)[a-z]{2,}"
    r"|\d(?:[ ./-]?\d){5,}"
    r"|\b(?:pin|cvv|cvc|otp)\b\W{0,3}\d"
    r"|\b(?:pass(?:word|code|wd|phrase)?|pwd|secret|token|api[ _-]?key|authorization)s?"
    r"\s*(?:[:=]|\bis\b)\s*(?!(?:" + _STOPS + r")\b)\S"
    r"|\bbearer\s+[\w.+/=-]{8,}"
    r"|\b(?:sk|pk|rk)_(?:live|test)_|\b(?:ghp|gho|ghs|xox[abp])[_-]",
    re.ASCII | re.IGNORECASE,
)
_JWT = re.compile(r"eyJ[\w-]{5,}", re.ASCII)
_ISO_DATE = re.compile(r"\b\d{4}[-/]\d{2}[-/]\d{2}\b", re.ASCII)
_TOKENS = re.compile(r"[A-Za-z0-9+]+", re.ASCII)


def _random_looking(token: str) -> bool:
    if len(token) < K_RANDOM_TOKEN:
        return False
    uppers = sum(c.isupper() for c in token)
    return (
        any(c.isdigit() for c in token)
        or "+" in token
        or (0 < uppers < len(token) and uppers * 5 >= len(token))
    )


def _looks_encoded(text: str) -> bool:
    tokens = _TOKENS.findall(text)
    flags = [_random_looking(token) for token in tokens]
    return any(
        flag and (len(token) >= 20 or (i + 1 < len(flags) and flags[i + 1]))
        for i, (token, flag) in enumerate(zip(tokens, flags, strict=True))
    )


def said_text(raw: object) -> str | None:
    if not isinstance(raw, str):
        return None
    folded = unicodedata.normalize("NFKC", raw[:K_SAID_INPUT])
    plain = _plain("".join(c for c in folded if unicodedata.category(c)[0] != "C"))
    plain = plain[:K_OUTLINE_TEXT]
    view = _ISO_DATE.sub("~", plain)
    if _NOT_PERSONAL.search(view) or _JWT.search(view) or _looks_encoded(view):
        return None
    return _said(plain)


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
