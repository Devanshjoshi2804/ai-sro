# Notes for `backend/src/sro/application/connection/session_life.py`

Comments and docstrings moved out of [`backend/src/sro/application/connection/session_life.py`](../../../../../../../backend/src/sro/application/connection/session_life.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/connection/session_life.py#L1): Docstring

> How long this system's sessions actually last, learned rather than guessed.
>
> The obvious plan is to sign in every two hours, or every four. Both are
> guesses, and a guess here is expensive in both directions: too often and the
> system signs the operator's own browser out of a WMS that permits one session;
> too rarely and the first thing anybody notices is a batch failing at 3am.
>
> Nothing in the credential says. The session is three opaque cookies with no
> expiry to read -- so the number has to be measured, the way anything else here
> is measured: watch when a session was minted, when it last worked, and when it
> first did not, and keep the answer beside everything else known about that
> system. A second customer's WMS gets its own number instead of inheriting ours.
>
> Until a session has been seen to die, there is no measurement and the refresh
> falls back to a deliberately short interval. Being early costs one login.

## module, [line 11](../../../../../../../backend/src/sro/application/connection/session_life.py#L11): Note on the line above

Code: `UNKNOWN_LIFE = timedelta(minutes=30)`

> What to assume before anything has been observed. Short on purpose: a
> needless login costs a browser slot, a missed one costs the run.

## module, [line 13](../../../../../../../backend/src/sro/application/connection/session_life.py#L13): Note on the line above

Code: `SAFETY = 0.5`

> Refresh at half the observed life. A session that lived four hours once may
> live three the next time -- the identity provider counts idle time too, and
> this system is idle most of the night.

## `Life`, [line 19](../../../../../../../backend/src/sro/application/connection/session_life.py#L19): Note on the line above

Code: `observed: timedelta | None`

> The shortest life seen so far, or None while nothing has expired yet.

## `SessionLife`, [line 36](../../../../../../../backend/src/sro/application/connection/session_life.py#L36): Docstring

> Watch a session's clock, and say what it has been observed to be.

## `Life.stale_at`, [line 28](../../../../../../../backend/src/sro/application/connection/session_life.py#L28): Docstring

> When this session should be replaced, if we know when it began.

## `SessionLife.minted`, [line 41](../../../../../../../backend/src/sro/application/connection/session_life.py#L41): Docstring

> A fresh session exists as of now.

## `SessionLife.died`, [line 58](../../../../../../../backend/src/sro/application/connection/session_life.py#L58): Docstring

> A session that used to work does not any more.
>
> The life recorded is from minting to the last call that worked, not to
> the failure: everything in between is when it may already have been
> dead, and taking the longer number would schedule the next refresh
> after the point sessions have been seen to expire.

## `SessionLife.died`, [line 65](../../../../../../../backend/src/sro/application/connection/session_life.py#L65): Comment

Code: `shortest = min(lived, known.observed) if known.observed else lived`

> The shortest observed life, not the latest: one long weekend where
> nothing was asked of it does not prove the session survived it.

## `SessionLife._write`, [line 106](../../../../../../../backend/src/sro/application/connection/session_life.py#L106): Comment

Code: `evidence=EvidenceLevel.OBSERVED,`

> Watched, not read off a document: the strongest thing
> anybody can say about a credential nobody can inspect.
