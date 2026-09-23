from __future__ import annotations

from dataclasses import dataclass, field

from sro.application.context import RequestContext
from sro.application.intent.plan_task import Proposal


@dataclass(frozen=True, slots=True)
class Goal:
    intent: str

    start_url: str | None

    changes_the_system: bool

    facts: tuple[str, ...] = field(default_factory=tuple)

    fields: tuple[str, ...] = field(default_factory=tuple)

    watch_out: tuple[str, ...] = field(default_factory=tuple)

    def brief(self) -> str:
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
    facts = tuple(f"{step.what}: {step.detail}" for step in (proposal.steps if proposal else ()))
    return Goal(
        intent=intent.strip(),
        start_url=_start_url(proposal),
        changes_the_system=_writes(intent, proposal),
        facts=facts,
        fields=_fields(proposal),
        watch_out=_cautions(proposal),
    )


def _start_url(proposal: Proposal | None) -> str | None:
    for step in proposal.steps if proposal else ():
        if step.detail.startswith(("http://", "https://")):
            return step.detail.split()[0]
    return None


def _fields(proposal: Proposal | None) -> tuple[str, ...]:
    named: list[str] = []
    for step in proposal.steps if proposal else ():
        if step.what.lower().startswith(("fill in", "field", "enter")):
            named.extend(part.strip() for part in step.detail.split(",") if part.strip())
    return tuple(dict.fromkeys(named))[:6]


def _cautions(proposal: Proposal | None) -> tuple[str, ...]:
    return tuple(
        step.detail
        for step in (proposal.steps if proposal else ())
        if step.what.lower().startswith(("watch out", "quirk", "caution"))
    )


_READING = ("how many", "which", "list", "show", "what is", "are there", "count of")


def _writes(intent: str, proposal: Proposal | None) -> bool:
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


_ESSENTIAL = {
    "which": "which one",
    "where": "which site",
    "what": "what value",
}
