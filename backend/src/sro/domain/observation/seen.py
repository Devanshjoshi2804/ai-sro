from __future__ import annotations

import re
from collections.abc import Mapping

from sro.domain.observation.gesture import Choice, CookieSeen, Effect, FieldChange, Place, Seen
from sro.domain.observation.outline import said_text
from sro.domain.observation.trim import path_shape
from sro.domain.recording.sensitivity import redact_shapes

SEEN_ROLES = frozenset(
    {"dialog", "alertdialog", "alert", "status", "toast", "row", "mask", "invalid", "progressbar"}
)
FIELD_CHANGES = frozenset({"enabled", "disabled", "shown", "hidden", "invalid", "valid"})
ENDINGS = frozenset({"quiet", "max", "next"})

K_SEEN_ITEMS = 20
K_FIELD_CHANGES = 40
K_ERRORS = 10
K_SHORTCUTS = 10
K_CHOICE_OPTIONS = 50
K_PLACE_HEADINGS = 3
K_PLACE_ITEMS = 10
K_BUTTONS = 8
K_MS = 60_000
K_COOKIES = 40
K_COOKIE_NAME = 64
K_MAIL_REF = 200

_URL = re.compile(r"\S+://\S+")
_SHORTCUT = re.compile(
    r"(?:(?:ctrl|alt|meta|shift)\+)+(?:[a-z0-9]|f[0-9]{1,2}|enter|escape|delete|backspace)"
)
_MAIL_REF = re.compile(r"[A-Za-z0-9_\-=+/.]+")
_COOKIE_NAME = re.compile(r"[A-Za-z0-9_\-.]+")


def _items(raw: object, cap: int) -> list[Mapping[str, object]]:
    return [one for one in raw if isinstance(one, Mapping)][:cap] if isinstance(raw, list) else []


def _texts(raw: object, cap: int) -> list[str]:
    items = raw if isinstance(raw, list) else []
    return [said for one in items if (said := said_text(one)) is not None][:cap]


def _route(raw: object) -> str | None:
    if not isinstance(raw, str) or not raw.strip():
        return None
    path, _, hashed = raw.partition("#")
    shaped = path_shape(path) if path else ""
    if hashed:
        shaped += "#" + path_shape(hashed)
    return shaped or None


def _ms(raw: object) -> int | None:
    if isinstance(raw, bool) or not isinstance(raw, int | float) or raw < 0:
        return None
    return min(int(raw), K_MS)


def _count(raw: object) -> int | None:
    return raw if isinstance(raw, int) and not isinstance(raw, bool) and raw >= 0 else None


def _seen(one: Mapping[str, object]) -> dict[str, object] | None:
    role = one.get("role")
    if not isinstance(role, str) or role not in SEEN_ROLES:
        return None
    text, title = one.get("text"), one.get("title")
    if (isinstance(text, str) and text and said_text(text) is None) or (
        isinstance(title, str) and title and said_text(title) is None
    ):
        return None
    return {
        "role": role,
        "text": said_text(text),
        "title": said_text(title),
        "buttons": _texts(one.get("buttons"), K_BUTTONS),
    }


def _seens(raw: object) -> list[dict[str, object]]:
    return [s for one in _items(raw, K_SEEN_ITEMS * 5) if (s := _seen(one))][:K_SEEN_ITEMS]


def _strings(raw: object) -> list[str]:
    return [one for one in raw if isinstance(one, str)] if isinstance(raw, list) else []


def place_kept(raw: object) -> dict[str, object] | None:
    if not isinstance(raw, Mapping):
        return None
    kept: dict[str, object] = {
        "route": _route(raw.get("route")),
        "title": said_text(raw.get("title")),
        "headings": _texts(raw.get("headings"), K_PLACE_HEADINGS),
        "tabs": _texts(raw.get("tabs"), K_PLACE_ITEMS),
        "grid": said_text(raw.get("grid")),
        "landmarks": _texts(raw.get("landmarks"), K_PLACE_ITEMS),
        "version": said_text(raw.get("version")),
    }
    return kept if any(kept.values()) else None


def effect_kept(raw: object) -> dict[str, object] | None:
    if not isinstance(raw, Mapping):
        return None
    fields = [
        {"label": label, "change": change}
        for one in _items(raw.get("fields"), K_FIELD_CHANGES * 2)
        if (label := said_text(one.get("label"))) is not None
        and isinstance(change := one.get("change"), str)
        and change in FIELD_CHANGES
    ][:K_FIELD_CHANGES]
    errors = [
        said
        for one in _strings(raw.get("errors"))
        if (said := said_text(redact_shapes(_URL.sub("«url»", one)))) is not None
    ][:K_ERRORS]
    shortcuts = [one for one in _strings(raw.get("shortcuts")) if _SHORTCUT.fullmatch(one)][
        :K_SHORTCUTS
    ]
    ended = raw.get("ended")
    kept: dict[str, object] = {
        "appeared": _seens(raw.get("appeared")),
        "vanished": _seens(raw.get("vanished")),
        "route_before": _route(raw.get("route_before")),
        "route_after": _route(raw.get("route_after")),
        "fields": fields,
        "requests_ms": _ms(raw.get("requests_ms")),
        "mask_ms": _ms(raw.get("mask_ms")),
        "quiet_ms": _ms(raw.get("quiet_ms")),
        "ended": ended if isinstance(ended, str) and ended in ENDINGS else None,
        "errors": errors,
        "shortcuts": shortcuts,
    }
    return kept if any(value not in (None, []) for value in kept.values()) else None


def choice_kept(raw: object) -> dict[str, object] | None:
    if not isinstance(raw, Mapping):
        return None
    index = raw.get("index")
    if index is not None and _count(index) is None:
        return None
    kept: dict[str, object] = {
        "chosen": said_text(raw.get("chosen")),
        "index": index,
        "options": _texts(raw.get("options"), K_CHOICE_OPTIONS),
    }
    return kept if kept["chosen"] is not None or kept["options"] else None


def cookies_kept(raw: object) -> list[dict[str, object]]:
    kept: list[dict[str, object]] = []
    for one in _items(raw, K_COOKIES):
        name = one.get("name")
        if (
            not isinstance(name, str)
            or len(name) > K_COOKIE_NAME
            or not _COOKIE_NAME.fullmatch(name)
            or redact_shapes(name) != name
        ):
            continue
        expires = one.get("expires_at")
        domain = one.get("domain")
        kept.append(
            {
                "name": name,
                "expires_at": float(expires)
                if isinstance(expires, int | float) and not isinstance(expires, bool)
                else None,
                "domain": domain if isinstance(domain, str) and len(domain) <= 253 else None,
                "session": one.get("session") is True,
            }
        )
    return kept


def mail_thread_kept(raw: object) -> str | None:
    if not isinstance(raw, str) or len(raw) > K_MAIL_REF or not _MAIL_REF.fullmatch(raw):
        return None
    return raw


def extras_kept(target: Mapping[str, object]) -> dict[str, object]:
    return {
        "labelText": said_text(target.get("labelText")),
        "fullName": said_text(target.get("fullName")),
        "siblingIndex": _count(target.get("siblingIndex")),
        "siblingCount": _count(target.get("siblingCount")),
    }


def _optional(raw: object) -> str | None:
    return raw if isinstance(raw, str) else None


def _seen_of(one: Mapping[str, object]) -> Seen:
    return Seen(
        str(one["role"]),
        _optional(one["text"]),
        _optional(one["title"]),
        tuple(_strings(one["buttons"])),
    )


def place_from(raw: object) -> Place | None:
    kept = place_kept(raw)
    if kept is None:
        return None
    return Place(
        route=_optional(kept["route"]),
        title=_optional(kept["title"]),
        headings=tuple(_strings(kept["headings"])),
        tabs=tuple(_strings(kept["tabs"])),
        grid=_optional(kept["grid"]),
        landmarks=tuple(_strings(kept["landmarks"])),
        version=_optional(kept["version"]),
    )


def effect_from(raw: object) -> Effect | None:
    kept = effect_kept(raw)
    if kept is None:
        return None
    return Effect(
        appeared=tuple(_seen_of(one) for one in _items(kept["appeared"], K_SEEN_ITEMS)),
        vanished=tuple(_seen_of(one) for one in _items(kept["vanished"], K_SEEN_ITEMS)),
        route_before=_optional(kept["route_before"]),
        route_after=_optional(kept["route_after"]),
        fields=tuple(
            FieldChange(str(one["label"]), str(one["change"]))
            for one in _items(kept["fields"], K_FIELD_CHANGES)
        ),
        requests_ms=_count(kept["requests_ms"]),
        mask_ms=_count(kept["mask_ms"]),
        quiet_ms=_count(kept["quiet_ms"]),
        ended=_optional(kept["ended"]),
        errors=tuple(_strings(kept["errors"])),
        shortcuts=tuple(_strings(kept["shortcuts"])),
    )


def choice_from(raw: object) -> Choice | None:
    kept = choice_kept(raw)
    if kept is None:
        return None
    return Choice(
        _optional(kept["chosen"]), _count(kept["index"]), tuple(_strings(kept["options"]))
    )


def cookies_from(raw: object) -> tuple[CookieSeen, ...]:
    return tuple(
        CookieSeen(
            str(one["name"]),
            float(one["expires_at"]) if isinstance(one["expires_at"], float) else None,
            _optional(one["domain"]),
            one["session"] is True,
        )
        for one in cookies_kept(raw)
    )
