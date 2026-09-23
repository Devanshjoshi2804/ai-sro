# Notes for `backend/src/sro/application/trigger/read_triggers.py`

Comments and docstrings moved out of [`backend/src/sro/application/trigger/read_triggers.py`](../../../../../../../backend/src/sro/application/trigger/read_triggers.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/trigger/read_triggers.py#L1): Docstring

> What is on a clock, and switching one off.

## `SetTriggerEnabled`, [line 47](../../../../../../../backend/src/sro/application/trigger/read_triggers.py#L47): Docstring

> Pausing a trigger unschedules it rather than letting it fire into a
> check. A schedule that runs every minute to decide it should not have is a
> schedule somebody will find in a bill.

## `ReadTriggers.watches`, [line 24](../../../../../../../backend/src/sro/application/trigger/read_triggers.py#L24): Docstring

> What this one browser is watching for.
>
> A watch is evaluated nowhere else -- the browser that already has the
> mailbox open applies the rule locally, and nothing about the mail ever
> leaves it -- so the browser has to be able to ask what its rules are.
>
> Scoped to the device as well as the tenant, and that is the point: two
> operators in the same tenant have their own mailboxes, and a rule about
> one person's mail handed to another person's browser is that mail being
> read by somebody who was never offered it. Disabled ones are left out
> rather than sent with a flag, because a browser that had to remember to
> check the flag is a browser that one day does not.

## `ReadTriggers.arrivals`, [line 35](../../../../../../../backend/src/sro/application/trigger/read_triggers.py#L35): Docstring

> The pages this one browser starts a job on.
>
> Watches and arrivals are asked for separately rather than as "the rules
> this browser holds", because the browser does two different things with
> them: a watch is evaluated against a mail and OFFERS what it matched,
> an arrival is evaluated against the page in front of somebody and
> STARTS something. One list would make the caller sort them by kind,
> which is this method's job.
>
> Scoped to the device for `watches`'s reason and one of its own: an
> arrival drives that browser, and a rule about one operator's window
> handed to another's is that window being driven by somebody who never
> agreed to it.

## `ReadTriggers.watches`, [line 26](../../../../../../../backend/src/sro/application/trigger/read_triggers.py#L26): Comment (debt)

Code: `triggers = await uow.triggers.list_for_tenant(ctx.tenant_id)`

> ponytail: filtered here rather than in SQL -- a tenant has tens of
> triggers, not thousands. A `device_id` clause on `list_for_tenant`
> is the move the first time that stops being true.

## `DeleteTrigger.execute`, [line 80](../../../../../../../backend/src/sro/application/trigger/read_triggers.py#L80): Comment

Code: `trigger = await uow.triggers.get(ctx.tenant_id, trigger_id)`

> Read first: deleting a trigger that is not this tenant's must be
> the same "not found" as one that never existed, and a blind
> DELETE would answer 200 either way.

## `DeleteTrigger.execute`, [line 81](../../../../../../../backend/src/sro/application/trigger/read_triggers.py#L81): Comment

Code: `if trigger.kind is TriggerKind.SCHEDULE:`

> Only a schedule kind was ever registered with the scheduler --
> the same gate SetTriggerEnabled applies. Without it, deleting a
> manual or inbound trigger, which never depended on it, could
> not be done during exactly the outage the rest of this system
> goes out of its way to tolerate.
