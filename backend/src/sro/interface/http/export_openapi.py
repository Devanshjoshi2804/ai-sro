"""Print the OpenAPI document. ``make types`` pipes this into the frontend.

The document is generated from the app rather than hand-written, so the frontend
build breaks when a wire type changes. That break is the contract working.
"""

from __future__ import annotations

import json
import sys

from sro.interface.http.app import create_app


def main() -> None:
    json.dump(create_app().openapi(), sys.stdout, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
