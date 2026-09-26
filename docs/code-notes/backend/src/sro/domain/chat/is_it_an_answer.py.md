# Notes for `backend/src/sro/domain/chat/is_it_an_answer.py`

Comments and docstrings moved out of [`backend/src/sro/domain/chat/is_it_an_answer.py`](../../../../../../../backend/src/sro/domain/chat/is_it_an_answer.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/domain/chat/is_it_an_answer.py#L1): Docstring

> Whether what somebody typed is the answer to the question standing in front
> of them, or something else entirely.
>
> Until now it was neither asked nor answerable: a question standing in the
> conversation took the next sentence as its value, whatever the sentence was.
> That is right for `GU9` and wrong for everything else a person types while
> waiting -- and what they type while waiting is usually about the waiting.
>
> Measured on the deployment 2026-09-18. A question stood asking for
> `Customer Type`. The operator, who had already sent the answer by MAIL and was
> watching for it to arrive, typed `has reply arrived` into the panel to ask
> this system a question. It was taken as the value, a run started one
> millisecond later, and `HAS REPLY ARRIVED` was typed into a four-character box
> in a live warehouse system, which refused it. Nothing in the path asked whether
> that sentence was an answer, because nothing could.
>
> Two tiers, and the cheap one first. A value is usually a value and looks like
> one -- one word, no punctuation of the kind sentences have -- and a reading
> spent on `S057` is a reading spent proving the obvious. What is not obviously a
> value goes to the model, which is asked one question and given the words that
> were actually said.
>
> Pure. The model call lives in `application.chat.reading_an_answer`, and the
> question it asks is the `IS_IT_AN_ANSWER` record in
> `sro.domain.prompts.is_it_an_answer`; what is here is the half that needs
> nobody to answer it.

## module, [line 5](../../../../../../../backend/src/sro/domain/chat/is_it_an_answer.py#L5): Note on the line above

Code: `K_ONE_WORD = 60`

> How long a single word may be and still read as a value without asking.
>
> A code, an id, a quantity, a date. Past this a lone token is a sentence with
> its spaces eaten -- a url, a pasted line -- and worth a reading.

## module, [line 7](../../../../../../../backend/src/sro/domain/chat/is_it_an_answer.py#L7): Note on the line above

Code: `K_SENTENCE = "?!,;:"`

> Punctuation a value does not carry. A question mark is the clearest signal a
> person ever gives that they are asking rather than answering, and this system
> threw it away.

## module, [line 9](../../../../../../../backend/src/sro/domain/chat/is_it_an_answer.py#L9): Note on the line above

Code: `K_PROSE = 200`

> How roomy a box has to be before what goes in it is prose.
>
> The whole of this module exists because `HAS REPLY ARRIVED` was typed into a
> **four-character** box. That is the harm: a sentence in a field that cannot
> hold a sentence, in a live warehouse system.
>
> A field that holds two thousand characters is not that field. It is a
> description, and a description is prose -- so a reading asked "is this really
> the description" is being asked to judge somebody's prose, which it cannot do
> and should not be asked to. Measured on the deployment 2026-09-20: asked what
> `Customer Type Description` should be, the operator typed `my sro is best`
> twice and was refused twice, the model calling it "a casual comment or test
> remark". It was the description. It was the second-longest field in the job
> and there was nothing else it could have been.
>
> Two hundred, because that is comfortably longer than any code, id, quantity or
> date this system has met and comfortably shorter than any description field it
> has. Nothing is read INTO the number: what it separates is "a box a sentence
> fits in" from "a box a sentence does not fit in", and those are far apart.

## module, [line 26](../../../../../../../backend/src/sro/domain/chat/is_it_an_answer.py#L26): Note on the line above

Code: `K_SAID_AS = (":", "=")`

> How somebody names the field themselves. `Address: SRO Depot One`.

## `plainly_a_value`, [line 12](../../../../../../../backend/src/sro/domain/chat/is_it_an_answer.py#L12): Docstring

> Whether this is a value with no doubt about it -- no reading needed.
>
> Deliberately narrow. What it returns False for is not "not an answer": it
> is "worth asking about", and the caller asks. The cost of being narrow is a
> model call on a sentence that turned out to be a value; the cost of being
> wide is what happened on 2026-09-18.

## `said_as_the_value`, [line 29](../../../../../../../backend/src/sro/domain/chat/is_it_an_answer.py#L29): Docstring

> The value where the person named the field themselves, or None.
>
> The way out. A reading that refuses is told to refuse when it is unsure,
> and that is the right default -- but it leaves an operator who typed a
> real value with no move except typing it again and being refused again,
> which is the loop `question` exists to not be. `Address: testing for new
> purpose` is somebody saying what the sentence is FOR, and nothing needs to
> be read to know it.
>
> Only the field standing in front of them. `url: http://…` typed under a
> question about Address is not a value named for Address, and taking it
> would be the substring matching this whole module replaced.

## `_plainly`, [line 39](../../../../../../../backend/src/sro/domain/chat/is_it_an_answer.py#L39): Docstring

> A field name as a person would type it. `long_description` and
> `Long Description` are the same name, and the one on the form is not
> always the one the job declares.

## `plainly_a_value`, [line 17](../../../../../../../backend/src/sro/domain/chat/is_it_an_answer.py#L17): Comment

Code: `if holds is not None and holds >= K_PROSE:`

> A box roomy enough for prose, holding prose that fits. See `K_PROSE`.
>
> The question mark still decides, and only it: a comma, a colon and a
> semicolon are ordinary inside a description, while a question mark is
> the clearest signal a person ever gives that they are asking rather than
> answering -- which is what `K_SENTENCE` says about it and the only part
> of that rule a prose field has any business keeping.

## `plainly_a_value`, [line 23](../../../../../../../backend/src/sro/domain/chat/is_it_an_answer.py#L23): Comment

Code: `return holds is None or len(value) <= holds`

> And it has to fit the box it is for. A lone word too long for the field
> is already refused further down, but it is not OBVIOUSLY a value either,
> and the question this asks is about obviousness.
