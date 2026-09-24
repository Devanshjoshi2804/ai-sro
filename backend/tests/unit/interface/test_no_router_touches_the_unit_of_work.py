from __future__ import annotations

from pathlib import Path

INTERFACE = Path(__file__).resolve().parents[3] / "src" / "sro" / "interface"


def test_nothing_under_interface_calls_unit_of_work_directly() -> None:
    offenders = sorted(
        str(path)
        for path in INTERFACE.rglob("*.py")
        if "unit_of_work()" in path.read_text(encoding="utf-8")
    )

    assert offenders == []
