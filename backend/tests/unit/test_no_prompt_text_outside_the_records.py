import re
from pathlib import Path

import sro

_PROMPT_TEXT = re.compile(
    r"^\s*_?[A-Z_]*(INSTRUCTIONS|PROMPT|READING|NAMING|JUDGING|HOW_TO_READ)\s*[:=]", re.M
)


def test_no_prompt_text_lives_outside_the_prompt_records() -> None:
    root = Path(sro.__file__).parent
    offenders = [
        path.relative_to(root).as_posix()
        for path in root.rglob("*.py")
        if "prompts" not in path.parts and _PROMPT_TEXT.search(path.read_text(encoding="utf-8"))
    ]
    assert offenders == []
