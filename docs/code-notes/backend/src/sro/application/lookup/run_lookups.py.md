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

## module, [line 42](../../../../../../../backend/src/sro/application/lookup/run_lookups.py#L42): Note on the line above

Code: `K_AFTER_HEADERS_S = 1.0`

> Room kept inside a lookup's budget after the header wait: `headers_for`
> answers inside its deadline (the round trips to Chrome included), and then
> the broker reads the cookie jar and the lookup decides. Without it the
> header wait ends when the budget does, the budget's own timeout wins, and
> the lookup says "timed out" instead of naming the header that never came
> -- and "ask again" fails the same way for ever.
> ponytail: a fixed second; a measured cookie-read time if a slow Chrome
> ever eats it.

## module, [line 27](../../../../../../../backend/src/sro/application/lookup/run_lookups.py#L27): Note on the line above

Code: `K_GAPS = (DomainError, PoolFull, PageGone, TargetUnreachable, AccountBusy, BrowserUnavailable)`

> What makes one lookup a named gap instead of failing the whole plan: a
> `DomainError` (a sign-in that needs a password, an account with no recorded
> username), a full pool, a tab or lease that went away, an unreachable system,
> an account parked waiting for a person, a Steel browser that is down. A sign-in
> that needs a person is a gap and not a question: nothing is waiting to resume
> a lookup, so a lookup never waits on a person.

## module, [line 38](../../../../../../../backend/src/sro/application/lookup/run_lookups.py#L38): Note on the line above

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

## module, [line 40](../../../../../../../backend/src/sro/application/lookup/run_lookups.py#L40): Note on the line above

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

## `Looked`, [line 50](../../../../../../../backend/src/sro/application/lookup/run_lookups.py#L50): Docstring

> What one lookup came back with.

## `Looked`, [line 55](../../../../../../../backend/src/sro/application/lookup/run_lookups.py#L55): Note on the line above

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

## `Looked`, [line 57](../../../../../../../backend/src/sro/application/lookup/run_lookups.py#L57): Note on the line above

Code: `detail: str = ""`

> Why not, when not. Kept in the refusal's own words -- a sign-in that needs a
> person is a different problem from an unreachable system, and flattening them
> to "failed" throws away the one thing that says which.

## `MissingHeaders`, [line 30](../../../../../../../backend/src/sro/application/lookup/run_lookups.py#L30): Note on the line above

Code: `class MissingHeaders(DomainError):`

> A header the read needs that the account's context never sent within the
> budget. A `DomainError`, so it is that one lookup's named gap.

## `RunLookups`, [line 71](../../../../../../../backend/src/sro/application/lookup/run_lookups.py#L71): Docstring

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

## `RunLookups.execute`, [line 75](../../../../../../../backend/src/sro/application/lookup/run_lookups.py#L75): Docstring

> `within` is the caller's budget, because the callers have different
> ones: a lookup somebody asked for may take as long as the slowest
> warehouse, and a lookup inside a conversation turn may not. See
> `K_WHILE_TALKING`.

## `RunLookups.execute`, [line 81](../../../../../../../backend/src/sro/application/lookup/run_lookups.py#L81): Comment (debt)

Code: `gestures = list(await uow.gestures.gestures_for(ctx.tenant_id))`

> Every gesture, scanned per lookup. The store holds hundreds per
> tenant, so this is cheaper than the round trip that would fetch
> one call.
> ponytail: whole-store scan; a `calls_for_path` query if a tenant's
> capture outgrows memory.

## `RunLookups._one`, [line 138](../../../../../../../backend/src/sro/application/lookup/run_lookups.py#L138): Comment

Code: `if lookup.how == "call":`

> An auth refusal (`K_AUTH_REFUSED`, the API lane's rule) signs the account in
> again once, under the account lock, and the read is tried again. Any other
> answer that is not 2xx falls to the screen: the page the GET was made from is
> already up in the tab `acquire` opened (and `reauth` returns it there), so it
> is photographed with no navigation. The same rule as §3's, applied to a read.

## `RunLookups._one`, [line 155](../../../../../../../backend/src/sro/application/lookup/run_lookups.py#L155): Comment

Code: `raise SignedOut(f"{page} is still a sign-in page")`

> The page is read again, by the same structural check (`a_sign_in_page`),
> right before the photograph and after any sign-in: a sign-in that did not
> hold, or a single-page app that redirects to sign-in late, leaves a sign-in
> form in the tab. A photograph of it would answer the question with a login
> screen, so it is a named gap instead.

## `RunLookups._send`, [line 198](../../../../../../../backend/src/sro/application/lookup/run_lookups.py#L198): Comment

Code: `needs = needs_of(dict.fromkeys((*address.live_headers, *address.struck), REDACTED))`

> The headers the recording struck out whose role a request log keeps
> (`needs_of`, the API lane's one rule) are the ones the account's own context
> has to supply, so the broker waits for each of them in the context's request
> log (from tab arrival). After a re-sign-in the wait is `fresh`: only tokens
> sent after the reload count, never the pre-sign-in one still in the log. A value never reaches a log. The wait is what is left of
> the caller's budget -- chat's `K_WHILE_TALKING` or the door's own -- never
> the broker's fixed wait past it. With nothing needed the driver answers at
> once. A header still missing when it ends is a
> named gap (`MissingHeaders`), not a GET sent without it. From the recording
> only representation headers are sent, through the API lane's one rule
> (`session_headers`): a recorded `x-user-id` is the operator's, never this
> account's.

## `_looked`, [line 238](../../../../../../../backend/src/sro/application/lookup/run_lookups.py#L238): Comment

Code: `if isinstance(body, str) and (read := read_answer(body, url=address.url))`

> `url` so the counting is honest: `limit=50` in the query and `50` in
> the envelope are the same fact about what we ASKED for, and a total
> that merely echoes our own paging is not a total. `narrowed_by` carries what
> the replayed GET was narrowed by that the lookup did not ask for (a search or
> filter somebody ran when it was recorded): a list read through one is never
> "the whole list", so no "No, it does not exist" can come of it -- that sentence
> invites a duplicate record, the worst outcome here. `Address` prefers the
> recorded read with nothing narrowing it, and it does not strip a recorded
> parameter itself: a scope such as `siteId` stripped reads another list entirely.

## `RunLookups._send`, [line 213](../../../../../../../backend/src/sro/application/lookup/run_lookups.py#L213): Note

Code: `return await self._broker.send(ctx, held, "GET", address.url, headers=headers)`

> Why the page sends it. A lookup's GET goes out through `SessionBroker.send`, the page itself, and
> never through the worker's own HTTP client. Measured on QA 2026-10-02: the same
> GET with the same cookie and token from the worker's client was answered `302` by
> the site's edge; from the page it answers the grid's JSON. The old path took the
> `302` for "not a success" and fell through to a photograph, which holds no
> records, so every existence question ended "could not tell". A call that is not
> answered 2xx is now a failed lookup that names the status; a sign-in redirect
> (`is_login`), `401/403/419` or status `0` (the browser's fetch refused, as it is
> when an expired session redirects across origins) signs in once and tries again.
> Still `403` after that is the system's answer ("the system answered 403"), not
> "still a sign-in page": only a page that is one raises `SignedOut`.

## `RunLookups.execute`, [line 96](../../../../../../../backend/src/sro/application/lookup/run_lookups.py#L96): Note

Code: `async with asyncio.timeout_at(until) as budget:`

> One turn budget for the whole plan, not one per lookup: a conversation says how
> long it can wait, and six lookups of ten seconds is a minute. A lookup that starts
> with the budget spent is "timed out" without being tried.

## `RunLookups._one`, [line 152](../../../../../../../backend/src/sro/application/lookup/run_lookups.py#L152): Note

Code: `ctx, held, address.url, address.reads, deadline_s=min(K_PAINT_S, _left(budget))`

> A screen is photographed after its own reads, QA 2026-10-02: the photograph of the Warehouse Equipment Type page was a spinner
> and "Loading". The tab had settled (no request in flight at that instant) before the
> grid's own GET went out. The recording of the screen says which GETs the page made
> (`Address.reads`, the path shapes of every gesture on that route's successful GETs,
> the most often made first: the newest gesture may be a click that read nothing); the
> page is loaded again while the call log listens and the photograph waits for those
> calls under one deadline, `K_PAINT_S` or what is left of the turn if that is less. A
> read that never recurs costs the deadline, not the lookup: the photograph is taken
> anyway. The reload stays because it is what starts the listening: `mark` attaches the
> log and `wait_for_call` answers False for a log that began after the mark, so a tab
> opened by `acquire` (not listening) cannot be waited on without it.
