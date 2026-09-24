from __future__ import annotations

import argparse
import ast
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import cast

HEADING_RE = re.compile(
    r"^(?P<prefix>## (?:`(?P<name>[^`]+)`|(?P<module>module)), \[line )"
    r"(?P<line>\d+)"
    r"(?P<mid>\]\([^)]*?#L)"
    r"(?P<line2>\d+)"
    r"(?P<suffix>\):.*)$"
)
CODE_RE = re.compile(r"^Code: `(?P<code>.*)`\s*$")


@dataclass
class Anchor:
    note_path: Path
    heading_index: int
    name: str | None
    stated_line: int
    code: str | None


@dataclass
class SourceInfo:
    tree: ast.Module | None
    lines: list[str]


@dataclass
class AnchorEval:
    anchor: Anchor
    symbol_key: str | None
    kind: str  # "certain" | "ambiguous" | "dead"
    line: int | None
    hits: list[int] = field(default_factory=list)
    floor_default: int = 0
    dead_reason: str | None = None


def notes_root(repo_root: Path) -> Path:
    return repo_root / "docs" / "code-notes"


def source_path_for(repo_root: Path, note_path: Path) -> Path:
    rel = note_path.relative_to(notes_root(repo_root))
    return repo_root / str(rel).removesuffix(".md")


def parse_anchors(note_path: Path, lines: list[str]) -> tuple[list[Anchor], list[str]]:
    anchors: list[Anchor] = []
    malformed: list[str] = []
    for index, line in enumerate(lines):
        if not (line.startswith("## `") or line.startswith("## module,")):
            continue
        match = HEADING_RE.match(line)
        if match is None:
            malformed.append(f"{note_path}:{index + 1}: heading has no `line N` anchor: {line!r}")
            continue
        code = None
        following = index + 1
        while following < len(lines) and lines[following].strip() == "":
            following += 1
        if following < len(lines):
            code_match = CODE_RE.match(lines[following])
            if code_match is not None:
                code = code_match.group("code")
        anchors.append(
            Anchor(
                note_path=note_path,
                heading_index=index,
                name=match.group("name"),
                stated_line=int(match.group("line")),
                code=code,
            )
        )
    return anchors, malformed


def load_source(path: Path, cache: dict[Path, SourceInfo]) -> SourceInfo:
    if path not in cache:
        try:
            text = path.read_text(encoding="utf-8")
            tree: ast.Module | None = ast.parse(text, filename=str(path))
        except (OSError, SyntaxError):
            tree = None
            text = ""
        cache[path] = SourceInfo(tree=tree, lines=text.splitlines())
    return cache[path]


def _defines_name(node: ast.stmt, name: str) -> bool:
    if isinstance(node, ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
        return node.name == name
    if isinstance(node, ast.Assign):
        return any(isinstance(target, ast.Name) and target.id == name for target in node.targets)
    if isinstance(node, ast.AnnAssign):
        return isinstance(node.target, ast.Name) and node.target.id == name
    return False


def _flatten(body: list[ast.stmt]) -> list[ast.stmt]:
    """Every statement reachable from `body` without crossing into a nested
    function or class -- a `def` one level down is a different scope (a
    further dotted-name part), but a `with`/`try`/`if`/`for`/`while`/`match`
    is not a scope at all, so a name declared inside one is still a direct
    member of the scope that contains it."""
    flat: list[ast.stmt] = []
    for node in body:
        flat.append(node)
        if isinstance(node, ast.With | ast.AsyncWith):
            flat.extend(_flatten(node.body))
        elif isinstance(node, ast.If | ast.For | ast.AsyncFor | ast.While):
            flat.extend(_flatten(node.body))
            flat.extend(_flatten(node.orelse))
        elif isinstance(node, ast.Try) or (
            hasattr(ast, "TryStar") and isinstance(node, ast.TryStar)
        ):
            flat.extend(_flatten(node.body))
            for handler in node.handlers:
                flat.extend(_flatten(handler.body))
            flat.extend(_flatten(node.orelse))
            flat.extend(_flatten(node.finalbody))
        elif isinstance(node, ast.Match):
            for case in node.cases:
                flat.extend(_flatten(case.body))
    return flat


def _find_in_body(body: list[ast.stmt], name: str) -> list[ast.stmt]:
    return [node for node in _flatten(body) if _defines_name(node, name)]


def _quote_search_start(node: ast.stmt) -> int:
    """Where a symbol's quoted code may start being searched for. A name
    anchor with no quote still means the `def`/`class` line itself (that is
    `node.lineno`, untouched) -- but the decorator above it (a common thing
    to comment on: `@dataclass(frozen=True)`) is quotable code that belongs
    to this symbol too, so the search span widens to include it."""
    if (
        isinstance(node, ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef)
        and node.decorator_list
    ):
        return min(decorator.lineno for decorator in node.decorator_list)
    return node.lineno


def resolve_symbol(tree: ast.Module, dotted_name: str) -> tuple[ast.stmt | None, str | None]:
    scope: ast.stmt | ast.Module = tree
    node: ast.stmt | None = None
    for part in dotted_name.split("."):
        matches = _find_in_body(getattr(scope, "body", []), part)
        if not matches:
            return None, "missing"
        if len(matches) > 1:
            return None, "ambiguous"
        node = scope = matches[0]
    return node, None


def find_hits(lines: list[str], code: str, start: int, end: int) -> list[int]:
    target = code.strip()
    return [
        line_no
        for line_no in range(start, min(end, len(lines)) + 1)
        if lines[line_no - 1].strip() == target
    ]


def evaluate_anchor(anchor: Anchor, source: SourceInfo) -> AnchorEval:
    if source.tree is None:
        return AnchorEval(
            anchor, anchor.name, "dead", None, dead_reason="source file does not parse"
        )

    if anchor.name is None:
        floor_default = 0
        if anchor.code is None:
            return AnchorEval(anchor, None, "certain", 1, floor_default=floor_default)
        scope_start, scope_end = 1, len(source.lines)
    else:
        node, error = resolve_symbol(source.tree, anchor.name)
        if node is None:
            return AnchorEval(
                anchor, anchor.name, "dead", None, dead_reason=f"symbol `{anchor.name}` {error}"
            )
        floor_default = _quote_search_start(node)
        if anchor.code is None:
            return AnchorEval(
                anchor, anchor.name, "certain", node.lineno, floor_default=floor_default
            )
        scope_start = floor_default
        scope_end = getattr(node, "end_lineno", scope_start)

    hits = find_hits(source.lines, anchor.code, scope_start, scope_end)
    if not hits:
        return AnchorEval(
            anchor,
            anchor.name,
            "dead",
            None,
            floor_default=floor_default,
            dead_reason=f"code `{anchor.code}` not found in its symbol's current lines",
        )
    if len(hits) == 1 or anchor.stated_line in hits:
        line = hits[0] if len(hits) == 1 else anchor.stated_line
        return AnchorEval(anchor, anchor.name, "certain", line, hits, floor_default)
    return AnchorEval(anchor, anchor.name, "ambiguous", None, hits, floor_default)


def order_violations(evals: list[AnchorEval]) -> set[str | None]:
    broken: set[str | None] = set()
    last: dict[str | None, int] = {}
    for ev in evals:
        if ev.kind != "certain":
            continue
        line = cast(int, ev.line)
        previous = last.get(ev.symbol_key)
        if previous is not None and line < previous:
            broken.add(ev.symbol_key)
        last[ev.symbol_key] = line
    return broken


def _dead(anchor: Anchor, reason: str) -> str:
    where = anchor.name or "module"
    return f"{anchor.note_path}:{anchor.heading_index + 1}: `{where}` -- {reason}"


def resolve_note_file(
    note_path: Path, note_lines: list[str], source: SourceInfo
) -> tuple[list[tuple[Anchor, int]], list[str]]:
    anchors, malformed = parse_anchors(note_path, note_lines)
    evals = [evaluate_anchor(anchor, source) for anchor in anchors]
    broken = order_violations(evals)

    resolved: list[tuple[Anchor, int]] = []
    dead_messages: list[str] = list(malformed)
    last_resolved: dict[str | None, int] = {}

    for ev in evals:
        anchor = ev.anchor
        if ev.kind == "certain":
            line = cast(int, ev.line)
            resolved.append((anchor, line))
            last_resolved[ev.symbol_key] = line
        elif ev.kind == "dead":
            dead_messages.append(_dead(anchor, cast(str, ev.dead_reason)))
        elif ev.symbol_key in broken:
            dead_messages.append(
                _dead(
                    anchor,
                    f"code `{anchor.code}` matches {len(ev.hits)} lines and this symbol's notes "
                    "are not in source order in this file, so position cannot disambiguate it",
                )
            )
        else:
            floor = last_resolved.get(ev.symbol_key, ev.floor_default)
            candidates = [hit for hit in ev.hits if hit > floor]
            if not candidates:
                dead_messages.append(
                    _dead(
                        anchor,
                        f"code `{anchor.code}` matches {len(ev.hits)} lines, none after the "
                        f"previous note's line {floor}",
                    )
                )
                continue
            line = min(candidates)
            resolved.append((anchor, line))
            last_resolved[ev.symbol_key] = line

    return resolved, dead_messages


def rewrite_heading(heading_line: str, new_line: int) -> str:
    match = HEADING_RE.match(heading_line)
    if match is None:
        raise ValueError(f"not an anchor heading: {heading_line!r}")
    return f"{match['prefix']}{new_line}{match['mid']}{new_line}{match['suffix']}"


@dataclass
class Report:
    stale: list[str]
    dead: list[str]

    @property
    def findings(self) -> int:
        return len(self.stale) + len(self.dead)


def run(repo_root: Path, *, fix: bool) -> Report:
    report = Report(stale=[], dead=[])
    source_cache: dict[Path, SourceInfo] = {}

    root = notes_root(repo_root)
    note_paths = sorted(p for p in root.rglob("*.md") if p != root / "README.md")

    for note_path in note_paths:
        source_path = source_path_for(repo_root, note_path)
        if not source_path.is_file():
            report.dead.append(f"{note_path}: no source file at {source_path}")
            continue

        note_lines = note_path.read_text(encoding="utf-8").splitlines()
        source = load_source(source_path, source_cache)
        resolved, dead_messages = resolve_note_file(note_path, note_lines, source)
        report.dead.extend(dead_messages)

        rewrites: list[tuple[int, int]] = []
        for anchor, target_line in resolved:
            if target_line != anchor.stated_line:
                report.stale.append(
                    f"{note_path}:{anchor.heading_index + 1}: "
                    f"`{anchor.name or 'module'}` stated line {anchor.stated_line}, "
                    f"now at {target_line}"
                )
                rewrites.append((anchor.heading_index, target_line))

        if fix and rewrites:
            for heading_index, new_line in rewrites:
                note_lines[heading_index] = rewrite_heading(note_lines[heading_index], new_line)
            note_path.write_text("\n".join(note_lines) + "\n", encoding="utf-8")

    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fix", action="store_true")
    args = parser.parse_args(argv)

    repo_root = Path(__file__).resolve().parents[2]
    report = run(repo_root, fix=args.fix)

    for line in [*report.stale, *report.dead]:
        print(line)
    print(f"{len(report.stale)} stale anchor(s), {len(report.dead)} dead/unresolvable note(s).")
    return 1 if report.findings else 0


if __name__ == "__main__":
    sys.exit(main())
