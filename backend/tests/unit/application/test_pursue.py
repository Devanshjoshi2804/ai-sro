"""An unknown task is pursued, not refused.

"Teach me this one" is a dead end wearing a polite face. A person put in front
of an unfamiliar WMS screen reads what is on it and works out which control does
the thing; the point of the last rung is to do the same, watched, and to keep
what it learns so the next time is a taught skill over the API.

What these test is where it stops: a goal is not permission.
"""

from __future__ import annotations

from sro.application.context import RequestContext
from sro.application.intent.plan_task import Proposal, ProposedStep
from sro.application.intent.pursue import Pursuit, compose
from sro.domain.knowledge.entry import EvidenceLevel
from tests import factories as f

CTX = RequestContext(tenant_id=f.TENANT, principal_id=f.OPERATOR)


def _proposal(*steps: ProposedStep) -> Proposal:
    return Proposal(steps=steps, sources=("index/app-map.json",))


def _step(what: str, detail: str) -> ProposedStep:
    return ProposedStep(
        what=what, detail=detail, source="index/app-map.json", evidence=EvidenceLevel.ASSERTED
    )


def test_a_write_is_never_pursued_without_being_asked() -> None:
    goal = compose(
        "create a transport mode called SROTEST9",
        _proposal(_step("the screen calls", "POST /data/WM/wm/transportModes")),
    )

    pursuit = Pursuit.of(CTX, goal)

    assert goal.changes_the_system
    assert pursuit.needs_confirmation
    assert pursuit.question and "say go" in pursuit.question


def test_a_read_is_simply_done() -> None:
    goal = compose(
        "how many transport modes are there",
        _proposal(_step("the screen calls", "GET /data/WM/wm/transportModes")),
    )

    assert not goal.changes_the_system
    assert not Pursuit.of(CTX, goal).needs_confirmation


def test_the_method_decides_rather_than_the_sentence() -> None:
    """A verb in a sentence is an opinion; a method is a fact.

    "Show me the adjustment screen" reads like a question and the endpoint
    behind it is a POST.
    """
    goal = compose(
        "show me the adjustment", _proposal(_step("the screen calls", "PUT /data/WM/wm/adjust"))
    )

    assert goal.changes_the_system


def test_an_unrecognised_sentence_is_treated_as_a_write() -> None:
    """The tie goes to caution: a confirmation nobody needed costs a click, and
    the alternative costs a warehouse changed without one."""
    assert compose("do the thing with the pallets", None).changes_the_system


def test_the_brief_carries_what_is_known_and_what_bites() -> None:
    goal = compose(
        "create a transport mode",
        _proposal(
            _step("open", "Configuration ▸ Partners ▸ Carriers"),
            _step("watch out", "a duplicate is blocked client-side with no network call"),
        ),
    )
    brief = goal.brief()

    assert "create a transport mode" in brief
    assert "Configuration" in brief
    # The trap has to reach the model, or it clicks Save and reports success.
    assert "blocked client-side" in brief
    assert "Do not navigate away" in brief
