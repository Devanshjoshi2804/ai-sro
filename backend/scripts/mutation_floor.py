from __future__ import annotations

import pathlib
import re
import subprocess
import sys

FLOORS = {
    "sro.application.skill": (85.6, "the bridge -- a model's reading into a runnable Skill"),
    "sro.domain.execution": (91.5, "the ladder -- what may write, and what proves it landed"),
    "sro.application.execution": (92.8, "the step -- what this run sends, and what settles it"),
    "sro.domain.skill.shape": (99.8, "the offer -- which jobs a browser is shown, and where"),
}

STATS = pathlib.Path(__file__).resolve().parent.parent / "mutants" / "mutmut-cicd-stats.json"

RESULT = re.compile(r"^\s+(?P<name>\S+): (?P<status>.+)$")


def _results() -> list[tuple[str, str]]:
    listed = subprocess.run(
        [sys.executable, "-m", "mutmut", "results", "--all", "true"],
        capture_output=True,
        text=True,
        check=False,
        cwd=STATS.parent.parent,
    )
    if listed.returncode != 0:
        print(f"`mutmut results` failed:\n{listed.stderr.strip()}")
        return []
    found = []
    for line in listed.stdout.splitlines():
        if match := RESULT.match(line):
            found.append((match["name"], match["status"].strip()))
    return found


def main() -> int:
    if not STATS.exists():
        print(f"no mutation stats at {STATS} -- run `mutmut run` then `mutmut export-cicd-stats`")
        return 2

    results = _results()
    if not results:
        print("no mutants were run")
        return 2

    worst = 0
    for area, (floor, what) in FLOORS.items():
        mine = [status for name, status in results if name.startswith(area + ".")]
        killed = sum(1 for status in mine if status == "killed")
        survived = sum(1 for status in mine if status == "survived")
        considered = killed + survived
        if not considered:
            print(f"{area}: no mutants were run")
            worst = max(worst, 2)
            continue
        score = 100 * killed / considered
        print(f"{area}  {score:.1f}%  ({killed} killed, {survived} survived)  floor {floor}%")
        print(f"    {what}")
        unreachable = len(mine) - considered
        if unreachable:
            print(f"    {unreachable} mutants no test reaches at all")
        if score < floor:
            print(f"    FAILED: the suite got weaker. {floor - score:.1f} points below the floor.")
            worst = max(worst, 1)

    named = sum(len([1 for name, _ in results if name.startswith(area + ".")]) for area in FLOORS)
    if named < len(results):
        print(f"FAILED: {len(results) - named} mutants are in no scored area")
        worst = max(worst, 1)
    return worst


if __name__ == "__main__":
    sys.exit(main())
