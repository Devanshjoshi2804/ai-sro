"""The Outlook connector answers what the Gmail connector answers, from Microsoft Graph.

`outlook-connector/server.py` runs on its own, so it is loaded by path like the Gmail
one. Graph is a fake Nango proxy (httpx MockTransport) that answers recorded Graph
JSON; every tool runs through the real functions, and one test goes through the real
JSON-RPC server. Mail content is data: nothing here executes or obeys it.
"""

from __future__ import annotations

import asyncio
import importlib.util
import json
import random
import re
import sys
import threading
from collections.abc import Callable, Iterator
from datetime import UTC, datetime, timedelta
from email.utils import getaddresses, parseaddr
from http.server import ThreadingHTTPServer
from pathlib import Path
from types import ModuleType
from typing import Any

import httpx
import pytest

from sro.domain.execution.connector_bearer import sign_bearer

BACKEND = Path(__file__).resolve().parents[2]
KEY = "k" * 40
NOW = datetime(2026, 10, 2, 12, 0, 0, tzinfo=UTC)


def _load(name: str, folder: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, BACKEND / folder / "server.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module  # dataclasses resolve their annotations through it
    spec.loader.exec_module(module)
    return module


def _address(name: str, address: str) -> dict[str, Any]:
    return {"emailAddress": {"name": name, "address": address}}


def _mail(ident: str, **over: Any) -> dict[str, Any]:
    return {
        "id": ident,
        "conversationId": "conv-1",
        "internetMessageId": f"<{ident}@mail.example>",
        "from": _address("Alice Ng", "alice@example.com"),
        "toRecipients": [_address("Me", "me@corp.example")],
        "ccRecipients": [_address("", "bob@example.com")],
        "subject": "Create a Customer Type",
        "receivedDateTime": "2026-10-02T09:30:00Z",
        "sentDateTime": "2026-10-02T09:29:50Z",
        "bodyPreview": "please add Gold",
        "body": {"contentType": "text", "content": "please add Gold"},
        "parentFolderId": "ID-inbox",
        "isRead": False,
        "hasAttachments": False,
        "isDraft": False,
        **over,
    }


class FakeNango:
    """Nango's connection list and its proxy, answering recorded Graph JSON."""

    def __init__(self) -> None:
        self.seen: list[tuple[str, str, dict[str, str], Any, dict[str, str]]] = []
        self.connections: list[dict[str, Any]] = [
            {
                "connection_id": "nango-conn-1",
                "provider_config_key": "microsoft",
                "created": "2026-09-30T00:00:00+00:00",
                "errors": [],
            }
        ]
        self.routes: dict[tuple[str, str], Callable[[dict[str, str], Any], Any]] = {}
        self.status = 200

    def on(self, method: str, path: str, answer: Any) -> None:
        self.routes[(method, path)] = answer if callable(answer) else (lambda _p, _b: answer)

    def handler(self, request: httpx.Request) -> httpx.Response:
        params = dict(request.url.params)
        body = json.loads(request.content) if request.content else None
        path = request.url.path
        self.seen.append(
            (
                request.method,
                path,
                params,
                body,
                {
                    k: v
                    for k, v in request.headers.items()
                    if k.lower() in ("connection-id", "nango-proxy-prefer")
                },
            )
        )
        if path == "/connection":
            assert params["tags[end_user_id]"].startswith("acme:")
            return httpx.Response(
                200,
                json={
                    "connections": [
                        {"tags": {"end_user_id": params["tags[end_user_id]"]}, **one}
                        for one in self.connections
                    ]
                },
            )
        assert path.startswith("/proxy")
        assert request.headers["provider-config-key"] == "microsoft"
        graph = path.removeprefix("/proxy")
        if self.status >= 400:
            return httpx.Response(self.status, json={"error": {"message": "nope"}})
        found = self.routes.get((request.method, graph))
        if found is None:
            return httpx.Response(404, json={"error": {"message": f"no route {graph}"}})
        answered = found(params, body)
        if answered is None:
            return httpx.Response(202)
        return httpx.Response(200, json=answered)

    def graph_calls(self, method: str = "GET") -> list[tuple[str, dict[str, str]]]:
        return [(p, q) for m, p, q, _b, _h in self.seen if m == method and p.startswith("/proxy")]


@pytest.fixture
def outlook(monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    module = _load("outlook_connector_under_test", "outlook-connector")
    monkeypatch.setattr(module, "SIGNING_KEY", KEY)
    monkeypatch.setattr(module, "NANGO_URL", "http://nango.test")
    monkeypatch.setattr(module, "NANGO_KEY", "nango-secret")
    monkeypatch.setattr(module, "now", lambda: NOW)
    return module


@pytest.fixture
def nango(outlook: ModuleType, monkeypatch: pytest.MonkeyPatch) -> FakeNango:
    fake = FakeNango()
    monkeypatch.setattr(outlook, "TRANSPORT", httpx.MockTransport(fake.handler))
    for name in ("inbox", "sentitems", "deleteditems", "junkemail"):
        fake.on("GET", f"/v1.0/me/mailFolders/{name}", {"id": f"ID-{name}"})
    fake.on(
        "GET", "/v1.0/me", {"mail": "me@corp.example", "userPrincipalName": "me@corp.onmicrosoft"}
    )
    return fake


def listing(nango: FakeNango) -> dict[str, str]:
    """The params of the last message listing (not a folder or profile lookup)."""
    return [q for p, q in nango.graph_calls() if p.endswith("/messages")][-1]


def run(outlook: ModuleType, name: str, arguments: dict[str, Any]) -> Any:
    return json.loads(asyncio.run(outlook.run_tool("acme", "sam", name, arguments)))


def iso(moment: datetime) -> str:
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


# --- shapes: key for key what the Gmail connector answers -----------------------------


def _gmail_answers(monkeypatch: pytest.MonkeyPatch) -> tuple[Any, Any, Any]:
    gmail = _load("gmail_connector_for_shapes", "gmail-connector")
    mail = {
        "id": "g1",
        "threadId": "t1",
        "snippet": "s",
        "internalDate": "1",
        "labelIds": ["INBOX"],
        "payload": {
            "mimeType": "text/plain",
            "body": {"data": "aGk="},
            "headers": [{"name": "From", "value": "a@b"}],
        },
    }

    def fake_get(url: str, **_kw: Any) -> httpx.Response:
        if url.endswith("/messages"):
            return httpx.Response(200, json={"messages": [{"id": "g1"}], "nextPageToken": "n"})
        if "/threads/" in url:
            return httpx.Response(200, json={"id": "t1", "messages": [mail]})
        return httpx.Response(200, json=mail)

    monkeypatch.setattr(gmail.httpx, "get", fake_get)
    return (
        json.loads(gmail._search("tok", {"query": "x"})),
        json.loads(gmail._get("tok", {"id": "g1"}, "me@x")),
        json.loads(gmail._thread("tok", {"id": "t1"})),
    )


def _routes_for_mail(nango: FakeNango) -> None:
    nango.on("GET", "/v1.0/me/messages", {"value": [_mail("m1")]})
    nango.on(
        "GET",
        "/v1.0/me/messages/m1",
        _mail(
            "m1",
            internetMessageHeaders=[
                {"name": "Auto-Submitted", "value": "auto-replied"},
                {"name": "Message-ID", "value": "<m1@mail.example>"},
                {"name": "In-Reply-To", "value": "<prev@mail.example>"},
                {"name": "References", "value": "<prev@mail.example>"},
                {"name": "X-SRO-Marker", "value": "mk-1"},
                {"name": "Received", "value": "from somewhere"},
                {"name": "Date", "value": "Fri, 02 Oct 2026 09:29:50 +0000"},
            ],
        ),
    )


def test_every_tool_answers_the_keys_the_gmail_connector_answers(
    outlook: ModuleType, nango: FakeNango, monkeypatch: pytest.MonkeyPatch
) -> None:
    g_search, g_get, g_thread = _gmail_answers(monkeypatch)
    _routes_for_mail(nango)

    searched = run(outlook, "search_threads", {"query": "newer_than:2d"})
    got = run(outlook, "get_message", {"id": "m1"})
    nango.on("GET", "/v1.0/me/messages", {"value": [_mail("m1")]})
    thread = run(outlook, "get_thread", {"id": "conv-1"})

    assert list(searched) == list(g_search)
    assert list(searched["messages"][0]) == list(g_search["messages"][0])
    assert list(got) == list(g_get)
    assert list(thread) == list(g_thread)
    assert list(thread["messages"][0]) == list(g_thread["messages"][0])
    assert {type(v) for v in got.values()} == {type(v) for v in g_get.values()}
    assert type(thread["messages"][0]["sent_at"]) is type(g_thread["messages"][0]["sent_at"])


def test_the_tools_declare_what_the_gmail_connector_declares(outlook: ModuleType) -> None:
    gmail = _load("gmail_connector_for_tools", "gmail-connector")
    assert [
        (t["name"], t["inputSchema"]["required"], list(t["inputSchema"]["properties"]))
        for t in outlook.TOOLS
    ] == [
        (t["name"], t["inputSchema"]["required"], list(t["inputSchema"]["properties"]))
        for t in gmail.TOOLS
    ]


def test_get_message_reads_the_mail_as_gmail_would(outlook: ModuleType, nango: FakeNango) -> None:
    _routes_for_mail(nango)
    got = run(outlook, "get_message", {"id": "m1"})

    assert got["id"] == "m1"
    assert got["thread_id"] == "conv-1"
    assert got["rfc822_message_id"] == "<m1@mail.example>"
    assert got["from"] == "Alice Ng <alice@example.com>"
    assert got["to"] == "Me <me@corp.example>"
    assert got["cc"] == "bob@example.com"
    assert got["date"] == "Fri, 02 Oct 2026 09:29:50 +0000"
    assert got["sent"] is False
    assert got["in_reply_to"] == "<prev@mail.example>"
    assert got["references"] == "<prev@mail.example>"
    assert got["marker"] == "mk-1"
    assert got["mailbox"] == "me@corp.example"
    assert got["subject"] == "Create a Customer Type"
    assert got["body"] == "please add Gold"
    # Auto-Submitted and Content-Type-like automation headers only, names lowercased.
    assert got["headers"] == {"auto-submitted": "auto-replied"}
    (_, params), *_ = [c for c in nango.graph_calls() if c[0].endswith("/messages/m1")]
    assert "internetMessageHeaders" in params["$select"]


def test_a_message_without_graph_headers_has_empty_headers(
    outlook: ModuleType, nango: FakeNango
) -> None:
    nango.on("GET", "/v1.0/me/messages/m2", _mail("m2"))
    got = run(outlook, "get_message", {"id": "m2"})

    assert got["headers"] == {}
    assert got["marker"] == got["in_reply_to"] == got["references"] == ""
    # No Date header: the sent time stands in, in the RFC 2822 form Gmail's Date has.
    assert got["date"] == "Fri, 02 Oct 2026 09:29:50 +0000"


def test_a_html_body_is_read_as_text_and_never_as_markup(
    outlook: ModuleType, nango: FakeNango
) -> None:
    html = (
        "<html><style>p{}</style><body><p>Create a <b>Gold</b></p>"
        "<script>x()</script></body></html>"
    )
    nango.on(
        "GET", "/v1.0/me/messages/m3", _mail("m3", body={"contentType": "html", "content": html})
    )

    assert run(outlook, "get_message", {"id": "m3"})["body"] == "Create a Gold"


def test_a_message_in_sent_items_is_sent(outlook: ModuleType, nango: FakeNango) -> None:
    nango.on("GET", "/v1.0/me/messages/m4", _mail("m4", parentFolderId="ID-sentitems"))

    assert run(outlook, "get_message", {"id": "m4"})["sent"] is True


def test_a_thread_is_the_conversation_oldest_first(outlook: ModuleType, nango: FakeNango) -> None:
    late = _mail("late", receivedDateTime="2026-10-02T11:00:00Z", subject="Re: x")
    early = _mail("early", receivedDateTime="2026-10-02T08:00:00Z")
    sent = _mail("mine", parentFolderId="ID-sentitems", receivedDateTime="2026-10-02T09:00:00Z")
    nango.on("GET", "/v1.0/me/messages", {"value": [late, early, sent]})

    thread = run(outlook, "get_thread", {"id": "conv-1"})

    assert thread["id"] == "conv-1"
    assert [m["id"] for m in thread["messages"]] == ["early", "mine", "late"]
    assert thread["messages"][1]["sent"] is True
    assert thread["messages"][0]["sent_at"] == datetime(2026, 10, 2, 8, tzinfo=UTC).timestamp()
    (_, params) = nango.graph_calls()[-1]
    # Graph refuses $orderby on a property the $filter does not name (InefficientFilter).
    assert "$orderby" not in params
    assert params["$filter"] == "conversationId eq 'conv-1'"


def test_a_conversation_id_is_quoted_so_it_cannot_widen_the_filter(
    outlook: ModuleType, nango: FakeNango
) -> None:
    nango.on("GET", "/v1.0/me/messages", {"value": []})
    run(outlook, "get_thread", {"id": "x' or isRead eq false or id eq 'y"})

    assert nango.graph_calls()[-1][1]["$filter"] == (
        "conversationId eq 'x'' or isRead eq false or id eq ''y'"
    )


def test_a_long_conversation_is_read_to_its_end(outlook: ModuleType, nango: FakeNango) -> None:
    nxt = "https://graph.microsoft.com/v1.0/me/messages?%24filter=x&%24skip=10"
    pages = iter(
        [
            {"value": [_mail("a")], "@odata.nextLink": nxt},
            {"value": [_mail("b", receivedDateTime="2026-10-02T10:00:00Z")]},
        ]
    )
    nango.on("GET", "/v1.0/me/messages", lambda _p, _b: next(pages))

    thread = run(outlook, "get_thread", {"id": "conv-1"})

    assert [m["id"] for m in thread["messages"]] == ["a", "b"]
    assert nango.graph_calls()[-1][1]["$skip"] == "10"


# --- the queries actually sent ---------------------------------------------------------


def test_the_mail_doors_query_is_a_filter_on_the_inbox_window(
    outlook: ModuleType, nango: FakeNango
) -> None:
    """K_RECENT = "newer_than:2d -in:chats": dates are a $filter, chats do not exist here."""
    nango.on("GET", "/v1.0/me/messages", {"value": [_mail("m1")]})

    got = run(outlook, "search_threads", {"query": "newer_than:2d -in:chats", "limit": "7"})

    (_, params) = next(c for c in nango.graph_calls() if c[0] == "/proxy/v1.0/me/messages")
    assert params["$filter"] == f"receivedDateTime ge {iso(NOW - timedelta(days=2))}"
    assert params["$orderby"] == "receivedDateTime desc"
    assert params["$top"] == "7"
    assert "$search" not in params
    assert got["messages"] == [
        {
            "id": "m1",
            "from": "Alice Ng <alice@example.com>",
            "subject": "Create a Customer Type",
            "date": "Fri, 02 Oct 2026 09:29:50 +0000",
            "snippet": "please add Gold",
        }
    ]
    assert got["next_page"] == ""


def test_mail_in_deleted_items_and_junk_is_not_work(outlook: ModuleType, nango: FakeNango) -> None:
    nango.on(
        "GET",
        "/v1.0/me/messages",
        {
            "value": [
                _mail("keep"),
                _mail("trash", parentFolderId="ID-deleteditems"),
                _mail("spam", parentFolderId="ID-junkemail"),
            ]
        },
    )

    got = run(outlook, "search_threads", {"query": "newer_than:2d -in:chats"})

    assert [m["id"] for m in got["messages"]] == ["keep"]


def test_the_sent_window_query_is_a_filter_on_sent_items(
    outlook: ModuleType, nango: FakeNango
) -> None:
    """mail_job.py: "in:sent after:<epoch> before:<epoch>"."""
    nango.on("GET", "/v1.0/me/mailFolders/sentitems/messages", {"value": [_mail("s1")]})
    after, before = 1_790_000_000, 1_790_000_600

    run(outlook, "search_threads", {"query": f"in:sent after:{after} before:{before}"})

    (path, params) = nango.graph_calls()[-1]
    assert path == "/proxy/v1.0/me/mailFolders/sentitems/messages"
    lo = iso(datetime.fromtimestamp(after, UTC))
    hi = iso(datetime.fromtimestamp(before, UTC))
    assert params["$filter"] == f"receivedDateTime ge {lo} and receivedDateTime lt {hi}"
    assert params["$orderby"] == "receivedDateTime desc"


def test_a_model_written_query_is_a_search_with_nothing_to_conflict(
    outlook: ModuleType, nango: FakeNango
) -> None:
    """gather.py: free text with operators. Graph refuses $search with $filter/$orderby."""
    nango.on("GET", "/v1.0/me/messages", {"value": [_mail("m1")]})

    run(
        outlook,
        "search_threads",
        {"query": 'from:alice@example.com subject:invoice "Gold tier" -refund', "limit": "5"},
    )

    (_, params) = next(c for c in nango.graph_calls() if c[0] == "/proxy/v1.0/me/messages")
    assert params["$search"] == (
        '"from:alice@example.com AND subject:invoice AND (Gold AND tier) AND NOT refund"'
    )
    assert "$filter" not in params and "$orderby" not in params
    assert params["$top"] == "5"


def test_a_search_still_keeps_to_its_date_window_exactly(
    outlook: ModuleType, nango: FakeNango
) -> None:
    """KQL has no exact time bound and Graph forbids $filter beside $search, so the window
    is applied to the page that came back -- exactly, not to the day."""
    inside = _mail("in", receivedDateTime="2026-10-02T10:00:00Z")
    outside = _mail("out", receivedDateTime="2026-09-20T10:00:00Z")
    nango.on("GET", "/v1.0/me/messages", {"value": [outside, inside]})

    got = run(outlook, "search_threads", {"query": "invoice newer_than:2d"})

    assert [m["id"] for m in got["messages"]] == ["in"]


def test_unread_and_attachment_are_filters_without_words_and_client_side_with_them(
    outlook: ModuleType, nango: FakeNango
) -> None:
    nango.on("GET", "/v1.0/me/messages", {"value": [_mail("u"), _mail("r", isRead=True)]})

    only = run(outlook, "search_threads", {"query": "is:unread has:attachment"})
    params = listing(nango)
    assert params["$filter"] == "isRead eq false and hasAttachments eq true"
    assert [m["id"] for m in only["messages"]] == ["u", "r"]  # Graph already filtered

    with_words = run(outlook, "search_threads", {"query": "invoice is:unread"})
    assert [m["id"] for m in with_words["messages"]] == ["u"]


def test_an_unknown_operator_is_searched_as_plain_words(
    outlook: ModuleType, nango: FakeNango
) -> None:
    nango.on("GET", "/v1.0/me/messages", {"value": []})

    run(outlook, "search_threads", {"query": 'label:work "x\\" OR 1=1" (a)'})

    params = listing(nango)
    # Only the operators this connector writes (AND, OR, NOT, grouping) reach KQL: quotes
    # and backslashes in the mail-derived query are gone.
    assert params["$search"] == '"(label AND work) AND x OR (1 AND 1) AND (a)"'
    assert "\\" not in params["$search"].strip('"')


def test_or_between_terms_is_kept_and_a_dangling_one_is_dropped(
    outlook: ModuleType, nango: FakeNango
) -> None:
    nango.on("GET", "/v1.0/me/messages", {"value": []})

    run(outlook, "search_threads", {"query": "OR from:a OR from:b OR"})

    assert listing(nango)["$search"] == '"from:a OR from:b"'


def test_page_tokens_are_short_opaque_and_followed(outlook: ModuleType, nango: FakeNango) -> None:
    nxt = "https://graph.microsoft.com/v1.0/me/messages?%24top=1&%24skip=1&%24filter=receivedDateTime%20ge%202026"
    pages = iter(
        [
            {"value": [_mail("a")], "@odata.nextLink": nxt},
            {"value": [_mail("b")]},
        ]
    )
    nango.on("GET", "/v1.0/me/messages", lambda _p, _b: next(pages))
    first = run(outlook, "search_threads", {"query": "newer_than:2d", "limit": "1"})
    token = first["next_page"]

    assert re.fullmatch(r"[A-Za-z0-9_-]{1,256}", token)
    assert "graph.microsoft.com" not in token

    second = run(outlook, "search_threads", {"query": "newer_than:2d", "limit": "1", "page": token})

    assert [m["id"] for m in second["messages"]] == ["b"]
    assert second["next_page"] == ""
    (_, params) = nango.graph_calls()[-1]
    assert params["$skip"] == "1" and params["$filter"] == "receivedDateTime ge 2026"


def test_a_page_token_this_connector_did_not_hand_out_is_refused(
    outlook: ModuleType, nango: FakeNango
) -> None:
    with pytest.raises(ValueError, match="page token"):
        asyncio.run(
            outlook.run_tool("acme", "sam", "search_threads", {"query": "x", "page": "abc"})
        )
    with pytest.raises(ValueError, match="page token"):
        asyncio.run(
            outlook.run_tool("acme", "sam", "search_threads", {"query": "x", "page": "../../me"})
        )


def test_one_operators_page_token_is_no_use_to_another(
    outlook: ModuleType, nango: FakeNango
) -> None:
    nxt = "https://graph.microsoft.com/v1.0/me/messages?%24skip=1"
    nango.on("GET", "/v1.0/me/messages", {"value": [_mail("a")], "@odata.nextLink": nxt})
    token = run(outlook, "search_threads", {"query": "newer_than:2d"})["next_page"]

    with pytest.raises(ValueError, match="page token"):
        asyncio.run(
            outlook.run_tool(
                "acme", "someone-else", "search_threads", {"query": "x", "page": token}
            )
        )


# --- sending ------------------------------------------------------------------------------


def _posts(nango: FakeNango) -> list[tuple[str, Any]]:
    return [(p, b) for m, p, _q, b, _h in nango.seen if m == "POST"]


def _drafts(nango: FakeNango, ident: str = "AAMk-imm-1") -> None:
    nango.on("POST", "/v1.0/me/messages", {"id": ident})
    nango.on("POST", f"/v1.0/me/messages/{ident}/send", None)


def test_a_new_mail_is_made_a_draft_with_the_marker_then_sent_and_answers_its_id(
    outlook: ModuleType, nango: FakeNango
) -> None:
    _drafts(nango)

    got = run(
        outlook,
        "send_message",
        {
            "to": "Ann <ann@x.test>, bo@x.test",
            "bcc": "audit@x.test",
            "subject": "Done",
            "body": "It is done.",
            "marker": "mk-9",
        },
    )

    # The id is the draft's immutable id: it is the Sent Items copy's id too
    # (learn.microsoft.com/graph/outlook-immutable-id, "Immutable ID with sending mail").
    assert got == {"status": "sent", "id": "AAMk-imm-1"}
    made, sent = _posts(nango)
    assert (
        made[0] == "/proxy/v1.0/me/messages"
        and sent[0] == "/proxy/v1.0/me/messages/AAMk-imm-1/send"
    )
    message = made[1]
    assert message["subject"] == "Done"
    assert message["body"] == {"contentType": "Text", "content": "It is done."}
    assert [r["emailAddress"]["address"] for r in message["toRecipients"]] == [
        "ann@x.test",
        "bo@x.test",
    ]
    assert message["bccRecipients"][0]["emailAddress"]["address"] == "audit@x.test"
    assert message["internetMessageHeaders"] == [{"name": "X-SRO-Marker", "value": "mk-9"}]


def test_no_marker_means_no_header(outlook: ModuleType, nango: FakeNango) -> None:
    _drafts(nango)
    run(outlook, "send_message", {"to": "a@x.test", "body": "hi"})

    assert "internetMessageHeaders" not in _posts(nango)[0][1]


def test_an_answer_is_a_reply_draft_made_with_the_marker_then_sent(
    outlook: ModuleType, nango: FakeNango
) -> None:
    nango.on("GET", "/v1.0/me/messages", lambda p, _b: {"value": [_mail("orig")]})
    nango.on("POST", "/v1.0/me/messages/orig/createReply", {"id": "AAMk-imm-2"})
    nango.on("POST", "/v1.0/me/messages/AAMk-imm-2/send", None)

    got = run(
        outlook,
        "send_message",
        {
            "to": "alice@example.com",
            "body": "Added.",
            "subject": "ignored",
            "thread_id": "conv-1",
            "in_reply_to": "<orig@mail.example>",
            "marker": "mk-2",
        },
    )

    assert got == {"status": "sent", "id": "AAMk-imm-2"}
    made, sent = _posts(nango)
    assert made[0] == "/proxy/v1.0/me/messages/orig/createReply"
    assert sent[0] == "/proxy/v1.0/me/messages/AAMk-imm-2/send"
    body = made[1]
    assert body["comment"] == "Added."
    assert "body" not in body["message"]  # Graph refuses a comment and a body together
    assert body["message"]["internetMessageHeaders"] == [{"name": "X-SRO-Marker", "value": "mk-2"}]
    assert body["message"]["toRecipients"][0]["emailAddress"]["address"] == "alice@example.com"
    looked = next(q for p, q in nango.graph_calls() if p == "/proxy/v1.0/me/messages")
    assert looked["$filter"] == "internetMessageId eq '<orig@mail.example>'"


def test_a_draft_that_will_not_send_is_an_error_not_a_sent_mail(
    outlook: ModuleType, nango: FakeNango
) -> None:
    nango.on("POST", "/v1.0/me/messages", {"id": "AAMk-imm-1"})  # no /send route: Graph 404s

    with pytest.raises(RuntimeError, match="the send"):
        asyncio.run(
            outlook.run_tool("acme", "sam", "send_message", {"to": "a@x.test", "body": "x"})
        )


def test_a_send_whose_deadline_has_passed_makes_no_send_call(
    outlook: ModuleType, nango: FakeNango, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The backend gives up on a call after 30 s and tells the operator nothing was sent; a mail
    that went after that would be sent again by the Retry."""
    now = [0.0]
    monkeypatch.setattr(outlook, "monotonic", lambda: now[0])

    def slow_draft(_p: dict[str, str], _b: Any) -> dict[str, str]:
        now[0] = outlook.SEND_BUDGET_S + 1  # Graph was slow making the draft
        return {"id": "AAMk-imm-1"}

    nango.on("POST", "/v1.0/me/messages", slow_draft)
    nango.on("POST", "/v1.0/me/messages/AAMk-imm-1/send", None)

    with pytest.raises(RuntimeError, match="nothing was sent"):
        asyncio.run(
            outlook.run_tool("acme", "sam", "send_message", {"to": "a@x.test", "body": "x"})
        )

    assert [p for p, _b in _posts(nango)] == ["/proxy/v1.0/me/messages"], "no /send"


def test_a_send_that_does_not_answer_within_the_budget_says_it_may_have_gone(
    outlook: ModuleType, nango: FakeNango, monkeypatch: pytest.MonkeyPatch
) -> None:
    _drafts(nango)
    monkeypatch.setattr(outlook, "SEND_BUDGET_S", 0.2)
    first = outlook.Graph.call

    async def hangs(self: Any, method: str, path: str, what: str, **kept: Any) -> Any:
        if what == "the send":
            await asyncio.sleep(5)
        return await first(self, method, path, what, **kept)

    monkeypatch.setattr(outlook.Graph, "call", hangs)

    with pytest.raises(RuntimeError, match="check Sent before retrying"):
        asyncio.run(
            outlook.run_tool("acme", "sam", "send_message", {"to": "a@x.test", "body": "x"})
        )


def test_every_graph_call_asks_for_immutable_ids(outlook: ModuleType, nango: FakeNango) -> None:
    """Ids change when a mail moves folders unless asked otherwise
    (learn.microsoft.com/graph/outlook-immutable-id); Nango forwards `Nango-Proxy-*`
    headers (nango.dev/docs/reference/api/proxy/get)."""
    _drafts(nango)
    nango.on("GET", "/v1.0/me/messages", {"value": [_mail("m1")]})
    nango.on("GET", "/v1.0/me/messages/m1", _mail("m1"))

    run(outlook, "search_threads", {"query": "newer_than:2d"})
    run(outlook, "get_message", {"id": "m1"})
    run(outlook, "get_thread", {"id": "conv-1"})
    run(outlook, "send_message", {"to": "a@x.test", "body": "hi"})

    graph = [h for _m, p, _q, _b, h in nango.seen if p.startswith("/proxy")]
    assert len(graph) >= 8
    assert all(h["nango-proxy-prefer"] == 'IdType="ImmutableId"' for h in graph)


def test_a_reply_to_a_mail_that_is_not_here_is_not_sent_as_a_new_one(
    outlook: ModuleType, nango: FakeNango
) -> None:
    nango.on("GET", "/v1.0/me/messages", {"value": []})

    with pytest.raises(RuntimeError, match="not in this mailbox"):
        asyncio.run(
            outlook.run_tool(
                "acme",
                "sam",
                "send_message",
                {"to": "a@x.test", "body": "x", "in_reply_to": "<z@x>"},
            )
        )
    assert not [s for s in nango.seen if s[0] == "POST"]


# --- who may call, and whose mailbox -------------------------------------------------------


def test_graph_is_reached_through_the_connection_nango_holds_for_this_operator(
    outlook: ModuleType, nango: FakeNango
) -> None:
    nango.connections = [
        {
            "connection_id": "old",
            "provider_config_key": "microsoft",
            "created": "2026-01-01T00:00:00+00:00",
            "errors": [],
        },
        {
            "connection_id": "new",
            "provider_config_key": "microsoft",
            "created": "2026-09-01T00:00:00+00:00",
            "errors": [],
        },
        {
            "connection_id": "broken",
            "provider_config_key": "microsoft",
            "created": "2026-10-01T00:00:00+00:00",
            "errors": [{"type": "auth"}],
        },
        {
            "connection_id": "other",
            "provider_config_key": "google-mail",
            "created": "2026-10-01T00:00:00+00:00",
            "errors": [],
        },
    ]
    nango.on("GET", "/v1.0/me/messages", {"value": []})

    run(outlook, "search_threads", {"query": "newer_than:2d"})

    used = {h["connection-id"] for m, p, _q, _b, h in nango.seen if p.startswith("/proxy")}
    assert used == {"new"}


def test_the_connection_is_remembered_briefly_then_asked_again(
    outlook: ModuleType, nango: FakeNango, monkeypatch: pytest.MonkeyPatch
) -> None:
    clock = [1000.0]
    monkeypatch.setattr(outlook, "monotonic", lambda: clock[0])
    nango.on("GET", "/v1.0/me/messages", {"value": []})

    run(outlook, "search_threads", {"query": "newer_than:2d"})
    run(outlook, "search_threads", {"query": "newer_than:2d"})
    assert len([s for s in nango.seen if s[1] == "/connection"]) == 1

    clock[0] += outlook.CONNECTION_TTL_S + 1
    nango.connections = []  # the operator disconnected in Nango
    with pytest.raises(outlook.NoGrant):
        asyncio.run(outlook.run_tool("acme", "sam", "search_threads", {"query": "x"}))
    assert len([s for s in nango.seen if s[1] == "/connection"]) == 2


def test_graph_refusing_is_an_error_the_caller_can_read_without_a_token(
    outlook: ModuleType, nango: FakeNango
) -> None:
    nango.status = 403
    with pytest.raises(RuntimeError) as refused:
        asyncio.run(outlook.run_tool("acme", "sam", "get_message", {"id": "m1"}))

    assert "403" in str(refused.value) and "nope" in str(refused.value)
    assert "nango-secret" not in str(refused.value)


# --- the JSON-RPC server, with its bearer ------------------------------------------------------


@pytest.fixture
def server(outlook: ModuleType, nango: FakeNango) -> Iterator[str]:
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), outlook.Connector)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}/mcp"
    httpd.shutdown()
    httpd.server_close()


def _rpc(
    url: str, method: str, params: dict[str, Any], *, bearer: str = "", session: str = ""
) -> httpx.Response:
    headers = {}
    if bearer:
        headers["Authorization"] = f"Bearer {bearer}"
    if session:
        headers["Mcp-Session-Id"] = session
    return httpx.post(
        url, headers=headers, json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
    )


def _session(url: str) -> str:
    return _rpc(url, "initialize", {}).headers["Mcp-Session-Id"]


def test_the_server_lists_and_calls_the_tools_for_a_signed_bearer(
    outlook: ModuleType, nango: FakeNango, server: str
) -> None:
    _routes_for_mail(nango)
    session = _session(server)
    bearer = sign_bearer(KEY, "outlook", "acme", "sam")

    listed = _rpc(server, "tools/list", {}, session=session).json()["result"]["tools"]
    called = _rpc(
        server,
        "tools/call",
        {"name": "search_threads", "arguments": {"query": "newer_than:2d"}},
        bearer=bearer,
        session=session,
    ).json()["result"]

    assert [t["name"] for t in listed] == [
        "search_threads",
        "get_message",
        "get_thread",
        "send_message",
    ]
    assert not called.get("isError")
    assert json.loads(called["content"][0]["text"])["messages"][0]["id"] == "m1"
    assert _rpc(server, "initialize", {}).json()["result"]["serverInfo"]["name"] == "outlook"


@pytest.mark.parametrize(
    "bearer",
    [
        "",
        "garbage",
        "acme:sam.",
        "acme:sam." + "0" * 64,
        sign_bearer("z" * 40, "outlook", "acme", "sam"),  # signed with another key
        sign_bearer(KEY, "gmail", "acme", "sam"),  # another connector's bearer
        sign_bearer(KEY, "outlook", "acme", "sam").replace("sam", "root", 1),  # forged operator
    ],
)
def test_a_bearer_that_is_not_ours_gets_the_no_grant_envelope(
    outlook: ModuleType, nango: FakeNango, server: str, bearer: str
) -> None:
    session = _session(server)
    answered = _rpc(
        server,
        "tools/call",
        {"name": "get_message", "arguments": {"id": "m1"}},
        bearer=bearer,
        session=session,
    ).json()

    assert answered["error"] == {
        "code": -32001,
        "message": "no grant for that credential: connect this tenant first",
    }
    assert not nango.seen  # nothing was asked of Nango, let alone Graph


def test_a_disconnected_account_gets_the_same_envelope_though_the_bearer_is_good(
    outlook: ModuleType, nango: FakeNango, server: str
) -> None:
    nango.connections = []
    session = _session(server)
    answered = _rpc(
        server,
        "tools/call",
        {"name": "get_message", "arguments": {"id": "m1"}},
        bearer=sign_bearer(KEY, "outlook", "acme", "sam"),
        session=session,
    ).json()

    assert answered["error"]["code"] == -32001
    assert not [s for s in nango.seen if s[1].startswith("/proxy")]


def test_an_unhealthy_only_connection_is_no_grant(
    outlook: ModuleType, nango: FakeNango, server: str
) -> None:
    nango.connections[0]["errors"] = [{"type": "refresh_token_error"}]
    session = _session(server)
    answered = _rpc(
        server,
        "tools/call",
        {"name": "get_message", "arguments": {"id": "m1"}},
        bearer=sign_bearer(KEY, "outlook", "acme", "sam"),
        session=session,
    ).json()

    assert answered["error"]["code"] == -32001


def test_a_call_without_the_session_is_refused_like_gmails(
    outlook: ModuleType, nango: FakeNango, server: str
) -> None:
    answered = _rpc(server, "tools/list", {}).json()

    assert answered["error"]["message"] == "Bad Request: Missing session ID"


def test_a_server_without_a_strong_key_does_not_start(
    outlook: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    for weak in ("", "short"):
        monkeypatch.setattr(outlook, "SIGNING_KEY", weak)
        with pytest.raises(SystemExit, match="CONNECTOR_SIGNING_KEY"):
            outlook.check_config()


# --- fix round 1 ---------------------------------------------------------------------------


def _search_of(outlook: ModuleType, nango: FakeNango, query: str) -> str:
    nango.on("GET", "/v1.0/me/messages", {"value": []})
    run(outlook, "search_threads", {"query": query})
    return listing(nango)["$search"]


@pytest.mark.parametrize(
    ("asked", "kql"),
    [
        ("a AND b", "a AND b"),
        ("AND foo", "foo"),
        ("foo AND", "foo"),
        ("invoice NOT paid", "invoice AND NOT paid"),
        ("NOT paid", "NOT paid"),
        ("invoice NOT", "invoice"),
        ("(refund NOT)", "(refund)"),
        ("invoice (paid NOT)", "invoice AND (paid)"),
        ("a OR OR b", "a OR b"),
        ("a AND OR b", "a OR b"),
        ("(a OR b) c", "(a OR b) AND c"),
        ("c (a OR b)", "c AND (a OR b)"),
        ("-(a b)", "NOT (a AND b)"),
        ("a ()", "a"),
        ("a (b", "a AND (b)"),
        ("a b) c", "a AND b AND c"),
        ("subject:(a OR b)", "(subject:a OR subject:b)"),
        ("from:x subject:(a b) c", "from:x AND (subject:a AND subject:b) AND c"),
    ],
)
def test_a_models_operators_become_valid_kql(
    outlook: ModuleType, nango: FakeNango, asked: str, kql: str
) -> None:
    assert _search_of(outlook, nango, asked) == f'"{kql}"'


def test_two_operators_are_never_written_in_a_row(outlook: ModuleType) -> None:
    for asked in ("a AND AND b", "NOT NOT a", "a OR AND NOT", "((a)) OR (", "OR ( OR a )"):
        said = outlook._kql(outlook.translate(asked, NOW).clauses)
        assert not re.search(r"\b(AND|OR|NOT) (AND|OR)\b", said), (asked, said)
        assert said.count("(") == said.count(")"), (asked, said)


def _parses_as_kql(text: str) -> bool:
    """A tiny KQL grammar: expr := term ((AND|OR)? term)*, term := NOT term | ( expr ) | word."""
    toks = re.findall(r'\(|\)|"[^"]*"|[^\s()]+', text)
    at = 0

    def term() -> bool:
        nonlocal at
        if at >= len(toks):
            return False
        t = toks[at]
        if t == "NOT":
            at += 1
            return term()
        if t == "(":
            at += 1
            if not expr() or at >= len(toks) or toks[at] != ")":
                return False
            at += 1
            return True
        if t in (")", "AND", "OR"):
            return False
        at += 1
        return True

    def expr() -> bool:
        nonlocal at
        if not term():
            return False
        while at < len(toks) and toks[at] != ")":
            if toks[at] in ("AND", "OR"):
                at += 1
            if not term():
                return False
        return True

    return not toks or (expr() and at == len(toks))


def test_random_operator_soup_always_becomes_parseable_kql(outlook: ModuleType) -> None:
    rng = random.Random(7)  # noqa: S311 - a seeded test generator, not a secret
    pieces = ["refund", "invoice", "AND", "OR", "NOT", "(", ")", "-", "from:x", "subject:(a b)"]
    for _ in range(5000):
        asked = " ".join(rng.choice(pieces) for _ in range(rng.randint(1, 9)))
        said = outlook._kql(outlook.translate(asked, NOW).clauses)
        assert _parses_as_kql(said), (asked, said)


def test_a_mailbox_reads_as_the_decoded_header_would(outlook: ModuleType) -> None:
    def one(name: str, address: str) -> str:
        return str(outlook._one({"emailAddress": {"name": name, "address": address}}))

    assert one("Jörg Müller", "jm@x.test") == "Jörg Müller <jm@x.test>"
    assert one("Doe, John", "jd@x.test") == '"Doe, John" <jd@x.test>'
    assert one('Say "hi" \\', "q@x.test") == '"Say \\"hi\\" \\\\" <q@x.test>'
    assert one("Ann\r\nB", "a@x.test") == "Ann B <a@x.test>"
    assert one("", "k@x.test") == "k@x.test"
    for name, address in [
        ("Jörg Müller", "jm@x.test"),
        ("Doe, John", "jd@x.test"),
        ('Say "hi"', "q@x.test"),
        ("日本語", "ü@b.test"),
        ("Ann\r\nB", "a@x.test"),
    ]:
        said = one(name, address)
        assert parseaddr(said)[1] == address, said
        assert [a for _, a in getaddresses([said])] == [address], said
    one("", "/O=ORG/CN=RECIPIENTS/CN=jd")  # an X500 address does not raise


def test_a_filter_with_no_date_bound_has_no_orderby_and_no_sentinel_date(
    outlook: ModuleType, nango: FakeNango
) -> None:
    """$orderby's property must appear in $filter first (user-list-messages); with no date
    to put there, ordering is left out rather than faking a date."""
    nango.on("GET", "/v1.0/me/messages", {"value": []})

    run(outlook, "search_threads", {"query": "is:unread"})
    params = listing(nango)
    assert params["$filter"] == "isRead eq false"
    assert "$orderby" not in params

    run(outlook, "search_threads", {"query": "before:2026/10/01"})
    params = listing(nango)
    assert params["$filter"] == "receivedDateTime lt 2026-10-01T00:00:00Z"
    assert params["$orderby"] == "receivedDateTime desc"


def test_a_next_link_token_is_handed_back_verbatim(outlook: ModuleType, nango: FakeNango) -> None:
    nxt = (
        "https://graph.microsoft.com/v1.0/me/messages?%24top=1&%24skiptoken=a%2Bb%3D%3D+c&%24blank="
    )
    nango.on("GET", "/v1.0/me/messages", {"value": [], "@odata.nextLink": nxt})
    first = run(outlook, "search_threads", {"query": "newer_than:2d"})

    run(outlook, "search_threads", {"query": "x", "page": first["next_page"]})

    params = listing(nango)
    assert params["$skiptoken"] == "a+b==+c"  # %2B stays +, a literal + stays + (not a space)
    assert params["$blank"] == ""


def test_a_comma_in_a_display_name_does_not_break_the_address(
    outlook: ModuleType, nango: FakeNango
) -> None:
    from email.utils import getaddresses, parseaddr

    from sro.application.chat.mailbox import sent_to_others

    own = _mail(
        "m1",
        **{
            "from": _address("Jain, Devansh", "me@corp.example"),
            "toRecipients": [_address("Doe, John", "jd@x.test"), _address("", "kay@x.test")],
        },
    )
    nango.on("GET", "/v1.0/me/messages/m1", own)

    got = run(outlook, "get_message", {"id": "m1"})

    assert parseaddr(got["from"]) == ("Jain, Devansh", "me@corp.example")
    assert [a for _n, a in getaddresses([got["to"]])] == ["jd@x.test", "kay@x.test"]
    assert sent_to_others(got["from"], got["to"], got["cc"], got["mailbox"]) == (
        "jd@x.test",
        "kay@x.test",
        "bob@example.com",
    )


def test_the_caches_follow_the_connection_not_the_operator(
    outlook: ModuleType, nango: FakeNango, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Disconnect mailbox A, connect B: B's own address and folders, not A's."""
    clock = [1000.0]
    monkeypatch.setattr(outlook, "monotonic", lambda: clock[0])
    nango.on("GET", "/v1.0/me/messages/m1", _mail("m1"))
    run(outlook, "get_message", {"id": "m1"})

    nango.connections = [
        {
            "connection_id": "nango-conn-B",
            "provider_config_key": "microsoft",
            "created": "2026-10-01T00:00:00+00:00",
            "errors": [],
        }
    ]
    nango.on("GET", "/v1.0/me", {"mail": "b@other.example"})
    nango.on("GET", "/v1.0/me/mailFolders/sentitems", {"id": "B-sent"})
    clock[0] += outlook.CONNECTION_TTL_S + 1

    got = run(outlook, "get_message", {"id": "m1"})

    assert got["mailbox"] == "b@other.example"
    assert got["sent"] is False  # B's Sent Items folder is B-sent, not A's id


def test_a_cached_address_expires(
    outlook: ModuleType, nango: FakeNango, monkeypatch: pytest.MonkeyPatch
) -> None:
    clock = [1000.0]
    monkeypatch.setattr(outlook, "monotonic", lambda: clock[0])
    nango.on("GET", "/v1.0/me/messages/m1", _mail("m1"))
    run(outlook, "get_message", {"id": "m1"})
    run(outlook, "get_message", {"id": "m1"})

    def asked() -> int:
        return len([p for p, _q in nango.graph_calls() if p == "/proxy/v1.0/me"])

    assert asked() == 1

    clock[0] += outlook.CONNECTION_TTL_S + 1
    run(outlook, "get_message", {"id": "m1"})
    assert asked() == 2


def test_a_connection_tagged_for_another_operator_is_no_grant(
    outlook: ModuleType, nango: FakeNango
) -> None:
    """Defence in depth: Nango's tag filter is trusted, but not alone."""
    nango.connections = [
        {
            "connection_id": "mallory",
            "provider_config_key": "microsoft",
            "created": "2026-10-01T00:00:00+00:00",
            "errors": [],
            "tags": {"end_user_id": "acme:eve"},
        }
    ]

    with pytest.raises(outlook.NoGrant):
        asyncio.run(outlook.run_tool("acme", "sam", "search_threads", {"query": "x"}))
    assert not [s for s in nango.seen if s[1].startswith("/proxy")]


@pytest.mark.parametrize("arguments", [None, "text", ["a"], {"id": 5}])
def test_any_failure_is_the_error_envelope_not_a_dropped_socket(
    outlook: ModuleType, nango: FakeNango, server: str, arguments: Any
) -> None:
    nango.on("GET", "/v1.0/me/messages/5", _mail("5"))
    session = _session(server)
    got = _rpc(
        server,
        "tools/call",
        {"name": "get_message", "arguments": arguments},
        bearer=sign_bearer(KEY, "outlook", "acme", "sam"),
        session=session,
    ).json()

    result = got["result"]
    if arguments == {"id": 5}:
        assert "isError" not in result  # a number id is read as text, like Gmail's
    else:
        assert result["isError"] is True


def test_an_unexpected_error_is_logged_by_type_only(
    outlook: ModuleType,
    nango: FakeNango,
    server: str,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    async def boom(*_a: Any, **_k: Any) -> str:
        raise KeyError("secret-mail-body nango-secret")

    monkeypatch.setattr(outlook, "run_tool", boom)
    session = _session(server)
    got = _rpc(
        server,
        "tools/call",
        {"name": "get_message", "arguments": {"id": "m1"}},
        bearer=sign_bearer(KEY, "outlook", "acme", "sam"),
        session=session,
    ).json()

    assert got["result"]["isError"] is True
    shown = got["result"]["content"][0]["text"] + capsys.readouterr().out
    assert "KeyError" in shown
    assert "secret-mail-body" not in shown and "nango-secret" not in shown
