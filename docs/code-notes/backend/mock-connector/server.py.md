# Notes for `backend/mock-connector/server.py`

Comments and docstrings moved out of [`backend/mock-connector/server.py`](../../../../backend/mock-connector/server.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../backend/mock-connector/server.py#L1): Docstring

> A mail connector that speaks MCP, for proving the tool-step path locally.
>
> Not Gmail. A stand-in that answers the way a real streamable-HTTP MCP server
> answers -- `initialize` first, a session id on everything after -- so the whole
> chain can be driven without Google credentials, a hosted provider, or a tunnel:
> list the tools, put one in a skill as a step, run it, and watch the run come out
> `Medium.TOOL` rather than a click.
>
> Run it:
>
>     uv run python backend/mock-connector/server.py 8931
>
> Point the system at it:
>
>     SRO_MCP_SERVERS="mail=http://localhost:8931/mcp"
>
> What it is NOT: a test of Google's API, of OAuth, or of anything a real
> connector does differently. It is a test of this system's half -- which is the
> half that was broken, and the half a real connector cannot help us prove.
>
> The mailbox is seeded with the mail this was built against, so the demo is the
> task somebody actually does rather than a lorem ipsum.

## `Connector.do_POST`, [line 121](../../../../backend/mock-connector/server.py#L121): Comment

Code: `if self.headers.get("Mcp-Session-Id") != SESSION:`

> Everything after the greeting must carry the session, exactly as a
> real streamable-HTTP server insists. This is the rule that caught the
> client going straight to `tools/list`.

## module, [line 175](../../../../backend/mock-connector/server.py#L175): Comment

Code: `print(f"port {port} is already in use ({taken.strerror}).")`

> A stack trace for "something else is on that port" tells you what
> Python noticed rather than what to do about it.
