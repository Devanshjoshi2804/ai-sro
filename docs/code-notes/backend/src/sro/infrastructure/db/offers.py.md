# Notes for `backend/src/sro/infrastructure/db/offers.py`

Comments and docstrings moved out of [`backend/src/sro/infrastructure/db/offers.py`](../../../../../../../backend/src/sro/infrastructure/db/offers.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/infrastructure/db/offers.py#L1): Docstring

> What was offered on Postgres, and what a sentence at the chat door cost.
>
> The rules here are the rig's -- ``record_offer`` and ``counsel``'s two selects
> in ``rig/offers.py``, the ``chats`` insert and select in ``rig/api.py`` -- and
> they were SQLite there. What had to be translated rather than copied is marked
> where it happens:
>
> * ``ORDER BY at DESC, rowid DESC`` becomes ``ORDER BY at DESC, seq DESC`` on an
>   identity column. SQLite's ``rowid`` is a real column with a real order;
>   Postgres promises nothing at all about the order of two rows that tie on
>   ``at``, and several offers of one job routinely carry the same second because
>   the extension sends whole-second ISO instants. The three newest offers of a
>   browser decide whether a job is rested, so the tie has to break on arrival.
> * The rig kept every clock as text and compared it as text. ``at`` is
>   ``timestamptz`` here because both indexes order on it and an offset-less
>   string sorts beside an offset-bearing one with neither being wrong. The
>   records still carry ISO strings, so this converts on both edges.
> * ``k > 0`` stays in the query rather than moving to ``counsel_over``. An
>   arrival nudge is not evidence either way, and the domain says so, but keeping
>   it out is what lets ``LIMIT`` mean what it says: a window of ten that a run of
>   nudges could fill is not a window of ten offers.
>
> The row-to-record mapping lives here rather than in ``mappers.py``: a
> repository's mapping belongs with the repository, and neither shape is read by
> anything else.

## module, [line 16](../../../../../../../backend/src/sro/infrastructure/db/offers.py#L16): Note on the line above

Code: `_NEWEST_FIRST = (OfferRow.at.desc(), OfferRow.seq.desc())`

> One clause, read by both selects rather than written out twice.
>
> The window and the audit ask the same question -- newest first, arrival
> breaking the tie -- and only ``since`` can be made to prove it: for the
> window's own answer a pure arrival tiebreak *is* reverse-insertion order, so no
> plant can tell a missing ``seq`` apart from the row order Postgres happened to
> hand back. Written out twice, deleting the window's copy left both the contract
> and the integration suites green. Shared, the test that does bite guards both.

## `SqlChatRepository`, [line 97](../../../../../../../backend/src/sro/infrastructure/db/offers.py#L97): Docstring

> The bill for the chat door, and nothing else it read.
>
> There is no column for the sentence and there is no method that would write
> one. The row exists for the cap and the spend line; the words are an
> operator's about their own warehouse.

## module, [line 12](../../../../../../../backend/src/sro/infrastructure/db/offers.py#L12): Comment

Code: `from sro.domain.skill.offers import OfferRow as OfferWindow`

> The domain's three-column window row, aliased apart from the table of the
> same name. ``counsel_over`` reads k, fate and at and has no use for the rest.

## `SqlOfferRepository.record`, [line 24](../../../../../../../backend/src/sro/infrastructure/db/offers.py#L24): Comment

Code: `self._session.add(`

> Plain insert, no upsert: an offer is a thing that happened once, and
> its id is minted where it is made. Two offers of one job in one second
> are two rows, which is why ``seq`` exists.

## `SqlOfferRepository.fates`, [line 57](../../../../../../../backend/src/sro/infrastructure/db/offers.py#L57): Comment

Code: `query = (`

> No ``k > 0`` and no limit, unlike the window above: this is the tally
> of what the job was offered for and what came of it, and an arrival
> nudge is still an offer that was made.

## `SqlOfferRepository.since`, [line 66](../../../../../../../backend/src/sro/infrastructure/db/offers.py#L66): Comment

Code: `query = (`

> The whole offer, and every one of them: the audit asks what this
> tenant's browsers were shown, so neither the window's ``k > 0`` nor
> its limit applies. The ``seq`` tiebreak does, for the same reason it
> does there -- several offers routinely carry one second.

## `SqlChatRepository.since`, [line 121](../../../../../../../backend/src/sro/infrastructure/db/offers.py#L121): Comment

Code: `.order_by(ChatRow.at.desc(), ChatRow.id.desc())`

> The id breaks the tie, as `seq` does for offers: `at` comes off
> the record rather than off a server clock, so two readings can
> carry one instant and there is no arrival column to fall back on.
