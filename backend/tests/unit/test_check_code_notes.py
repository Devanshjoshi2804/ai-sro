"""`scripts/check_code_notes.py` against a tiny, hand-built repo tree.

Not `sro.*`: the checker lives in `backend/scripts/`, which -- like every
other script there -- has no `__init__.py` and is run as a file, not
imported as a package. Loaded here by path instead.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "check_code_notes.py"


def _load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_code_notes", _SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # dataclasses resolves deferred annotations via sys.modules
    spec.loader.exec_module(module)
    return module


check_code_notes = _load_script()


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_check_then_fix_over_a_tiny_tree(tmp_path: Path) -> None:
    repo = tmp_path

    # Two blank lines pushed everything below down by two -- the ordinary
    # drift the checker exists to catch.
    _write(
        repo / "backend/src/sro/pkg/mod.py",
        '\n\nCOUNT = 1\n\n\nclass Greeter:\n    def hello(self) -> str:\n        name = "world"\n'
        '        pass\n        pass\n        return f"hello {name}"\n',
    )
    _write(
        repo / "docs/code-notes/backend/src/sro/pkg/mod.py.md",
        "# Notes for `backend/src/sro/pkg/mod.py`\n\n"
        "## module, [line 1](../../../../../backend/src/sro/pkg/mod.py#L1): Docstring\n\n"
        "> Fixed at the top by convention -- never stale.\n\n"
        "## `COUNT`, [line 1](../../../../../backend/src/sro/pkg/mod.py#L1): Constant\n\n"
        "Code: `COUNT = 1`\n\n"
        "> Was line 1, drifted to line 3.\n\n"
        "## `Greeter`, [line 4](../../../../../backend/src/sro/pkg/mod.py#L4): Class\n\n"
        "> Was line 4, drifted to line 6.\n\n"
        "## `Greeter.hello`, [line 5](../../../../../backend/src/sro/pkg/mod.py#L5): Function\n\n"
        "> Was line 5, drifted to line 7.\n\n"
        "## `Greeter.hello`, [line 7](../../../../../backend/src/sro/pkg/mod.py#L7): Comment\n\n"
        'Code: `return f"hello {name}"`\n\n'
        "> Was line 7, drifted to line 11 -- the unique line in its scope.\n\n"
        "## `Greeter.hello`, [line 1](../../../../../backend/src/sro/pkg/mod.py#L1): Comment\n\n"
        "Code: `pass`\n\n"
        "> Two identical lines in scope -- ambiguous, never guessed at.\n\n"
        "## `Ghost`, [line 99](../../../../../backend/src/sro/pkg/mod.py#L99): Docstring\n\n"
        "> Names a class that does not exist -- dead.\n\n"
        "## `Broken`: Docstring\n\n"
        "> No `line N` at all -- malformed, reported rather than skipped.\n",
    )

    # An empty file never carried a comment; no note required.
    _write(repo / "backend/src/sro/pkg/__init__.py", "")
    # Real content, no note file: the gap `check` exists to find.
    _write(repo / "backend/src/sro/pkg/orphan.py", "VALUE = 2\n")
    # `interface/http/` may keep its own docstrings; no note required.
    _write(repo / "backend/src/sro/interface/http/thing.py", '"""Kept in code, on purpose."""\n')
    # A note with no source behind it at all.
    _write(
        repo / "docs/code-notes/backend/src/sro/pkg/gone.py.md",
        "# Notes for `backend/src/sro/pkg/gone.py`\n\n"
        "## module, [line 1](../../../../../backend/src/sro/pkg/gone.py#L1): Docstring\n\n"
        "> The source this described was deleted.\n",
    )

    report = check_code_notes.run(repo, fix=False)

    assert {entry.split(":", 2)[-1].strip() for entry in report.stale if "mod.py.md" in entry} == {
        "`COUNT` stated line 1, now at 3",
        "`Greeter` stated line 4, now at 6",
        "`Greeter.hello` stated line 5, now at 7",
        "`Greeter.hello` stated line 7, now at 11",
    }
    assert any("Ghost` -- symbol `Ghost` missing" in entry for entry in report.dead)
    assert any("matches 2 lines in its symbol -- ambiguous" in entry for entry in report.dead)
    assert any("no `line N` anchor" in entry for entry in report.dead)
    assert any("gone.py.md: no source file" in entry for entry in report.dead)
    assert any(
        str(repo / "backend/src/sro/pkg/orphan.py") in entry for entry in report.missing_notes
    )
    assert not any("__init__.py" in entry for entry in report.missing_notes)
    assert not any("interface/http/thing.py" in entry for entry in report.missing_notes)

    fixed = check_code_notes.run(repo, fix=True)
    assert fixed.stale == report.stale  # --fix reports exactly what check found

    note_text = (repo / "docs/code-notes/backend/src/sro/pkg/mod.py.md").read_text(encoding="utf-8")
    assert "Was line 4, drifted to line 6." in note_text  # note text is never touched
    assert "[line 6](../../../../../backend/src/sro/pkg/mod.py#L6): Class" in note_text
    assert "[line 3](../../../../../backend/src/sro/pkg/mod.py#L3): Constant" in note_text
    assert (
        "[line 1](../../../../../backend/src/sro/pkg/mod.py#L1): Docstring" in note_text
    )  # unchanged

    settled = check_code_notes.run(repo, fix=False)
    assert settled.stale == []  # nothing left to fix; the ambiguous and dead anchors are untouched
    assert len(settled.dead) == len(report.dead)


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
