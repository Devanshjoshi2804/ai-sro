# Notes for `backend/src/sro/infrastructure/mcp/client.py`

Comments and docstrings moved out of [`backend/src/sro/infrastructure/mcp/client.py`](../../../../../../../backend/src/sro/infrastructure/mcp/client.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/infrastructure/mcp/client.py#L1): Docstring

> Calling somebody else's MCP tools from a skill's own step.
>
> The other half of `server.py`. That one hands this system's skills to another
> agent; this one lets a step be performed by calling a connector the tenant
> configured -- which is what makes a mail step a call rather than a click, and a
> click is the one thing that can never be clean.
>
> Configured rather than discovered. A server is named in settings with its URL;
> nothing here goes looking for connectors, because a system that found one and
> used it would be making the tenant's integration decisions for them.
>
> **The URL is deployment config and the credential never is.** Settings used to
> carry `name=url#token`, one bearer for the whole deployment, and every tenant's
> step went out holding it -- so a skill run for any tenant reached the same
> connector and the same person's Google grant. The token now comes from the
> vault under `tenant/server/mcp_token`, per tenant, and a tenant with no grant
> gets `NotConnected` rather than somebody else's mailbox. The `#token` form is
> gone rather than deprecated: left in, it is a working shared-credential path
> that nothing would stop a deployment using.

## module, [line 21](../../../../../../../backend/src/sro/infrastructure/mcp/client.py#L21): Note on the line above

Code: `CALL_TIMEOUT = 30.0`

> Long enough for a mail to be sent, short enough that a hung connector is a
> failed step rather than a run nobody can finish.

## module, [line 23](../../../../../../../backend/src/sro/infrastructure/mcp/client.py#L23): Note on the line above

Code: `PROTOCOL = "2025-06-18"`

> The version this client says it speaks when it opens a session.
>
> Named rather than inlined because it is the one thing in the handshake a server
> may refuse over, and a refusal that names a version is one somebody can act on.

## `McpServer`, [line 30](../../../../../../../backend/src/sro/infrastructure/mcp/client.py#L30): Docstring

> Where a connector is. Deliberately no credential on it -- see the module
> docstring: a bearer here is a bearer every tenant shares.

## `McpToolCaller`, [line 35](../../../../../../../backend/src/sro/infrastructure/mcp/client.py#L35): Docstring

> Streamable-HTTP MCP, spoken directly.
>
> The SDK's client wants to own a connection and a session for the life of a
> conversation; a step is one call and then nothing, sometimes hours before
> the next. Two JSON-RPC requests over `httpx` is the whole of what that
> needs, and it fails in ways this code can report rather than in the SDK's.

## `_argument_names`, [line 176](../../../../../../../backend/src/sro/infrastructure/mcp/client.py#L176): Docstring

> What this tool takes, for a person choosing what to map onto it.
>
> Read from the schema rather than required to be there: a server that
> declares no properties still offers the tool, and a mapping screen that
> hid it would be hiding a working connector over a missing description.

## `_payload`, [line 183](../../../../../../../backend/src/sro/infrastructure/mcp/client.py#L183): Docstring

> The JSON-RPC envelope, whether it arrived as JSON or as one SSE event.
>
> Streamable HTTP may answer either, and which one is the server's choice
> rather than ours.

## `_text_of`, [line 203](../../../../../../../backend/src/sro/infrastructure/mcp/client.py#L203): Docstring

> What the tool said, as the text an assertion is checked against.
>
> MCP answers with a list of content blocks. The text ones are joined and the
> rest are left out: an assertion reads a document, and an image in the
> middle of one is not part of the document.

## `McpToolCaller._bearer`, [line 46](../../../../../../../backend/src/sro/infrastructure/mcp/client.py#L46): Docstring

> This OPERATOR's grant for this connector, or a refusal naming both.
>
> The whole security property of this adapter. `secret_key_of` is the
> vault's own `tenant/system/field` shape rather than a second spelling,
> so a connector's grant sits beside the passwords a step types and is
> revoked the same way.
>
> A deployment with no vault configured cannot hold a per-tenant grant,
> so it gets the refusal too. That is stricter than before -- it used to
> call with no credential at all -- and it is the point: a connector
> reached without a tenant's grant is a connector reached on somebody
> else's behalf.

## `McpToolCaller._greet`, [line 142](../../../../../../../backend/src/sro/infrastructure/mcp/client.py#L142): Docstring

> Open a session, and the header that carries it.
>
> A streamable-HTTP MCP server built on the standard SDK answers anything
> before `initialize` with "Bad Request: Missing session ID", so a client
> that went straight to `tools/list` could talk to a permissive stub and
> to nothing else. This one greets first, then sends the session id back
> on the call itself.
>
> `{}` where the server needs no session: a server that does not answer
> with `Mcp-Session-Id` is one that never asked for it, and a call
> carrying an invented header would be worse than one carrying none.
>
> A failed greeting is not raised here. The call that follows fails on
> its own and says why in its own words -- reporting the handshake
> instead would name the wrong request.

## `McpToolCaller._bearer`, [line 51](../../../../../../../backend/src/sro/infrastructure/mcp/client.py#L51): Comment

Code: `key = connector_key(tenant_id.value, server, principal_id.value)`

> `connector_key` on both sides, never a hand-spelled key. It hashes
> the principal in, because `_as_key` collapses punctuation and
> `devansh.j` and `devansh_j` would otherwise be one key -- which is
> one operator reading another's mail.

## `McpToolCaller._bearer`, [line 55](../../../../../../../backend/src/sro/infrastructure/mcp/client.py#L55): Comment

Code: `raise ToolsUnavailable(f"the vault holding {server}'s grant is unreachable") from down`

> A different fact from "not connected", and the caller tells them
> apart: one is a console saying "connect Gmail", the other is a
> deployment problem no operator can act on.

## `McpToolCaller.call`, [line 92](../../../../../../../backend/src/sro/infrastructure/mcp/client.py#L92): Comment

Code: `return ToolResult(`

> `isError` is the tool saying no, which is an answer. Reported as a
> failed result rather than raised, because the escalation table treats
> "it refused" and "there was nothing to ask" differently and both
> arriving as an exception would collapse them.

## `McpToolCaller._greet`, [line 167](../../../../../../../backend/src/sro/infrastructure/mcp/client.py#L167): Comment

Code: `with contextlib.suppress(httpx.HTTPError):`

> The spec's third step. A server may hold `tools/list` until it
> arrives, and one that does not is unbothered by receiving it.

## `McpToolCaller._rpc`, [line 108](../../../../../../../backend/src/sro/infrastructure/mcp/client.py#L108): Comment

Code: `raise NotConnected(f"no connector called {server} is configured on this deployment")`

> A connector nothing here configures, and one that answers JSON-RPC error -32001 (the
> Outlook connector's no-grant, sent before any Graph call), both sent nothing. They are
> `NotConnected`, so a send says "nothing was sent; reconnect" instead of "may have gone; check
> Sent", and a mail look reads the mailbox as not connected. Any other error stays
> `ToolsUnavailable`: for those the connector may have carried on.
