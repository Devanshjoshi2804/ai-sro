# Notes for `backend/src/sro/application/lookup/answer.py`

Comments and docstrings moved out of [`backend/src/sro/application/lookup/answer.py`](../../../../../../../backend/src/sro/application/lookup/answer.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/lookup/answer.py#L1): Docstring

> One system's answer to one lookup, in the shape every surface draws it from.
>
> An answer is read in three places -- the panel's card, the conversation, and
> whatever model is asked to make sense of it -- and each of them was parsing the
> raw body for itself. So each of them guessed, and the panel guessed badly:
> asked "is there a customer type called KKYT" it drew `URNFORMAT |
> ABSOLUTEGROUP | ALLOCATIONSEARCHPATH` as five columns of em dashes, beside a
> warehouse screen showing `Customer Type` and `Description`. Those were the
> first six KEYS of a payload that alphabetises.
>
> **Nothing here decides what a record is.** `application.execution.answer` does,
> for every other read in this system, and it decided all of it already: a
> column earns its place by carrying a value, the ranking puts code, name and
> description first, a `self_uri` is dropped as a link, two columns holding the
> same value in every row are one, the count is the system's own total rather
> than the page length, and `sentence()` says it in a line. This carries that
> across the wire and adds the one thing the reader cannot know -- what the
> records are OF, which is in the address they came from.
>
> **In `application`, beside the door that runs the lookup, rather than in the
> domain.** It was in `domain.lookup` and imported `application.execution.answer`
> from there, which is the layering check going red for a reason that was true:
> the domain imports nothing else in this codebase, and it cannot borrow a
> reader by reaching up a layer. Reading a warehouse's JSON is not a rule about
> lookups either -- the rules are in `plan.py` and `address.py`, which stayed
> where they are. This is what the application does with what came back.
>
> The raw body still travels for an answer that is not records: a page of HTML,
> one scalar, a screen whose picture stays on the other side. Those have nothing
> structural to preserve and are trimmed by character, the way they always were.

## module, [line 9](../../../../../../../backend/src/sro/application/lookup/answer.py#L9): Note on the line above

Code: `K_ANSWER_CHARS = 64 * 1024`

> How much of a body that is NOT records travels.
>
> Records do not use this: they cross as the reader's own bounded sample. This
> is the last guard, for a page of HTML or a scalar, and it is a character cut
> because there is nothing structural in those to cut along.

## module, [line 11](../../../../../../../backend/src/sro/application/lookup/answer.py#L11): Note on the line above

Code: `K_SAMPLE = 200`

> How many read records cross to a surface that draws them.
>
> `answer.py` bounds its sample at two thousand, which is right where the answer
> IS the product -- a taught read whose rows a person works from. A panel beside
> a warehouse screen draws eight and offers the console for the rest, and two
> thousand records of ten columns is a megabyte of JSON for a question somebody
> typed. Two hundred is far past what is drawn and far short of that.

## `subject_of`, [line 14](../../../../../../../backend/src/sro/application/lookup/answer.py#L14): Docstring

> What the records are OF, from the address they came from.
>
> `/data/WM/wm/customerTypes` is customer types. The reader cannot know this
> -- it is handed a body and never the question -- and `sentence()` needs it
> to say "There are 50 customer types" rather than "There are 50".
>
> The last path segment, un-camel-cased and singularised, because that is
> what a REST collection is named after and this base has no counter-example
> in 296 captured exchanges. A target that is not a path -- a screen route --
> answers empty, and the sentence says "records".

## `trimmed`, [line 24](../../../../../../../backend/src/sro/application/lookup/answer.py#L24): Docstring

> A body that is not records, small enough to send.

## `_found`, [line 30](../../../../../../../backend/src/sro/application/lookup/answer.py#L30): Docstring

> The answer to a question that named something, rather than a count.
>
> "is there a customer type called KKYT" is a yes and a record. It was
> answered "There are 110 customer type: leaning SRO 4 (DPP), ..." -- true,
> and not what anybody asked.

## `_describes`, [line 42](../../../../../../../backend/src/sro/application/lookup/answer.py#L42): Docstring

> One record, named the way `answer.py` names one: the ranked fields, best
> first, so this is what a person would call it.

## `as_seen`, [line 49](../../../../../../../backend/src/sro/application/lookup/answer.py#L49): Docstring

> One answer, as every surface draws it.
>
> The picture a screen lookup takes is deliberately not here: it is hundreds
> of kilobytes of base64 per screen, and what a picture MEANS is a model's
> question rather than a field on this shape.

## `subject_of`, [line 21](../../../../../../../backend/src/sro/application/lookup/answer.py#L21): Comment

Code: `return re.sub(r"ies$", "y", words) if words.endswith("ies") else words.removesuffix("s")`

> Singular, because `sentence` counts them: "There are 50 customer type"
> is the one place English needs this and the rest of the system names an
> entity in the singular everywhere.

## `as_seen`, [line 74](../../../../../../../backend/src/sro/application/lookup/answer.py#L74): Comment

Code: `matched = [dict(one) for one in named(question, every, subject)] if question else []`

> Which of them the question NAMED, where it named any. See
> `application.lookup.naming`: the panel worked this out in JavaScript, the
> console would have worked it out again, and a rule with a copy per
> surface drifts on all of them.

## `as_seen`, [line 76](../../../../../../../backend/src/sro/application/lookup/answer.py#L76): Comment

Code: `rest = [one for one in every if one not in shown][: max(0, K_SAMPLE - len(shown))]`

> And the ones it did not name, so the answer can be an answer without
> being the only thing a person may see. A question that named a record is
> answered with that record -- and somebody who wanted the collection
> after all should not have to ask again in different words.
>
> Bounded together rather than separately: matched and rest share
> `K_SAMPLE`, so an answer costs the same on the wire whether it named
> something or not.

## `as_seen`, [line 80](../../../../../../../backend/src/sro/application/lookup/answer.py#L80): Comment

Code: `"truncated": read.truncated or len(every) > K_SAMPLE,`

> The reader's own word for it, so a page nobody can size is never
> reported as a total. See `Answer.counted`.

## `as_seen`, [line 86](../../../../../../../backend/src/sro/application/lookup/answer.py#L86): Comment

Code: `"sentence": (`

> The answer to what was ASKED where something was, and the
> collection's own count where nothing was.

## `as_seen`, [line 91](../../../../../../../backend/src/sro/application/lookup/answer.py#L91): Comment

Code: `"rest": [dict(one) for one in rest] if matched else [],`

> Everything the question did NOT name. Empty where it named
> nothing, because then `records` is already all of them.

## `as_seen`, [line 92](../../../../../../../backend/src/sro/application/lookup/answer.py#L92): Comment

Code: `"matched": len(matched),`

> How many of the collection these are, so a surface can say "1 of
> 110" and offer the rest rather than pretending the answer is the
> whole of it.
