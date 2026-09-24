# Notes for `backend/src/sro/infrastructure/mcp/server.py`

Comments and docstrings moved out of [`backend/src/sro/infrastructure/mcp/server.py`](../../../../../../../backend/src/sro/infrastructure/mcp/server.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/infrastructure/mcp/server.py#L1): Docstring

> Runnable skills, exposed as MCP tools.
>
> One tool per skill this tenant has taught past ``recorded``. The credential is
> per HTTP request rather than per connection -- the SDK's OAuth apparatus wants
> an authorization server this deployment is not, and every other door here
> already accepts the same pasted bearer token, so this one middleware checks it
> the same way `interface/http/deps.py` does and stashes the caller in a
> contextvar for the two handlers below to read.
>
> A tool call runs the skill durably (`DurableExecution.execute_skill`, the same
> path a schedule fires) and waits for it, because an agent calling a tool wants
> an answer, not a run id to go poll.

## `_tool_for`, [line 65](../../../../../../../backend/src/sro/infrastructure/mcp/server.py#L65): Comment

Code: `return None`

> Not reviewed by anybody yet. Offering it as a tool would let a run
> start on a recipe nobody has looked at.

## `SkillToolServer.__init__`, [line 113](../../../../../../../backend/src/sro/infrastructure/mcp/server.py#L113): Comment

Code: `self._list_skills = list_skills`

> Factories, not instances: this server is built once for the whole
> process, but a `UnitOfWork` is not -- built once and shared, two
> concurrent requests would fight over the same session the way a
> fresh-per-request router call never does.
