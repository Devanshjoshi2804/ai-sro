"""The OpenAPI document the frontend is built from, against the code it claims
to describe.

Written after finding it five fields stale. `may_take_focus`, `recording_id`,
`artifacts` and `device_id` all shipped without anyone regenerating, and the
only thing checking was a CI step that diffs the file -- so the pipeline had
been failing on it for three commits while every local `make check` passed.

A generated artifact that is only verified somewhere else is a generated
artifact that drifts. This asks the question where the code lives, and says
what to run.
"""

from __future__ import annotations

import json
from pathlib import Path

from sro.interface.http.app import create_app

COMMITTED = Path(__file__).resolve().parents[3] / "frontend" / "openapi.json"
GENERATED = (
    Path(__file__).resolve().parents[3] / "frontend" / "src" / "lib" / "api" / "generated.ts"
)


def test_the_committed_openapi_matches_the_code() -> None:
    current = create_app().openapi()
    committed = json.loads(COMMITTED.read_text(encoding="utf-8"))

    if current == committed:
        return

    # Named rather than a whole-document diff nobody reads: what breaks the
    # frontend build is a type it does not have, and what breaks CI is this
    # file, so the useful sentence is which shapes moved.
    moved = sorted(
        name
        for name in set(current["components"]["schemas"]) | set(committed["components"]["schemas"])
        if current["components"]["schemas"].get(name)
        != committed["components"]["schemas"].get(name)
    )
    paths = sorted(set(current["paths"]) ^ set(committed["paths"]))

    raise AssertionError(
        "frontend/openapi.json no longer describes this code. Run `make types` and "
        f"commit both regenerated files.\n  shapes that changed: {moved or 'none'}\n"
        f"  paths added or removed: {paths or 'none'}"
    )


def test_the_committed_file_is_byte_for_byte_what_the_exporter_writes() -> None:
    """CI compares text, not parsed JSON. A file that parses equal but is
    formatted differently passes the test above and fails the pipeline, which
    is the most annoying way to learn about indentation."""
    written = json.dumps(create_app().openapi(), indent=2) + "\n"

    assert COMMITTED.read_text(encoding="utf-8") == written, (
        "frontend/openapi.json parses correctly but is not what `make types` writes; "
        "regenerate it rather than editing it by hand"
    )


def test_the_generated_types_were_regenerated_too() -> None:
    """`make types` writes two files and the second is the one the frontend
    actually imports.

    Shape *names* only -- checking every field would mean running the generator
    from a Python test, and the failure this exists for is the blunt one: the
    document was regenerated and the types were not.
    """
    types = GENERATED.read_text(encoding="utf-8")
    missing = sorted(
        name
        for name in json.loads(COMMITTED.read_text(encoding="utf-8"))["components"]["schemas"]
        if f"{name}:" not in types
    )

    assert not missing, (
        f"frontend/src/lib/api/generated.ts is missing {missing} -- openapi.json was "
        "regenerated without it. Run `make types`, which writes both."
    )
