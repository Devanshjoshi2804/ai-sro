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
