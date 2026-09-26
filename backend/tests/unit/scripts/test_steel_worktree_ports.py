"""Each worktree's own Steel gets a fixed pair of host ports.

Derived from the worktree's path so a second `make steel-up` lands on the same
pair, kept inside one range, and moved to the next pair when a port is taken.
"""

from __future__ import annotations

from pathlib import Path

from scripts.steel_worktree import K_FIRST_PORT, K_LAST_PORT, ports_for


def test_the_same_path_gets_the_same_pair_inside_the_range() -> None:
    root = Path("/work/AI-SRO-rt-steel-wt")
    api, cdp = ports_for(root, lambda _: True)
    assert (api, cdp) == ports_for(root, lambda _: True)
    assert cdp == api + 1
    assert K_FIRST_PORT <= api < cdp <= K_LAST_PORT


def test_different_worktrees_get_different_pairs() -> None:
    pairs = {ports_for(Path(f"/work/wt-{n}"), lambda _: True) for n in range(20)}
    assert len(pairs) > 1


def test_a_taken_port_moves_to_the_next_pair() -> None:
    root = Path("/work/AI-SRO-rt-steel-wt")
    api, cdp = ports_for(root, lambda _: True)
    moved = ports_for(root, lambda port: port != cdp)
    assert moved != (api, cdp)
    assert moved[1] == moved[0] + 1
    assert K_FIRST_PORT <= moved[0] < moved[1] <= K_LAST_PORT
    assert cdp not in moved


def test_the_last_pair_wraps_to_the_first() -> None:
    root = Path("/work/AI-SRO-rt-steel-wt")
    first = ports_for(root, lambda _: True)
    taken = set(range(first[0], K_LAST_PORT + 1))
    assert ports_for(root, lambda port: port not in taken) == (K_FIRST_PORT, K_FIRST_PORT + 1)
