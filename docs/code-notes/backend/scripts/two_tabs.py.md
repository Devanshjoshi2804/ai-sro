# Notes for `backend/scripts/two_tabs.py`

Comments and docstrings moved out of [`backend/scripts/two_tabs.py`](../../../../backend/scripts/two_tabs.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../backend/scripts/two_tabs.py#L1): Docstring

> Work that alternated between two systems, and what the miner makes of it.
>
> A job can be two halves in two tabs -- read the mail, create the thing it asks
> for -- and `shared_values` is the only rule that links them. It links on a
> TYPED VALUE appearing in both systems, so a mail somebody read but never typed
> into links nothing, however plainly the work follows from it.
>
>     uv run python scripts/two_tabs.py            # every tenant
>     uv run python scripts/two_tabs.py acme --gap 60
>
> Reads only. For each tenant it prints the sittings where the browser went to
> another system and came back -- an alternation, not a one-way trip to a login
> page -- and how many of those gestures the value rule links.
>
> Measured on 2026-09-14: on `acme`, 5 of 43 sittings alternate, carrying 219
> gestures, of which 211 are linked by no shared value; the rule links 23 in the
> whole store. The consequence is visible in the output: an `acme` sitting at
> 15:00 where the operator read a mail whose subject is "create a customer type
> :", typed the value into the warehouse six seconds later, and the job mined
> from it has no mail step at all.

## `_sittings`, [line 14](../../../../backend/scripts/two_tabs.py#L14): Docstring

> Stretches with no more than `gap` seconds of silence in them.
>
> A sitting rather than a day: what makes two tabs one job is somebody
> working in both, and an hour of quiet between them is two sittings however
> the day is sliced.

## `_turns`, [line 29](../../../../backend/scripts/two_tabs.py#L29): Docstring

> How many times the browser changed system inside this sitting.

## `_woven`, [line 34](../../../../backend/scripts/two_tabs.py#L34): Docstring

> Whether this sitting went to another system and came BACK.
>
> A one-way trip is not evidence of one job: every warehouse session starts
> at a login host. Coming back is what says somebody was using two tabs for
> one piece of work.

## `_read`, [line 64](../../../../backend/scripts/two_tabs.py#L64): Comment

Code: `woven.sort(key=_turns, reverse=True)`

> Loudest first. A login dance -- warehouse, identity provider, keycloak,
> warehouse -- changes system three times and is plumbing. Somebody working
> a mail against a warehouse form changes it five times in three minutes and
> is one job. Printed in that order, the difference is the first line.
