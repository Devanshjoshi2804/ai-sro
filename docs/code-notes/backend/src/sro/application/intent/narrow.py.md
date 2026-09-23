# Notes for `backend/src/sro/application/intent/narrow.py`

Comments and docstrings moved out of [`backend/src/sro/application/intent/narrow.py`](../../../../../../../backend/src/sro/application/intent/narrow.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/intent/narrow.py#L1): Docstring

> Asking the system a question nobody taught it, out of what it already knows.
>
> "Show me one supplier in detail TESTSUPPLIERSRO" used to return all 239
> suppliers: retrieval found the taught read, replayed it exactly as demonstrated
> and dropped the only word in the sentence that said which supplier. That is a
> replay engine, not a system that understands anything.
>
> Everything needed to do better is already here and was going unused:
>
> - the taught read proves the endpoint, its session and its filter dialect;
> - the knowledge base's field dictionary says what that entity's fields are
>   called, in the system's own vocabulary and the screen's -- `supplierNumber`
>   is labelled "Supplier";
> - a model can say which of those fields a value in a sentence belongs to.
>
> So the model chooses between fields that exist rather than inventing one, the
> request is composed in the dialect a real 200 proved, and what comes back is
> this warehouse answering the question that was actually asked.

## module, [line 21](../../../../../../../backend/src/sro/application/intent/narrow.py#L21): Note on the line above

Code: `MOST_FIELDS = 30`

> How many fields the model chooses between. A dictionary of everything is a
> prompt nobody can afford and a choice nobody can check.

## `value_key`, [line 17](../../../../../../../backend/src/sro/application/intent/narrow.py#L17): Docstring

> Where the answer to "what does this word mean here" is kept.

## `NeedToAsk`, [line 25](../../../../../../../backend/src/sro/application/intent/narrow.py#L25): Docstring

> A word in the sentence that names a value nothing here can place.
>
> "Which suppliers are used for parcel" -- parcel is plainly a value, and
> nothing in the field dictionary says which field it belongs to. Listing
> every supplier instead answers a wider question and calls it an answer, so
> the honest move is to ask, once, and remember what the operator says.

## `Narrowed`, [line 35](../../../../../../../backend/src/sro/application/intent/narrow.py#L35): Docstring

> One request, composed rather than taught.

## `Narrowed`, [line 39](../../../../../../../backend/src/sro/application/intent/narrow.py#L39): Note on the line above

Code: `because: tuple[str, ...]`

> Where each part came from. A derived request cites its evidence or it is
> a guess with a URL.

## `_mentions`, [line 332](../../../../../../../backend/src/sro/application/intent/narrow.py#L332): Docstring

> Whether this documentation is about that word, rather than containing it.
>
> Substrings are not mentions: "all" sits inside `allowMultipleOpenContainers`,
> and matching it there made "list all transport modes" ask which field the
> word "all" names. A word is mentioned when it appears as a word.

## `_the_read`, [line 336](../../../../../../../backend/src/sro/application/intent/narrow.py#L336): Docstring

> The call this skill reads with, if it has one nothing has to fill in.

## `NarrowARead.for_utterance`, [line 55](../../../../../../../backend/src/sro/application/intent/narrow.py#L55): Docstring

> The same read, asked about one record.
>
> ``None`` when the sentence named nothing to narrow by, and then the
> taught skill runs as it always did. A :class:`NeedToAsk` when it named
> something and nothing here can place it -- which is a question, not a
> reason to answer something wider.

## `NarrowARead._place`, [line 122](../../../../../../../backend/src/sro/application/intent/narrow.py#L122): Docstring

> Work out which field an unplaceable word belongs to, or ask.

## `NarrowARead._as_the_records_have_it`, [line 260](../../../../../../../backend/src/sro/application/intent/narrow.py#L260): Docstring

> What this word looks like in the data, or what the data does hold.
>
> A word in a sentence is rarely what a WMS stores: "parcel" is a flag
> somewhere, spelled `Y` or `true` or `PARCEL`. Asking the system for a
> value it has never stored returns nothing and reads as "there are none"
> -- so the column's own values are read first, and if the word is not
> among them, they become the options for one question.

## `NarrowARead._settled`, [line 281](../../../../../../../backend/src/sro/application/intent/narrow.py#L281): Docstring

> What somebody already said this word means here.

## `NarrowARead._mentioning`, [line 288](../../../../../../../backend/src/sro/application/intent/narrow.py#L288): Docstring

> Fields the catalogue documents as carrying this value.

## `NarrowARead._term_shape`, [line 299](../../../../../../../backend/src/sro/application/intent/narrow.py#L299): Docstring

> How this system writes a filter term, taken from one it answered.
>
> The supplier screen sends `query=[]`; the address screen sends
> `query=[{"column":…,"operator":"EQ","value":…}]`. Same deployment, same
> dialect -- and reading it off a call that got a 200 is the difference
> between composing a request and guessing at an API.

## `NarrowARead._fields`, [line 313](../../../../../../../backend/src/sro/application/intent/narrow.py#L313): Docstring

> This entity's fields, as the system and the screen name them.

## `NarrowARead.for_utterance`, [line 78](../../../../../../../backend/src/sro/application/intent/narrow.py#L78): Comment

Code: `extraction = await self._parser.extract(`

> The model picks between fields that exist. It cannot name one that
> does not, because what it returns is checked against this list.

## `NarrowARead.for_utterance`, [line 96](../../../../../../../backend/src/sro/application/intent/narrow.py#L96): Comment

Code: `return await self._place(`

> The sentence named a value the dictionary has no field for. Where
> somebody has said what such a word means, that answer is used;
> where the catalogue itself mentions it under exactly one field,
> that is evidence; otherwise it is asked.

## `NarrowARead.for_utterance`, [line 107](../../../../../../../backend/src/sro/application/intent/narrow.py#L107): Comment

Code: `shape = await self._term_shape(ctx, system=system)`

> The endpoint may take a filter it was sent nothing in. What a term
> looks like then comes from a call on this system that did carry one.

## `NarrowARead.for_utterance`, [line 68](../../../../../../../backend/src/sro/application/intent/narrow.py#L68): Comment

Code: `return None`

> This endpoint never showed us a filter. Inventing one is the
> confident wrong request this whole design refuses to make.

## `NarrowARead._place`, [line 135](../../../../../../../backend/src/sro/application/intent/narrow.py#L135): Comment

Code: `continue`

> Nothing here has ever heard of this word. "Used" is not a
> value anybody can place, and asking which field it names
> produces a question nobody can answer either.

## `NarrowARead._place`, [line 141](../../../../../../../backend/src/sro/application/intent/narrow.py#L141): Comment

Code: `field, held = settled.split("=", 1)`

> Already settled down to the value the records actually carry.

## `NarrowARead._place`, [line 155](../../../../../../../backend/src/sro/application/intent/narrow.py#L155): Comment

Code: `placed = await self._as_the_records_have_it(`

> Their answer, not our dictionary: an operator saying "parcel
> means smallPackageFlag" outranks anything the catalogue
> happens to list under the entity, which is why they were
> asked in the first place.

## `NarrowARead._place`, [line 175](../../../../../../../backend/src/sro/application/intent/narrow.py#L175): Comment

Code: `return NeedToAsk(`

> The field is settled; what the value looks like in the
> data is not. Asking for a word this system has never
> stored would return nothing and call it an answer.

## `NarrowARead._place`, [line 189](../../../../../../../backend/src/sro/application/intent/narrow.py#L189): Comment

Code: `return NeedToAsk(`

> Settled onto a field this read does not return. Saying so
> beats both answering something wider and asking a question
> whose answer would change nothing.

## `NarrowARead._place`, [line 217](../../../../../../../backend/src/sro/application/intent/narrow.py#L217): Comment

Code: `choices = tuple(mentions or fields)[:5]`

> Either nothing mentions it, or several do -- and choosing between
> several is the guess this exists to avoid.

## `NarrowARead._place`, [line 225](../../../../../../../backend/src/sro/application/intent/narrow.py#L225): Comment

Code: `question=f"Which field of {entity.replace('_', ' ')} does {word!r} name?",`

> The question, and only the question. The candidates are
> buttons directly underneath it, and reciting them inside the
> sentence made a two-line question forty words long -- three of
> those stacked filled the screen and none of them could be read
> at a glance. What each one is called in the catalogue goes to
> the reasons, which is where a reader looks for detail.

## `NarrowARead._mentioning`, [line 296](../../../../../../../backend/src/sro/application/intent/narrow.py#L296): Comment

Code: `if entry.key.isidentifier() and _mentions(entry.title or entry.key, word)`

> The label counts as documentation: "Parcel (smallPackageFlag)" is
> the catalogue saying what that flag is, in the words on the screen.
> The label, not the whole entry. Every field's body mentions
> half the dictionary somewhere -- "all" appears as a word in
> `expectedResidualLocation`'s description, and asking which field
> the word "all" names is a question with no answer.
