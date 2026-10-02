"""An MCP connector for Outlook mail, answering what the Gmail connector answers.

It reaches Microsoft Graph through self-hosted Nango's proxy, so it holds no Microsoft
token. Who may call is the signed bearer the backend wrote when the operator linked the
account (`sro.domain.execution.connector_bearer`); whose mailbox is read is the healthy
Nango connection tagged with that operator. Mail content is data and is only ever
returned, never acted on.

Graph facts this leans on (learn.microsoft.com/en-us/graph):
  api/user-list-messages        $filter+$orderby: every $orderby property must lead the
                                $filter (else InefficientFilter); a nextLink is applied whole.
  search-query-parameter        $search on messages: KQL, newest first, up to 1000 results.
  api/message-reply, user-sendmail  202 with no body; custom headers must be named x-*.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import secrets
import sys
import urllib.parse
import uuid
from collections import OrderedDict
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from email.utils import format_datetime, getaddresses
from html.parser import HTMLParser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Lock
from time import monotonic
from typing import Any

import httpx

from sro.application.ports.nango import NangoUnavailable
from sro.domain.execution.connector_bearer import verify_bearer
from sro.infrastructure.nango.client import NangoClient

SERVER = "outlook"
INTEGRATION = "microsoft"
HOST = os.environ.get("OUTLOOK_CONNECTOR_HOST", "127.0.0.1")
NANGO_URL = os.environ.get("NANGO_URL", "")
NANGO_KEY = os.environ.get("NANGO_SECRET_KEY", "")
SIGNING_KEY = os.environ.get("CONNECTOR_SIGNING_KEY", "")
TRANSPORT: httpx.AsyncBaseTransport | None = None  # a test's stand-in for the network
SESSION = uuid.uuid4().hex

GRAPH = "/v1.0/me"
CONNECTION_TTL_S = 60.0  # how long a disconnect in Nango can go unnoticed
K_MAX_LIMIT = 100
K_THREAD_PAGES = 10
K_STASHED_PAGES = 2000
NO_GRANT = "no grant for that credential: connect this tenant first"
PAGE_TOKEN = re.compile(r"[A-Za-z0-9_-]{1,256}")


def now() -> datetime:
    return datetime.now(UTC)


class NoGrant(Exception):
    """No valid bearer, or no healthy Nango connection behind it."""


def _tool(
    name: str, description: str, properties: dict[str, Any], required: list[str]
) -> dict[str, Any]:
    return {
        "name": name,
        "description": description,
        "inputSchema": {"type": "object", "properties": properties, "required": required},
    }


TOOLS = [
    _tool(
        "search_threads",
        "Find mails matching a Gmail search query, newest first.",
        {
            "query": {"type": "string", "description": "Gmail search syntax"},
            "limit": {"type": "string"},
            "page": {"type": "string", "description": "next_page of the search before"},
        },
        ["query"],
    ),
    _tool(
        "get_message",
        "One mail in full: sender, subject and body text.",
        {"id": {"type": "string"}},
        ["id"],
    ),
    _tool(
        "get_thread",
        "Every mail in one conversation, oldest first. Use this when a mail refers to"
        " something said earlier -- 'as discussed', 'the code above' -- because what it"
        " refers to is in the same conversation.",
        {"id": {"type": "string", "description": "thread_id"}},
        ["id"],
    ),
    _tool(
        "send_message",
        "Send a mail. The least reversible thing this connector does.",
        {
            "to": {"type": "string"},
            "bcc": {"type": "string"},
            "subject": {"type": "string"},
            "body": {"type": "string"},
            "thread_id": {
                "type": "string",
                "description": (
                    "Reply inside this conversation rather than starting a new one. "
                    "A reply that lands on its own thread cannot be matched back to "
                    "what it answers."
                ),
            },
            "in_reply_to": {
                "type": "string",
                "description": (
                    "The RFC822 Message-Id being answered, for mail clients that "
                    "thread on headers rather than on Gmail's own thread id."
                ),
            },
            "marker": {
                "type": "string",
                "description": (
                    "Written as the X-SRO-Marker header and read back by get_message "
                    "and get_thread: the mail is known as this system's own before "
                    "Gmail has answered with its id."
                ),
            },
        },
        ["to", "body"],
    ),
]

# What says a mail is a machine's (RFC 3834): the look never answers or reads one.
_AUTOMATION = (
    "auto-submitted",
    "precedence",
    "content-type",
    "x-auto-response-suppress",
    "list-unsubscribe",
    "x-autoreply",
    "x-autorespond",
)
_LIST_SELECT = (
    "id,conversationId,from,subject,receivedDateTime,sentDateTime,bodyPreview,"
    "parentFolderId,isRead,hasAttachments"
)
_FULL_SELECT = (
    "id,conversationId,internetMessageId,internetMessageHeaders,from,toRecipients,"
    "ccRecipients,bccRecipients,subject,body,receivedDateTime,sentDateTime,"
    "parentFolderId,isDraft"
)


# --- Graph, through Nango -----------------------------------------------------------------


@dataclass(frozen=True)
class Graph:
    nango: NangoClient
    connection: str
    who: tuple[str, str]

    async def call(
        self,
        method: str,
        path: str,
        what: str,
        *,
        params: Mapping[str, str] | None = None,
        body: object | None = None,
    ) -> dict[str, Any]:
        response = await self.nango.proxy(
            method,
            path,
            connection_id=self.connection,
            integration=INTEGRATION,
            params=params,
            body=body,
        )
        if response.status_code >= 400:
            detail = ""
            try:
                detail = str(response.json().get("error", {}).get("message", ""))[:200]
            except (ValueError, AttributeError):
                detail = ""
            raise RuntimeError(f"Outlook refused {what} ({response.status_code}): {detail}")
        try:
            said = response.json() if response.content else {}
        except ValueError:
            said = {}
        return said if isinstance(said, dict) else {}


_CONNECTIONS: dict[tuple[str, str], tuple[str, float]] = {}
_FOLDERS: dict[tuple[str, str], dict[str, str]] = {}
_MAILBOXES: dict[tuple[str, str], str] = {}


async def _connection(nango: NangoClient, who: tuple[str, str]) -> str:
    """The newest healthy connection of this operator; remembered briefly, never when empty."""
    kept = _CONNECTIONS.get(who)
    if kept and kept[1] > monotonic():
        return kept[0]
    found = [
        one
        for one in await nango.connections(f"{who[0]}:{who[1]}")
        if one.integration == INTEGRATION and one.healthy
    ]
    if not found:
        _CONNECTIONS.pop(who, None)
        raise NoGrant
    newest = max(found, key=lambda one: one.created_at).connection_id
    _CONNECTIONS[who] = (newest, monotonic() + CONNECTION_TTL_S)
    return newest


async def _folder(graph: Graph, name: str) -> str:
    """A well-known folder's id (the id is what a message's parentFolderId says)."""
    known = _FOLDERS.setdefault(graph.who, {})
    if name not in known:
        got = await graph.call(
            "GET", f"{GRAPH}/mailFolders/{name}", f"the {name} folder", params={"$select": "id"}
        )
        known[name] = str(got.get("id", ""))
    return known[name]


async def _mailbox(graph: Graph) -> str:
    if graph.who not in _MAILBOXES:
        got = await graph.call(
            "GET", GRAPH, "the mailbox's own address", params={"$select": "mail,userPrincipalName"}
        )
        _MAILBOXES[graph.who] = str(got.get("mail") or got.get("userPrincipalName") or "")
    return _MAILBOXES[graph.who]


# --- Graph's shapes into Gmail's -----------------------------------------------------------


def _when(stamp: object) -> datetime | None:
    try:
        return datetime.fromisoformat(str(stamp))
    except ValueError:
        return None


def _rfc2822(stamp: object) -> str:
    moment = _when(stamp)
    return format_datetime(moment.astimezone(UTC)) if moment else ""


def _one(recipient: object) -> str:
    mail = recipient.get("emailAddress") if isinstance(recipient, dict) else None
    if not isinstance(mail, dict):
        return ""
    name, address = str(mail.get("name") or ""), str(mail.get("address") or "")
    return f"{name} <{address}>" if name and address else address or name


def _many(recipients: object) -> str:
    return ", ".join(
        one for one in map(_one, recipients if isinstance(recipients, list) else []) if one
    )


def _headers_of(mail: dict[str, Any]) -> dict[str, str]:
    return {
        str(one.get("name", "")).lower(): str(one.get("value", ""))
        for one in mail.get("internetMessageHeaders") or []
        if isinstance(one, dict)
    }


class _Text(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self.skip = 0

    def handle_starttag(self, tag: str, attrs: Any) -> None:
        self.skip += tag in ("script", "style")
        if tag in ("br", "p", "div", "tr", "li"):
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        self.skip -= tag in ("script", "style") and self.skip > 0

    def handle_data(self, data: str) -> None:
        if not self.skip:
            self.parts.append(data)


def _body_of(mail: dict[str, Any]) -> str:
    body = mail.get("body") if isinstance(mail.get("body"), dict) else {}
    content = str(body.get("content") or "")
    if str(body.get("contentType", "")).lower() != "html":
        return content
    reader = _Text()
    reader.feed(content)
    return re.sub(r"\n\s*\n+", "\n", "".join(reader.parts)).strip()


# --- Gmail's query into Graph's ------------------------------------------------------------

_FOLDERS_OF = {
    "sent": "sentitems",
    "inbox": "inbox",
    "drafts": "drafts",
    "trash": "deleteditems",
    "spam": "junkemail",
}
_TOKEN = re.compile(r'-?(?:[A-Za-z_]+:)?(?:"[^"]*"|\S+)')
_UNIT = {
    "h": timedelta(hours=1),
    "d": timedelta(days=1),
    "m": timedelta(days=30),
    "y": timedelta(days=365),
}


@dataclass
class Query:
    clauses: list[str] = field(default_factory=list)  # KQL, joined by AND unless an OR sits between
    after: datetime | None = None
    before: datetime | None = None
    folder: str = ""
    anywhere: bool = False  # deleted and junk mail are in play
    unread: bool | None = None
    attachment: bool | None = None


def _clean(text: str) -> str:
    return " ".join(re.sub(r"[^\w@.+\-]+", " ", text).split())


def _term(text: str, prop: str = "") -> str:
    words = _clean(text).split()
    named = [f"{prop}:{w}" if prop else w for w in words]
    return named[0] if len(named) == 1 else f"({' AND '.join(named)})" if named else ""


def _instant(text: str) -> datetime | None:
    if text.isdigit() and len(text) >= 9:
        return datetime.fromtimestamp(int(text), UTC)
    try:
        return datetime.strptime(text.replace("/", "-"), "%Y-%m-%d").replace(tzinfo=UTC)
    except ValueError:
        return None


def translate(query: str, at: datetime) -> Query:
    """The Gmail operators this system sends, in Graph's terms; the rest is plain words."""
    out = Query()
    for found in _TOKEN.findall(re.sub(r"[(){}]", " ", query)):
        negated, term = found.startswith("-"), found.lstrip("-")
        if term == "OR":
            out.clauses.append("OR")
            continue
        op, _, value = term.partition(":") if re.match(r"[A-Za-z_]+:", term) else ("", "", term)
        op, value = op.lower(), value.strip('"')
        plain = _term(f"{op} {value}" if op else value)
        if op == "in" and value.lower() == "chats":
            continue
        if op == "in" and value.lower() == "anywhere":
            out.anywhere = True
        elif op == "in" and value.lower() in _FOLDERS_OF and not negated:
            out.folder = _FOLDERS_OF[value.lower()]
        elif op in ("newer_than", "older_than") and (m := re.fullmatch(r"(\d+)([hdmy])", value)):
            edge = at - int(m[1]) * _UNIT[m[2]]
            if op == "newer_than":
                out.after = edge
            else:
                out.before = edge
        elif op in ("after", "before") and (edge := _instant(value)):
            if op == "after":
                out.after = edge
            else:
                out.before = edge
        elif op == "is" and value.lower() in ("unread", "read"):
            out.unread = (value.lower() == "unread") != negated
        elif op == "has" and value.lower() == "attachment":
            out.attachment = not negated
        elif op in ("from", "to", "cc", "bcc", "subject") and _term(value, op):
            out.clauses.append(("NOT " if negated else "") + _term(value, op))
        elif plain:
            out.clauses.append(("NOT " if negated else "") + plain)
    return out


def _kql(clauses: list[str]) -> str:
    kept = list(clauses)
    while kept and kept[0] == "OR":
        kept.pop(0)
    while kept and kept[-1] == "OR":
        kept.pop()
    out: list[str] = []
    for clause in kept:
        if out and out[-1] != "OR" and clause != "OR":
            out.append("AND")
        if clause == "OR" and out and out[-1] == "OR":
            continue
        out.append(clause)
    return " ".join(out)


def _filter(q: Query) -> str:
    # $orderby's property has to lead the $filter, so it is always there when anything is.
    low = iso(q.after) if q.after else "0001-01-01T00:00:00Z"
    parts = [f"receivedDateTime ge {low}"]
    if q.before:
        parts.append(f"receivedDateTime lt {iso(q.before)}")
    if q.unread is not None:
        parts.append(f"isRead eq {str(not q.unread).lower()}")
    if q.attachment is not None:
        parts.append(f"hasAttachments eq {str(q.attachment).lower()}")
    return " and ".join(parts)


def iso(moment: datetime) -> str:
    return moment.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _keeps(row: dict[str, Any], q: Query, hidden: set[str], *, filtered: bool) -> bool:
    """What Graph could not be asked for, asked of the page that came back."""
    if row.get("parentFolderId") in hidden:
        return False
    if filtered:
        return True
    got = _when(row.get("receivedDateTime"))
    if got and ((q.after and got < q.after) or (q.before and got >= q.before)):
        return False
    if q.unread is not None and bool(row.get("isRead")) == q.unread:
        return False
    return not (q.attachment is not None and bool(row.get("hasAttachments")) != q.attachment)


# --- paging: Graph's nextLink is applied whole, and does not fit Gmail's page token --------

_PAGES: OrderedDict[str, tuple[tuple[str, str], str, dict[str, str], Query]] = OrderedDict()
_PAGES_LOCK = Lock()


def _stash(who: tuple[str, str], link: object, q: Query) -> str:
    if not isinstance(link, str) or not link:
        return ""
    split = urllib.parse.urlsplit(link)
    token = secrets.token_urlsafe(16)
    with _PAGES_LOCK:
        _PAGES[token] = (who, split.path, dict(urllib.parse.parse_qsl(split.query)), q)
        while len(_PAGES) > K_STASHED_PAGES:
            _PAGES.popitem(last=False)
    return token


def _unstash(who: tuple[str, str], token: str) -> tuple[str, dict[str, str], Query]:
    kept = _PAGES.get(token) if PAGE_TOKEN.fullmatch(token) else None
    if kept is None or kept[0] != who:
        raise ValueError("not a page token this connector handed out")
    return kept[1], kept[2], kept[3]


# --- the tools ------------------------------------------------------------------------------


async def _search(graph: Graph, arguments: Mapping[str, Any]) -> str:
    page = str(arguments.get("page") or "")
    if page:
        path, params, q = _unstash(graph.who, page)
    else:
        limit = max(1, min(int(str(arguments.get("limit", "10"))), K_MAX_LIMIT))
        q = translate(str(arguments.get("query", "")), now())
        path = f"{GRAPH}/mailFolders/{q.folder}/messages" if q.folder else f"{GRAPH}/messages"
        params = {"$top": str(limit), "$select": _LIST_SELECT}
        if q.clauses:  # Graph refuses $filter and $orderby beside $search
            params["$search"] = f'"{_kql(q.clauses)}"'
        else:
            params["$orderby"] = "receivedDateTime desc"
            if q.after or q.before or q.unread is not None or q.attachment is not None:
                params["$filter"] = _filter(q)
    listed = await graph.call("GET", path, "the search", params=params)
    hidden = (
        set()
        if q.folder or q.anywhere
        else {await _folder(graph, "deleteditems"), await _folder(graph, "junkemail")}
    )
    rows = [
        r
        for r in listed.get("value") or []
        if isinstance(r, dict) and _keeps(r, q, hidden, filtered=not q.clauses)
    ]
    return json.dumps(
        {
            "messages": [
                {
                    "id": r.get("id", ""),
                    "from": _one(r.get("from")),
                    "subject": r.get("subject", ""),
                    "date": _rfc2822(r.get("sentDateTime") or r.get("receivedDateTime")),
                    "snippet": r.get("bodyPreview", ""),
                }
                for r in rows
            ],
            "next_page": _stash(graph.who, listed.get("@odata.nextLink"), q),
        },
        indent=1,
    )


async def _get(graph: Graph, arguments: Mapping[str, Any]) -> str:
    ident = urllib.parse.quote(str(arguments.get("id", "")), safe="")
    mail = await graph.call(
        "GET", f"{GRAPH}/messages/{ident}", "that message", params={"$select": _FULL_SELECT}
    )
    head = _headers_of(mail)
    return json.dumps(
        {
            "id": mail.get("id", ""),
            "thread_id": mail.get("conversationId", ""),
            "rfc822_message_id": mail.get("internetMessageId") or head.get("message-id", ""),
            "from": _one(mail.get("from")),
            "to": _many(mail.get("toRecipients")),
            "cc": _many(mail.get("ccRecipients")),
            "date": head.get("date")
            or _rfc2822(mail.get("sentDateTime") or mail.get("receivedDateTime")),
            "sent": mail.get("parentFolderId") == await _folder(graph, "sentitems"),
            "in_reply_to": head.get("in-reply-to", ""),
            "marker": head.get("x-sro-marker", ""),
            "references": head.get("references", ""),
            "mailbox": await _mailbox(graph),
            "subject": mail.get("subject", ""),
            "body": _body_of(mail),
            "headers": {name: head[name] for name in _AUTOMATION if name in head},
        },
        indent=1,
    )


def _quote(text: str) -> str:
    return text.replace("'", "''")


async def _conversation(graph: Graph, conversation: str) -> list[dict[str, Any]]:
    """Every message of one conversation. No $orderby: Graph refuses it beside this $filter."""
    found: list[dict[str, Any]] = []
    path, params = (
        "/v1.0/me/messages",
        {
            "$filter": f"conversationId eq '{_quote(conversation)}'",
            "$select": _FULL_SELECT,
            "$top": "100",
        },
    )
    for _ in range(K_THREAD_PAGES):
        got = await graph.call("GET", path, "that conversation", params=params)
        found += [r for r in got.get("value") or [] if isinstance(r, dict)]
        link = got.get("@odata.nextLink")
        if not isinstance(link, str) or not link:
            break
        split = urllib.parse.urlsplit(link)
        path, params = split.path, dict(urllib.parse.parse_qsl(split.query))
    return sorted(
        found, key=lambda r: _when(r.get("receivedDateTime")) or datetime.min.replace(tzinfo=UTC)
    )


async def _thread(graph: Graph, arguments: Mapping[str, Any]) -> str:
    conversation = str(arguments.get("id", ""))
    sent_id = await _folder(graph, "sentitems")
    said = []
    for mail in await _conversation(graph, conversation):
        head = _headers_of(mail)
        at = _when(mail.get("receivedDateTime") or mail.get("sentDateTime"))
        said.append(
            {
                "id": mail.get("id", ""),
                "rfc822_message_id": mail.get("internetMessageId") or head.get("message-id", ""),
                "from": _one(mail.get("from")),
                "to": _many(mail.get("toRecipients")),
                "cc": _many(mail.get("ccRecipients")),
                "bcc": _many(mail.get("bccRecipients")),
                "sent": mail.get("parentFolderId") == sent_id,
                "sent_at": at.timestamp() if at else 0.0,
                "marker": head.get("x-sro-marker", ""),
                "date": head.get("date")
                or _rfc2822(mail.get("sentDateTime") or mail.get("receivedDateTime")),
                "subject": mail.get("subject", ""),
                "body": _body_of(mail),
            }
        )
    return json.dumps({"id": conversation, "messages": said}, indent=1)


def _recipients(text: object) -> list[dict[str, Any]]:
    return [
        {"emailAddress": {"address": address}}
        for _, address in getaddresses([str(text or "")])
        if address
    ]


async def _answered(graph: Graph, answering: str, thread: str) -> str:
    """Graph's id of the mail being answered: by its Message-Id, else the conversation's newest."""
    if answering:
        got = await graph.call(
            "GET",
            f"{GRAPH}/messages",
            "the mail being answered",
            params={
                "$filter": f"internetMessageId eq '{_quote(answering)}'",
                "$select": "id",
                "$top": "1",
            },
        )
        for one in got.get("value") or []:
            if isinstance(one, dict) and one.get("id"):
                return str(one["id"])
    if thread:
        newest = [m for m in await _conversation(graph, thread) if not m.get("isDraft")]
        if newest:
            return str(newest[-1]["id"])
    raise RuntimeError("Outlook cannot answer a mail that is not in this mailbox")


async def _send(graph: Graph, arguments: Mapping[str, Any]) -> str:
    message: dict[str, Any] = {"toRecipients": _recipients(arguments.get("to"))}
    if arguments.get("bcc"):
        message["bccRecipients"] = _recipients(arguments["bcc"])
    if arguments.get("marker"):
        message["internetMessageHeaders"] = [
            {"name": "X-SRO-Marker", "value": str(arguments["marker"])}
        ]
    answering = str(arguments.get("in_reply_to", "")).strip()
    thread = str(arguments.get("thread_id", "")).strip()
    if answering or thread:
        target = urllib.parse.quote(await _answered(graph, answering, thread), safe="")
        await graph.call(
            "POST",
            f"{GRAPH}/messages/{target}/reply",
            "the reply",
            body={"comment": str(arguments.get("body", "")), "message": message},
        )
    else:
        message["subject"] = str(arguments.get("subject", ""))
        message["body"] = {"contentType": "Text", "content": str(arguments.get("body", ""))}
        await graph.call("POST", f"{GRAPH}/sendMail", "the send", body={"message": message})
    print(f"  -> sent to {len(message['toRecipients'])} recipient(s)")
    # Graph answers 202 with no body, so there is no id to give back; the marker is the handle.
    return json.dumps({"status": "sent", "id": ""})


_DO = {"search_threads": _search, "get_message": _get, "get_thread": _thread, "send_message": _send}


async def run_tool(tenant: str, operator: str, name: str, arguments: Mapping[str, Any]) -> str:
    if name not in _DO:
        raise LookupError(f"no tool called {name}")
    client = httpx.AsyncClient(timeout=20.0, transport=TRANSPORT)
    nango = NangoClient(NANGO_URL, NANGO_KEY, http=client)
    try:
        who = (tenant, operator)
        return await _DO[name](Graph(nango, await _connection(nango, who), who), arguments)
    finally:
        await nango.aclose()


# --- the JSON-RPC server, the Gmail connector's shape ---------------------------------------


class Connector(BaseHTTPRequestHandler):
    def log_message(self, *args: Any) -> None:
        return

    def do_POST(self) -> None:
        raw = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        request = json.loads(raw or b"{}")
        method = request.get("method", "")
        print(f"{method}")

        if method == "initialize":
            self._reply(
                200,
                self._envelope(
                    request.get("id"),
                    {
                        "protocolVersion": "2025-06-18",
                        "capabilities": {"tools": {"listChanged": False}},
                        "serverInfo": {"name": SERVER, "version": "1"},
                    },
                ),
                session=SESSION,
            )
            return

        if self.headers.get("Mcp-Session-Id") != SESSION:
            self._reply(
                200, self._error(request.get("id"), -32600, "Bad Request: Missing session ID")
            )
            return

        if method == "notifications/initialized":
            self._reply(202, b"")
            return
        if method == "tools/list":
            self._reply(200, self._envelope(request.get("id"), {"tools": TOOLS}))
            return
        if method == "tools/call":
            bearer = self.headers.get("Authorization", "").removeprefix("Bearer ").strip()
            who = verify_bearer(SIGNING_KEY, SERVER, bearer)
            params = request.get("params", {})
            name, arguments = params.get("name", ""), params.get("arguments", {})
            try:
                if who is None:
                    raise NoGrant
                text = asyncio.run(run_tool(who[0], who[1], name, arguments))
            except NoGrant:
                print("  ! a call with no grant behind its bearer")
                self._reply(200, self._error(request.get("id"), -32001, NO_GRANT))
                return
            except LookupError as unknown:
                self._reply(200, self._failed(request.get("id"), str(unknown)))
                return
            except (RuntimeError, ValueError, NangoUnavailable) as refused:
                print(f"  ! {refused}")
                self._reply(200, self._failed(request.get("id"), str(refused)))
                return
            self._reply(
                200,
                self._envelope(request.get("id"), {"content": [{"type": "text", "text": text}]}),
            )
            return

        self._reply(200, self._error(request.get("id"), -32601, f"no method {method}"))

    def _failed(self, ident: Any, message: str) -> bytes:
        return self._envelope(
            ident, {"content": [{"type": "text", "text": message}], "isError": True}
        )

    def _envelope(self, ident: Any, result: dict[str, Any]) -> bytes:
        return json.dumps({"jsonrpc": "2.0", "id": ident, "result": result}).encode()

    def _error(self, ident: Any, code: int, message: str) -> bytes:
        return json.dumps(
            {"jsonrpc": "2.0", "id": ident, "error": {"code": code, "message": message}}
        ).encode()

    def _reply(self, code: int, body: bytes, session: str = "") -> None:
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        if session:
            self.send_header("Mcp-Session-Id", session)
        self.end_headers()
        self.wfile.write(body)


def check_config() -> None:
    if len(SIGNING_KEY.encode()) < 32:
        raise SystemExit(
            "CONNECTOR_SIGNING_KEY must be set, at least 32 bytes "
            "(the backend's SRO_CONNECTOR_SIGNING_KEY)"
        )
    if not NANGO_URL or not NANGO_KEY:
        raise SystemExit("NANGO_URL and NANGO_SECRET_KEY must be set")


if __name__ == "__main__":
    port = int(next((one for one in sys.argv[1:] if one.isdigit()), "8934"))
    check_config()
    try:
        server = ThreadingHTTPServer((HOST, port), Connector)
    except OSError as taken:
        print(f"port {port} is already in use ({taken.strerror}).")
        raise SystemExit(1) from taken

    print(f"outlook connector on http://{HOST}:{port}/mcp")
    print(f"  SRO_MCP_SERVERS=outlook=http://localhost:{port}/mcp")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped.")
