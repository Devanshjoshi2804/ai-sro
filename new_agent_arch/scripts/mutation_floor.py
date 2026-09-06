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
#
# Then two plans landed -- the runner's loop, the planner, the verifier, runs,
# entry, effects, shapes, offers -- adding ~2,700 mutants of code whose tests
# killed fewer of them than the suite's average. 2026-09-06, over 534 tests:
# **74.1%**, 3,768 killed, 1,318 survived. The score fell without a single test
# breaking, which is the whole reason this file exists.
#
# Re-measured the same day over 592 tests: **79.45%**, 4,041 killed, 1,045
# survived. 273 more mutants dead, and the reading of the 602 survivors that
# found them says something about where a suite goes thin: almost every kill
# was a private helper with no test of its own, exercised only through the
# integration test of whatever calls it.
#
#     runner._look      ~40 mutants, no direct test at all
#     planner            55 real of 101, mostly the five ways out of plan_step
#     verify             55 real of 92, one belt at a time
#     locators           20 real of 26
#
# What was deliberately NOT chased, on top of the list above: `runs` is 73
# equivalent mutants out of 85 (it is almost entirely SQL and `sqlite3.Row`
# reads, both case-insensitive), `effects` 18 of 19, and ~100 real ones inside
# `run_workflow`'s own loop, each of which needs a whole scripted run to reach.
# Those are the next round's, not this one's.
#
# 79.4 rather than 79.45: the floor is the measured score rounded DOWN, so the
# very run that set it cannot fail against it on the printed rounding.
FLOOR = 79.4

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
