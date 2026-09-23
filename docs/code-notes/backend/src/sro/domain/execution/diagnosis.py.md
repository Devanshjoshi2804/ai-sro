# Notes for `backend/src/sro/domain/execution/diagnosis.py`

Comments and docstrings moved out of [`backend/src/sro/domain/execution/diagnosis.py`](../../../../../../../backend/src/sro/domain/execution/diagnosis.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/domain/execution/diagnosis.py#L1): Docstring

> What a failed step is actually complaining about, and what would fix it.
>
> A table, for the same reason the escalation policy is one: every entry is a
> claim that can be read, argued with and tested, where a chain of branches inside
> the executor is none of those things.
>
> The entries here were each paid for. A shadow run of the first task ever taught
> came back ``302`` to the login page while the console reported the connection
> signed in, and nothing in the run said why -- the session had rotated, and a
> redirect to an identity provider is indistinguishable from being signed out.
> Diagnosing that by hand took an afternoon. Doing it twice would be a choice.
>
> Two rules bound every remedy, and neither is negotiable:
>
> **A remedy repairs the session, never the skill.** Refreshing a cookie is
> recovering something the system owns. Changing what a step sends is rewriting
> evidence, and evidence is only rewritten by a demonstration.
>
> **A write is retried only when the evidence says it never arrived.** A redirect
> to a login page is proof the application never saw the request. A timeout, a 500
> or a 409 are not, and retrying those risks doing a warehouse task twice.

## `Remedy`, [line 10](../../../../../../../backend/src/sro/domain/execution/diagnosis.py#L10): Note on the line above

Code: `NONE = "none"`

> Nothing safe to try. The honest answer for most failures: the system
> said no for a reason of its own, and guessing at it is how an executor
> turns one bad call into six.

## `Remedy`, [line 12](../../../../../../../backend/src/sro/domain/execution/diagnosis.py#L12): Note on the line above

Code: `REFRESH_SESSION = "refresh_session"`

> Sign the connection in again and take what it produces -- cookies, the
> tokens the application mints, the page it calls from. The remedy for a
> session that has aged out underneath a skill that is still correct.

## `Remedy`, [line 14](../../../../../../../backend/src/sro/domain/execution/diagnosis.py#L14): Note on the line above

Code: `REFRESH_SESSION_CONTEXT = "refresh_session_context"`

> The session is good but what the executor holds beside it is not: a
> token the page reissues, a per-session context in the Referer. Observed
> from the application again without a new login, which matters on a system
> that permits one session at a time -- signing in again would take the
> operator's own browser down with it.

## `Remedy`, [line 16](../../../../../../../backend/src/sro/domain/execution/diagnosis.py#L16): Note on the line above

Code: `ESCALATE_MEDIUM = "escalate_medium"`

> The call cannot be made to work as a call. The interface can still do
> it, and the escalation table already says when that is sensible.

## `Diagnosis`, [line 23](../../../../../../../backend/src/sro/domain/execution/diagnosis.py#L23): Note on the line above

Code: `safe_for_writes: bool`

> Whether the evidence proves the request never reached the application.
> False stops a mutating step even when the remedy would work, because a
> write that may have landed must be looked at by a person.

## `diagnose`, [line 35](../../../../../../../backend/src/sro/domain/execution/diagnosis.py#L35): Docstring

> Read the symptom. Never the skill, and never the operator's intent.

## `diagnose`, [line 50](../../../../../../../backend/src/sro/domain/execution/diagnosis.py#L50): Comment

Code: `safe_for_writes=True,`

> Nothing was sent: the step refused before the request was built.

## `diagnose`, [line 57](../../../../../../../backend/src/sro/domain/execution/diagnosis.py#L57): Comment

Code: `safe_for_writes=True,`

> A login page is proof the request was turned away before the
> application saw it. This is the one status where that is provable.

## `diagnose`, [line 84](../../../../../../../backend/src/sro/domain/execution/diagnosis.py#L84): Comment

Code: `return _NOTHING`

> Everything else on purpose. A 500 may have written half a task, a 409 is
> the system disagreeing on facts, a timeout leaves the outcome unknown --
> and none of them are fixed by trying again with the same request.
