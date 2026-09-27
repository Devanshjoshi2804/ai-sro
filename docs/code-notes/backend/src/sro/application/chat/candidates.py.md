# Notes for `backend/src/sro/application/chat/candidates.py`

Which jobs the reader is shown, chosen in code (R1).

## `sign_in_names`, [line 17](../../../../../../../backend/src/sro/application/chat/candidates.py#L17): Design

> What was typed just before a password, in any job's evidence: the sign-in
> username. It is never a job value (amendment 2, item 2). Kept in lower case
> through `normal`, never logged, and never put in an eval case.
> ponytail: the operator's own login from the vault is not consulted; the
> recorded one is what the operator types. Add the vault's when a sign-in
> was never recorded.

## `_first`, [line 60](../../../../../../../backend/src/sro/application/chat/candidates.py#L60): Design

> The canonical copy among duplicate titles: a runnable one first (C1's gate
> would refuse the others), then the most parameters, then the most held runs
> (amendment 2, item 7), then the smallest id. The real store held two
> 0-parameter 'Create a Customer Type' copies beside the 4-parameter one.

## `rank_jobs`, [line 65](../../../../../../../backend/src/sro/application/chat/candidates.py#L65): Design

> Duplicate titles collapse to their canonical copy, so "X or X or X?" can
> never be asked. Sign-in jobs (`signs_in`) are never candidates. A job that
> cannot run stays a candidate (C1's ruling): a request for it is answered
> with why. The rest are ranked by word overlap between the request and the
> job's title, field labels, aliases and `asked_by` mails, and the top
> `K_CANDIDATES` are sent.
> ponytail: word overlap misses a request that shares no word with the job;
> upgrade by embedding titles and `asked_by` with the knowledge base's
> embedding model.

## `chore_named`, [line 82](../../../../../../../backend/src/sro/application/chat/candidates.py#L82): Design

> A request whose words match a sign-in job more than any work job names a
> chore, and gets a note saying the session broker signs in (amendment 2,
> item 5). Log Out copies are not caught: nothing marks a job as signing out,
> and `signs_in` is set by the miner's judge (M1/S6).
