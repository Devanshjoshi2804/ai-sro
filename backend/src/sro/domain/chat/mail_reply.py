"""What a person typed in a reply, without the mail it quotes."""

import re

_ORIGINAL = re.compile(r"\s*-{2,}\s*(?:Original|Forwarded) Message\s*-{2,}\s*", re.IGNORECASE)
_WROTE = re.compile(r"On .{1,200}wrote:\s*", re.DOTALL)
_HEADER = re.compile(r"\s*From:\s.+")
_RULE = re.compile(r"\s*_{5,}\s*")
_HEADERS = re.compile(r"\s*(?:Sent|Date|To|Subject):\s", re.IGNORECASE)


def without_the_quote(body: str) -> str:
    """Drops `>` lines, an "On ... wrote:" attribution, and everything under an
    original-message or `From:/Sent:` header block (a top-posted quote)."""
    lines = body.replace("\r\n", "\n").split("\n")
    kept: list[str] = []
    skip = 0
    for at, line in enumerate(lines):
        if skip:
            skip -= 1
        elif _ORIGINAL.fullmatch(line) or (
            _HEADER.fullmatch(line) and any(_HEADERS.match(one) for one in lines[at + 1 : at + 4])
        ):
            break
        elif _WROTE.fullmatch(line):
            continue
        elif _WROTE.fullmatch(" ".join(lines[at : at + 2])):
            skip = 1
        elif not line.lstrip().startswith(">") and not _RULE.fullmatch(line):
            kept.append(line)
    return "\n".join(kept).strip()
