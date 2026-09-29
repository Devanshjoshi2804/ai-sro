"""The extension's generated content scripts must match what generates them.

`recorder.js` and `sensitivity.py` are the single source of the credential
rules, and the extension gets its copies by generation rather than by hand for
exactly that reason. Nothing checked that the copies were current, so adding a
word to `SECRET_TOKENS` and forgetting `make gen-recorder` would leave the
browser -- the only place the redaction actually happens -- running the old
list, with no symptom until a credential turned up in the evidence plane.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from sro.config import get_settings
from sro.infrastructure.steel.capture import _recorder_script
from sro.infrastructure.steel.generate_extension_recorder import (
    PAGE_CODE_OUT,
    RECORDER_OUT,
    SENSITIVITY_MODULE_OUT,
    SENSITIVITY_OUT,
    SHAPE_OUT,
    page_code_source,
    recorder_source,
    sensitivity_module_source,
    sensitivity_source,
    shape_source,
)


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        pytest.param(RECORDER_OUT, recorder_source, id="recorder"),
        pytest.param(SENSITIVITY_OUT, sensitivity_source, id="sensitivity"),
        pytest.param(SENSITIVITY_MODULE_OUT, sensitivity_module_source, id="sensitivity-module"),
        pytest.param(SHAPE_OUT, shape_source, id="shape"),
        pytest.param(PAGE_CODE_OUT, page_code_source, id="page-code-secret-words"),
    ],
)
def test_the_committed_copy_is_what_the_generator_writes(path, expected) -> None:  # type: ignore[no-untyped-def]
    if not path.is_file():
        pytest.skip(f"{path.name} has not been generated in this checkout")
    assert path.read_text(encoding="utf-8") == expected(), (
        f"{path.name} is stale -- run `make gen-recorder` and commit the result"
    )


def test_the_generated_recorder_has_no_unsubstituted_marker() -> None:
    """The marker means the word list never made it in, and every credential
    check in the browser would silently answer no."""
    if not RECORDER_OUT.is_file():
        pytest.skip("the recorder has not been generated in this checkout")
    assert "__SECRET_WORDS__" not in RECORDER_OUT.read_text(encoding="utf-8")
    assert "__PAGE_READERS__" not in RECORDER_OUT.read_text(encoding="utf-8")


def test_the_recorder_reads_the_page_with_page_codes_own_helpers() -> None:
    """One source for how a control is named, placed and pathed: what the
    recorder writes into evidence and what `page-code.js` resolves it against
    are the same text, spliced in, never a second copy that can drift."""
    page_code = Path(get_settings().page_code_path).read_text(encoding="utf-8")
    start = page_code.index("  const readers = (() => {")
    end = page_code.index("\n  })();\n", start)
    shared = page_code[start + len("  const readers = ") : end + len("\n  })()")]

    script = _recorder_script()

    assert "__PAGE_READERS__" not in script
    assert shared in script
    assert "const roleOf = " not in script.replace(shared, "")
