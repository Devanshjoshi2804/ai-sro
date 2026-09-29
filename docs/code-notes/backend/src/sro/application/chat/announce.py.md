# Notes for `backend/src/sro/application/chat/announce.py`

Comments and docstrings moved out of [`backend/src/sro/application/chat/announce.py`](../../../../../../../backend/src/sro/application/chat/announce.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/chat/announce.py#L1): Docstring

> Saying, in the operator's own conversation, that something happened.
>
> An offer is a `SYSTEM` message: "you have done this 3 times, want me to do the
> next one?". Until now nothing said what came of it, so the console showed every
> offer permanently unanswered, and a reopened panel drew both buttons again as
> though the question were still open.
>
> So the answer is a message too. Not a mutation of the offer -- a `Message` is a
> record of something that was said, and editing one to report its own answer
> would make the thread a state machine rather than an account of what happened.

## `SayWhatHappened`, [line 15](../../../../../../../backend/src/sro/application/chat/announce.py#L15): Docstring

> Append a `SYSTEM` message to the conversation one operator is in.
>
> Deliberately not shared with `ProposeAboutCandidates._offer`, which writes
> its message and the candidate's `offered_at` in one transaction: written
> and not recorded means the sweep says it again, recorded and not written
> means it is never said at all. That coupling belongs to offering, and
> folding it into a general helper would hide it.

## `SayWhatHappened.execute`, [line 21](../../../../../../../backend/src/sro/application/chat/announce.py#L21): Docstring

> Say it in `for_operator`'s thread, not the caller's.
>
> The two differ whenever something happens on an operator's behalf, and
> a message in the wrong conversation is worse than none: the operator
> never sees it, and somebody else sees work they did not do.
>
> **A question is the assistant speaking; an announcement is not.**
> `SYSTEM` is this door's default and the right one for what it was built
> to say -- a run finished, a skill was induced, things that HAPPENED
> rather than things anybody said. A question is the other kind, and the
> difference is load-bearing rather than cosmetic: `pending_job` reads
> back "the last thing the ASSISTANT decided", so a question filed as
> SYSTEM is one nothing can find.
>
> Measured on the deployment 2026-09-18. Three questions stood in the
> thread reading `Customer Type takes 4 characters. What should it be?`,
> the operator typed a sentence, and it went past all three to the skill
> resolver, which answered `Nobody has demonstrated that`. Every question
> this door has ever asked was invisible to the reader that exists to
> answer it, including the run path's since `5a2d10b1`.

## `SayWhatHappened.answered_elsewhere`, [line 37](../../../../../../../backend/src/sro/application/chat/announce.py#L37): Docstring

> A run's wait ended with its question open, and a reply reached only a
> colleague's mailbox (the mail door left `elsewhere_key`): the starter is told
> in their own thread. Two callers can reach it at once, `RunSteps.finish` and
> a colleague's look that marked the question as the run finished. Forgetting
> the mark is the compare-and-set: the one that removes the row tells, the
> other finds nothing. Only a colleague's mark (`K_ELSEWHERE`) is forgotten:
> the starter's own take leaves `K_TAKEN`, which says nothing.
>
> The starter's thread is found or made first, in its own commit
> (`_thread_for`). Then the forget, the read of the thread, the note and its
> save commit in one unit of work, so a note that fails to be said leaves the
> mark for the retried `finish`. Making the thread inside that unit committed
> the shared session's DELETE early: a starter with no thread yet lost the
> mark to a failure after `StartThread`, and the retry said nothing
> (invariants 6 and 12; S1 rounds 2 and 3).

## `SayWhatHappened._thread_for`, [line 66](../../../../../../../backend/src/sro/application/chat/announce.py#L66): Comment

Code: `if about.strip():`

> Said in the chat of the question about `about` when one is named --
> opened if it is not there yet, idempotently, because its id is derived.

## `SayWhatHappened._thread_for`, [line 77](../../../../../../../backend/src/sro/application/chat/announce.py#L77): Comment

Code: `if run_id:`

> Else in the chat that names the decision's run, so a run the answer in a
> question's chat started reports its progress and result there. Else the
> operator's own conversation, as before.
