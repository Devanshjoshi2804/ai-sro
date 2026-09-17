"""What a run found out about a step, kept for the next one.

`mark_stale` is this module's negative twin: a step that only the weakest rung
could find is recorded as about to break. Nothing recorded what the rung
actually FOUND, so the discovery lived for one command and the next run climbed
the same ladder to reach the same control.

Measured on the deployment, 2026-09-17. `Create a Customer Type` step 2 clicks
a tab whose recorded identity no longer matches anything: three runs in one
afternoon paid for two model calls each, worked out that the control is called
"Customer Types", and wrote it into a log line. At the end of the afternoon the
job knew exactly what it knew at the start. That is not a system that learns --
it is one that repeats.

**What is kept is a locator, not a point.** A point is where a control was on
one screen at one size; a name is what it is. The rung that looks at a picture
is the expensive one and the only one that can recover from a page that moved,
so its answer is the one worth keeping -- as `text=Customer Types`, which every
run after it can try first for the price of a DOM query.

**A run may write this and may not write the workflow.** The workflow is what a
mining pass produces from evidence; this is what one run observed, and the two
are kept apart so neither rewrites the other. Same reason the stale table
exists, and the same shape: one row per step, the last answer winning.
"""

from __future__ import annotations

from dataclasses import dataclass

K_NAME = 80
"""How much of a control's name is kept. A button's accessible name is a few
words; eighty characters is a label, and anything longer is a paragraph that
happens to sit in a `<div>`."""

WORTH_KEEPING = ("sight", "css_path", "text")
"""The rungs whose answer is worth writing down.

`component` and `test_id` are the job's own recorded identity -- when they
match, the job is right and there is nothing to learn. These three are what a
run falls back to when it is not, and `sight` is the one that costs a model
call and a picture.
"""


@dataclass(frozen=True, slots=True)
class LearnedStep:
    """One step, and the locator that last worked for it."""

    ord: int
    strategy: str
    query: str
    found_by: str
    """Which rung produced it, so a reader can tell a name a picture found from
    one a css path did."""

    @property
    def usable(self) -> bool:
        return bool(self.strategy and self.query)


def learned_from(ord_: int, matched_by: str | None, result: object) -> LearnedStep | None:
    """What this step's reply is worth keeping, or None.

    Nothing is kept for a step the job's own identity found: that is the
    ordinary case and writing it down would be the job telling itself what it
    already says. Nothing is kept from a reply that names no control either --
    a run cannot pass on what it did not learn.
    """
    if matched_by not in WORTH_KEEPING or not isinstance(result, dict):
        return None
    control = result.get("control")
    matched = result.get("matched")
    # The locator that worked, where the browser named one: a css path that
    # matched is a css path worth trying first next time.
    if isinstance(matched, dict) and matched.get("strategy") in WORTH_KEEPING:
        strategy, query = str(matched.get("strategy") or ""), str(matched.get("query") or "")
        if strategy and query:
            return LearnedStep(ord_, strategy, query[:K_NAME], str(matched_by))
    # Otherwise the control the point turned out to be, named. This is the
    # sight rung's answer turned into something cheap.
    if isinstance(control, dict):
        name = str(control.get("name") or "").strip()
        item_id = str(control.get("item_id") or "").strip()
        if item_id:
            return LearnedStep(ord_, "component", item_id[:K_NAME], str(matched_by))
        if name:
            return LearnedStep(ord_, "text", name[:K_NAME], str(matched_by))
    return None
