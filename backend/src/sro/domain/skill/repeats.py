"""A job whose middle is done once per thing on a list.

"Add these three equipment types" is one job. Until this existed the rig could
only say it was a job that adds ONE -- so a mail carrying three rows produced
one run that created the first, and an operator did the other two by hand while
watching a browser that had just proved it could do them.

**The list is a person's, and that is the whole of the first version.** The
items come from what somebody wrote -- a mail the browser matched, a sentence
typed into the panel -- so the count is a human's rather than a guess, and
getting the block wrong costs three wrong records instead of forty. The other
source, the list a page fetched for itself, is the more powerful one and is
deliberately not this: it needs the list call to have been captured, it needs a
re-read at run time, and its count is whatever the warehouse answers that day.
`domain/skill/loop.py` is that shape, for skills, and is where it goes when the
machinery here has done real work.

**The body is contiguous.** A block with a hole in it is two blocks somebody
has to be able to see separately, which is the same rule `Loop` states for the
same reason.

**Nothing here is the runner's decision.** What repeats is a fact about the
job; how many times is a fact about the request. A workflow with a `Repeat` and
a run given one item runs exactly like a workflow without one.
"""

from __future__ import annotations

from dataclasses import dataclass

from sro.domain.shared.errors import InvariantViolation

K_MOST_ITEMS = 25
"""How many times one run may do the body before a person is asked again.

Not a performance limit -- a limit on what one press can mean. An operator
pressing yes on "add these" has read a mail with a handful of rows in it; a
list of two hundred is either a mistake or a different decision, and the run
that would make two hundred records is not the one they authorised. The cap is
here rather than in the runner because it is part of what a repeat IS: the
runner asks the domain rather than carrying a number of its own.
"""


@dataclass(frozen=True, slots=True)
class Repeat:
    """The steps of a job that are done once per item, inclusive."""

    first_step: int
    last_step: int

    def __post_init__(self) -> None:
        if self.first_step < 0:
            raise InvariantViolation("a repeated block starts at a step that exists")
        if self.last_step < self.first_step:
            raise InvariantViolation("a repeated block ends before it begins")

    def covers(self, order: int) -> bool:
        return self.first_step <= order <= self.last_step

    @property
    def steps(self) -> int:
        return self.last_step - self.first_step + 1
