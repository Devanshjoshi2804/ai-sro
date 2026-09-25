# Notes for `backend/src/sro/application/lookup/run_lookups.py`

Comments and docstrings moved out of [`backend/src/sro/application/lookup/run_lookups.py`](../../../../../../../backend/src/sro/application/lookup/run_lookups.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/lookup/run_lookups.py#L1): Docstring

> Going and looking, one plan at a time.
>
> `PlanLookups` says where the answer lives; this goes there. It is the half
> that leaves the building, so everything it may do is narrow on purpose:
>
> **A GET, or a page opened and photographed. Nothing else.** The plan cannot
> express a write and `address_for` refuses anything that is not a recorded GET,
> so a mail carrying "and then delete the old one" has no shape to become by the
> time it reaches here.
>
> **From the account's own Steel session, never the operator's browser.** The
> broker picks the account whose recorded sign-in lands on the page, takes a
> Steel tab on that page in the account's context, and the GET goes out from
> the API process with the cookie and live headers that context holds
> (`SessionBroker.headers`, with the full URL). Nobody's screen is taken and no
> browser needs to be connected.
>
> **One lookup's failure is not the plan's.** A sign-in that needs a person, a
> full pool, a tab that went away, an unreachable system, an endpoint this
> deployment has never been to, a lookup that ran out of its budget: each comes
> back as that lookup's own refusal beside the answers that
> did arrive. A question asked of four systems and answered by three is three
> answers and a named gap, which is worth more than nothing at all -- the
> opposite reading from the PLANNER's, where a target nobody has seen refuses
> the whole plan. The difference is that a planning failure means the plan is
> wrong about the world, and a looking failure means one system was shut.

## module, [line 24](../../../../../../../backend/src/sro/application/lookup/run_lookups.py#L24): Note on the line above

Code: `K_GAPS = (DomainError, PoolFull, PageGone, TargetUnreachable, AccountBusy, BrowserUnavailable)`

> What makes one lookup a named gap instead of failing the whole plan: a
> `DomainError` (a sign-in that needs a password, an account with no recorded
> username), a full pool, a tab or lease that went away, an unreachable system,
> an account parked waiting for a person, a Steel browser that is down. A sign-in
> that needs a person is a gap and not a question: nothing is waiting to resume
> a lookup, so a lookup never waits on a person.

## module, [line 26](../../../../../../../backend/src/sro/application/lookup/run_lookups.py#L26): Note on the line above

Code: `K_DEADLINE_S = 45.0`

> How long one lookup may take, when the lookup is what somebody is waiting on.
>
> Longer than a run's step, which has an operator watching it: a lookup is
> answered by whichever system is slowest, and a question that comes back
> incomplete because a warehouse took twelve seconds is a worse outcome than one
> that takes twelve seconds.
>
> This is the budget for `/v1/lookups` and `/v1/ask`, where the answer IS the
> request and nothing else is held up behind it.

## module, [line 28](../../../../../../../backend/src/sro/application/lookup/run_lookups.py#L28): Note on the line above

Code: `K_WHILE_TALKING = 10.0`

> And how long one may take when a CONVERSATION is waiting on it.
>
> A reply in a panel is not a lookup somebody is watching a spinner for. It is a
> turn in a conversation, and a turn that takes a minute has stopped being one.
>
> Measured on the deployment 2026-09-21, request `req_10d3ff9b`:
>
>     19:23:23  the sentence arrives
>     19:23:38  device disconnected
>     19:23:39  device connected
>     19:24:19  device disconnected
>     19:24:30  reply -- 67459ms
>
> The browser's socket dropped twice inside one request. One command waited out
> the full 45 seconds, the model calls either side cost the rest, and the person
> who typed a question sat in front of a panel that said nothing for over a
> minute. Before the conversation asked the lookup door at all, the same door
> answered in 7691ms.
>
> Ten seconds, because that is roughly twice what the whole of `/v1/ask` costs
> end to end -- two model calls and a warehouse round trip measured at 5913ms on
> the same deployment -- so a browser that is answering at all answers inside
> it, and one that is not is not worth a conversation waiting on.
>
> A lookup that runs out says so, and the thread stays usable. That is the
> trade: a question answered late is worth less than a conversation that
> kept going.

## `Looked`, [line 32](../../../../../../../backend/src/sro/application/lookup/run_lookups.py#L32): Docstring

> What one lookup came back with.

## `Looked`, [line 37](../../../../../../../backend/src/sro/application/lookup/run_lookups.py#L37): Note on the line above

Code: `read: Answer | None = None`

> The records in it, READ, rather than the body they arrived in.
>
> Every other read in this system goes through `read_answer`: the taught
> skill's own calls, a derived read, the capability probe. The lookup plane
> was the one that did not -- it handed the raw body on and left whoever
> drew it to parse JSON, pick columns and count rows.
>
> So each surface guessed, and the panel guessed badly. Measured on the
> deployment 2026-09-21: asked "is there a customer type called KKYT", it
> drew `URNFORMAT | ABSOLUTEGROUP | ALLOCATIONSEARCHPATH` -- the first six
> KEYS of a payload that alphabetises -- as five columns of em dashes,
> beside a warehouse screen showing `Customer Type` and `Description`.
>
> `answer.py` had already solved every part of that, for the plane that uses
> it: a column earns its place by carrying a value, the ranking puts code,
> name and description first, `self_uri` is dropped as a link, two columns
> holding the same value in every row are one, the count is the system's own
> total rather than the page length, and `sentence()` says it in a line.
>
> None where there are no records to speak of -- a page of HTML, one scalar,
> a screen's photograph. Those keep `answer` and are drawn from it.

## `Looked`, [line 39](../../../../../../../backend/src/sro/application/lookup/run_lookups.py#L39): Note on the line above

Code: `detail: str = ""`

> Why not, when not. Kept in the refusal's own words -- a sign-in that needs a
> person is a different problem from an unreachable system, and flattening them
> to "failed" throws away the one thing that says which.

## `RunLookups`, [line 52](../../../../../../../backend/src/sro/application/lookup/run_lookups.py#L52): Docstring

> Execute a plan on backend Steel, never the operator's browser.
>
> A lookup takes a tab and not a durable run: it lives inside the request that
> asked, bounded by the caller's deadline, so there is nothing to resume.
>
> **Nothing here can write**, by three structural facts, one test each:
> `address_for` returns only GETs that answered 2xx; the API half sends the
> literal method `"GET"`; the tab half calls only `acquire` (a tab opened on
> the page), `screenshot` and `release` -- never `act`, `point` or the sight
> model. A target seen only as a write addresses nothing, and nothing is sent.

## `RunLookups.execute`, [line 56](../../../../../../../backend/src/sro/application/lookup/run_lookups.py#L56): Docstring

> `within` is the caller's budget, because the callers have different
> ones: a lookup somebody asked for may take as long as the slowest
> warehouse, and a lookup inside a conversation turn may not. See
> `K_WHILE_TALKING`.

## `RunLookups.execute`, [line 62](../../../../../../../backend/src/sro/application/lookup/run_lookups.py#L62): Comment (debt)

Code: `gestures = list(await uow.gestures.gestures_for(ctx.tenant_id))`

> Every gesture, scanned per lookup. The store holds hundreds per
> tenant, so this is cheaper than the round trip that would fetch
> one call.
> ponytail: whole-store scan; a `calls_for_path` query if a tenant's
> capture outgrows memory.

## `RunLookups._one`, [line 94](../../../../../../../backend/src/sro/application/lookup/run_lookups.py#L94): Comment

Code: `if lookup.how == "call":`

> An auth refusal (`K_AUTH_REFUSED`, the API lane's rule) signs the account in
> again once, under the account lock, and the read is tried again. Any other
> answer that is not 2xx falls to the screen: the page the GET was made from is
> already up in the tab `acquire` opened (and `reauth` returns it there), so it
> is photographed with no navigation. The same rule as §3's, applied to a read.

## `RunLookups._send`, [line 122](../../../../../../../backend/src/sro/application/lookup/run_lookups.py#L122): Comment

Code: `needs = [name.lower() for name in (*address.live_headers, *address.struck)]`

> Every header the recording struck out is one the account's own context has to
> supply, so the broker waits for each of them in the context's request log
> (from tab arrival). A value never reaches a log. The recorded headers that
> were not struck are sent as recorded, unless the session carries the same
> name, which wins.

## `_looked`, [line 136](../../../../../../../backend/src/sro/application/lookup/run_lookups.py#L136): Comment

Code: `read=read_answer(body, url=address.url) if isinstance(body, str) else None,`

> `url` so the counting is honest: `limit=50` in the query and `50` in
> the envelope are the same fact about what we ASKED for, and a total
> that merely echoes our own paging is not a total.
