# Notes for `backend/src/sro/domain/chat/standing.py`

Comments and docstrings moved out of [`backend/src/sro/domain/chat/standing.py`](../../../../../../../backend/src/sro/domain/chat/standing.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/domain/chat/standing.py#L1): Docstring

> What stands in a conversation, and what is said about it when asked (F2).
>
> Measured on the deployment: "check now", "have you recived mail", "what did
> you fetch from mail" and "i will type it here", each typed while a run or a
> question was standing, were each answered "Nobody has demonstrated that…"
> and offered as work to explore on the screen. None of them asked for work.
> They asked where the thing already going had got to.
>
> Pure: given the messages, a run and a time, say what stands and put it in
> words. Nothing here reads a repository or a model.

## `last_run`, [line 22](../../../../../../../backend/src/sro/domain/chat/standing.py#L22): Docstring

> The run this conversation last named. Every message about a run carries its
> id (`Said.RUN` from `SayTheRunStarted`, `run_asks` from `RunSteps`, a note
> the operator addressed to it), so the last one is the run the thread is
> about. Whether that run still stands is the row's to say, not the thread's.

## `stands`, [line 30](../../../../../../../backend/src/sro/domain/chat/standing.py#L30): Docstring

> A run stands while it is going, while it is asking somebody
> (`asks_a_person`), or while it is waiting on a reply inside its deadline
> (`still_waiting`). Those are the three states a person could reasonably be
> asking about; a run that has finished has nothing left to report but its
> result, which the thread already carries.

## `of_the_run`, [line 38](../../../../../../../backend/src/sro/domain/chat/standing.py#L38): Docstring

> The answer, from the run's own state: where it is (its `doing` line when it
> is gathering, else its step), its outcome when it is no longer going, what
> it is waiting on (its question, the mail reply, the values it still needs),
> and the values it holds -- marked where they were read from the mail,
> because "what did you fetch from mail" is one of the four sentences.
>
> A secret-named value is never said (`is_secret_field`, the same name rule
> capture uses): a run's values can hold a password, and a panel line is a
> place a secret must never travel (global invariant 11). Values are
> shortened the way every other line in a question is.
