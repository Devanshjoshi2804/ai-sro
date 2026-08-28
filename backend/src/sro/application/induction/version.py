"""Which rules induction is running today.

Evidence that refused to induce is not refused forever: several times now a
defect in induction has been fixed and the same stored doings have become
learnable. A candidate remembers this number alongside how many doings its
last attempt saw, and `LearnWhatRepeats` retries it when either has moved --
there is new evidence, or there are new rules to read the old evidence with.

Bump it deliberately, like writing a migration, whenever induction changes such
that evidence which refused before may now induce: a fix to alignment, to
parameterisation, to what counts as optional. A bump costs one attempt per
waiting candidate. Not bumping costs a candidate sitting refused forever in
front of an operator while the code that could learn it is already merged.

Nothing else reads it, nothing derives it, and it does not mean "version of the
induction module" -- a refactor that changes no outcome leaves it alone.

Zero is not a value it takes: it is what a candidate carries when its last
attempt was made before any of this existed, which is why every candidate
already stored is worth exactly one more attempt.
"""

from __future__ import annotations

INDUCTION_VERSION = 1
"""1: optionality read across every doing of a candidate rather than the two
most recent (69ec07e), on top of the alignment fixes of the same day."""
