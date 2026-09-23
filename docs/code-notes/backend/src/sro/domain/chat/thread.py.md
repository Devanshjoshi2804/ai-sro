# Notes for `backend/src/sro/domain/chat/thread.py`

Comments and docstrings moved out of [`backend/src/sro/domain/chat/thread.py`](../../../../../../../backend/src/sro/domain/chat/thread.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/domain/chat/thread.py#L1): Docstring

> A conversation about work, kept because the work is auditable.
>
> A thread is not a transcript of a chatbot. It is the record of what was asked,
> what the system decided that meant, and what was done about it — which is the
> first thing anybody reads after an incident. So messages are append-only and
> carry the decision that produced them, not just prose.

## `Speaker`, [line 20](../../../../../../../backend/src/sro/domain/chat/thread.py#L20): Note on the line above

Code: `SYSTEM = "system"`

> Things that happened rather than things anybody said: a run finished, a
> skill was induced.

## `Said`, [line 23](../../../../../../../backend/src/sro/domain/chat/thread.py#L23): Docstring

> What a message's ``decision["kind"]`` may be.
>
> Two surfaces draw a thread -- the operator's side panel and the console --
> and they draw different shapes for a run in progress, the record of what it
> made, a task being offered, and a question waiting on somebody. The kind is
> what tells those apart. Without it each surface infers the shape from which
> fields happen to be present, and they infer differently.
>
> Named here rather than as strings at the call sites so there is one list to
> read, and so a surface meeting a kind it has never heard of knows it is
> looking at an older client rather than a typo. Both surfaces draw the words
> and no buttons in that case: a backend must be able to add a kind without
> every browser in the field going dark first.

## `Said`, [line 24](../../../../../../../backend/src/sro/domain/chat/thread.py#L24): Note on the line above

Code: `OFFER = "offer"`

> A task done often enough to be worth doing for somebody.

## `Said`, [line 26](../../../../../../../backend/src/sro/domain/chat/thread.py#L26): Note on the line above

Code: `MAIL_MATCH = "mail_match"`

> A watched mailbox recognised a task. Names only -- what was read out of
> the mail stays in the browser that read it.

## `Said`, [line 28](../../../../../../../backend/src/sro/domain/chat/thread.py#L28): Note on the line above

Code: `NOTE = "note"`

> Something said to a run while it is happening, rather than a request.

## `Said`, [line 30](../../../../../../../backend/src/sro/domain/chat/thread.py#L30): Note on the line above

Code: `RUN = "run"`

> A run, from the moment it starts. The message the steps land against.

## `Said`, [line 32](../../../../../../../backend/src/sro/domain/chat/thread.py#L32): Note on the line above

Code: `RESULT = "result"`

> What a finished run made.

## `Said`, [line 34](../../../../../../../backend/src/sro/domain/chat/thread.py#L34): Note on the line above

Code: `QUESTION = "question"`

> A run stopped and needs a person to decide.

## `Said`, [line 36](../../../../../../../backend/src/sro/domain/chat/thread.py#L36): Note on the line above

Code: `FAILURE = "failure"`

> A run that could not go on, and the one thing that would help.

## `Message`, [line 46](../../../../../../../backend/src/sro/domain/chat/thread.py#L46): Note on the line above

Code: `decision: dict[str, object] = field(default_factory=dict)`

> What the system worked out, alongside what it said.
>
> Kept structured as well as in prose because "why did it do that" is
> answered by the resolution, not by the sentence that reported it.

## `Thread.title`, [line 72](../../../../../../../backend/src/sro/domain/chat/thread.py#L72): Docstring

> What this conversation was about, and what came of it.
>
> The first sentence alone left six conversations in the sidebar all
> called "how many transport modes a…", indistinguishable from each
> other. What tells them apart is what was done in them, so the last task
> that actually ran is added when there was one.

## `Thread._what_was_done`, [line 77](../../../../../../../backend/src/sro/domain/chat/thread.py#L77): Docstring

> The last thing this conversation actually performed, if anything.

## `Thread.say`, [line 85](../../../../../../../backend/src/sro/domain/chat/thread.py#L85): Docstring

> Append. Nothing in a thread is ever edited or removed.
