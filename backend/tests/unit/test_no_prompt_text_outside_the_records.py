import ast
import re
from pathlib import Path

import sro

_PROMPT_TEXT = re.compile(
    r"^\s*_?[A-Z_]*(INSTRUCTIONS|PROMPT|READING|NAMING|JUDGING|HOW_TO_READ)\s*[:=]", re.M
)

_INSTRUCTING = re.compile(r"\bYou are\b|\bAnswer with\b|\bReturn\b|\bSay no unless\b")

_LONG = 200


def _outside_the_records() -> list[Path]:
    root = Path(sro.__file__).parent
    return [path for path in root.rglob("*.py") if "prompts" not in path.parts]


def _instruction_literals(source: str) -> list[int]:
    return [
        node.lineno
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and len(node.value) > _LONG
        and _INSTRUCTING.search(node.value)
    ]


def test_no_prompt_text_lives_outside_the_prompt_records() -> None:
    root = Path(sro.__file__).parent
    offenders = [
        path.relative_to(root).as_posix()
        for path in _outside_the_records()
        if _PROMPT_TEXT.search(path.read_text(encoding="utf-8"))
    ]
    assert offenders == []


def test_no_long_string_outside_the_records_reads_like_model_instructions() -> None:
    """The name check only sees a constant named like a prompt. Text handed to a
    model inline, or under any other name, is caught by what it says."""
    root = Path(sro.__file__).parent
    offenders = [
        f"{path.relative_to(root).as_posix()}:{line}"
        for path in _outside_the_records()
        for line in _instruction_literals(path.read_text(encoding="utf-8"))
    ]
    assert offenders == []


def test_the_scan_sees_instructions_under_any_name_and_passes_short_ones() -> None:
    inline = "You are reading one warehouse task. " * 10
    assert _instruction_literals(f"contents = [{inline!r}, evidence]") == [1]
    assert _instruction_literals(f"x = ({('Answer with one gesture. ' * 12)!r})") == [1]
    assert _instruction_literals("x = 'You are here'") == []
