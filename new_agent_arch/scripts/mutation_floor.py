"""The mutation score, against the floor it may not fall below.

    uv run mutmut run
    uv run mutmut export-cicd-stats
    uv run python scripts/mutation_floor.py

A passing suite says the code does what the tests say. A mutation score says
whether the tests would notice if it stopped. Most of the real defects this
project has found were found by hand-deleting a guard and seeing that nothing
failed; this is that sweep, automated, over every mutable line.

The floor is a ratchet, not a target. It is set to the measured baseline, so
the number can only go up: a change that leaves more mutants alive than the
last measurement fails here, and raising the floor after genuinely improving
the suite is a deliberate edit to the line below.

Do NOT lower it to make a build pass. If the score dropped, the tests got
weaker -- that is the finding, not the obstacle.
"""

from __future__ import annotations

import json
import pathlib
import sys

# Measured on 2026-09-04, over a suite of 333 tests: 2,488 mutants, 1,803
# killed, 661 survived, 13 with no test covering them at all and 11 that timed
# out. 73.2%. The survivors cluster in `rig.api` (135) and `rig.window` (128)
# and were deliberately left where they are -- recording the baseline is the
# work; killing 661 mutants is its own.
FLOOR = 73.0

STATS = pathlib.Path(__file__).resolve().parent.parent / "mutants" / "mutmut-cicd-stats.json"


def main() -> int:
    if not STATS.exists():
        print(f"no mutation stats at {STATS} -- run `mutmut run` then `mutmut export-cicd-stats`")
        return 2

    stats = json.loads(STATS.read_text())
    killed, survived = stats["killed"], stats["survived"]
    # Killed over killed-plus-survived, so a mutant nothing could reach --
    # skipped, timed out, no test covers the line -- neither flatters the score
    # nor is silently counted as a pass.
    considered = killed + survived
    if not considered:
        print("no mutants were run")
        return 2

    score = 100 * killed / considered
    print(f"mutation score {score:.1f}% ({killed} killed, {survived} survived) -- floor {FLOOR}%")
    for name in ("no_tests", "skipped", "suspicious", "timeout", "segfault"):
        if stats.get(name):
            print(f"  {name}: {stats[name]}")

    if score < FLOOR:
        print(f"FAILED: the suite got weaker. {FLOOR - score:.1f} points below the floor.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
