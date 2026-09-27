# Notes for `backend/src/sro/application/chat/candidates.py`

Which jobs the reader is shown, chosen in code (R1).

## `_first`, [line 39](../../../../../../../backend/src/sro/application/chat/candidates.py#L39): Design

> The canonical copy among duplicate titles: the most parameters, then the
> most held runs (amendment 2, item 7), then the smallest id. The real store
> held two 0-parameter 'Create a Customer Type' copies beside the 4-parameter
> one. Runnability never picks it (R1 review, I8): a blocked 4-parameter job
> is answered with why, where a runnable 0-parameter copy would take the
> request and replay the demonstrated values.

## `rank_jobs`, [line 44](../../../../../../../backend/src/sro/application/chat/candidates.py#L44): Design

> Duplicate titles collapse to their canonical copy, so "X or X or X?" can
> never be asked. Sign-in jobs (`signs_in`) are never candidates. A job that
> cannot run stays a candidate (C1's ruling): a request for it is answered
> with why. The rest are ranked by word overlap between the request and the
> job's title, field labels, aliases and `asked_by` mails, and the top
> `K_CANDIDATES` are sent.
> ponytail: word overlap misses a request that shares no word with the job;
> upgrade by embedding titles and `asked_by` with the knowledge base's
> embedding model.

## `chore_named`, [line 61](../../../../../../../backend/src/sro/application/chat/candidates.py#L61): Design

> A request whose words match a sign-in job more than any work job names a
> chore, and gets a note saying the session broker signs in (amendment 2,
> item 5). Log Out copies are not caught: nothing marks a job as signing out,
> and `signs_in` is set by the miner's judge (M1/S6).
