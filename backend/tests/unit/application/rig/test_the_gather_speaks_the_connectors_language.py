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
import json
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


def test_a_conversation_carries_each_mail_s_own_id() -> None:
    """The half a reply is threaded on, and the same two-program gap.

    `ask_the_asker` reads `rfc822_message_id` off a thread and puts it in
    `In-Reply-To`. The connector sent Gmail's internal id and nothing else, so
    the header named a message the receiving client had never heard of and it
    drew an orphan. Measured on the deployment 2026-09-18: the mail this system
    sent arrived in the recipient's mailbox as a new conversation rather than
    under the request it was answering.

    Read out of the module rather than asserted about Gmail, for this file's
    own reason: what is under test is that two programs agree about a name.
    """
    module = _connector()
    thread = {
        "id": "t-1",
        "messages": [
            {
                "id": "1a0b5053",
                "payload": {
                    "headers": [
                        {"name": "Message-ID", "value": "<abc@mail.example>"},
                        {"name": "From", "value": "asker@example.com"},
                        {"name": "Subject", "value": "a customer type"},
                    ],
                    "body": {},
                },
            }
        ],
    }
    module.httpx = _Answers(thread)

    said = json.loads(module._thread("token", {"id": "t-1"}))

    (one,) = said["messages"]
    # The mail's own id, and Gmail's kept beside it: the first is what a reply
    # is threaded on and the second is what this system claims a message by.
    assert one["rfc822_message_id"] == "<abc@mail.example>"
    assert one["id"] == "1a0b5053"


class _Answers:
    """`httpx`, answering one body. The connector calls `httpx.get` directly."""

    def __init__(self, body: dict[str, Any]) -> None:
        self._body = body

    def get(self, *_args: Any, **_kwargs: Any) -> Any:
        return _Said(self._body)


class _Said:
    def __init__(self, body: dict[str, Any]) -> None:
        self._body = body
        self.status_code = 200
        self.text = json.dumps(body)

    def json(self) -> dict[str, Any]:
        return self._body


class _Routed:
    """`httpx` answering the profile and one message, counting profile reads."""

    def __init__(self, message: dict[str, Any]) -> None:
        self._message = message
        self.profiles = 0

    def get(self, url: str, *_args: Any, **_kwargs: Any) -> Any:
        if url.endswith("/profile"):
            self.profiles += 1
            return _Said({"emailAddress": "Operator@Example.com"})
        return _Said(self._message)


def test_a_message_says_whose_mailbox_it_is_and_who_it_went_to() -> None:
    module = _connector()
    routed = _Routed(
        {
            "id": "m-1",
            "threadId": "t-1",
            "payload": {
                "headers": [
                    {"name": "From", "value": "Operator <operator@example.com>"},
                    {"name": "To", "value": "Colleague <colleague@example.com>"},
                    {"name": "Cc", "value": "boss@example.com"},
                ],
                "body": {},
            },
        }
    )
    module.httpx = routed
    grant = {"tenant": "acme", "operator": "op", "refresh_token": "r"}

    first = json.loads(module._get("token", {"id": "m-1"}, module._mailbox(grant, "token")))
    module._mailbox(grant, "token")

    assert first["mailbox"] == "Operator@Example.com"
    assert first["to"] == "Colleague <colleague@example.com>"
    assert first["cc"] == "boss@example.com"
    assert routed.profiles == 1


class _Listed:
    """`httpx` answering a message list with a next page, recording what it was asked."""

    def __init__(self) -> None:
        self.asked: list[dict[str, Any]] = []

    def get(self, url: str, *_args: Any, params: dict[str, Any], **_kwargs: Any) -> Any:
        self.asked.append(params)
        if url.endswith("/messages"):
            return _Said({"messages": [{"id": "m-9"}], "nextPageToken": "p-2"})
        return _Said({"id": "m-9", "payload": {"headers": []}})


def test_a_search_turns_the_page_the_look_asks_for() -> None:
    """`_recent` pages back with `page` until a page brings nothing new; the
    connector hands Gmail's token over and back under those names."""
    module = _connector()
    listed = _Listed()
    module.httpx = listed

    said = json.loads(module._search("token", {"query": "q", "limit": "8", "page": "p-1"}))

    assert "page" in module.TOOLS[0]["inputSchema"]["properties"]
    assert listed.asked[0]["pageToken"] == "p-1"
    assert said["next_page"] == "p-2"
