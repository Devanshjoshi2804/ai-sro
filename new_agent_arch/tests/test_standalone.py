import subprocess
import sys
from pathlib import Path

SRC = Path(__file__).parent.parent / "src"


def _imports_sro(path: Path) -> bool:
    for line in path.read_text().splitlines():
        if line.strip().startswith(("import sro", "from sro")):
            return True
    return False


def test_the_rig_never_imports_the_backend() -> None:
    """Standalone by design. See 'Decision: no path dependency' in the plan."""
    offenders = [str(path) for path in SRC.rglob("*.py") if _imports_sro(path)]

    assert offenders == []


def test_the_package_imports_with_nothing_else_on_the_path() -> None:
    result = subprocess.run(
        [sys.executable, "-c", "import rig.store; import rig.config; print('ok')"],
        capture_output=True,
        text=True,
        cwd=SRC,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "ok" in result.stdout
