# Notes for `backend/src/sro/interface/http/schemas.py`

Comments and docstrings moved out of [`backend/src/sro/interface/http/schemas.py`](../../../../../../../backend/src/sro/interface/http/schemas.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## `TrackRecordModel`, [line 476](../../../../../../../backend/src/sro/interface/http/schemas.py#L476): Comment

Code: `clean_runs_needed: int = REQUIRED_CLEAN_RUNS`

> The two thresholds the streak is measured against, sent rather than left
> for a reader to know. A console drawing "7 of 10" from a 10 it hardcoded
> would go on saying 10 the day `REQUIRED_CLEAN_RUNS` moved, and the bar
> would disagree with the rule that actually refuses the promotion.

## `SpendResponse.of`, [line 1698](../../../../../../../backend/src/sro/interface/http/schemas.py#L1698): Comment

Code: `return cls(cost_usd=round(day.cost_usd, 6), unpriced=day.blind, cap_usd=cap_usd)`

> Six places, as every dollar figure the rig answered with: a sum of
> floats reaches a console as $0.30000000000000004, and a twentieth of
> a cent is nothing a cap in dollars can notice.
>
> And this is the ONLY place anything rounds, deliberately. `over_cap`
> judges the raw `DaySpend`, so the figure that decides whether a
> tenant is cut off is never the figure a screen was shown. The
> asymmetry is intended and is not a bug to fix one layer down: a cap
> rounded to whole dollars moves the trip point by a dollar, and any
> rounding fine enough to be safe here moves it by less than the
> resolution a dollar cap has -- so the rounding belongs on the way
> out, where it is a display decision, and nowhere else.

## `WorkflowModel.of`, [line 1797](../../../../../../../backend/src/sro/interface/http/schemas.py#L1797): Comment

Code: `steps=[`

> Sorted here, because `Workflow.steps` is a list nothing promises
> is ordered -- `ordered_cites` sorts it for the same reason. A
> step list served in storage order is a job served in the wrong
> order, and it reads as a plausible one.

## `EvidenceResponse.of`, [line 1900](../../../../../../../backend/src/sro/interface/http/schemas.py#L1900): Comment

Code: `calls[gesture.id] = whole.pop("requests")`

> Split out, never copied: see the class docstring. `tenant` goes
> with them -- the caller proved which tenant it is to get here,
> and echoing it back is one more field to keep true.

## `LookupResponse.of`, [line 2536](../../../../../../../backend/src/sro/interface/http/schemas.py#L2536): Comment

Code: `answers=[`

> The question travels with the answers, because an answer to a
> question that named something is that thing and not the
> collection it was in.

## `_mail_link`, [line 2935](../../../../../../../backend/src/sro/interface/http/schemas.py#L2935): Comment

Code: `return _MAIL_LINKS[server] + quote(thread, safe="") if thread and server in _MAIL_LINKS else ""`

> A thread id is a link only on the server that issued it: Gmail's goes after `#all/` and
> an Outlook conversation id after `deeplink/readconv/`. The run stores which server its mail came
> from; one nobody here knows gets no link rather than a wrong one, and a run stored before the
> server was kept reads as Gmail, which was all there was.
