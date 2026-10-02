# Notes for `backend/gmail-connector/server.py`

Comments and docstrings moved out of [`backend/gmail-connector/server.py`](../../../../backend/gmail-connector/server.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../backend/gmail-connector/server.py#L1): Docstring

> Gmail, as a connector a skill's step can call.
>
> The point is not convenience. A step done by clicking can never be trusted to
> run unattended -- `verdict.py` makes a run with a UI step DEGRADED, and DEGRADED
> resets the streak autonomy counts -- so a mail half taught by clicking in Gmail
> is capped at assisted forever, however many times it works. A step that is a
> call is clean-eligible, and can climb.
>
> Streamable-HTTP MCP, because that is what this system's connector speaks. Most
> Gmail MCP servers are stdio and cannot be reached by it at all.
>
>     # once per operator, in a browser that operator is signed into:
>     uv run python backend/gmail-connector/server.py --authorize <tenant> <operator>
>
>     # then, to serve:
>     uv run python backend/gmail-connector/server.py 8932
>
> Credentials come from the environment, never from arguments -- an argument is in
> the shell history and in `ps`:
>
>     GMAIL_CLIENT_ID=...     # the OAuth client, from Google Cloud
>     GMAIL_CLIENT_SECRET=... # put it in backend/.env; it is not printed here
>
> Each grant is written to `backend/.gmail-grants/`, gitignored, named by the
> sha256 of the bearer that reaches it -- so what is on disk cannot be read back
> into a credential. Nothing about the mailbox is stored: this reads and sends,
> and keeps no copy.
>
> **One grant per OPERATOR, and a call with no grant behind its bearer reaches
> nothing.** Each operator reads their own mail, so the grant belongs to a person
> and not to a company: a connector keyed by tenant would have one operator's
> inbox answering for everybody in it.
>
> It was one grant for everybody until 2026-09-16, and this checked no credential
> at all: it listens on localhost, so whatever ran on the box got whichever
> mailbox it had. The backend now sends that operator's own bearer, read from the
> vault under `secrets.connector_key`.

## module, [line 22](../../../../backend/gmail-connector/server.py#L22): Note on the line above

Code: `TOKEN_FILE = HERE.parent / ".gmail-token.json"`

> The single-tenant grant this connector used to keep. Read only to adopt it
> into the per-tenant store below; nothing serves from it.

## module, [line 24](../../../../backend/gmail-connector/server.py#L24): Note on the line above

Code: `HOST = os.environ.get("GMAIL_CONNECTOR_HOST", "127.0.0.1")`

> What to bind. Loopback by default, because on a laptop this is a local tool
> and a connector on 0.0.0.0 is a mailbox on the office network.
>
> A container is the other case and is why this is settable: inside one, loopback
> is reachable by nothing, so the compose service sets `0.0.0.0` and publishes no
> port. What can reach it is then exactly the compose network -- the API and the
> worker -- and a bearer is still required from every one of them.

## module, [line 26](../../../../backend/gmail-connector/server.py#L26): Note on the line above

Code: `GRANTS = HERE.parent / ".gmail-grants"`

> One grant per tenant, each named by the sha256 of the bearer that reaches it.
>
> A connector holding ONE Google grant and checking no credential is a connector
> that hands whoever reaches it whichever mailbox it has -- and it listens on
> localhost, so "whoever reaches it" is anything on the box. Every tenant's step
> went to the same inbox.
>
> Keyed by the hash of the bearer rather than by the tenant's name, so this
> directory is a lookup and not a mapping table: a request either carries a
> bearer we have a grant for or it does not, and the answer needs no second file
> to be kept in step. The bearer itself is never written down -- what is on disk
> cannot be replayed against this server.

## module, [line 39](../../../../backend/gmail-connector/server.py#L39): Note on the line above

Code: `REDIRECT = "http://localhost:8933/oauth/callback"`

> Where Google sends the operator back. Must be listed in the OAuth client's
> Authorized redirect URIs, exactly as written here.

## module, [line 41](../../../../backend/gmail-connector/server.py#L41): Note on the line above

Code: `SCOPES = [`

> Read and send, and nothing else. `gmail.modify` would also let this delete,
> which no step here does and no operator agreed to.

## `_grant_of`, [line 29](../../../../backend/gmail-connector/server.py#L29): Docstring

> The grant this bearer reaches, or None. The whole of the gate.

## `_client`, [line 125](../../../../backend/gmail-connector/server.py#L125): Docstring

> The OAuth client, from the file Google hands you.
>
> Read out of `client_secret*.json` as downloaded, rather than asking anybody
> to copy two values into a second place. A secret copied by hand is a secret
> typed into a shell, pasted into a chat, and left in a scrollback -- and the
> file is already the thing Google treats as canonical.
>
> The environment still wins where it is set, because a deployment that keeps
> its secrets somewhere else should not have to invent this file.

## `_access_token`, [line 159](../../../../backend/gmail-connector/server.py#L159): Docstring

> A live access token, refreshed from THIS tenant's grant.
>
> Refreshed on every call rather than cached with an expiry: this serves one
> request at a time, minutes apart, and a token that expired between two of
> them is a failure nobody could explain from the logs.
>
> The grant is passed in rather than read from a module global, because which
> grant to use is a fact about the request: it is whichever one the caller's
> bearer reached.

## `_keep`, [line 180](../../../../backend/gmail-connector/server.py#L180): Docstring

> Write one operator's grant, and print the bearer that reaches it once.
>
> The bearer is minted here rather than chosen, and printed rather than
> stored: what goes on disk is its sha256, so this directory cannot be read
> back into a credential that reaches this server. Whoever runs this puts the
> printed value in the vault under `tenant/gmail/mcp-token` and it is never
> seen again.

## `_vault_key`, [line 197](../../../../backend/gmail-connector/server.py#L197): Docstring

> The same key the backend asks the vault for.
>
> Spelled here rather than imported: this script runs on its own, outside the
> package, and a second spelling is how a grant gets stored where nothing
> looks for it. Held to the original by
> `test_the_connector_and_the_backend_agree_on_where_a_grant_lives`.

## `authorize`, [line 202](../../../../backend/gmail-connector/server.py#L202): Docstring

> The one step nobody can take on the operator's behalf.
>
> Their Google account, their consent screen, their decision about what this
> may read and send. All this does is open the page and catch the code Google
> sends back.
>
> Per OPERATOR, because a grant belongs to one person: each reads their own
> mail. A connector holding a single grant and checking no credential hands
> whichever mailbox it has to whoever reaches it -- and it listens on
> localhost, so that is anything on the box.
>
> Adopts the old single-tenant `.gmail-token.json` where one is still there,
> so a deployment that authorized before this existed does not have to send
> somebody back to Google. The old file is left alone rather than deleted: it
> is a credential, and deleting somebody's credential is not this script's
> decision to make.

## `_body_of`, [line 292](../../../../backend/gmail-connector/server.py#L292): Docstring

> The readable text of a mail, preferring plain over HTML.
>
> Walked rather than assumed: a mail is a tree of parts, and the one a person
> reads is rarely the first.

## `_answered`, [line 305](../../../../backend/gmail-connector/server.py#L305): Docstring

> The body, or a refusal said out loud.
>
> Gmail answers a disabled API, a missing scope and a revoked grant with a
> 4xx and a JSON body that simply has no results in it. Read with `.json()`
> and no check, every one of those becomes an empty inbox -- a failure
> wearing the face of a success, which is worse than an error because nobody
> goes looking for the cause of nothing.

## `_thread`, [line 415](../../../../backend/gmail-connector/server.py#L415): Docstring

> Every mail in one conversation, oldest first.
>
> The conversation and not a search: a reply names no values and the mail it
> replies to holds them, and which mail that is, is a fact Gmail already
> knows. Searching for it is guessing at something nobody has to guess at.

## `Connector`, [line 493](../../../../backend/gmail-connector/server.py#L493): Docstring

> The MCP half: greet, hand out a session, then answer calls.
>
> The same protocol the mock connector speaks, and for the same reason -- a
> client that skipped the greeting could talk to neither.

## `_keep`, [line 193](../../../../backend/gmail-connector/server.py#L193): Comment

Code: `print(f"  key: {_vault_key(tenant, operator)}")`

> Printed because the key hashes the operator in and nobody can derive it
> by eye -- see `secrets.connector_key` for why it has to.

## `authorize`, [line 234](../../../../backend/gmail-connector/server.py#L234): Comment

Code: `"access_type": "offline",`

> Offline and forced, so a refresh token comes back. Google sends
> one only on the first consent unless asked again.

## `_get`, [line 395](../../../../backend/gmail-connector/server.py#L395): Comment

Code: `"thread_id": full.get("threadId", ""),`

> Which conversation this belongs to.
>
> A request rarely carries what it is about -- "please create the
> customer type as discussed" -- and what it is about is in the
> mail before it, in the same thread. Without this the only way to
> reach that mail is to search the whole mailbox and hope, which on
> a mailbox holding seventeen near-identical threads finds the
> wrong one or none. Measured on the deployment, 2026-09-17 at
> 21:26: "gathered 0 of 2 ... the mailbox holds none of the values
> this job needs", about values sitting one mail away.

## `_get`, [line 396](../../../../backend/gmail-connector/server.py#L396): Comment

Code: `"rfc822_message_id": head.get("message-id", ""),`

> The mail's own id, for the same reason `_thread` carries one: a
> reply names it in `In-Reply-To`, and Gmail's internal id is not
> one any other client can thread on.

## `_thread`, [line 432](../../../../backend/gmail-connector/server.py#L432): Comment

Code: `"rfc822_message_id": head.get("message-id", ""),`

> The mail's OWN id, which is not Gmail's id for it.
>
> `In-Reply-To` must carry an RFC822 `Message-Id` -- the
> `<...@host>` the sending client minted -- and this was
> sending Gmail's internal `1a0b...` instead, because it was
> the only id here. Gmail itself threads on `threadId` and
> never noticed; every other client saw a header naming a
> message it has never heard of and drew an orphan.
>
> Measured on the deployment 2026-09-18: the mail this system
> sent arrived in the recipient's mailbox as a NEW
> conversation, not under the request it was answering.

## `_send`, [line 457](../../../../backend/gmail-connector/server.py#L457): Comment

Code: `within = str(arguments.get("thread_id", "")).strip()`

> Threaded two ways, because two different things do the threading.
>
> `threadId` is what GMAIL uses, and it is what makes the reply findable:
> this system matches an arriving mail to the run waiting on it by thread
> id, so a reply that starts its own conversation answers nobody. The
> `In-Reply-To` header is what every OTHER mail client uses, and without it
> the person who receives this sees an orphan.

## `Connector.do_POST`, [line 531](../../../../backend/gmail-connector/server.py#L531): Comment

Code: `bearer = self.headers.get("Authorization", "").removeprefix("Bearer ").strip()`

> The gate, and it is here rather than at `initialize` on purpose:
> a handshake tells a caller nothing about a mailbox, and a call
> is the first thing that would. An unknown bearer reaches no
> grant, so it reaches no mail.

## `Connector.do_POST`, [line 569](../../../../backend/gmail-connector/server.py#L569): Comment

Code: `print(f"  ! {refused}")`

> `isError` rather than a transport failure: the escalation table
> treats "it refused" and "there was nothing to ask" differently,
> and both arriving as an exception would collapse them.

## module, [line 619](../../../../backend/gmail-connector/server.py#L619): Inline

Code: `_client()`

> fail now, with a sentence, rather than on the first call

## `_mailbox`, [line 364](../../../../backend/gmail-connector/server.py#L364): Note

> The grant's own address, from Gmail's `users.getProfile`, so the backend can
> tell the operator's own mail from everybody else's. Read once per grant and
> kept in `MAILBOXES` for the life of the process: an address does not change
> under a grant, and each message would otherwise cost a second request. A
> failed read is not kept, so the next message tries again.

## `_thread`, [line 434](../../../../backend/gmail-connector/server.py#L434): Comment

Code: `"to": head.get("to", ""),`

> Who each mail went to, `to` and `cc` both. A draft may go only to the
> conversation's participants, and a participant is a recipient as much as a
> sender -- with `from` alone, everyone but the senders was invisible.

## `_get`, [line 401](../../../../backend/gmail-connector/server.py#L401): Comment

Code: `"sent": "SENT" in (full.get("labelIds") or []),`

> Whether this is the operator's own sent copy, by Gmail's SENT label rather
> than the `From` header any sender can write: an operator's own reply is the
> only mail that may name a recipient. `in_reply_to` and `references` say it is
> a reply, whose quote must then be found by its structure or it names nobody.

## `_thread`, [line 437](../../../../backend/gmail-connector/server.py#L437): Comment

Code: `"sent": "SENT" in (one.get("labelIds") or []),`

> Which messages the operator's own mailbox sent: only their To and Cc make
> somebody a participant a draft may go to. A Cc an incoming sender set names
> nobody. With them, `bcc` (Gmail keeps it on the sender's copy only) and
> `sent_at`, Gmail's own `internalDate` in seconds: a mail job finds the mail its
> demonstration sent as the one SENT message of the click's thread dated near
> the click, and reads who it went to from these.

## `_send`, [line 489](../../../../backend/gmail-connector/server.py#L489): Comment

Code: `print(f"  → sent to {len(getaddresses([str(arguments.get('to', ''))]))} recipient(s)")`

> A count, never the addresses: the console is a log like any other.
