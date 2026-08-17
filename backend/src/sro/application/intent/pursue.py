"""Do it anyway: pursue a goal nobody has demonstrated.

The console's honest answer to an unknown task used to be "teach me this one",
and for an operator with a job to finish that is a dead end wearing a polite
face. A person put in front of an unfamiliar WMS screen does not refuse; they
read what is on it, work out which control does the thing, and do it.

So this composes what is known into a goal and drives the browser toward it:
the screen the knowledge base says the entity lives on, the fields its form
declares, the endpoint that would confirm it worked, the quirks somebody has
already been caught by. The model chooses gestures; every one of them is
executed by the same driver a taught skill uses, against the same guards.

Two things make this safe enough to exist.

**A goal is not permission.** A pursuit that would change the system stops and
shows what it is about to do. The operator's confirmation is what an assisted
run has always required, and nothing here weakens it.

**A pursuit is a demonstration.** Every gesture and every call is captured
exactly as a taught session is, so a task done this way once can be induced
into a skill and done over the API the next time. That is the whole point: the
slow rung exists to make itself unnecessary.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sro.application.context import RequestContext
from sro.application.intent.plan_task import Proposal


@dataclass(frozen=True, slots=True)
class Goal:
    """What to accomplish, said the way a person would say it to a colleague.

    Composed rather than generated: every line of it comes from something
    observed -- a screen in the catalogue, a field in a form model, an endpoint
    somebody's run has answered. A goal made up of guesses would be a model
    inventing a warehouse task, which is the failure this whole system is
    arranged against.
    """

    intent: str
    """The operator's own sentence. Kept verbatim -- it is the only part that
    says what they actually wanted."""

    start_url: str | None
    """Where to begin, when the knowledge base knows the screen."""

    changes_the_system: bool
    """Whether achieving this would write. Decides whether a confirmation is
    required before anything is done, not whether it may be attempted."""

    facts: tuple[str, ...] = field(default_factory=tuple)
    """What is known about doing this here, each traceable to a source."""

    watch_out: tuple[str, ...] = field(default_factory=tuple)
    """Quirks already paid for by somebody. A duplicate transport mode is
    blocked client-side with no network call at all -- a model that does not
    know this will click Save and conclude it worked."""

    def brief(self) -> str:
        """The goal as the model receives it."""
        lines = [f"Goal: {self.intent}"]
        if self.facts:
            lines.append("What is known about this system:")
            lines.extend(f"- {fact}" for fact in self.facts)
        if self.watch_out:
            lines.append("Known traps:")
            lines.extend(f"- {trap}" for trap in self.watch_out)
        lines.append(
            "Work on the screen in front of you. Do not navigate away from this system. "
            "Say done only when the screen shows the result, not when you have clicked."
        )
        return "\n".join(lines)


def compose(intent: str, proposal: Proposal | None) -> Goal:
    """Turn what is known into something a browser can be pointed at."""
    facts = tuple(f"{step.what}: {step.detail}" for step in (proposal.steps if proposal else ()))
    return Goal(
        intent=intent.strip(),
        start_url=_start_url(proposal),
        changes_the_system=_writes(intent, proposal),
        facts=facts,
        watch_out=_cautions(proposal),
    )


def _start_url(proposal: Proposal | None) -> str | None:
    """The screen the catalogue says this lives on, if it named one."""
    for step in proposal.steps if proposal else ():
        if step.detail.startswith(("http://", "https://")):
            return step.detail.split()[0]
    return None


def _cautions(proposal: Proposal | None) -> tuple[str, ...]:
    """Quirks somebody has already been caught by."""
    return tuple(
        step.detail
        for step in (proposal.steps if proposal else ())
        if step.what.lower().startswith(("watch out", "quirk", "caution"))
    )


_READING = ("how many", "which", "list", "show", "what is", "are there", "count of")


def _writes(intent: str, proposal: Proposal | None) -> bool:
    """Whether pursuing this would change anything.

    Read off the proposal's own endpoints where there are any, because a method
    is a fact and a verb in a sentence is an opinion. Where there are none, the
    sentence is all there is -- and the tie is broken towards "this writes",
    since the cost of asking for a confirmation nobody needed is a click, and
    the cost of not asking is a warehouse changed without one.
    """
    if proposal is not None and proposal.steps:
        methods = {
            word
            for step in proposal.steps
            for word in step.detail.split()[:1]
            if word.isupper() and word.isalpha()
        }
        if methods:
            return bool(methods - {"GET", "HEAD", "OPTIONS"})
    lowered = intent.strip().lower()
    return not any(lowered.startswith(opening) for opening in _READING)


@dataclass(frozen=True, slots=True)
class Pursuit:
    goal: Goal
    needs_confirmation: bool
    question: str | None = None

    @classmethod
    def of(cls, ctx: RequestContext, goal: Goal) -> Pursuit:
        """A pursuit, and whether it may start without being asked twice."""
        if not goal.changes_the_system:
            return cls(goal=goal, needs_confirmation=False)
        return cls(
            goal=goal,
            needs_confirmation=True,
            question=(
                f"Nobody has demonstrated that, so I would work it out on the screen: "
                f"{goal.intent}. It changes the system, so say go and I will do it while "
                "you watch — and I will keep what I learn so it is a taught skill next time."
            ),
        )
