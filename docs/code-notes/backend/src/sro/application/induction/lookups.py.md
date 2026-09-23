# Notes for `backend/src/sro/application/induction/lookups.py`

Comments and docstrings moved out of [`backend/src/sro/application/induction/lookups.py`](../../../../../../../backend/src/sro/application/induction/lookups.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/induction/lookups.py#L1): Docstring

> Turning a remembered id into a lookup somebody can actually answer.
>
> The diff finds that both demonstrations sent one address id. Asking about it is
> better than replaying it and worse than not needing to ask: the operator picked
> that address off a screen, and the screen is in the recording.
>
> So the record they picked is found in the listing that showed it, and the
> fields beside the id are examined. Two things can make a field usable, and
> either is enough.
>
> The first is that the write sent it: the listing carried the field, the write
> sent the same value, and no other record in the collection had that value. The
> last one is what makes it a way of finding the record rather than a fact about
> it -- there are forty addresses in Ontario and one called APPLIANCE HAUS.
>
> The second is that the operator searched by it. A read filtered on
> `addressName` is the demonstration saying, in the application's own words, how
> a human finds this record here. That evidence beats uniqueness, and it is the
> only evidence there is for a value that was picked rather than typed: the
> create sends `codAddressId` and nothing else off that record, so the write-sent
> rule can never be satisfied for it. Where both apply the searched column leads,
> because it is the one a person was seen using.
>
> Where no such field exists the id stays a question for a human, because a
> lookup that cannot identify one record is a lookup that picks the wrong one.

## module, [line 20](../../../../../../../backend/src/sro/application/induction/lookups.py#L20): Note on the line above

Code: `MOST_FIELDS = 3`

> How many of the record's fields to show in the list.
>
> Not one. Four addresses in this warehouse share the line the operator picked
> by, and a dropdown of four identical rows is a coin toss -- the name and the
> street beside it are what tell them apart.

## `Wanted`, [line 24](../../../../../../../backend/src/sro/application/induction/lookups.py#L24): Docstring

> A value the skill will ask for, and the step that sent it.
>
> A constant the operator chose twice and a value that differed between
> doings arrive here as the same thing, because they are the same thing: an
> id nobody memorised, picked off a screen the recording still holds. Whether
> the skill will vary it is a question about the parameter, not about where
> its value comes from.

## `Wanted`, [line 26](../../../../../../../backend/src/sro/application/induction/lookups.py#L26): Note on the line above

Code: `values: tuple[str, ...]`

> What was picked. One value for a constant; one per run for a value that
> varied, every one of which must be explainable or this is not one list.

## `PlannedLookup`, [line 32](../../../../../../../backend/src/sro/application/induction/lookups.py#L32): Docstring

> A field that was a dropdown, and the call that filled it.

## `PlannedLookup`, [line 34](../../../../../../../backend/src/sro/application/induction/lookups.py#L34): Note on the line above

Code: `request: CapturedRequest`

> The listing the operator picked from, as the demonstration fetched it.

## `PlannedLookup`, [line 37](../../../../../../../backend/src/sro/application/induction/lookups.py#L37): Note on the line above

Code: `shown: str`

> What the picked record looked like on the screen, for the reviewer.

## `filtered_on`, [line 40](../../../../../../../backend/src/sro/application/induction/lookups.py#L40): Docstring

> The column this read was filtered on, where exactly one was.
>
> The operator typed a name into a dialog and the application turned it into
> `query=[{"column":"addressName","operator":"EQ","value":"test"}]`. That URL
> is the only place in the evidence that says how a human finds this record
> in this system -- better than any field that merely happens to be unique,
> because a person was seen using it.
>
> ``None`` for two columns as well as none: two answers about how a record is
> found is not evidence, and the rule is that disagreement refuses.

## `plan`, [line 45](../../../../../../../backend/src/sro/application/induction/lookups.py#L45): Docstring

> A lookup for every chosen id the demonstration can explain.
>
> ``run_a``/``run_b`` are the paired steps, which is what a wanted value's
> index refers to. ``others`` is every other doing the candidate holds --
> searched for the listing too, since the two aligned doings can hold nothing
> but the write. ``screens`` is the whole recording: the click that chose the
> record is usually one of the steps alignment dropped as exploration, and
> that click is the best evidence there is about how a person finds it.

## `_search_column`, [line 136](../../../../../../../backend/src/sro/application/induction/lookups.py#L136): Docstring

> The column the live query may be re-aimed at, where one was proved.
>
> `Options.search` is what `as_a_filter` swaps into the demonstrated filter at
> run time, so a column the demonstration never filtered on sends a real query
> to the warehouse system filtered on a column nothing showed that endpoint
> accepting -- ADR 004's inference on top of evidence, with a live request
> behind it. Only the searched column may go here, and `Options.search` is
> optional for exactly that reason: without one the page is fetched whole and
> narrowed in the console, which is slower and true.
>
> The exception is a listing that carries no filter to re-aim. `as_a_filter`
> returns nothing there, `choices._searched` fetches the raw URL, and this
> column is read by nobody -- the pre-existing shape where the whole page is
> narrowed here, which this is not the change that fixes.

## `_seen_on_screen`, [line 144](../../../../../../../backend/src/sro/application/induction/lookups.py#L144): Docstring

> Whether the demonstration shows a human handling this value.
>
> Typed into a field, or the text of a control they clicked. Compared with
> whitespace flattened, because a dropdown renders `UNIT  7  BUILDING A` as
> `UNIT 7 BUILDING A` and those are the same address.

## `_reads_in`, [line 164](../../../../../../../backend/src/sro/application/induction/lookups.py#L164): Docstring

> Every read these frames made, with the records it returned.
>
> No bound and no judgement: this is what the application answered, which is
> all a question about the data itself needs.

## `_reads`, [line 173](../../../../../../../backend/src/sro/application/induction/lookups.py#L173): Docstring

> The reads that are evidence of what the operator did, with their records.
>
> One definition, because two rules used to have two: which read showed the
> record and which column a person searched by are the same question --
> what did they do, and in what order, before the write -- and answering it
> from different halves of the evidence is how they drift apart. How wide the
> collection is is *not* that question, and is deliberately not asked here.
>
> A read is evidence when it did not change anything, was not the browser
> talking to itself on a timer, and happened before the write. ``step_index``
> bounds the aligned runs, where a step index means something. In the other
> doings it does not, so the bound is that doing's own first mutating request:
> the same rule -- before the write -- said without reference to an alignment
> those frames were never part of.

## `_holds`, [line 183](../../../../../../../backend/src/sro/application/induction/lookups.py#L183): Docstring

> Whether this read returned a record the operator picked.

## `_listing_of`, [line 187](../../../../../../../backend/src/sro/application/induction/lookups.py#L187): Docstring

> The read that showed this value, and the records it returned.
>
> Searched across every doing the candidate holds, not only the two that
> aligned. The pair that aligns is chosen for being the same task twice, and
> that is a different question from which doing happened to have the dialog
> open -- in the evidence this was written against, the two aligned doings
> hold one call each and the address listing is in neither.
>
> Where the same collection was read both unfiltered and filtered, the
> filtered read is the listing even though the page came first -- and it
> usually does, because the dialog opens on page one and only then does
> anybody type. `Options.url` is the call the dropdown re-issues, and
> `as_a_filter` re-aims it by replacing the terms of a filter the URL already
> carries. An unfiltered page has no terms to replace, so `as_a_filter`
> returns nothing, the raw URL is fetched, and typing in the dropdown narrows
> nothing: a `search` column read off the filtered read, pointed at a URL that
> cannot use it.
>
> Only where the column that read was filtered on is a field of the record
> that came back, though. A read filtered on `nickname` returning a row that
> has no `nickname` proves nothing about the record the operator picked, and
> promoting it makes `as_a_filter` succeed with some other column riding a
> filter shape the demonstration built for that one. The unfiltered page is
> the honest listing there: it narrows nothing at run time and says so.

## `_picked`, [line 205](../../../../../../../backend/src/sro/application/induction/lookups.py#L205): Docstring

> The record holding this value, and the field of it that holds it.

## `_identifying_column`, [line 213](../../../../../../../backend/src/sro/application/induction/lookups.py#L213): Docstring

> The column this read was filtered on, where the picked record has it.
>
> The same test `_plan_one` puts a searched column through before it will use
> one: filtered on one column, that column is a field of the record with
> something in it, and it is not the id the lookup exists to spare anybody.

## `_searched_column`, [line 224](../../../../../../../backend/src/sro/application/induction/lookups.py#L224): Docstring

> The column the doings searched these records by, where they agree.
>
> Every doing that filtered at all is asked. A doing that scrolled instead is
> silent rather than dissenting -- it has no opinion about how the record is
> found, and silence is not disagreement. Two doings naming different columns
> is disagreement, and plans nothing.
>
> Only reads of the collection the record came from get a vote. A carriers
> listing filtered on `name` happens to carry `codAddressId`, and letting it
> speak would re-aim the ADDRESS query at a column only the CARRIERS endpoint
> was ever shown to accept.
>
> Asked about every value, not only the first: two doings that picked
> different records only ever disagree through the reads that found them, and
> a doing's read holds its own doing's record, never the other's.

## `_same_collection`, [line 240](../../../../../../../backend/src/sro/application/induction/lookups.py#L240): Docstring

> Two reads of the same thing. The path is the collection; the query is
> which slice of it somebody happened to ask for.

## `_sent_by_the_write`, [line 257](../../../../../../../backend/src/sro/application/induction/lookups.py#L257): Docstring

> The write's own payload, flattened to field name and value.
>
> A field the write does not send is not part of how the operator identified
> the record -- it is something the screen happened to show them.

## `_plan_one`, [line 72](../../../../../../../backend/src/sro/application/induction/lookups.py#L72): Comment

Code: `reads = [_listing_of(runs, value, wanted.step_index) for value in wanted.values]`

> Every value has to be explainable, and by the same list. A value that
> varied between doings was picked twice, once per doing, and a dropdown
> can only offer both if both came off one collection: two ids found in
> two different endpoints are two lists, and no single lookup answers them.

## `_plan_one`, [line 87](../../../../../../../backend/src/sro/application/induction/lookups.py#L87): Comment

Code: `listing_url = request.url`

> A filtered read returns one row, and every field on one row is trivially
> the only one of its kind. What tells records apart is what the collection
> looks like unfiltered, so uniqueness is judged against the widest read of
> it any doing made -- but only among the reads that hold the record itself.
> Page two of a listing is wider and does not contain the picked row, so
> judging against it makes every field on that row unique nowhere and
> rejects the lot. Where there is no wider read the narrow result stands:
> the operator picks from the dropdown, so an ambiguous label costs a second
> look, not a wrong write.
>
> Every read counts here, including ones after a write. How many addresses
> are in BURLINGTON is a fact about the collection, not about what the
> operator did in what order, and the grid refreshing after the save is a
> perfectly good witness to it. Bounding this the way the evidence questions
> are bounded hides the duplicates and calls a shared value unique -- which
> is the exact mistake judging against the widest read exists to prevent.

## `_plan_one`, [line 112](../../../../../../../backend/src/sro/application/induction/lookups.py#L112): Comment

Code: `proven = [(column, str(picked[column]))]`

> An operator's own search names the column. It goes first and it goes
> in whether or not the write sends it: the write sends the id and
> nothing else off this record, so requiring the write to send the
> identifying field is requiring the impossible for every value that
> was picked rather than typed.

## `_plan_one`, [line 75](../../../../../../../backend/src/sro/application/induction/lookups.py#L75): Comment

Code: `return None`

> Nothing on that screen tells one record from another in words. The id
> stays a question rather than becoming a lookup that guesses.

## `_plan_one`, [line 118](../../../../../../../backend/src/sro/application/induction/lookups.py#L118): Comment

Code: `on_screen = [pair for pair in usable if _seen_on_screen(screens, pair[1])]`

> What the operator actually clicked, where the recording shows it. They
> chose that address by reading "UNIT 7 BUILDING A" off a dropdown, and a
> field a human was seen using beats one that merely happens to be unique.
>
> Only among the fields nothing proved, though. This is a heuristic about
> what reads well in a dropdown, and a searched column is evidence about
> how the record is found. So the searched one stays in front and this
> orders what is left.
