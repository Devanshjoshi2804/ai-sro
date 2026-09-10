"""The committed fixtures against what the extension emits today.

A golden payload is only worth something while it is evidence. A file that
still parses but no longer resembles what the extension produces passes the
contract test forever, and the two tracks go on believing they fit -- which is
the exact failure these files exist to prevent, arrived at slowly.

So this captures a fresh set into a temporary directory and compares the
*shape* of each committed file against it: the same keys, nested the same way.
Not the values -- a port number, a timestamp and an element's pixel bounds are
different every run, and asserting on those would be a test that fails for
being run twice.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from tests.browser.capture_fixtures import FIXTURES, main
from tests.contract.test_observation_payloads import NOT_EXTENSION_OUTPUT

pytestmark = pytest.mark.browser


def _shape(value: Any) -> Any:
    """Keys, nested, with values thrown away.

    A list becomes the shape of its first element, because a fixture's arrays
    are homogeneous -- headers, redacted field names, AX properties -- and an
    empty one says nothing either way.

    A number is a number. A gesture's `at` is milliseconds since the epoch, and
    JSON has one number type: whether a browser hands back 1787725123456 or
    1787725123456.7 is a fact about that millisecond, not about the protocol.
    Telling those apart made this test fail about one run in five, which is the
    kind of failure that teaches people to re-run rather than to read.
    """
    if isinstance(value, dict):
        return {key: _shape(inner) for key, inner in sorted(value.items())}
    if isinstance(value, list):
        return [_shape(value[0])] if value else []
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int | float):
        return "number"
    return type(value).__name__


@pytest.fixture(scope="module")
def freshly_captured(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """One capture for the whole module: it drives a real browser."""
    into = tmp_path_factory.mktemp("fixtures")
    if main(into) != 0:
        pytest.fail("the capture could not produce a full set; see its output")
    return into


def _committed() -> list[Path]:
    # A file the capture never writes cannot have drifted from it. Same set the
    # contract suite skips, for the same reason: it is not extension output.
    return sorted(p for p in FIXTURES.glob("*.json") if p.name not in NOT_EXTENSION_OUTPUT)


@pytest.mark.parametrize("path", _committed(), ids=lambda p: p.stem)
def test_a_committed_fixture_still_has_the_shape_the_extension_emits(
    path: Path, freshly_captured: Path
) -> None:
    fresh = freshly_captured / path.name
    if not fresh.is_file():
        pytest.fail(
            f"{path.name} is committed but the capture no longer produces it -- either the "
            "extension stopped emitting this, or the capture stopped asking for it"
        )

    committed = _shape(json.loads(path.read_text(encoding="utf-8")))
    emitted = _shape(json.loads(fresh.read_text(encoding="utf-8")))

    assert committed == emitted, (
        f"{path.name} no longer looks like what the extension emits. Run `make fixtures` "
        "and read the diff before committing it: this is either a protocol change both "
        "tracks need to know about, or a capture bug."
    )
