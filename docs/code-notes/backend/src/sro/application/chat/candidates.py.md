# Notes for `backend/src/sro/application/chat/candidates.py`

Which jobs the reader is shown, chosen in code (R1).

## `_first`, [line 48](../../../../../../../backend/src/sro/application/chat/candidates.py#L48): Design

> The canonical copy among duplicate titles: the most parameters, then the
> most held runs (amendment 2, item 7), then the smallest id. The real store
> held two 0-parameter 'Create a Customer Type' copies beside the 4-parameter
> one. Runnability never picks it (R1 review, I8): a blocked 4-parameter job
> is answered with why, where a runnable 0-parameter copy would take the
> request and replay the demonstrated values.

## `rank_jobs`, [line 53](../../../../../../../backend/src/sro/application/chat/candidates.py#L53): Design

> Duplicate titles collapse to their canonical copy, so "X or X or X?" can
> never be asked. Chores (`Workflow.chore`: sign-ins and sign-outs) are never candidates. A job that
> cannot run stays a candidate (C1's ruling): a request for it is answered
> with why. The rest are ranked by word overlap between the request and the
> job's title, field labels, aliases and `asked_by` mails, and the top
> `K_CANDIDATES` are sent.
> ponytail: word overlap misses a request that shares no word with the job;
> upgrade by embedding titles and `asked_by` with the knowledge base's
> embedding model.

## `chore_named`, [line 70](../../../../../../../backend/src/sro/application/chat/candidates.py#L70): Design

> A request whose words match a chore more than any work job names that
> chore, and gets a note saying the session broker signs in and out
> (amendment 2, item 5). Both verdicts are set by the miner's judge (M1/S6,
> and F3 for `signs_out`, which catches the Log Out copies).
