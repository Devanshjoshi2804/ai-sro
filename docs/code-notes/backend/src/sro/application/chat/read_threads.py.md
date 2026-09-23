# Notes for `backend/src/sro/application/chat/read_threads.py`

Comments and docstrings moved out of [`backend/src/sro/application/chat/read_threads.py`](../../../../../../../backend/src/sro/application/chat/read_threads.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/chat/read_threads.py#L1): Docstring

> Reading threads. A router never touches a repository.

## `ReadThreads.current`, [line 20](../../../../../../../backend/src/sro/application/chat/read_threads.py#L20): Docstring

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
