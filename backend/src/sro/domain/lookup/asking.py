from __future__ import annotations

DOING = frozenset(
    {
        "create",
        "add",
        "make",
        "new",
        "update",
        "change",
        "edit",
        "set",
        "delete",
        "remove",
        "cancel",
        "assign",
        "upload",
        "import",
        "export",
        "start",
        "run",
        "send",
        "submit",
        "approve",
        "release",
        "print",
        "close",
        "confirm",
        "fix",
        "do",
    }
)

ASKING = frozenset(
    {
        "what",
        "which",
        "where",
        "when",
        "who",
        "whose",
        "why",
        "how",
        "is",
        "are",
        "was",
        "were",
        "does",
        "do",
        "did",
        "can",
        "has",
        "have",
        "any",
    }
)

LOOKING = frozenset(
    {
        "find",
        "search",
        "look",
        "check",
        "show",
        "list",
        "get",
        "fetch",
        "tell",
        "status",
        "count",
    }
)


def is_a_question(said: str) -> bool:
    words = [word.strip(",.?!\"'()[]:;").lower() for word in said.split()]
    words = [word for word in words if word]
    if not words:
        return False

    first = words[0]
    if first in DOING:
        return False
    if first in ("please", "could", "would", "can", "pls", "plz", "hey", "ok") and len(words) > 1:
        rest = (
            words[1] if words[1] not in ("you", "we", "i") else (words[2] if len(words) > 2 else "")
        )
        if rest in DOING:
            return False
        if rest in LOOKING or rest in ASKING:
            return True
    if first in ASKING or first in LOOKING:
        return True
    return said.rstrip().endswith("?")
