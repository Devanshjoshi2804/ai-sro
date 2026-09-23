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
> **From the operator's own session.** The call goes out through the extension's
> `http.send`, in the tab the operator is signed into, with the session cookie
> the browser already has -- which is why this needs a connected browser and not
> a credential in a file.
>
> **A system nobody has open is opened, in the background.** Every command that
> reaches a system needs a tab already on it -- the point of sending from the
> browser is the session that origin's cookies carry -- so without `tab.open` a
> question asked of four systems is answerable only for the ones the operator
> happens to have in front of them. The tab is opened behind what they are
> doing and their focus never moves.
>
> **One lookup's failure is not the plan's.** A system with no tab open, an
> endpoint this deployment has never been to, a page whose session token has
> expired: each comes back as that lookup's own refusal beside the answers that
> did arrive. A question asked of four systems and answered by three is three
> answers and a named gap, which is worth more than nothing at all -- the
> opposite reading from the PLANNER's, where a target nobody has seen refuses
> the whole plan. The difference is that a planning failure means the plan is
> wrong about the world, and a looking failure means one system was shut.

## module, [line 18](../../../../../../../backend/src/sro/application/lookup/run_lookups.py#L18): Note on the line above

Code: `NO_TAB = frozenset({"no_tab_for_origin", "no_tab_for_system"})`

> The extension's two words for "nobody has that system open", which is the
> one failure this side can do something about. Every other error kind -- a page
> that would not answer, a header with no live source, a refused focus -- is a
> fact about the attempt, and retrying it would just cost the same time twice.

## module, [line 20](../../../../../../../backend/src/sro/application/lookup/run_lookups.py#L20): Note on the line above

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

## module, [line 22](../../../../../../../backend/src/sro/application/lookup/run_lookups.py#L22): Note on the line above

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

## `Looked`, [line 26](../../../../../../../backend/src/sro/application/lookup/run_lookups.py#L26): Docstring

> What one lookup came back with.

## `Looked`, [line 31](../../../../../../../backend/src/sro/application/lookup/run_lookups.py#L31): Note on the line above

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

## `Looked`, [line 33](../../../../../../../backend/src/sro/application/lookup/run_lookups.py#L33): Note on the line above

Code: `detail: str = ""`

> Why not, when not. Kept in the extension's own words -- `no_tab_for_origin`
> is a different problem from `unreachable`, and flattening them to "failed"
> throws away the one thing that says which.

## `RunLookups`, [line 46](../../../../../../../backend/src/sro/application/lookup/run_lookups.py#L46): Docstring

> Execute a plan against one browser.

## `_shut`, [line 176](../../../../../../../backend/src/sro/application/lookup/run_lookups.py#L176): Docstring

> Whether this failed because nobody has that system open.

## `RunLookups.execute`, [line 51](../../../../../../../backend/src/sro/application/lookup/run_lookups.py#L51): Docstring

> `within` is the caller's budget, because the callers have different
> ones: a lookup somebody asked for may take as long as the slowest
> warehouse, and a lookup inside a conversation turn may not. See
> `K_WHILE_TALKING`.

## `RunLookups._reopened`, [line 125](../../../../../../../backend/src/sro/application/lookup/run_lookups.py#L125): Docstring

> Open the system this command could not find, and ask it once more.
>
> Once. A second failure is a system that is open and still would not
> answer, which is a different problem and not one another tab fixes.

## `RunLookups.execute`, [line 74](../../../../../../../backend/src/sro/application/lookup/run_lookups.py#L74): Comment (debt)

Code: `gestures = list(await uow.gestures.gestures_for(ctx.tenant_id))`

> Every gesture, scanned per lookup. The store holds hundreds per
> tenant, so this is cheaper than the round trip that would fetch
> one call.
> ponytail: whole-store scan; a `calls_for_path` query if a tenant's
> capture outgrows memory.

## `RunLookups._one`, [line 113](../../../../../../../backend/src/sro/application/lookup/run_lookups.py#L113): Comment

Code: `origin = system_of(address.url)`

> A screen takes two commands: put the page up, then photograph it.
> Separate because the second one is the one that needs the operator's
> permission to take their screen, and a navigate that worked is worth
> saying so even when the picture is refused.
> Scheme and host, which is what the extension matches a tab on --
> `hosts.origin_of` answers the host alone, and that is the rule for
> deciding whether two urls are one SYSTEM, not for finding a tab.

## `RunLookups._one`, [line 117](../../../../../../../backend/src/sro/application/lookup/run_lookups.py#L117): Comment

Code: `moved = await self._reopened(ctx, device, address, "navigate", going, within)`

> The tab `tab.open` makes is already ON the address, so the
> navigate that follows is a no-op that confirms it -- cheaper than
> a second code path, and it keeps the failure shape identical
> whether the operator had the system open or not.

## `_looked`, [line 171](../../../../../../../backend/src/sro/application/lookup/run_lookups.py#L171): Comment

Code: `read=read_answer(body, url=address.url) if isinstance(body, str) else None,`

> `url` so the counting is honest: `limit=50` in the query and `50` in
> the envelope are the same fact about what we ASKED for, and a total
> that merely echoes our own paging is not a total.
