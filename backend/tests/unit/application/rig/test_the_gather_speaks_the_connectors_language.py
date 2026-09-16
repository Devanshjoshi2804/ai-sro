"""The gather asks for the arguments the connector declares.

Two programs again. `gmail-connector/server.py` declares each tool's arguments
in its own `TOOLS` list; `gather.py` sends them. A name that disagrees is not a
type error and not a crash -- the connector reads a missing key as empty, asks
Gmail for message `""`, and hands back a record with nothing in it. The gather
then searches its whole budget against bodies that were never fetched and
refuses, correctly, on nothing.

That is exactly what happened on the live mailbox, 2026-09-16: `message_id`
sent, `id` declared, six rounds, no values. The refusal was right and the cause
was a spelling.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType
from typing import Any

from sro.application.execution.gather import SERVER

CONNECTOR = Path(__file__).resolve().parents[4] / "gmail-connector" / "server.py"


def _connector() -> ModuleType:
    spec = importlib.util.spec_from_file_location("gmail_connector_arguments", CONNECTOR)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _declared() -> dict[str, set[str]]:
    """Each tool's required arguments, read off the connector's own list."""
    tools: list[dict[str, Any]] = _connector().TOOLS
    return {
        str(tool["name"]): set(tool.get("inputSchema", {}).get("required", []))
        for tool in tools
        if isinstance(tool, dict) and tool.get("name")
    }


def test_the_gather_asks_for_what_the_connector_declares() -> None:
    declared = _declared()

    # What `_look` sends, kept beside the source it has to agree with.
    assert declared["search_threads"] <= {"query", "limit"}
    assert "query" in declared["search_threads"]
    assert declared["get_message"] == {"id"}, (
        "the gather sends `id`; a connector that wants another name reads a "
        "missing key as empty and answers with an empty message"
    )


def test_the_connector_this_gather_looks_in_is_one_it_could_be_pointed_at() -> None:
    """`SERVER` is the connector's own name in `SRO_MCP_SERVERS`, and the
    connector announces the same one at `initialize`."""
    assert SERVER == "gmail"
