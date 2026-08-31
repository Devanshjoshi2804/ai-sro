"""Trees are read on the path a task takes when nobody deliberately taught it.

An accessibility tree is the one view that says what a control *is* rather than
where it happens to sit today, and induction builds a locator from it. Without
one a skill has only what the DOM offers: a css path of framework ids assigned
in render order -- `span#button-1350-btnIconEl` -- which is a different element
on the next page load.

Deliberate demonstration always took them. Passive observation did not, so every
skill that arrived the way this product intends -- watch the operator, notice the
repetition, offer it back -- got the weaker ladder, and the good locators were
reserved for the one path an operator has to remember to press a button for.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sro.application.capture.events import SnapshotEvent
from sro.application.observation.teach import _capture
from sro.domain.observation.candidate import Episode
from sro.domain.shared.identifiers import BatchId

DURING = Episode(
    started_at=datetime(2026, 8, 31, 7, 0, tzinfo=UTC),
    ended_at=datetime(2026, 8, 31, 7, 30, tzinfo=UTC),
    host="wms.example",
    batch_ids=(BatchId("bat-1"),),
)

TREE = {
    "nodes": [
        {
            "nodeId": "1",
            "role": {"value": "button"},
            "name": {"value": "Add"},
            "ignored": False,
            "childIds": [],
        }
    ]
}


def _snapshot(**over: object) -> dict[str, object]:
    return {
        "kind": "snapshot",
        "snapshot": TREE,
        "taken_at": "2026-08-31T07:10:00+00:00",
        "url": "https://wms.example/portal#work.operations",
        **over,
    }


def test_a_tree_captured_without_a_demonstration_is_still_read() -> None:
    """This is the whole point. The teach-from-a-candidate path passed over
    every snapshot it was given, so a task could be watched a hundred times,
    have a tree for every gesture, and still induce to css paths."""
    read = _capture(_snapshot(), DURING)

    assert isinstance(read, SnapshotEvent)
    assert read.snapshot.nodes


def test_a_tree_from_outside_the_episode_belongs_to_other_work() -> None:
    """The same rule gestures and calls go by. A window holds a day of somebody
    working; the episode is the doing of this one task, and a tree of the screen
    they were on twenty minutes later describes a different page."""
    assert _capture(_snapshot(taken_at="2026-08-31T09:00:00+00:00"), DURING) is None


def test_a_snapshot_the_browser_mangled_is_skipped_not_fatal() -> None:
    """One malformed event out of forty is not a reason to make somebody do the
    task again -- the same judgement the call path already makes."""
    assert _capture(_snapshot(snapshot="not a tree"), DURING) is None
    assert _capture(_snapshot(taken_at=None), DURING) is None
    assert _capture(_snapshot(taken_at="halfway through tuesday"), DURING) is None


def test_watching_does_not_debug_a_browser_nobody_agreed_to() -> None:
    """Off unless a tenant says otherwise, and the only capture setting that is.

    Trees come from `chrome.debugger`, and Chrome shows "AI-SRO is debugging
    this browser" for as long as anything is attached. A force-installed
    extension raises no banner -- the deployment this exists for -- but an
    unpacked copy does, and no extension can suppress it from inside.

    So this is an administrator's decision about a browser they manage, taken
    where the cost is written down, rather than a default an operator discovers
    on their own screen one morning.
    """
    from sro.domain.observation.policy import ObservationPolicy

    assert ObservationPolicy().capture_snapshots is False
    # Everything else it might have inherited a default from is on.
    assert ObservationPolicy().capture_screenshots is True


def test_trees_have_their_own_budget_not_the_screenshots() -> None:
    """A tree is a round trip and some JSON; a picture is a PNG. One shared
    counter would have whichever happened first spend the other's allowance,
    and the operator would see whichever they happened to trigger less."""
    from sro.domain.observation.policy import ObservationPolicy

    policy = ObservationPolicy(screenshot_max_per_minute=0, snapshot_max_per_minute=20)

    assert policy.screenshot_max_per_minute == 0
    assert policy.snapshot_max_per_minute == 20


def test_a_negative_budget_is_refused_like_every_other() -> None:
    from pytest import raises

    from sro.domain.observation.policy import ObservationPolicy
    from sro.domain.shared.errors import InvariantViolation

    with raises(InvariantViolation, match="snapshot_max_per_minute"):
        ObservationPolicy(snapshot_max_per_minute=-1)
