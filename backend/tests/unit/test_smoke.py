"""`scripts/smoke.py`'s own checks, against fakes -- no network, no deployment.

Not `sro.*`: the script lives in `backend/scripts/`, which -- like every other
script there -- has no `__init__.py` and is run as a file, not imported as a
package. Loaded here by path instead, the same way `test_check_code_notes.py`
loads `check_code_notes.py`.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "smoke.py"


def _load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("smoke", _SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


smoke = _load_script()


def test_a_page_code_mismatch_fails() -> None:
    # `make smoke` runs this inside the api container, where
    # `get_settings().page_code_path` used to be `SRO_PAGE_CODE_PATH` -- the
    # very file `/health` hashes, so the check could never see a drifted
    # image. `check_page_code` now takes the wanted hash as an argument,
    # computed on the host, so a deployment built from a stale commit is a
    # real mismatch rather than a file compared with itself.
    smoke._failures.clear()

    smoke.check_page_code(deployed="deadbeef", wanted="beefdead")

    assert "page code" in smoke._failures


def test_a_page_code_match_is_not_a_failure() -> None:
    smoke._failures.clear()

    smoke.check_page_code(deployed="deadbeef", wanted="deadbeef")

    assert "page code" not in smoke._failures
