from __future__ import annotations

from datetime import timedelta
from email.utils import getaddresses, parseaddr

SERVER = "gmail"

K_REMEMBER = timedelta(days=30)


def sent_to_others(sender: str, to: str, cc: str, mailbox: str) -> tuple[str, ...]:
    me = mailbox.strip().casefold()
    if not me or parseaddr(sender)[1].casefold() != me:
        return ()
    return tuple(
        address for _, address in getaddresses([to, cc]) if address and address.casefold() != me
    )
