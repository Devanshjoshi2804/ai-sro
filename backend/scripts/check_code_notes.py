from __future__ import annotations

import argparse
import ast
import re
import sys
from dataclasses import dataclass
from pathlib import Path

EXEMPT_FROM_NOTES = ("backend", "src", "sro", "interface", "http")

EXCLUDED_DIR_PARTS = {"tests", "migrations", "__pycache__", ".venv"}

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


def notes_root(repo_root: Path) -> Path:
    return repo_root / "docs" / "code-notes"


def iter_backend_sources(repo_root: Path) -> list[Path]:
    backend = repo_root / "backend"
    if not backend.is_dir():
        return []
    found = []
    for path in backend.rglob("*.py"):
        parts = path.relative_to(repo_root).parts
        if any(part in EXCLUDED_DIR_PARTS for part in parts):
            continue
        found.append(path)
    return sorted(found)


def requires_note(repo_root: Path, source_path: Path) -> bool:
    if not source_path.read_text(encoding="utf-8").strip():
        return False
    parts = source_path.relative_to(repo_root).parts
    return parts[: len(EXEMPT_FROM_NOTES)] != EXEMPT_FROM_NOTES


def note_path_for(repo_root: Path, source_path: Path) -> Path:
    rel = source_path.relative_to(repo_root)
    return notes_root(repo_root) / f"{rel}.md"


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


def _find_in_body(body: list[ast.stmt], name: str) -> list[ast.stmt]:
    return [node for node in body if _defines_name(node, name)]


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


def resolve_target_line(anchor: Anchor, source: SourceInfo) -> tuple[int | None, str | None]:
    if source.tree is None:
        return None, "source file does not parse"

    if anchor.name is None:
        if anchor.code is None:
            return 1, None
        scope_start, scope_end = 1, len(source.lines)
    else:
        node, error = resolve_symbol(source.tree, anchor.name)
        if node is None:
            return None, f"symbol `{anchor.name}` {error}"
        if anchor.code is None:
            return node.lineno, None
        scope_start = node.lineno
        scope_end = getattr(node, "end_lineno", scope_start)

    target = anchor.code.strip()
    hits = [
        line_no
        for line_no in range(scope_start, min(scope_end, len(source.lines)) + 1)
        if source.lines[line_no - 1].strip() == target
    ]
    if len(hits) == 1:
        return hits[0], None
    if not hits:
        return None, f"code `{anchor.code}` not found in its symbol's current lines"
    return None, f"code `{anchor.code}` matches {len(hits)} lines in its symbol -- ambiguous"


def rewrite_heading(heading_line: str, new_line: int) -> str:
    match = HEADING_RE.match(heading_line)
    if match is None:
        raise ValueError(f"not an anchor heading: {heading_line!r}")
    return f"{match['prefix']}{new_line}{match['mid']}{new_line}{match['suffix']}"


@dataclass
class Report:
    stale: list[str]
    dead: list[str]
    missing_notes: list[str]

    @property
    def findings(self) -> int:
        return len(self.stale) + len(self.dead) + len(self.missing_notes)


def run(repo_root: Path, *, fix: bool) -> Report:
    report = Report(stale=[], dead=[], missing_notes=[])
    source_cache: dict[Path, SourceInfo] = {}

    root = notes_root(repo_root)
    note_paths = sorted(p for p in root.rglob("*.md") if p != root / "README.md")

    for note_path in note_paths:
        source_path = source_path_for(repo_root, note_path)
        if not source_path.is_file():
            report.dead.append(f"{note_path}: no source file at {source_path}")
            continue

        note_lines = note_path.read_text(encoding="utf-8").splitlines()
        anchors, malformed = parse_anchors(note_path, note_lines)
        report.dead.extend(malformed)

        source = load_source(source_path, source_cache)
        rewrites: list[tuple[int, int]] = []
        for anchor in anchors:
            target_line, error = resolve_target_line(anchor, source)
            if error is not None:
                where = anchor.name or "module"
                report.dead.append(f"{note_path}:{anchor.heading_index + 1}: `{where}` -- {error}")
                continue
            if target_line != anchor.stated_line:
                report.stale.append(
                    f"{note_path}:{anchor.heading_index + 1}: "
                    f"`{anchor.name or 'module'}` stated line {anchor.stated_line}, "
                    f"now at {target_line}"
                )
                rewrites.append((anchor.heading_index, target_line))  # type: ignore[arg-type]

        if fix and rewrites:
            for heading_index, new_line in rewrites:
                note_lines[heading_index] = rewrite_heading(note_lines[heading_index], new_line)
            note_path.write_text("\n".join(note_lines) + "\n", encoding="utf-8")

    for source_path in iter_backend_sources(repo_root):
        if not requires_note(repo_root, source_path):
            continue
        if not note_path_for(repo_root, source_path).is_file():
            report.missing_notes.append(f"{source_path}: no note file")

    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fix", action="store_true")
    args = parser.parse_args(argv)

    repo_root = Path(__file__).resolve().parents[2]
    report = run(repo_root, fix=args.fix)

    for line in [*report.stale, *report.dead, *report.missing_notes]:
        print(line)
    print(
        f"{len(report.stale)} stale anchor(s), {len(report.dead)} dead/unresolvable note(s), "
        f"{len(report.missing_notes)} source file(s) with no note."
    )
    return 1 if report.findings else 0


if __name__ == "__main__":
    sys.exit(main())
