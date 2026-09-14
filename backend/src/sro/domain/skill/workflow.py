"""What a proven workflow is, and where it lives."""

from __future__ import annotations

import re
import secrets
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # Under `TYPE_CHECKING` for a cycle, not for load time: `repeats.detect`
    # reads a step's recorded call, `evidence` is where that lives, and
    # `evidence` imports this module for `Step`. The annotation is a string
    # either way -- `from __future__ import annotations` is the first line of
    # this file -- and nothing here resolves it at runtime.
    from sro.domain.skill.repeats import Repeat

K_MIN_VALUE_LENGTH = 3
"""How long a parameter value has to be before a title repeating it is quoting
it rather than coinciding with it. `DSS` and `DDD` name a customer type and an
equipment type; a voice code of `2` is a value too, and a title is allowed to
contain the word "3"."""

_DANGLING = frozenset(
    {"a", "an", "the", "and", "at", "by", "for", "from", "in", "of", "on", "to", "with"}
)
"""What a title is left ending on once a value is taken out of it: "Create a
Carrier Cross Reference for Test Drive LLC" loses the customer and keeps the
`for`."""


def new_workflow_id() -> str:
    return "wfl_" + secrets.token_hex(16)


@dataclass
class Step:
    order: int
    says: str
    system: str | None
    # Every step cites the gestures that prove it. Free-generated workflow JSON
    # hallucinated up to 21% of steps; forced to select from real evidence, that
    # fell below 7.5%. An uncited step is a rejected step -- see checks.py.
    cites: list[str] = field(default_factory=list)
    parameters: list[str] = field(default_factory=list)


@dataclass
class Workflow:
    id: str
    tenant: str
    title: str
    narrative: str
    systems: list[str] = field(default_factory=list)
    steps: list[Step] = field(default_factory=list)
    parameters: list[dict[str, object]] = field(default_factory=list)
    shape_key: list[list[str]] = field(default_factory=list)
    # The model's opinion about whether this is one it has proposed before. It is
    # recorded and it decides nothing: a model re-judging its own earlier verdict
    # disagrees with itself at roughly 90%. identity.py decides.
    same_as: str | None = None
    unproven: list[str] = field(default_factory=list)
    # The pass that found it. A workflow has no cost of its own -- one model
    # call proposes all of them -- so it names the row that does rather than
    # carrying a copy of the bill that three workflows would then sum to three
    # times. Empty for a workflow saved outside a pass, which today is only a
    # test.
    pass_id: str = ""

    repeat: Repeat | None = None
    """The steps done once per thing on a list, where this job has them.

    `None` is every job mined before this existed and every job that does one
    thing once, which is most of them. What repeats is a fact about the JOB;
    how many times is a fact about the request, and a run of a repeating job
    given one item performs exactly like a run of a job with no repeat at all.
    See `domain/skill/repeats`."""

    def generalise_title(self) -> None:
        """This job's own parameter values taken out of its name.

        The title is written by a model reading ONE doing, so it names that
        doing: "Create Customer Type DSS" for a job whose customer type has
        since been observed as DSS, DPP, CCD and CCF. Every later doing then
        looks like a different job to the person reading the offer card, which
        is the thing the title is for -- and `sro.domain.chat.reading` carries
        a paragraph of prompt whose only job is teaching the chat door to see
        past it.

        The moment a value is PROVEN to vary is the moment its presence in the
        title is known to be wrong, so this belongs beside the parameters
        rather than in the prompt alone: a model told to generalise still
        cannot tell a parameter from a constant on one doing. Whole words
        only, longest value first, and a title that turns out to be nothing
        but its values is left alone -- a job with a bad name beats a job with
        no name.
        """
        seen: list[str] = []
        for parameter in self.parameters:
            values = parameter.get("seen_values")
            if isinstance(values, list):
                seen += [str(value).strip() for value in values]

        title = self.title
        for value in sorted(set(seen), key=len, reverse=True):
            if len(value) < K_MIN_VALUE_LENGTH:
                continue
            title = re.sub(rf"(?<!\w){re.escape(value)}(?!\w)", " ", title, flags=re.IGNORECASE)

        words = " ".join(title.split()).strip(" -:,").split()
        while words and words[-1].lower() in _DANGLING:
            words.pop()
        tidied = " ".join(words).strip(" -:,")
        if tidied:
            self.title = tidied


def cited_ids(workflow: Workflow) -> set[str]:
    return {gesture_id for step in workflow.steps for gesture_id in step.cites}


def ordered_cites(workflow: Workflow) -> list[str]:
    """Every gesture the workflow cites, in step order.

    `cited_ids` is a set, and a shape key made in set order is not this job's
    shape -- the key is a SEQUENCE of (system, control, kind), so the order the
    steps run in is half of what it says. Here rather than beside either
    caller: the mining pass writes a shape key and `rekey_workflows` rewrites
    one, and two spellings of "in step order" is two shapes for one job.
    """
    return [cited for step in sorted(workflow.steps, key=lambda s: s.order) for cited in step.cites]
