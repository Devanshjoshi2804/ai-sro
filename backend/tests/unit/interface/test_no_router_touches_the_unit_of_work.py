"""AGENTS.md's mechanical check, run instead of trusted to memory.

A router that opens its own unit of work is a read the application layer never
saw -- this is the audit finding that put the rule there. import-linter checks
which modules a layer may import, not which methods it calls once imported, so
it cannot see a router that legitimately imports `Container` for dependency
injection and then reaches past the use cases it hands out. This is the only
gate narrow enough to catch that.

`app.py` and `secrets.py` are pre-existing offenders outside this change's
scope, named here the way the mypy gate names its two pre-existing errors:
tolerated, not silently allowed to spread.
"""

from __future__ import annotations

from pathlib import Path

INTERFACE = Path(__file__).resolve().parents[3] / "src" / "sro" / "interface"

ROUTERS = INTERFACE / "http" / "v1" / "routers"

PRE_EXISTING = {
    INTERFACE / "http" / "v1" / "routers" / "secrets.py",
    INTERFACE / "http" / "app.py",
}


def test_no_router_calls_unit_of_work_directly() -> None:
    offenders = {
        path
        for path in ROUTERS.rglob("*.py")
        if "unit_of_work()" in path.read_text(encoding="utf-8")
    } - PRE_EXISTING

    assert offenders == set(), (
        "a router calls container.unit_of_work() directly: "
        f"{sorted(str(path) for path in offenders)}. Reads and writes belong to "
        "a use case in sro.application, called through the container."
    )


def test_the_pre_existing_exceptions_have_not_grown() -> None:
    still_offending = {
        path
        for path in INTERFACE.rglob("*.py")
        if "unit_of_work()" in path.read_text(encoding="utf-8")
    }

    assert still_offending <= PRE_EXISTING, (
        "a file outside the known pre-existing exceptions now calls "
        f"unit_of_work(): {sorted(str(p) for p in still_offending - PRE_EXISTING)}. "
        "If this is a genuine new exception, name it in PRE_EXISTING; otherwise "
        "route the call through a use case."
    )
