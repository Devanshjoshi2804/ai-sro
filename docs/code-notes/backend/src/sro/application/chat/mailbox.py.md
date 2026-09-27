# Notes for `backend/src/sro/application/chat/mailbox.py`

Comments and docstrings moved out of [`backend/src/sro/application/chat/mailbox.py`](../../../../../../../backend/src/sro/application/chat/mailbox.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/chat/mailbox.py#L1): Note

> The two mailbox constants the mail doors share. A leaf, so `from_the_mail`,
> `ask_the_asker` and `mail_job` can each import them without importing one
> another: `from_the_mail` starts runs through `workflow_runs`, which imports
> `mail_job`, and `mail_job` used to take these from the two chat modules --
> a cycle.

## module, [line 6](../../../../../../../backend/src/sro/application/chat/mailbox.py#L6): Note on the line above

Code: `SERVER = "gmail"`

> The connector this looks in, named rather than every connector a deployment
> holds. `gather.SERVER` says the whole of why.

## module, [line 8](../../../../../../../backend/src/sro/application/chat/mailbox.py#L8): Note on the line above

Code: `K_REMEMBER = timedelta(days=30)`

> How long a message stays offered-once.
>
> Long enough that a mailbox re-read for a month says nothing twice, short enough
> that the ledger does not grow forever. A mail older than this that somehow
> comes round again is one nobody acted on in a month, and offering it a second
> time is not the worst thing this could do.

## `sent_to_others`, [line 15](../../../../../../../backend/src/sro/application/chat/mailbox.py#L15): Note

> Who else a request went to when the operator sent it: every To and Cc
> address other than the mailbox's own, when the sender is the mailbox. So a
> request the operator also copied a colleague on is a card that asks (decided
> 2026-09-26: "there is no harm in asking"). Empty for mail from anyone else,
> and for a request addressed ONLY to the operator -- that is how a person forwards themselves
> work, and how every test request on this deployment is written. Addresses
> are compared case-folded; `email.utils` does the parsing.

## `mail_key`, [line 11](../../../../../../../backend/src/sro/application/chat/mailbox.py#L11): Docstring

> The one key a mail is known by in the claim ledger, for every door: the look
> keeps a mail it has read under it, and a send this system made is remembered
> under it, so the look finds its own mail already taken and never reads it. It
> was two keys once (`mail:{id}` read, `mail:{operator}:{id}` sent), and this
> system's own sent mail was read back as the operator's -- a reply that could
> answer a value, or, once SENT counted as the operator's word, name a
> recipient.
