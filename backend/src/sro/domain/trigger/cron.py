"""Enough of cron to refuse the expressions that are wrong.

Not an implementation: the scheduler that runs these owns the meaning, and a
second parser here would be a second opinion about when a warehouse gets
written to. This checks the shape, so a typed mistake is caught by the person
who typed it rather than by silence at three in the morning.
"""

from __future__ import annotations

import re

FIELDS = ("minute", "hour", "day of month", "month", "day of week")

_RANGES = ((0, 59), (0, 23), (1, 31), (1, 12), (0, 7))

_NAMES = {
    "month": ("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"),
    "day of week": ("sun", "mon", "tue", "wed", "thu", "fri", "sat"),
}

_TERM = re.compile(r"^(\*|\d+|[a-z]{3})(-(\d+|[a-z]{3}))?(/\d+)?$")


def why_not(expression: str) -> str | None:
    """The reason this is not a cron expression, or ``None`` when it is one."""
    fields = expression.split()
    if len(fields) != len(FIELDS):
        return f"a cron expression has five fields ({', '.join(FIELDS)}), not {len(fields)}"

    for field, name, (low, high) in zip(fields, FIELDS, _RANGES, strict=True):
        for term in field.split(","):
            reason = _term(term.strip().lower(), name, low, high)
            if reason is not None:
                return reason
    return None


def _term(term: str, name: str, low: int, high: int) -> str | None:
    if not term or not _TERM.match(term):
        return f"{term!r} is not something the {name} field can say"

    step = term.split("/", 1)
    if len(step) == 2 and int(step[1]) == 0:
        return f"a step of zero in the {name} field never comes round"

    for part in step[0].split("-"):
        if part == "*":
            continue
        if part.isdigit():
            if not low <= int(part) <= high:
                return f"{part} is outside {low}-{high} in the {name} field"
        elif part not in _NAMES.get(name, ()):
            return f"{part!r} is not a {name}"
    return None
