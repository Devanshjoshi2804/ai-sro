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
# out. 73.2%. The survivors clustered in `rig.api` (135) and `rig.window` (128)
# and were deliberately left where they are -- recording the baseline is the
# work; killing 661 mutants is its own.
#
# Re-measured 2026-09-05 over 381 tests: 2,815 mutants, 2,079 killed, 709
# survived. 74.6% -- the code added since was better covered than the average
# of what was already here, survivors rising by 48 while kills rose by 276.
#
# Then three rounds of reading the survivors and writing tests for what they
# named, over 395 tests: **76.4%**, 2,132 killed, 658 survived.
#
#     parameters   76.7% -> 98.3%   (14 survivors -> 1)
#     umbrella     71.7% -> 78.5%   (60 -> 46)
#     window       57.4% -> 64.9%   (124 -> 102)
#
# Each round found something a test could not have caught by being more
# thorough: `pack`'s budget branch was unreachable because K_MIN_GESTURES is 25
# and the fixture holds 7; `strength`, which decides what the model ever sees,
# had no tests at all; and `bounded_crossings` emptied its whole block when the
# best-evidenced crossing did not fit, which was a defect rather than a gap.
#
# What was deliberately NOT chased: mutants that cannot be killed. SQL keywords
# and `sqlite3.Row` keys are case-insensitive, so most of `workflows`' 56 are
# equivalent; every `raw.get(key, [])` in `umbrella._as_workflow` sits behind an
# `isinstance` guard, so its default is unreachable; and 83 of `as_evidence`'s
# are JSON key names, where pinning them would assert the shape of a prompt
# rather than a behaviour. Chasing those moves the number and catches nothing.
#
# Raised to 76.2 rather than 76.4: this is a ratchet against the suite getting
# weaker, not a target to sit exactly on, and a hair of room stops an unrelated
# refactor tripping it over rounding.
FLOOR = 76.2

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
