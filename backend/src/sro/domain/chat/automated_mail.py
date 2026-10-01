"""A machine's mail is never answered and never read for work (RFC 3834).

An auto-reply, a bounce, a list or bulk mail and an alert can all carry a body that looks
like a request ("Location: A1 / Action: add customer type GT2"). Answering one starts a
mail loop, and reading one for work starts a run nobody asked for. Headers say what a mail
is; the body never does.
"""

from __future__ import annotations

from collections.abc import Mapping
from email.utils import parseaddr

# Headers whose mere presence marks a mail as automated.
_PRESENT = ("x-auto-response-suppress", "list-unsubscribe", "x-autoreply", "x-autorespond")
_BULK = frozenset({"bulk", "junk", "list"})
_MACHINES = frozenset({"mailer-daemon", "postmaster"})


def is_automated(sender: str, headers: Mapping[str, str]) -> bool:
    said = {str(name).lower(): str(value).strip() for name, value in headers.items()}
    submitted = said.get("auto-submitted", "").lower()
    if submitted and submitted != "no":
        return True
    if any(name in said for name in _PRESENT):
        return True
    if said.get("precedence", "").lower() in _BULK:
        return True
    if said.get("content-type", "").lower().startswith("multipart/report"):
        return True
    address = parseaddr(sender)[1].lower()
    return address.split("@", 1)[0] in _MACHINES
