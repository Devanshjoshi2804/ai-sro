from pathlib import Path

import sro


def test_only_an_operators_answer_writes_an_alias() -> None:
    root = Path(sro.__file__).parent
    writers = sorted(
        path.relative_to(root).as_posix()
        for path in root.rglob("*.py")
        if "confirm_alias(" in (text := path.read_text(encoding="utf-8"))
        and "def confirm_alias(" not in text
    )
    assert writers == ["application/runtime/run_steps.py"]
