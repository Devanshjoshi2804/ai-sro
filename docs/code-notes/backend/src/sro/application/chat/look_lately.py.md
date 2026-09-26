# Notes for `backend/src/sro/application/chat/look_lately.py`

Each note names the code it explains (function or class, then the line in the current file) and says what the code does and why.

## `LookInTheMailLately`, [line 21](../../../../../../../backend/src/sro/application/chat/look_lately.py#L21): Note

Code: `class LookInTheMailLately:`

> The server's read of every operator's mailbox. Each operator and not each
> tenant: the Gmail grant (`connector_key`) and the claim on each message are
> per operator. The operators are those with a registered, unrevoked browser
> -- the ones whose heartbeat reads mail today; nothing else lists who holds a
> grant, and one who never connected Gmail answers "not connected" at no model
> cost. Every look goes through `FromTheMail.execute`, the same use case the
> heartbeat's door calls, so what the poll decides is what the door decides.
> The claim alone keeps the two callers apart: one insert wins, with no lock
> and no timing window.

## `LookInTheMailLately.execute`, [line 46](../../../../../../../backend/src/sro/application/chat/look_lately.py#L46): Note

Code: `if not self._start.runs_on_steel(ctx):`

> Only tenants on Steel are polled until rollout step R2. For an extension
> tenant `_started` returns a sure, complete request unchanged and only its
> browser turns it into a card, so a poll that claimed the mail would lose it.

## `LookInTheMailLately.execute`, [line 48](../../../../../../../backend/src/sro/application/chat/look_lately.py#L48): Note

Code: `with about(tenant=tenant.value, principal=principal):`

> Every model call the look makes runs attributed to this tenant and
> operator; the metered asker refuses a call with no tenant.

## `LookInTheMailLately.execute`, [line 57](../../../../../../../backend/src/sro/application/chat/look_lately.py#L57): Note

Code: `if not one.started:`

> With no browser asking, every offer the look did not start becomes a
> question in the operator's thread, so nothing the poll reads is dropped. One
> still missing a value is the `needs_values` question; one that is complete
> -- held back because the operator sent it to somebody else, or because its
> thread already started a run -- is asked as "should our system do it?"
> (`ask_to_run`), naming the recipients, with a do-it and a leave-it. The panel
> draws both, and the heartbeat's `lookForAQuestion` finds both.

## `K_EVER`, [line 18](../../../../../../../backend/src/sro/application/chat/look_lately.py#L18): Note

Code: `K_EVER = datetime(1970, 1, 1, tzinfo=UTC)`

> Every tenant that has ever captured anything, as `rekey_everything` reads
> them: a tenant with no capture has no mined job and nothing to recognise.
