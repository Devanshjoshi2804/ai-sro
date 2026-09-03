import ast
import subprocess
import sys
from pathlib import Path

SRC = Path(__file__).parent.parent / "src"


def _imports_sro(path: Path) -> bool:
    """Every static import of the backend, including the forms a prefix match
    misses: `import os, sro` and `if x: import sro`."""
    tree = ast.parse(path.read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            if any(alias.name == "sro" or alias.name.startswith("sro.") for alias in node.names):
                return True
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module == "sro" or module.startswith("sro."):
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


def test_the_guard_catches_an_import_hidden_in_a_list(tmp_path: Path) -> None:
    """The prefix match this replaced missed exactly this form."""
    sneaky = tmp_path / "sneaky.py"
    sneaky.write_text("import os, sro\n")

    assert _imports_sro(sneaky) is True


def test_the_guard_leaves_an_innocent_module_alone(tmp_path: Path) -> None:
    innocent = tmp_path / "innocent.py"
    innocent.write_text("import srossignol\nfrom os import path\n")

    assert _imports_sro(innocent) is False
