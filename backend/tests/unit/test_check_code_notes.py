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


# 1-indexed by position, so every anchor below is written against a line
# number nobody has to count by hand.
SOURCE_LINES = [
    "",  # 1 -- two blank lines pushed everything below down by two, same as
    "",  # 2    any ordinary edit above an untouched note.
    "COUNT = 1",  # 3
    "",  # 4
    "",  # 5
    "class Greeter:",  # 6
    "    def hello(self) -> str:",  # 7
    '        name = "world"',  # 8
    "        pass",  # 9
    "        pass",  # 10
    '        return f"hello {name}"',  # 11
    "",  # 12
    "    def farewell(self) -> str:",  # 13
    "        pass",  # 14
    "        pass",  # 15
    '        return "bye"',  # 16
]


def test_check_then_fix_over_a_tiny_tree(tmp_path: Path) -> None:
    repo = tmp_path

    _write(repo / "backend/src/sro/pkg/mod.py", "\n".join(SOURCE_LINES) + "\n")
    _write(
        repo / "docs/code-notes/backend/src/sro/pkg/mod.py.md",
        "# Notes for `backend/src/sro/pkg/mod.py`\n\n"
        "## module, [line 1](../../../../../backend/src/sro/pkg/mod.py#L1): Docstring\n\n"
        "> Fixed at the top by convention -- never stale.\n\n"
        "## `COUNT`, [line 1](../../../../../backend/src/sro/pkg/mod.py#L1): Constant\n\n"
        "Code: `COUNT = 1`\n\n"
        "> Was line 1, drifted to line 3. One hit -- unambiguous.\n\n"
        "## `Greeter`, [line 4](../../../../../backend/src/sro/pkg/mod.py#L4): Class\n\n"
        "> Was line 4, drifted to line 6.\n\n"
        "## `Greeter.hello`, [line 5](../../../../../backend/src/sro/pkg/mod.py#L5): Function\n\n"
        "> Was line 5, drifted to line 7.\n\n"
        "## `Greeter.hello`, [line 7](../../../../../backend/src/sro/pkg/mod.py#L7): Comment\n\n"
        'Code: `return f"hello {name}"`\n\n'
        "> Was line 7, drifted to line 11 -- the unique line in its scope.\n\n"
        "## `Greeter.hello`, [line 2](../../../../../backend/src/sro/pkg/mod.py#L2): Comment\n\n"
        'Code: `name = "world"`\n\n'
        "> Resolves to line 8, *before* the note above it (line 11) -- these two\n"
        "> notes are not in source order, which the note above this one being\n"
        "> written first, correctly, is what proves.\n\n"
        "## `Greeter.hello`, [line 1](../../../../../backend/src/sro/pkg/mod.py#L1): Comment\n\n"
        "Code: `pass`\n\n"
        "> Two identical lines in scope, and `Greeter.hello`'s notes are already\n"
        "> known (above) not to be in source order -- position cannot be trusted\n"
        "> to break the tie, so this is reported rather than guessed.\n\n"
        "## `Greeter.farewell`, "
        "[line 99](../../../../../backend/src/sro/pkg/mod.py#L99): Function\n\n"
        "> Was line 99, drifted to line 13.\n\n"
        "## `Greeter.farewell`, [line 1](../../../../../backend/src/sro/pkg/mod.py#L1): Comment\n\n"
        "Code: `pass`\n\n"
        "> Two identical lines, but `Greeter.farewell`'s notes ARE in source\n"
        "> order -- the first `pass` note resolves to the first match after the\n"
        "> `Function` note above it (line 13), which is line 14.\n\n"
        "## `Greeter.farewell`, [line 1](../../../../../backend/src/sro/pkg/mod.py#L1): Comment\n\n"
        "Code: `pass`\n\n"
        "> The second `pass` note resolves to the first match after the one\n"
        "> above it (line 14), which is line 15.\n\n"
        "## `Ghost`, [line 99](../../../../../backend/src/sro/pkg/mod.py#L99): Docstring\n\n"
        "> Names a class that does not exist -- dead.\n\n"
        "## `Broken`: Docstring\n\n"
        "> No `line N` at all -- malformed, reported rather than skipped.\n",
    )
    # A note with no source behind it at all. Not "a source file with no note"
    # -- that check was removed; README.md only asks for a note where the
    # source once carried a comment, and a fresh, comment-free file (e.g.
    # `retire_workflow.py`) is not evidence of that either way.
    _write(
        repo / "docs/code-notes/backend/src/sro/pkg/gone.py.md",
        "# Notes for `backend/src/sro/pkg/gone.py`\n\n"
        "## module, [line 1](../../../../../backend/src/sro/pkg/gone.py#L1): Docstring\n\n"
        "> The source this described was deleted.\n",
    )

    report = check_code_notes.run(repo, fix=False)

    mod_stale = {entry.split(":", 2)[-1].strip() for entry in report.stale if "mod.py.md" in entry}
    assert mod_stale == {
        "`COUNT` stated line 1, now at 3",
        "`Greeter` stated line 4, now at 6",
        "`Greeter.hello` stated line 5, now at 7",
        "`Greeter.hello` stated line 7, now at 11",
        "`Greeter.hello` stated line 2, now at 8",
        "`Greeter.farewell` stated line 99, now at 13",
        "`Greeter.farewell` stated line 1, now at 14",
        "`Greeter.farewell` stated line 1, now at 15",
    }

    # Rule 1: a quote matching several lines is valid, not an error, when the
    # stated line is one of the matches -- nothing here exercises that
    # directly (every stale one above needed a real move), but `COUNT`'s
    # single-hit case and the settle-then-recheck pass below both confirm a
    # correctly-anchored multi-hit note is never flagged.
    assert any("Ghost` -- symbol `Ghost` missing" in entry for entry in report.dead)
    assert any("no `line N` anchor" in entry for entry in report.dead)
    assert any("gone.py.md: no source file" in entry for entry in report.dead)
    assert any(
        "`Greeter.hello` -- code `pass` matches 2 lines and this symbol's notes "
        "are not in source order" in entry
        for entry in report.dead
    )
    # Rule 3: no "source file has no note file" finding exists any more.
    assert not hasattr(report, "missing_notes")
    # Round 2: an out-of-order symbol is reported only through the anchor it
    # blocks (above, folded into `dead`) -- there is no separate category for
    # a symbol whose notes are out of order but happen to block nothing, e.g.
    # `Greeter.farewell`'s two identical `pass` notes, which resolved fine.
    assert not hasattr(report, "unordered")
    assert not any("Greeter.farewell" in entry for entry in report.dead)

    fixed = check_code_notes.run(repo, fix=True)
    assert fixed.stale == report.stale  # --fix reports exactly what check found
    assert fixed.dead == report.dead

    note_text = (repo / "docs/code-notes/backend/src/sro/pkg/mod.py.md").read_text(encoding="utf-8")
    assert "Was line 4, drifted to line 6." in note_text  # note text is never touched
    assert "[line 6](../../../../../backend/src/sro/pkg/mod.py#L6): Class" in note_text
    assert "[line 3](../../../../../backend/src/sro/pkg/mod.py#L3): Constant" in note_text
    assert "[line 14](../../../../../backend/src/sro/pkg/mod.py#L14): Comment" in note_text
    assert "[line 15](../../../../../backend/src/sro/pkg/mod.py#L15): Comment" in note_text
    assert (
        "## `Greeter.hello`, [line 1](../../../../../backend/src/sro/pkg/mod.py#L1): Comment"
        in note_text
    )  # the ambiguous, order-broken one is untouched
    assert (
        "[line 1](../../../../../backend/src/sro/pkg/mod.py#L1): Docstring" in note_text
    )  # unchanged

    settled = check_code_notes.run(repo, fix=False)
    assert settled.stale == []  # nothing left to fix
    assert settled.dead == report.dead  # the truly dead ones are still dead, unrenumbered


def test_decorator_line_is_inside_its_class(tmp_path: Path) -> None:
    # A decorated class/function's own `.lineno` is the `class`/`def` line,
    # not the decorator above it, so a note anchored to the decorator --
    # `@dataclass(frozen=True, slots=True)` is a common one to explain --
    # sat just outside the symbol's resolved span and was reported dead.
    repo = tmp_path

    # `class Boxed:` is line 5; its decorator is line 4.
    _write(
        repo / "backend/src/sro/pkg/boxed.py",
        "from dataclasses import dataclass\n\n\n"
        "@dataclass(frozen=True, slots=True)\n"
        "class Boxed:\n"
        "    value: int\n",
    )
    _write(
        repo / "docs/code-notes/backend/src/sro/pkg/boxed.py.md",
        "# Notes for `backend/src/sro/pkg/boxed.py`\n\n"
        # A name anchor with no quote still means the `class` line itself --
        # widening the search span for quoted code must not also drag this
        # one back onto the decorator.
        "## `Boxed`, [line 5](../../../../../backend/src/sro/pkg/boxed.py#L5): Docstring\n\n"
        "> A value nothing else may change once built.\n\n"
        # A quote that names the decorator itself must still resolve, since
        # the decorator is quotable code that belongs to this symbol.
        "## `Boxed`, [line 4](../../../../../backend/src/sro/pkg/boxed.py#L4): Comment\n\n"
        "Code: `@dataclass(frozen=True, slots=True)`\n\n"
        "> Frozen so a boxed value cannot be mutated after construction.\n",
    )

    report = check_code_notes.run(repo, fix=False)

    assert not any("boxed.py.md" in entry for entry in report.dead)
    assert not any("boxed.py.md" in entry for entry in report.stale)


def test_function_nested_in_with_and_try_resolves(tmp_path: Path) -> None:
    # `_find_in_body` only ever looked at a scope's immediate statement
    # list, so a closure declared inside a `with`/`try` (a very ordinary
    # place to put one) was invisible to it -- "missing", even though the
    # code was never touched.
    repo = tmp_path

    _write(
        repo / "backend/src/sro/pkg/nested.py",
        "def outer():\n"
        "    with open('x') as fh:\n"
        "        try:\n"
        "            def inner():\n"
        "                return 1\n"
        "        finally:\n"
        "            fh.close()\n"
        "    return inner\n",
    )
    _write(
        repo / "docs/code-notes/backend/src/sro/pkg/nested.py.md",
        "# Notes for `backend/src/sro/pkg/nested.py`\n\n"
        "## `outer.inner`, [line 4](../../../../../backend/src/sro/pkg/nested.py#L4): Function\n\n"
        "> The nested closure, still reachable through a `with`/`try`.\n",
    )

    report = check_code_notes.run(repo, fix=False)

    assert not any("nested.py.md" in entry for entry in report.dead)
    assert not any("nested.py.md" in entry for entry in report.stale)


def test_a_non_python_source_resolves_by_a_line_scan_not_ast(tmp_path: Path) -> None:
    # `ast.parse` throws on the first line of any JS -- `page-code.js.md`
    # (global-constraints.md's "the same rule holds for ... page-code.js")
    # would be entirely `dead` on that path alone, for every anchor, with no
    # way to write a real one. A `.py` file's behaviour above is untouched:
    # this only ever runs for a source whose suffix is not `.py`.
    repo = tmp_path

    _write(
        repo / "new-chrome-extension/src/page/page-code.js",
        "\n"
        "const sroPage = {\n"
        "  perform(payload) {\n"
        "    return null;\n"
        "  },\n"
        "  async send(payload) {\n"
        "    return null;\n"
        "  },\n"
        "};\n"
        "globalThis.sroPage = sroPage;\n",
    )
    _write(
        repo / "docs/code-notes/new-chrome-extension/src/page/page-code.js.md",
        "# Notes for `new-chrome-extension/src/page/page-code.js`\n\n"
        "## `perform`, "
        "[line 99](../../../../../new-chrome-extension/src/page/page-code.js#L99): Docstring\n\n"
        "> Was line 99, drifted to line 3.\n\n"
        "## `perform`, [line 1](../../../../../new-chrome-extension/src/page/page-code.js#L1): "
        "Comment\n\n"
        "Code: `return null;`\n\n"
        "> Scoped to `perform`'s own body -- `send`'s identical line is a "
        "different `return null;`.\n\n"
        "## `send`, [line 50](../../../../../new-chrome-extension/src/page/page-code.js#L50): "
        "Docstring\n\n"
        "> Was line 50, drifted to line 6.\n\n"
        "## `send`, [line 1](../../../../../new-chrome-extension/src/page/page-code.js#L1): "
        "Comment\n\n"
        "Code: `return null;`\n\n"
        "> The other `return null;` -- resolved inside `send`'s own scope, not "
        "`perform`'s, even though the quoted line is not unique in the file.\n\n"
        "## `Ghost`, [line 1](../../../../../new-chrome-extension/src/page/page-code.js#L1): "
        "Docstring\n\n"
        "> Names a function that does not exist -- dead.\n",
    )

    report = check_code_notes.run(repo, fix=False)

    page_stale = {
        entry.split(":", 2)[-1].strip() for entry in report.stale if "page-code.js.md" in entry
    }
    assert page_stale == {
        "`perform` stated line 99, now at 3",
        "`perform` stated line 1, now at 4",
        "`send` stated line 50, now at 6",
        "`send` stated line 1, now at 7",
    }
    assert any("Ghost` -- symbol `Ghost` missing" in entry for entry in report.dead)

    fixed = check_code_notes.run(repo, fix=True)
    assert fixed.stale == report.stale
    settled = check_code_notes.run(repo, fix=False)
    assert settled.stale == []


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
