from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import secrets
import sys
import urllib.parse
import uuid
import webbrowser
from email.message import EmailMessage
from email.utils import getaddresses
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import httpx

HERE = Path(__file__).resolve().parent
TOKEN_FILE = HERE.parent / ".gmail-token.json"

HOST = os.environ.get("GMAIL_CONNECTOR_HOST", "127.0.0.1")

GRANTS = HERE.parent / ".gmail-grants"


def _grant_of(bearer: str) -> dict[str, str] | None:
    if not bearer:
        return None
    named = GRANTS / f"{hashlib.sha256(bearer.encode()).hexdigest()}.json"
    if not named.is_file():
        return None
    kept = json.loads(named.read_text())
    return kept if isinstance(kept, dict) else None


REDIRECT = "http://localhost:8933/oauth/callback"

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
]

GMAIL = "https://gmail.googleapis.com/gmail/v1/users/me"
SESSION = uuid.uuid4().hex

TOOLS = [
    {
        "name": "search_threads",
        "description": "Find mails matching a Gmail search query, newest first.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Gmail search syntax"},
                "limit": {"type": "string"},
                "page": {"type": "string", "description": "next_page of the search before"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_message",
        "description": "One mail in full: sender, subject and body text.",
        "inputSchema": {
            "type": "object",
            "properties": {"id": {"type": "string"}},
            "required": ["id"],
        },
    },
    {
        "name": "get_thread",
        "description": (
            "Every mail in one conversation, oldest first. Use this when a mail"
            " refers to something said earlier -- 'as discussed', 'the code"
            " above' -- because what it refers to is in the same conversation."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {"id": {"type": "string", "description": "thread_id"}},
            "required": ["id"],
        },
    },
    {
        "name": "send_message",
        "description": "Send a mail. The least reversible thing this connector does.",
        "inputSchema": {
            "type": "object",
            "properties": {
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
            },
            "required": ["to", "body"],
        },
    },
]


def _client() -> tuple[str, str]:
    ident = os.environ.get("GMAIL_CLIENT_ID", "").strip()
    secret = os.environ.get("GMAIL_CLIENT_SECRET", "").strip()
    if ident and secret:
        return ident, secret

    downloaded = sorted(HERE.parent.glob("client_secret*.json"))
    if not downloaded:
        raise SystemExit(
            "No OAuth client found.\n"
            "  Either download the client's JSON from the Google Cloud console into\n"
            f"  {HERE.parent}/ -- it is gitignored -- or set GMAIL_CLIENT_ID and\n"
            "  GMAIL_CLIENT_SECRET in the environment."
        )
    if len(downloaded) > 1:
        raise SystemExit(
            f"More than one client_secret*.json in {HERE.parent}/. "
            "Leave the one this should use and move the others out: guessing which "
            "client an operator meant is how a grant ends up on the wrong project."
        )
    found = json.loads(downloaded[0].read_text())
    web = found.get("web") or found.get("installed") or {}
    if not web.get("client_id") or not web.get("client_secret"):
        raise SystemExit(f"{downloaded[0].name} has no client_id and client_secret in it")
    if REDIRECT not in (web.get("redirect_uris") or []):
        raise SystemExit(
            f"{downloaded[0].name} does not list {REDIRECT} as a redirect URI.\n"
            "  Add it in the Google Cloud console under this client's Authorized\n"
            "  redirect URIs, download the file again, and retry. Google matches it\n"
            "  exactly, so a trailing slash or https is a different URI."
        )
    return str(web["client_id"]), str(web["client_secret"])


def _access_token(grant: dict[str, str]) -> str:
    stored = grant
    ident, secret = _client()
    answer = httpx.post(
        "https://oauth2.googleapis.com/token",
        data={
            "client_id": ident,
            "client_secret": secret,
            "refresh_token": stored["refresh_token"],
            "grant_type": "refresh_token",
        },
        timeout=20.0,
    )
    if answer.status_code >= 400:
        raise SystemExit(
            f"Google refused the refresh ({answer.status_code}). "
            "A grant made in Testing expires after seven days; re-run --authorize."
        )
    return str(answer.json()["access_token"])


def _keep(tenant: str, operator: str, refresh_token: str) -> None:
    bearer = secrets.token_urlsafe(32)
    GRANTS.mkdir(mode=0o700, exist_ok=True)
    named = GRANTS / f"{hashlib.sha256(bearer.encode()).hexdigest()}.json"
    named.write_text(
        json.dumps(
            {"tenant": tenant, "operator": operator, "refresh_token": refresh_token}, indent=1
        )
    )
    named.chmod(0o600)
    print(f"\ngrant stored for {operator} of {tenant}. Gitignored, and holds no mail.")
    print("Put this in the vault as this operator's connector credential:")
    print(f"\n  {bearer}\n")
    print(f"  key: {_vault_key(tenant, operator)}")
    print("It is shown once. Losing it costs a re-authorize, not the mailbox.")


def _vault_key(tenant: str, operator: str) -> str:
    named = hashlib.sha256(operator.encode()).hexdigest()[:32]
    return f"{tenant}/gmail/mcp-token-{named}"


def authorize(tenant: str, operator: str) -> None:
    if TOKEN_FILE.exists():
        kept = json.loads(TOKEN_FILE.read_text())
        if kept.get("refresh_token"):
            print(f"adopting the grant already in {TOKEN_FILE.name} for {operator}.")
            print(f"  nothing was sent to Google. You may delete {TOKEN_FILE.name} when done.")
            _keep(tenant, operator, str(kept["refresh_token"]))
            return
    ident, secret = _client()
    got: dict[str, str] = {}

    class Catch(BaseHTTPRequestHandler):
        def log_message(self, *args: Any) -> None:
            return

        def do_GET(self) -> None:
            query = urllib.parse.urlparse(self.path).query
            found = urllib.parse.parse_qs(query)
            got.update({key: value[0] for key, value in found.items()})
            body = b"AI-SRO has the grant. You can close this tab."
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    consent = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(
        {
            "client_id": ident,
            "redirect_uri": REDIRECT,
            "response_type": "code",
            "scope": " ".join(SCOPES),
            "access_type": "offline",
            "prompt": "consent",
        }
    )
    print("opening Google's consent screen. Approve it in the browser.")
    print(f"  if it does not open: {consent}\n")
    webbrowser.open(consent)

    catcher = ThreadingHTTPServer(("127.0.0.1", 8933), Catch)
    while "code" not in got and "error" not in got:
        catcher.handle_request()
    catcher.server_close()

    if "error" in got:
        raise SystemExit(f"Google said no: {got['error']}")

    answer = httpx.post(
        "https://oauth2.googleapis.com/token",
        data={
            "client_id": ident,
            "client_secret": secret,
            "code": got["code"],
            "grant_type": "authorization_code",
            "redirect_uri": REDIRECT,
        },
        timeout=20.0,
    )
    if answer.status_code >= 400:
        raise SystemExit(f"the code would not exchange ({answer.status_code}): {answer.text[:200]}")
    granted = answer.json()
    if "refresh_token" not in granted:
        raise SystemExit(
            "Google returned no refresh token. That happens when this account has "
            "already granted this client: revoke it at "
            "https://myaccount.google.com/permissions and run --authorize again."
        )
    _keep(tenant, operator, str(granted["refresh_token"]))


def _headers_of(payload: dict[str, Any]) -> dict[str, str]:
    return {
        str(one.get("name", "")).lower(): str(one.get("value", ""))
        for one in payload.get("headers", [])
        if isinstance(one, dict)
    }


def _body_of(payload: dict[str, Any]) -> str:
    if payload.get("mimeType") == "text/plain":
        data = payload.get("body", {}).get("data", "")
        if data:
            return base64.urlsafe_b64decode(data + "===").decode("utf-8", "replace")
    for part in payload.get("parts", []) or []:
        if isinstance(part, dict):
            found = _body_of(part)
            if found:
                return found
    return ""


def _answered(response: httpx.Response, what: str) -> dict[str, Any]:
    if response.status_code >= 400:
        detail = ""
        try:
            detail = str(response.json().get("error", {}).get("message", ""))
        except ValueError:
            detail = response.text[:200]
        raise RuntimeError(f"Gmail refused {what} ({response.status_code}): {detail}")
    return dict(response.json())


PAGE_TOKEN = re.compile(r"[A-Za-z0-9_-]{1,256}")


def _search(token: str, arguments: dict[str, Any]) -> str:
    limit = str(arguments.get("limit", "10"))
    page = str(arguments.get("page") or "")
    if page and not PAGE_TOKEN.fullmatch(page):
        raise ValueError("not a page token this connector handed out")
    listed = _answered(
        httpx.get(
            f"{GMAIL}/messages",
            params={
                "q": arguments.get("query", ""),
                "maxResults": limit,
                **({"pageToken": page} if page else {}),
            },
            headers={"Authorization": f"Bearer {token}"},
            timeout=20.0,
        ),
        "the search",
    )
    found = []
    for one in listed.get("messages", []) or []:
        full = _answered(
            httpx.get(
                f"{GMAIL}/messages/{one['id']}",
                params={"format": "metadata", "metadataHeaders": ["From", "Subject", "Date"]},
                headers={"Authorization": f"Bearer {token}"},
                timeout=20.0,
            ),
            "one of the search results",
        )
        head = _headers_of(full.get("payload", {}))
        found.append(
            {
                "id": one["id"],
                "from": head.get("from", ""),
                "subject": head.get("subject", ""),
                "date": head.get("date", ""),
                "snippet": full.get("snippet", ""),
            }
        )
    return json.dumps({"messages": found, "next_page": listed.get("nextPageToken", "")}, indent=1)


MAILBOXES: dict[tuple[str, str], str] = {}


def _mailbox(grant: dict[str, str], token: str) -> str:
    whose = (grant.get("tenant", ""), grant.get("operator", ""))
    if whose not in MAILBOXES:
        MAILBOXES[whose] = str(
            _answered(
                httpx.get(
                    f"{GMAIL}/profile",
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=20.0,
                ),
                "the mailbox's own address",
            ).get("emailAddress", "")
        )
    return MAILBOXES[whose]


def _get(token: str, arguments: dict[str, Any], mailbox: str = "") -> str:
    full = _answered(
        httpx.get(
            f"{GMAIL}/messages/{arguments.get('id', '')}",
            params={"format": "full"},
            headers={"Authorization": f"Bearer {token}"},
            timeout=20.0,
        ),
        "that message",
    )
    payload = full.get("payload", {})
    head = _headers_of(payload)
    return json.dumps(
        {
            "id": full.get("id", ""),
            "thread_id": full.get("threadId", ""),
            "rfc822_message_id": head.get("message-id", ""),
            "from": head.get("from", ""),
            "to": head.get("to", ""),
            "cc": head.get("cc", ""),
            "bcc": head.get("bcc", ""),
            "sent": "SENT" in (full.get("labelIds") or []),
            "mailbox": mailbox,
            "subject": head.get("subject", ""),
            "body": _body_of(payload),
        },
        indent=1,
    )


def _thread(token: str, arguments: dict[str, Any]) -> str:
    whole = _answered(
        httpx.get(
            f"{GMAIL}/threads/{arguments.get('id', '')}",
            params={"format": "full"},
            headers={"Authorization": f"Bearer {token}"},
            timeout=20.0,
        ),
        "that conversation",
    )
    said = []
    for one in whole.get("messages", []) or []:
        payload = one.get("payload", {})
        head = _headers_of(payload)
        said.append(
            {
                "id": one.get("id", ""),
                "rfc822_message_id": head.get("message-id", ""),
                "from": head.get("from", ""),
                "to": head.get("to", ""),
                "cc": head.get("cc", ""),
                "sent": "SENT" in (one.get("labelIds") or []),
                "date": head.get("date", ""),
                "subject": head.get("subject", ""),
                "body": _body_of(payload),
            }
        )
    return json.dumps({"id": whole.get("id", ""), "messages": said}, indent=1)


def _send(token: str, arguments: dict[str, Any]) -> str:
    mail = EmailMessage()
    mail["To"] = str(arguments.get("to", ""))
    if arguments.get("bcc"):
        mail["Bcc"] = str(arguments["bcc"])
    mail["Subject"] = str(arguments.get("subject", ""))
    mail.set_content(str(arguments.get("body", "")))
    within = str(arguments.get("thread_id", "")).strip()
    answering = str(arguments.get("in_reply_to", "")).strip()
    if answering:
        mail["In-Reply-To"] = answering
        mail["References"] = answering
    raw = base64.urlsafe_b64encode(mail.as_bytes()).decode()
    answer = httpx.post(
        f"{GMAIL}/messages/send",
        json={"raw": raw, **({"threadId": within} if within else {})},
        headers={"Authorization": f"Bearer {token}"},
        timeout=30.0,
    )
    if answer.status_code >= 400:
        raise RuntimeError(f"Gmail refused the send ({answer.status_code}): {answer.text[:200]}")
    print(f"  → sent to {len(getaddresses([str(arguments.get('to', ''))]))} recipient(s)")
    return json.dumps({"status": "sent", "id": answer.json().get("id", "")})


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
                        "serverInfo": {"name": "gmail", "version": "1"},
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
            grant = _grant_of(bearer)
            if grant is None:
                print("  ! a call with no grant behind its bearer")
                self._reply(
                    200,
                    self._error(
                        request.get("id"),
                        -32001,
                        "no grant for that credential: connect this tenant first",
                    ),
                )
                return
            params = request.get("params", {})
            name, arguments = params.get("name", ""), params.get("arguments", {})
            try:
                token = _access_token(grant)
                if name == "search_threads":
                    text = _search(token, arguments)
                elif name == "get_message":
                    text = _get(token, arguments, _mailbox(grant, token))
                elif name == "get_thread":
                    text = _thread(token, arguments)
                elif name == "send_message":
                    text = _send(token, arguments)
                else:
                    self._reply(
                        200,
                        self._envelope(
                            request.get("id"),
                            {
                                "content": [{"type": "text", "text": f"no tool called {name}"}],
                                "isError": True,
                            },
                        ),
                    )
                    return
            except Exception as refused:
                print(f"  ! {refused}")
                self._reply(
                    200,
                    self._envelope(
                        request.get("id"),
                        {"content": [{"type": "text", "text": str(refused)}], "isError": True},
                    ),
                )
                return
            self._reply(
                200,
                self._envelope(request.get("id"), {"content": [{"type": "text", "text": text}]}),
            )
            return

        self._reply(200, self._error(request.get("id"), -32601, f"no method {method}"))

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


if __name__ == "__main__":
    if "--authorize" in sys.argv:
        named = [one for one in sys.argv[1:] if not one.startswith("-") and not one.isdigit()]
        if len(named) < 2:
            raise SystemExit(
                "who is this grant for?\n"
                f"  {sys.argv[0]} --authorize <tenant> <operator>\n"
                "A grant belongs to one person: each operator reads their own mail, "
                "and a connector holding one grant for everybody hands whichever "
                "mailbox it has to whoever reaches it."
            )
        authorize(named[0], named[1])
        raise SystemExit(0)

    port = int(next((one for one in sys.argv[1:] if one.isdigit()), "8932"))
    _client()
    if not GRANTS.is_dir() or not any(GRANTS.glob("*.json")):
        raise SystemExit(f"no grant yet: run `{sys.argv[0]} --authorize <tenant> <operator>` first")

    try:
        server = ThreadingHTTPServer((HOST, port), Connector)
    except OSError as taken:
        print(f"port {port} is already in use ({taken.strerror}).")
        print(f"  what has it:  lsof -ti :{port}")
        print(f"  free it:      lsof -ti :{port} | xargs kill")
        raise SystemExit(1) from taken

    print(f"gmail connector on http://{HOST}:{port}/mcp")
    print("point the system at it with, in backend/.env:")
    print(f"  SRO_MCP_SERVERS=gmail=http://localhost:{port}/mcp")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped.")
