"""The mutation score for the skill application package, against its floor.

    uv run mutmut run
    uv run mutmut export-cicd-stats
    uv run python scripts/mutation_floor.py

A passing suite says the code does what the tests say. A mutation score says
whether the tests would notice if it stopped.

**Scoped to `sro/application/skill/`, not the whole backend.** These modules turn
a model's reading of a captured day into a Skill the runner executes, they parse
untrusted JSON out of a column at every step, and they are the newest code here.
Widening this to `src/sro/` would mutate 297 files against a 30-second suite --
a different tool with a different cost. This one has to stay cheap enough to run
while a change is still in the working tree.

The floor is a ratchet, not a target. It is set just under the measured
baseline, so the number can only go up: a change that leaves more mutants alive
than the last measurement fails here, and raising the floor after genuinely
improving the suite is a deliberate edit to the line below.

Do NOT lower it to make a build pass. If the score dropped, the tests got
weaker -- that is the finding, not the obstacle.
"""

from __future__ import annotations

import json
import pathlib
import sys

# Measured 2026-09-05 over the 1,489-test unit suite: 1,622 mutants, 1,371
# killed, 251 survived, 58 with no test covering them. **84.5%**.
#
# The first sweep of the four bridge modules read far worse -- `from_rig` 57.8%,
# `network_from_rig` 63.3% -- and almost every survivor was a JSON key spelled
# in the wrong case. Unlike SQL keywords or `sqlite3.Row` keys, a Python dict is
# case-sensitive, so `component.get("ITEMID")` returns None and the field simply
# vanishes into a perfectly valid object built around the hole. `fingerprint_for`
# assembles eight signals a driver finds a control by, `_component` seven more
# and `request_from_rig` about fifteen, and not one of them was asserted end to
# end. Field-by-field round trips took those two to 90.0% and 86.3%.
#
#     from_rig             90.0%      network_from_rig     86.3%
#     repair_drift         87.3%      adopt_rig_workflow   86.1%
#     map_step_to_tool     82.0%      read_doings          81.6%
#     version_from_rig     80.5%      read_skills          78.6%
#     add_assertion        75.7%      promote_skill        69.6%
FLOOR = 84.3

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
