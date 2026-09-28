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

## module, [line 51](../../../../../../../backend/src/sro/domain/prompts/write_mail.py#L51): Note on the line above

Code: `"body": {"type": "string", "pattern": r"\S"},`

> A draft with an empty body is no draft. Two QA runs on 2026-09-28 got
> exactly that from 3.8-flash -- every field present, the body empty -- and
> stopped with "the model said nothing". Schema-valid, it was never a
> failure the fallback could see. Now it breaks the schema, so it is: the
> record falls back to 3.7-flash. Version 3 for the schema change.
>
> `pattern` and not `minLength`: the body must hold something that is not
> whitespace, which is what `write_the_mail` means by a body. A lone newline
> from a model that spent its tokens thinking is as empty as `""`. The
> schema is the one place a model's body is judged; `write_the_mail` checks
> again only a draft shown back to it (S4's yes to a refused draft).

## `WRITE_MAIL`, [line 32](../../../../../../../backend/src/sro/domain/prompts/write_mail.py#L32): Note

> Version 4 (S4, merged after S3's version 3) adds `request`, trusted JSON: the words the run's starter typed
> in their own panel and their answers to its questions. The model is told it is
> the operator speaking, not mail; an address it names may be written to, the
> body is what it asks for when the values hold none, and a value from it is
> cited to message `request`. QA 2026-09-28: `Compose and Send Email` from the
> operator's own chat came back `to=""`, `body=""` on 3.8-flash and 3.7-flash,
> with the operator's request never shown. `check_draft` still enforces every
> rule. No mail suite exists yet, so no `make eval` report (LIVE EVAL owed).
