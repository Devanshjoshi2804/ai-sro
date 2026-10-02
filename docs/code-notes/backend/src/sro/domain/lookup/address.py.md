# Notes for `backend/src/sro/domain/lookup/address.py`

Comments and docstrings moved out of [`backend/src/sro/domain/lookup/address.py`](../../../../../../../backend/src/sro/domain/lookup/address.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/domain/lookup/address.py#L1): Docstring

> Where a planned lookup actually goes on the wire.
>
> A plan names a knowledge key -- `/data/WM/wm/suppliers`, or the route hash
> `#wm.config/wm.config.partners.suppliers////` -- and neither is something a
> browser can open. The knowledge base holds no host: `api-endpoints.json`
> catalogues paths, and a deployment is whatever host that tenant's operator
> signs into.
>
> So an address is RESOLVED FROM WHERE THIS DEPLOYMENT HAS ALREADY BEEN. The
> same evidence discipline as everything else here: a lookup reaches a host
> because a gesture was recorded against that host, never because a host was
> assembled out of parts. Two consequences worth stating, because both look like
> limitations until the alternative is written down:
>
> **A screen is a url somebody was on, not a url built from a route.** The real
> page is `.../portal/page?libraryContext=f4d675...&siteId=SG&menu=wm.config
> #wm.config.partners.suppliers////`, and `libraryContext` is a session token
> this side cannot invent. Assembling `origin + hash` produces a url that loads
> the shell and not the screen. Reusing the recorded one is the only honest
> option, and when its token has expired the answer says the page did not come
> up -- which is a true answer, where a confidently wrong url is not.
>
> **A read may not write, checked again here.** The planner cannot express a
> write, and this refuses anything that is not a recorded GET. Two belts,
> because this is the half that reaches somebody's warehouse.

## `Address`, [line 18](../../../../../../../backend/src/sro/domain/lookup/address.py#L18): Docstring

> One lookup, as something the extension can be asked to do.

## `Address`, [line 21](../../../../../../../backend/src/sro/domain/lookup/address.py#L21): Note on the line above

Code: `live_headers: tuple[str, ...] = ()`

> Names the extension reads off the live page. The recorder strikes these
> out at the boundary, so what is stored is the marker's own text; the tab
> the operator is signed into has the real value.

## `Address`, [line 23](../../../../../../../backend/src/sro/domain/lookup/address.py#L23): Note on the line above

Code: `struck: tuple[str, ...] = ()`

> Struck out, with no live source. Not an error on its own -- the call
> goes without them and the system may well answer -- but the first thing to
> look at when it does not.

## `Address`, [line 25](../../../../../../../backend/src/sro/domain/lookup/address.py#L25): Note on the line above

Code: `seen_at: float | None = None`

> When the evidence this address came from was recorded. A month-old
> session still names the right host; its session token may be spent.

## `Address`, [line 27](../../../../../../../backend/src/sro/domain/lookup/address.py#L27): Note on the line above

Code: `page: str = ""`

> The page the addressed GET was made from: its gesture's `page_url`, else its
> `url`. A lookup opens its Steel tab there, so the account's session has made
> that page's own requests (the live headers come from them), and a GET the
> system refuses for any reason but auth is read off that page instead. Empty
> for a screen, whose `url` already is the page.

## `address_for`, [line 34](../../../../../../../backend/src/sro/domain/lookup/address.py#L34): Docstring

> Where this lookup goes, or nothing if this deployment has not been there.

## `_call_address`, [line 41](../../../../../../../backend/src/sro/domain/lookup/address.py#L41): Docstring

> The newest successful GET of this exact path, re-aimed at the question.
>
> Newest because a session moves: the last call that worked carries the
> headers the system wanted most recently. Exact path, because a prefix match
> would answer `/suppliers` with `/suppliers/count` -- a different question
> with a plausible-looking answer, which is the failure this whole module is
> arranged against.

## `_call_address`, [line 56](../../../../../../../backend/src/sro/domain/lookup/address.py#L56): Note

Code: `key=lambda one: (-len(_narrowing(one[1].url, lookup)), one[1].started_at or 0.0),`

> "Newest" is among the reads with the fewest things narrowing them. A recorded GET
> may be an operator's search (`query=[{"property":"code","value":"X"}]`), and a list
> read through it holds a match or nothing -- "No, it does not exist" off that is a
> false answer that invites a duplicate. So the recorded read with nothing narrowing
> it wins, and `Address.narrowed` names what still narrows the chosen one: every
> non-empty query parameter the lookup did not itself name (an empty `query=[]` is the
> unfiltered form). Nothing is stripped from the url: which parameter is a filter and
> which a scope (`siteId`) or a requirement is not written in a recording, and a scope
> removed reads another list. A narrowed read answers what it holds, never "No".

## `_screen_address`, [line 70](../../../../../../../backend/src/sro/domain/lookup/address.py#L70): Docstring

> The newest page url whose fragment names this route.
>
> Matched on the route name alone. The catalogue writes
> `#wm.config/wm.config.partners.suppliers////` -- the menu and the route --
> where the application's url carries `menu=wm.config` in the query and only
> `#wm.config.partners.suppliers////` after the hash. One screen, spelled
> differently by the two sides, so the comparison is over the part they
> agree on.

## `_route_name`, [line 113](../../../../../../../backend/src/sro/domain/lookup/address.py#L113): Docstring

> A route as the screen it names, however either side spells it.
>
> The catalogue writes `#<menu>/<route>////`; the application's url carries
> the menu in its query and only `#<route>////` after the hash. So the last
> non-empty segment is the screen in both spellings -- the leading `#` and
> the menu are the catalogue's, and the trailing separators are the
> application's own padding for parameters the screen was opened without.

## `_with_params`, [line 118](../../../../../../../backend/src/sro/domain/lookup/address.py#L118): Docstring

> The recorded url, asking the question that was planned.
>
> The recorded query is a previous operator's question -- `siteId=SG` from
> whenever this was captured -- and the plan's parameters are this one's, so
> the plan wins on any name they share. Names it does not mention are kept:
> dropping `libraryContext` or a paging parameter the system requires turns
> a working call into a 400.
