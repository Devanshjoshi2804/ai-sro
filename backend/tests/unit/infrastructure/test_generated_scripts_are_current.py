"""The extension's generated content scripts must match what generates them.

`recorder.js` and `sensitivity.py` are the single source of the credential
rules, and the extension gets its copies by generation rather than by hand for
exactly that reason. Nothing checked that the copies were current, so adding a
word to `SECRET_TOKENS` and forgetting `make gen-recorder` would leave the
browser -- the only place the redaction actually happens -- running the old
list, with no symptom until a credential turned up in the evidence plane.
"""

from __future__ import annotations

import pytest

from sro.infrastructure.steel.generate_extension_recorder import (
    RECORDER_OUT,
    SENSITIVITY_OUT,
    recorder_source,
    sensitivity_source,
)


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        pytest.param(RECORDER_OUT, recorder_source, id="recorder"),
        pytest.param(SENSITIVITY_OUT, sensitivity_source, id="sensitivity"),
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
