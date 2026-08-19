"""Where the values of a field come from, when the screen offered a list.

A demonstration writes to `/wm/addresses/A000144886`. Replayed literally, every
run writes to that one address. Turned into a parameter, an operator is asked
for an id nobody has ever memorised -- which is the same failure with a politer
face, because the answer they would have to look up is on the screen the
demonstration already read.

The screen is the answer. That address was a dropdown, and the dropdown was
filled by a call this recording captured -- session, site parameters, filter
dialect and all. So the field stays a dropdown: the console asks the system
what the options are, the operator picks one the way they did when they taught
it, and the id nobody remembers travels with the pick.

Which call, which fields to show and which field the create actually needs are
all read off the demonstration. Nothing is inferred at run time.
"""

from __future__ import annotations

from dataclasses import dataclass

from sro.domain.shared.errors import InvariantViolation
from sro.domain.skill.plan import HeaderPlan


@dataclass(frozen=True, slots=True)
class Options:
    """Where the values of a parameter come from, live.

    The field the operator is filling in was a dropdown on the screen, and that
    dropdown was filled by a call. Asking somebody to type the address line, or
    the id behind it, is asking them to reproduce from memory what the form
    would have handed them -- and the call that fills it is in the recording,
    with its session, its site parameters and its filter dialect.

    So a parameter carries where its options come from, the console asks for
    them when it draws the field, and what the operator picks is the record's
    own id. The mandatory fields of a create stop being things to remember and
    go back to being things to choose.
    """

    url: str
    """The listing call, as the demonstration made it. ``${query}`` where the
    operator's own search terms went, if the endpoint took any."""

    label: tuple[str, ...]
    """Fields to show, in order. An address is `APPLIANCE HAUS -- 10880 BAYVIEW
    AVENUE`, because one field alone was not enough to tell four of them apart."""

    value: str
    """The field the call underneath actually needs: `addressId`."""

    search: str | None = None
    """The field the endpoint filters on, where it filters at all. Without one
    the whole page is fetched and narrowed here."""

    headers: tuple[HeaderPlan, ...] = ()
    """What the demonstration sent with it -- the session cookie, the site, the
    anti-forgery token -- resolved the same way every other call in the skill
    resolves them. Without these the collection answers with a login page, and
    a dropdown that is silently empty is worse than one that fails."""

    def __post_init__(self) -> None:
        if not self.label:
            raise InvariantViolation("options with nothing to show are a list of blank rows")
        if not self.value.strip():
            raise InvariantViolation("options must say which field carries the value")
