"""Gmail, as a connector a skill's step can call.

The point is not convenience. A step done by clicking can never be trusted to
run unattended -- `verdict.py` makes a run with a UI step DEGRADED, and DEGRADED
resets the streak autonomy counts -- so a mail half taught by clicking in Gmail
is capped at assisted forever, however many times it works. A step that is a
call is clean-eligible, and can climb.

Streamable-HTTP MCP, because that is what this system's connector speaks. Most
Gmail MCP servers are stdio and cannot be reached by it at all.

    # once, in a browser you are signed into:
    uv run python backend/gmail-connector/server.py --authorize

    # then, to serve:
    uv run python backend/gmail-connector/server.py 8932

Credentials come from the environment, never from arguments -- an argument is in
the shell history and in `ps`:

    GMAIL_CLIENT_ID=...     # the OAuth client, from Google Cloud
    GMAIL_CLIENT_SECRET=... # put it in backend/.env; it is not printed here

The refresh token it obtains is written to `backend/.gmail-token.json`, which is
gitignored. Nothing about the mailbox is stored: this reads and sends, and keeps
no copy.
"""

from __future__ import annotations

import base64
import json
import os
import sys
import urllib.parse
import uuid
import webbrowser
from email.message import EmailMessage
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import httpx

HERE = Path(__file__).resolve().parent
TOKEN_FILE = HERE.parent / ".gmail-token.json"

REDIRECT = "http://localhost:8933/oauth/callback"
"""Where Google sends the operator back. Must be listed in the OAuth client's
Authorized redirect URIs, exactly as written here."""

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
]
"""Read and send, and nothing else. `gmail.modify` would also let this delete,
which no step here does and no operator agreed to."""

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
        "name": "send_message",
        "description": "Send a mail. The least reversible thing this connector does.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "to": {"type": "string"},
                "subject": {"type": "string"},
                "body": {"type": "string"},
            },
            "required": ["to", "body"],
        },
    },
]


def _client() -> tuple[str, str]:
    """The OAuth client, from the file Google hands you.

    Read out of `client_secret*.json` as downloaded, rather than asking anybody
    to copy two values into a second place. A secret copied by hand is a secret
    typed into a shell, pasted into a chat, and left in a scrollback -- and the
    file is already the thing Google treats as canonical.

    The environment still wins where it is set, because a deployment that keeps
    its secrets somewhere else should not have to invent this file.
    """
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


def _access_token() -> str:
    """A live access token, refreshed from the stored grant.

    Refreshed on every call rather than cached with an expiry: this serves one
    request at a time, minutes apart, and a token that expired between two of
    them is a failure nobody could explain from the logs.
    """
    if not TOKEN_FILE.exists():
        raise SystemExit(f"no grant yet: run `{sys.argv[0]} --authorize` first")
    stored = json.loads(TOKEN_FILE.read_text())
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


def authorize() -> None:
    """The one step nobody can take on the operator's behalf.

    Their Google account, their consent screen, their decision about what this
    may read and send. All this does is open the page and catch the code Google
    sends back.
    """
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
            # Offline and forced, so a refresh token comes back. Google sends
            # one only on the first consent unless asked again.
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
    TOKEN_FILE.write_text(json.dumps({"refresh_token": granted["refresh_token"]}, indent=1))
    TOKEN_FILE.chmod(0o600)
    print(f"grant stored in {TOKEN_FILE.name}. It is gitignored, and holds no mail.")


def _headers_of(payload: dict[str, Any]) -> dict[str, str]:
    return {
        str(one.get("name", "")).lower(): str(one.get("value", ""))
        for one in payload.get("headers", [])
        if isinstance(one, dict)
    }


def _body_of(payload: dict[str, Any]) -> str:
    """The readable text of a mail, preferring plain over HTML.

    Walked rather than assumed: a mail is a tree of parts, and the one a person
    reads is rarely the first.
    """
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


def _search(token: str, arguments: dict[str, Any]) -> str:
    limit = str(arguments.get("limit", "10"))
    listed = httpx.get(
        f"{GMAIL}/messages",
        params={"q": arguments.get("query", ""), "maxResults": limit},
        headers={"Authorization": f"Bearer {token}"},
        timeout=20.0,
    ).json()
    found = []
    for one in listed.get("messages", []) or []:
        full = httpx.get(
            f"{GMAIL}/messages/{one['id']}",
            params={"format": "metadata", "metadataHeaders": ["From", "Subject", "Date"]},
            headers={"Authorization": f"Bearer {token}"},
            timeout=20.0,
        ).json()
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
    return json.dumps({"messages": found}, indent=1)


def _get(token: str, arguments: dict[str, Any]) -> str:
    full = httpx.get(
        f"{GMAIL}/messages/{arguments.get('id', '')}",
        params={"format": "full"},
        headers={"Authorization": f"Bearer {token}"},
        timeout=20.0,
    ).json()
    payload = full.get("payload", {})
    head = _headers_of(payload)
    return json.dumps(
        {
            "id": full.get("id", ""),
            "from": head.get("from", ""),
            "subject": head.get("subject", ""),
            "body": _body_of(payload),
        },
        indent=1,
    )


def _send(token: str, arguments: dict[str, Any]) -> str:
    mail = EmailMessage()
    mail["To"] = str(arguments.get("to", ""))
    mail["Subject"] = str(arguments.get("subject", ""))
    mail.set_content(str(arguments.get("body", "")))
    raw = base64.urlsafe_b64encode(mail.as_bytes()).decode()
    answer = httpx.post(
        f"{GMAIL}/messages/send",
        json={"raw": raw},
        headers={"Authorization": f"Bearer {token}"},
        timeout=30.0,
    )
    if answer.status_code >= 400:
        raise RuntimeError(f"Gmail refused the send ({answer.status_code}): {answer.text[:200]}")
    print(f"  → sent to {arguments.get('to')}")
    return json.dumps({"status": "sent", "id": answer.json().get("id", "")})


class Connector(BaseHTTPRequestHandler):
    """The MCP half: greet, hand out a session, then answer calls.

    The same protocol the mock connector speaks, and for the same reason -- a
    client that skipped the greeting could talk to neither.
    """

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
            params = request.get("params", {})
            name, arguments = params.get("name", ""), params.get("arguments", {})
            try:
                token = _access_token()
                if name == "search_threads":
                    text = _search(token, arguments)
                elif name == "get_message":
                    text = _get(token, arguments)
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
                # `isError` rather than a transport failure: the escalation table
                # treats "it refused" and "there was nothing to ask" differently,
                # and both arriving as an exception would collapse them.
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
        authorize()
        raise SystemExit(0)

    port = int(next((one for one in sys.argv[1:] if one.isdigit()), "8932"))
    _client()  # fail now, with a sentence, rather than on the first call
    if not TOKEN_FILE.exists():
        raise SystemExit(f"no grant yet: run `{sys.argv[0]} --authorize` first")

    try:
        server = ThreadingHTTPServer(("127.0.0.1", port), Connector)
    except OSError as taken:
        print(f"port {port} is already in use ({taken.strerror}).")
        print(f"  what has it:  lsof -ti :{port}")
        print(f"  free it:      lsof -ti :{port} | xargs kill")
        raise SystemExit(1) from taken

    print(f"gmail connector on http://localhost:{port}/mcp")
    print("point the system at it with, in backend/.env:")
    print(f"  SRO_MCP_SERVERS=gmail=http://localhost:{port}/mcp")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped.")
