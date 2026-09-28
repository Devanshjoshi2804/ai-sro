# Notes for `backend/src/sro/domain/prompts/write_mail.py`

Notes on [`backend/src/sro/domain/prompts/write_mail.py`](../../../../../../../backend/src/sro/domain/prompts/write_mail.py). Each note names the code it explains (function or class, then the line in the current file).

## module, [line 1](../../../../../../../backend/src/sro/domain/prompts/write_mail.py#L1): Note

> Version 2 (M2) asks for `cited`, a `{value, message}` for every value the body
> takes from the conversation (its subject or body; run values are never cited),
> and shows each message's id, `to`, `cc` and whether the operator sent it, so it
> can cite and address by them. Recipients are the conversation's participants
> and `sent_before`, the addresses the job was demonstrated sending to. The model
> is told the rules; `check_draft` enforces them, so a draft that breaks them is
> refused and the operator asked, whatever the model did.
>
> There is no mail suite in the eval (spec §2.2), so this version has no
> `make eval` report; it merges on its code checks (ruled 2026-09-26), and P5
> adds a small mail suite.

## module, [line 45](../../../../../../../backend/src/sro/domain/prompts/write_mail.py#L45): Note on the line above

Code: `"body": {"type": "string", "minLength": 1},`

> A draft with an empty body is no draft. Two QA runs on 2026-09-28 got
> exactly that from 3.8-flash -- every field present, the body empty -- and
> stopped with "the model said nothing". Schema-valid, it was never a
> failure the fallback could see. Now it breaks the schema, so it is: the
> record falls back to 3.7-flash. Version 3 for the schema change.
