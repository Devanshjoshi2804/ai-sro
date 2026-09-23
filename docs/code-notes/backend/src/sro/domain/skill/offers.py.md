# Notes for `backend/src/sro/domain/skill/offers.py`

Comments and docstrings moved out of [`backend/src/sro/domain/skill/offers.py`](../../../../../../../backend/src/sro/domain/skill/offers.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/domain/skill/offers.py#L1): Docstring

> What was offered, and what became of it.
>
> Written by the extension, which made the offer, over `POST /v1/offers`. Read
> per job, when its shape is served: the labelled record of whether recognition
> was right. Offers that kept diverging move the job's threshold past the
> gesture they diverged at; offers refused three times running rest the job for
> a day.
>
> The repository queries that gather `OfferRow`s -- `record_offer`'s insert and
> `counsel`'s two selects, in the rig at `new_agent_arch/src/rig/offers.py` --
> move to the application layer; this module keeps only the pure rules that
> decide what a job's history means.

## module, [line 8](../../../../../../../backend/src/sro/domain/skill/offers.py#L8): Note on the line above

Code: `K_OFFER_AFTER = 2`

> How many gestures a tail must match before a job is offered, unless its
> offers have said otherwise. The extension holds the same value under the same
> name in `recognise.js`; a served shape's `offer_after` is what overrides it.

## module, [line 10](../../../../../../../backend/src/sro/domain/skill/offers.py#L10): Note on the line above

Code: `K_WINDOW = 10`

> How many of a job's newest offers are read. Older ones were made against a
> threshold that has since moved, or against a page that has.

## module, [line 12](../../../../../../../backend/src/sro/domain/skill/offers.py#L12): Note on the line above

Code: `K_ENOUGH = 3`

> Offers before their fates are read at all: in a row, from one browser, to
> rest a job for that browser; in the window, from every browser, to move its
> threshold. A single dismissal is a mood; three running is an answer.

## module, [line 14](../../../../../../../backend/src/sro/domain/skill/offers.py#L14): Note on the line above

Code: `K_QUIET_HOURS = 24`

> How long a job refused `K_ENOUGH` times running is left alone on the browser
> that refused it. A rest, not a retirement: the job is still proven, the next
> browser is still offered it, and tomorrow's shift on this one may want it.

## module, [line 16](../../../../../../../backend/src/sro/domain/skill/offers.py#L16): Note on the line above

Code: `REFUSED = ("dismissed", "did_it")`

> The two fates that mean the offer was understood and not wanted.

## module, [line 18](../../../../../../../backend/src/sro/domain/skill/offers.py#L18): Note on the line above

Code: `FATES = ("accepted", "dismissed", "did_it", "expired", "diverged")`

> accepted: Yes was pressed and a run started. dismissed: No thanks. did_it:
> the operator made the workflow's write themselves while it asked. expired: the
> nudge's lifetime passed. diverged: the tail stopped matching the prefix.

## `new_offer_id`, [line 21](../../../../../../../backend/src/sro/domain/skill/offers.py#L21): Docstring

> The shape every other id in the backend has, and enough randomness that
> two offers made in the same second cannot collide. The rig minted this
> inside its ``record_offer``; here the offer is a record before it is a row,
> so whoever builds it mints the id.

## `fate_of`, [line 25](../../../../../../../backend/src/sro/domain/skill/offers.py#L25): Docstring

> `name` if it is a fate an offer can have; raised, named, otherwise.

## `OfferRow`, [line 32](../../../../../../../backend/src/sro/domain/skill/offers.py#L32): Docstring

> The three columns `counsel_over` reads, and no more: a whole `Offer` is
> a row the rules have no use for.

## `Offer`, [line 39](../../../../../../../backend/src/sro/domain/skill/offers.py#L39): Docstring

> One offer the extension made from a recognised prefix, and its fate.

## `Counsel`, [line 52](../../../../../../../backend/src/sro/domain/skill/offers.py#L52): Note on the line above

Code: `offer_after: int`

> The k the extension should offer this job at.

## `Counsel`, [line 53](../../../../../../../backend/src/sro/domain/skill/offers.py#L53): Note on the line above

Code: `quiet_until: str | None`

> When the asking browser may be offered the job again; None when now.

## `clamped`, [line 63](../../../../../../../backend/src/sro/domain/skill/offers.py#L63): Docstring

> The browser's clock, never ahead of the rig's: parsed, made aware,
> and capped at `now`. `counsel_over` reads the newest offers and rests a
> job a day after the last refusal, and a browser a year fast would
> otherwise own the window, and the rest, for a year.

## `counsel_over`, [line 69](../../../../../../../backend/src/sro/domain/skill/offers.py#L69): Docstring

> What a job's newest offers say about offering it again.
>
> `window`: the tenant's newest `K_WINDOW` offers of the job with k > 0,
> newest first. `newest_for_device`: the asking browser's newest `K_ENOUGH`
> of the same, newest first; empty when no browser is named.
>
> Later: at least `K_ENOUGH` offers in `window` and half or more of them
> diverged, so the job is offered one gesture past the deepest k it
> diverged at. Recognition is a property of the job, not of who was asked,
> so every browser's offers count. The threshold only ever moves up here;
> it comes back down as the diverged offers age out of the window.
>
> Quiet: `newest_for_device` has exactly `K_ENOUGH` offers of this job, all
> refused, and the last under `K_QUIET_HOURS` ago. Any other fate in
> between -- accepted, expired, diverged -- breaks the run: an offer the
> operator did not answer is not one they turned down. With no browser named
> there is no rest to report: `newest_for_device` is empty, and a job nobody
> can be said to have refused is offered.
>
> Arrival nudges (k = 0) are excluded by the caller's query and are neither
> kind of evidence -- "you have been here before" with nothing typed is not
> a recognition that diverged and not an offer anyone turned down. Handed
> them anyway, this reads them like any other row; keeping them out is the
> repository's `k > 0`.
