"""Gmail, as a connector a skill's step can call.

The point is not convenience. A step done by clicking can never be trusted to
run unattended -- `verdict.py` makes a run with a UI step DEGRADED, and DEGRADED
resets the streak autonomy counts -- so a mail half taught by clicking in Gmail
is capped at assisted forever, however many times it works. A step that is a
call is clean-eligible, and can climb.

Streamable-HTTP MCP, because that is what this system's connector speaks. Most
Gmail MCP servers are stdio and cannot be reached by it at all.

    # once per tenant, in a browser that tenant's operator is signed into:
    uv run python backend/gmail-connector/server.py --authorize <tenant>

    # then, to serve:
    uv run python backend/gmail-connector/server.py 8932

Credentials come from the environment, never from arguments -- an argument is in
the shell history and in `ps`:

    GMAIL_CLIENT_ID=...     # the OAuth client, from Google Cloud
    GMAIL_CLIENT_SECRET=... # put it in backend/.env; it is not printed here

Each grant is written to `backend/.gmail-grants/`, gitignored, named by the
sha256 of the bearer that reaches it -- so what is on disk cannot be read back
into a credential. Nothing about the mailbox is stored: this reads and sends,
and keeps no copy.

**One grant per tenant, and a call with no grant behind its bearer reaches
nothing.** It was one grant for everybody until 2026-09-16, and this checked no
credential at all: it listens on localhost, so whatever ran on the box got
whichever mailbox it had. The backend now sends each tenant's own bearer, read
from the vault under `tenant/gmail/mcp-token`.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import secrets
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
"""The single-tenant grant this connector used to keep. Read only to adopt it
into the per-tenant store below; nothing serves from it."""

GRANTS = HERE.parent / ".gmail-grants"
"""One grant per tenant, each named by the sha256 of the bearer that reaches it.

A connector holding ONE Google grant and checking no credential is a connector
that hands whoever reaches it whichever mailbox it has -- and it listens on
localhost, so "whoever reaches it" is anything on the box. Every tenant's step
went to the same inbox.

Keyed by the hash of the bearer rather than by the tenant's name, so this
directory is a lookup and not a mapping table: a request either carries a
bearer we have a grant for or it does not, and the answer needs no second file
to be kept in step. The bearer itself is never written down -- what is on disk
cannot be replayed against this server.
"""


def _grant_of(bearer: str) -> dict[str, str] | None:
    """The grant this bearer reaches, or None. The whole of the gate."""
    if not bearer:
        return None
    named = GRANTS / f"{hashlib.sha256(bearer.encode()).hexdigest()}.json"
    if not named.is_file():
        return None
    kept = json.loads(named.read_text())
    return kept if isinstance(kept, dict) else None

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


def _access_token(grant: dict[str, str]) -> str:
    """A live access token, refreshed from THIS tenant's grant.

    Refreshed on every call rather than cached with an expiry: this serves one
    request at a time, minutes apart, and a token that expired between two of
    them is a failure nobody could explain from the logs.

    The grant is passed in rather than read from a module global, because which
    grant to use is a fact about the request: it is whichever one the caller's
    bearer reached.
    """
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


def _keep(tenant: str, refresh_token: str) -> None:
    """Write one tenant's grant, and print the bearer that reaches it once.

    The bearer is minted here rather than chosen, and printed rather than
    stored: what goes on disk is its sha256, so this directory cannot be read
    back into a credential that reaches this server. Whoever runs this puts the
    printed value in the vault under `tenant/gmail/mcp-token` and it is never
    seen again.
    """
    bearer = secrets.token_urlsafe(32)
    GRANTS.mkdir(mode=0o700, exist_ok=True)
    named = GRANTS / f"{hashlib.sha256(bearer.encode()).hexdigest()}.json"
    named.write_text(json.dumps({"tenant": tenant, "refresh_token": refresh_token}, indent=1))
    named.chmod(0o600)
    print(f"\ngrant stored for {tenant}. It is gitignored and holds no mail.")
    print("Put this in the vault as this tenant's connector credential:")
    print(f"\n  {bearer}\n")
    print(f"  key: {tenant}/gmail/mcp-token")
    print("It is shown once. Losing it costs a re-authorize, not the mailbox.")


def authorize(tenant: str) -> None:
    """The one step nobody can take on the operator's behalf.

    Their Google account, their consent screen, their decision about what this
    may read and send. All this does is open the page and catch the code Google
    sends back.

    Per TENANT, because a grant belongs to one. A connector holding a single
    grant and checking no credential hands whichever mailbox it has to whoever
    reaches it -- and it listens on localhost, so that is anything on the box.

    Adopts the old single-tenant `.gmail-token.json` where one is still there,
    so a deployment that authorized before this existed does not have to send
    somebody back to Google. The old file is left alone rather than deleted: it
    is a credential, and deleting somebody's credential is not this script's
    decision to make.
    """
    if TOKEN_FILE.exists():
        kept = json.loads(TOKEN_FILE.read_text())
        if kept.get("refresh_token"):
            print(f"adopting the grant already in {TOKEN_FILE.name} for {tenant}.")
            print(f"  nothing was sent to Google. You may delete {TOKEN_FILE.name} when done.")
            _keep(tenant, str(kept["refresh_token"]))
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
    _keep(tenant, str(granted["refresh_token"]))


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


def _answered(response: httpx.Response, what: str) -> dict[str, Any]:
    """The body, or a refusal said out loud.

    Gmail answers a disabled API, a missing scope and a revoked grant with a
    4xx and a JSON body that simply has no results in it. Read with `.json()`
    and no check, every one of those becomes an empty inbox -- a failure
    wearing the face of a success, which is worse than an error because nobody
    goes looking for the cause of nothing.
    """
    if response.status_code >= 400:
        detail = ""
        try:
            detail = str(response.json().get("error", {}).get("message", ""))
        except ValueError:
            detail = response.text[:200]
        raise RuntimeError(f"Gmail refused {what} ({response.status_code}): {detail}")
    return dict(response.json())


def _search(token: str, arguments: dict[str, Any]) -> str:
    limit = str(arguments.get("limit", "10"))
    listed = _answered(
        httpx.get(
            f"{GMAIL}/messages",
            params={"q": arguments.get("query", ""), "maxResults": limit},
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
    return json.dumps({"messages": found}, indent=1)


def _get(token: str, arguments: dict[str, Any]) -> str:
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
            # The gate, and it is here rather than at `initialize` on purpose:
            # a handshake tells a caller nothing about a mailbox, and a call
            # is the first thing that would. An unknown bearer reaches no
            # grant, so it reaches no mail.
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
        named = [one for one in sys.argv[1:] if not one.startswith("-") and not one.isdigit()]
        if not named:
            raise SystemExit(
                "which tenant is this grant for?\n"
                f"  {sys.argv[0]} --authorize <tenant>\n"
                "A grant belongs to one tenant: a connector holding one grant for "
                "everybody hands whichever mailbox it has to whoever reaches it."
            )
        authorize(named[0])
        raise SystemExit(0)

    port = int(next((one for one in sys.argv[1:] if one.isdigit()), "8932"))
    _client()  # fail now, with a sentence, rather than on the first call
    if not GRANTS.is_dir() or not any(GRANTS.glob("*.json")):
        raise SystemExit(f"no grant yet: run `{sys.argv[0]} --authorize <tenant>` first")

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
