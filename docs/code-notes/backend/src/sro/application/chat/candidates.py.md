# Notes for `backend/src/sro/application/chat/candidates.py`

Which jobs the reader is shown, chosen in code (R1).

## `_first`, [line 50](../../../../../../../backend/src/sro/application/chat/candidates.py#L50): Design

> The canonical copy among duplicate titles: the most parameters, then the
> most held runs (amendment 2, item 7), then the smallest id. The real store
> held two 0-parameter 'Create a Customer Type' copies beside the 4-parameter
> one. Runnability never picks it (R1 review, I8): a blocked 4-parameter job
> is answered with why, where a runnable 0-parameter copy would take the
> request and replay the demonstrated values.

## `_a_fragment`, [line 54](../../../../../../../backend/src/sro/application/chat/candidates.py#L54): Design

> A click-through that writes nothing is not a job anyone asks for (J1):
> "Navigate to Receiving" drew 17 offers on greyorange and 16 expired. The
> rule is the runtime's own notion of a write, `evidence.writes` (a non-read
> recorded call), or a mailbox send (`sends_mail`). A learned job has no kind
> that reads and reports data back, so no real job is hidden by it. It is
> decided only on full evidence: a job whose cited gestures are not all
> present is kept, so a job that cannot run is still answered with why (C1).
> Dropping the copies that write nothing before duplicates collapse is what
> makes the copy with a write the one offered.

## `real_jobs`, [line 64](../../../../../../../backend/src/sro/application/chat/candidates.py#L64): Design

> The ids of the jobs anyone is ever offered, the one rule every door reads:
> the chat and the mail door (through `rank_jobs`), the panel's learned list
> (`ReadWorkflows`' `offered`) and what a browser is served to nudge on
> (`shapes_for`). Chores (`Workflow.chore`: sign-ins and sign-outs),
> mail-only doings and fragments (`_a_fragment`) are never in it, and
> duplicate titles collapse to their canonical copy (`_first`), so "X or X
> or X?" can never be asked. A job that cannot run stays in (C1's ruling):
> a request for it is answered with why. It takes a workflow and its cited
> gestures rather than `JobFacts`, so the shapes read does not have to
> compile every job to ask.

## `rank_jobs`, [line 74](../../../../../../../backend/src/sro/application/chat/candidates.py#L74): Design

> Candidates are `real_jobs`, ranked by word overlap between the request and the
> job's title, field labels, aliases and `asked_by` mails, and the top
> `K_CANDIDATES` are sent.
> ponytail: word overlap misses a request that shares no word with the job;
> upgrade by embedding titles and `asked_by` with the knowledge base's
> embedding model.

## `chore_named`, [line 90](../../../../../../../backend/src/sro/application/chat/candidates.py#L90): Design

> A request whose words match a chore more than any work job names that
> chore, and gets a note saying the session broker signs in and out
> (amendment 2, item 5). Both verdicts are set by the miner's judge (M1/S6,
> and F3 for `signs_out`, which catches the Log Out copies).
