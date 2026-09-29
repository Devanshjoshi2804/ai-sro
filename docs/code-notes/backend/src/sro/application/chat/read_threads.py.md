# Notes for `backend/src/sro/application/chat/read_threads.py`

Comments and docstrings moved out of [`backend/src/sro/application/chat/read_threads.py`](../../../../../../../backend/src/sro/application/chat/read_threads.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/chat/read_threads.py#L1): Docstring

> Reading threads. A router never touches a repository.

## `ReadThreads.current`, [line 21](../../../../../../../backend/src/sro/application/chat/read_threads.py#L21): Docstring

> This operator's most recently opened thread, or `None` if they have
> none yet.
>
> One continuous thread rather than one per host: a job that spans a
> mailbox and the warehouse system is one piece of work, and splitting the
> conversation by tab is the same mistake as splitting the work by tab.
>
> Asked of the repository as one scoped query rather than filtered out of
> a page of the tenant's newest. The console starts a thread on every
> first ask, so somebody else's threads are exactly what a window would
> fill with -- and an operator whose own thread fell out of it would be
> handed a fresh conversation, orphaning every offer already said in the
> old one, which `offered_at` will never let be said again.
>
> Returns `None` rather than starting one itself: making a thread is
> `StartThread`'s job, not a second way for one to come into being. A
> reader that quietly writes on a cache-miss is no longer a reader --
> the caller (the router) already knows how to start a thread, so the
> fallback belongs there.

## `ReadThreads.current`, [line 24](../../../../../../../backend/src/sro/application/chat/read_threads.py#L24): Comment

Code: `ctx.tenant_id, opened_by=ctx.principal_id, asking=False, limit=1`

> Never a chat a question was asked in, though it is opened later: the
> conversation somebody is in is theirs. Were the newest question's chat
> "current", everything else said to the operator would pile into the chat of
> whichever mail asked last.

## `ReadThreads.asked`, [line 28](../../../../../../../backend/src/sro/application/chat/read_threads.py#L28): Comment

Code: `async def asked(self, ctx: RequestContext, *, limit: int = 10) -> tuple[Thread, ...]:`

> This operator's chats that each hold one question, newest first -- what
> the panel reads to put a waiting question on Home.

## `ReadThreads.asking`, [line 34](../../../../../../../backend/src/sro/application/chat/read_threads.py#L34): Comment

Code: `async def asking(self, ctx: RequestContext, about: str) -> Thread | None:`

> The chat a question about `about` (a mail conversation, or a run with
> none) was asked in, if one was. A reader: opening it is `SayWhatHappened`'s.
