# Notes for `backend/src/sro/application/chat/mailbox.py`

Comments and docstrings moved out of [`backend/src/sro/application/chat/mailbox.py`](../../../../../../../backend/src/sro/application/chat/mailbox.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/chat/mailbox.py#L1): Note

> The two mailbox constants the mail doors share. A leaf, so `from_the_mail`,
> `ask_the_asker` and `mail_job` can each import them without importing one
> another: `from_the_mail` starts runs through `workflow_runs`, which imports
> `mail_job`, and `mail_job` used to take these from the two chat modules --
> a cycle.

## module, [line 16](../../../../../../../backend/src/sro/application/chat/mailbox.py#L16): Note on the line above

Code: `SERVER = "gmail"`

> The connector this looks in, named rather than every connector a deployment
> holds. `SERVER` says the whole of why.

## module, [line 33](../../../../../../../backend/src/sro/application/chat/mailbox.py#L33): Note on the line above

Code: `K_REMEMBER = timedelta(days=30)`

> How long a message stays offered-once.
>
> Long enough that a mailbox re-read for a month says nothing twice, short enough
> that the ledger does not grow forever. A mail older than this that somehow
> comes round again is one nobody acted on in a month, and offering it a second
> time is not the worst thing this could do.

## `sent_to_others`, [line 133](../../../../../../../backend/src/sro/application/chat/mailbox.py#L133): Note

> Who else a request went to when the operator sent it: every To and Cc
> address other than the mailbox's own, when the sender is the mailbox. So a
> request the operator also copied a colleague on is a card that asks (decided
> 2026-09-26: "there is no harm in asking"). Empty for mail from anyone else,
> and for a request addressed ONLY to the operator -- that is how a person forwards themselves
> work, and how every test request on this deployment is written. Addresses
> are compared case-folded; `email.utils` does the parsing.

## `mail_key`, [line 47](../../../../../../../backend/src/sro/application/chat/mailbox.py#L47): Docstring

> The key a mail is read under in the claim ledger, for every door: the look
> keeps a mail it has read under it. It says "read", never "this system sent
> it" -- that is `sent_key` (M2 round 4). One key for both once made the
> operator's own demonstrated Send, already read by the look, look like this
> system's mail, and it granted no recipient. Before that it was two keys
> spelled apart (`mail:{id}` read, `mail:{operator}:{id}` sent), and this
> system's own sent mail was read back as the operator's; now `is_ours` is the
> one check of `sent_key`, and the look calls it before it reads a mail.

## `send_as_this_system`, [line 78](../../../../../../../backend/src/sro/application/chat/mailbox.py#L78): Comment

Code: `marker = secrets.token_hex(16)`

> And the mail this system just wrote is not a request TO it.
>
> The look reads the mailbox for anything asking for a job, and what it
> was handed back was our own question: "I am working on Create a
> Customer Type... I still need Customer Type" reads, correctly, as
> somebody asking for a customer type. Measured on the deployment
> 2026-09-18 -- the mail went out and the next look offered a card for
> it, which is this system asking itself to do the thing it had just
> asked a person about.
>
> Claimed in the same ledger a read claims, under its own key, `sent_key`:
> "this system sent it" is not "this was read", and `_allowed` must tell an
> operator's Send the look has read from a mail this system sent.
>
> Claimed before the send, not after (M2 round 3). Gmail has the mail before
> `send_message` answers with its id, and a look in that gap read it as the
> operator's own. So a random marker is claimed first and travels as the
> `X-SRO-Marker` header, which `get_message` and `get_thread` read back; a
> marker nobody claimed is just a header. A failed claim sends nothing and is
> raised, never logged away. The id is still claimed after the send, but only
> in addition: its failure is logged, because the mail already went.
