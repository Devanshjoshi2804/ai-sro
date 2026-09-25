"""A policy stored before the tree capture was removed still loads.

Tree capture (`capture_snapshots`, `snapshot_max_per_minute`) is gone: the
screen outline replaced it and needs no switch. The two keys are not columns
but entries inside `observation_policies.policy`, so rows written before stay
as they were, and reading one must ignore them rather than fail.
"""

from __future__ import annotations

from sro.domain.observation.policy import ObservationPolicy
from sro.infrastructure.db.codec import load_policy


def test_a_stored_policy_with_the_old_tree_keys_still_loads() -> None:
    stored = {"capture_enabled": True, "capture_snapshots": True, "snapshot_max_per_minute": 20}

    assert load_policy(stored) == ObservationPolicy(capture_enabled=True)
