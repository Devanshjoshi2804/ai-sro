# Notes for `backend/src/sro/application/chat/look_lately.py`

Each note names the code it explains (function or class, then the line in the current file) and says what the code does and why.

## `LookInTheMailLately`, [line 16](../../../../../../../backend/src/sro/application/chat/look_lately.py#L16): Note

Code: `class LookInTheMailLately:`

> The server's read of every operator's mailbox. Each operator and not each
> tenant: the Gmail grant (`connector_key`) and the claim on each message are
> per operator. The operators are those with a registered, unrevoked browser
> -- the ones whose heartbeat reads mail today; nothing else lists who holds a
> grant, and one who never connected Gmail answers "not connected" at no model
> cost. Every look goes through `FromTheMail.execute`, the same use case the
> heartbeat's door calls, so what the poll decides and asks is what the door
> decides and asks.

## `LookInTheMailLately.execute`, [line 24](../../../../../../../backend/src/sro/application/chat/look_lately.py#L24): Note

Code: `for tenant in map(TenantId, self._tenants):`

> Only the tenants configured to run on Steel (`steel_tenants`), until rollout
> step R2. For an extension tenant a sure, complete request becomes a card
> only in its browser, so a poll that read the mail would lose it. The list is
> the setting, not every tenant that ever captured something.

## `LookInTheMailLately.execute`, [line 35](../../../../../../../backend/src/sro/application/chat/look_lately.py#L35): Note

Code: `with about(tenant=tenant.value, principal=principal):`

> Every model call the look makes runs attributed to this tenant and
> operator; the metered asker refuses a call with no tenant.
