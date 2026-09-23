# Notes for `backend/src/sro/application/knowledge/open_questions.py`

Comments and docstrings moved out of [`backend/src/sro/application/knowledge/open_questions.py`](../../../../../../../backend/src/sro/application/knowledge/open_questions.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/knowledge/open_questions.py#L1): Docstring

> What the system does when it does not know, instead of choosing.
>
> Two endpoints answered "how many transport modes": the site's view said sixteen
> and the wider collection said twenty-three. Both were real, both had been
> observed, and the system picked the first one it happened to see -- so it gave a
> confident answer to a question it had not understood, and the operator found out
> by counting rows on a screen.
>
> Picking was the mistake, not picking wrongly. The failure mode this system is
> arranged against is a confident wrong action, and an ambiguity resolved by
> whichever evidence arrived first is exactly that with extra steps.
>
> So ambiguity is written down as a question, kept beside what is known about the
> system, and asked once. The answer is knowledge like any other: it supersedes
> the question, it carries who said it, and every later decision reads it instead
> of guessing again. A system that asks the same thing twice has not learned
> anything; a system that never asks has only hidden what it does not know.
>
> The shape is deliberately general. Anything that finds itself choosing between
> plausible readings -- which collection an entity lives in, which of two screens
> does a task, whether a field is an input or a constant -- records a question
> here rather than inventing a rule, and the operator's answer is what settles it
> for everybody afterwards.

## `Ambiguity`, [line 12](../../../../../../../backend/src/sro/application/knowledge/open_questions.py#L12): Docstring

> Two or more readings of one thing, none of which may be assumed.

## `Ambiguity`, [line 14](../../../../../../../backend/src/sro/application/knowledge/open_questions.py#L14): Note on the line above

Code: `key: str`

> What is ambiguous, addressed the same way twice so asking again finds
> the answer rather than asking again.

## `Ambiguity`, [line 18](../../../../../../../backend/src/sro/application/knowledge/open_questions.py#L18): Note on the line above

Code: `because: tuple[str, ...] = ()`

> The evidence for each reading. An operator choosing between two endpoint
> names needs to know one returned sixteen rows and the other twenty-three.

## `AskAbout`, [line 21](../../../../../../../backend/src/sro/application/knowledge/open_questions.py#L21): Docstring

> Record what could not be decided, and let it be decided once.

## `AskAbout.raise_question`, [line 26](../../../../../../../backend/src/sro/application/knowledge/open_questions.py#L26): Docstring

> Write the question down. Idempotent: the same ambiguity found twice
> is one question, and an answered one is never re-asked.

## `AskAbout.answer`, [line 53](../../../../../../../backend/src/sro/application/knowledge/open_questions.py#L53): Docstring

> Settle it, for everybody, permanently.
>
> Recorded as ``observed`` rather than asserted: somebody who works here
> looked at both readings and said which one their words mean, which is a
> stronger thing than a catalogue's opinion and supersedes the question.

## `AskAbout.settled`, [line 71](../../../../../../../backend/src/sro/application/knowledge/open_questions.py#L71): Docstring

> What was decided about this, if anybody has decided it.

## `AskAbout.outstanding`, [line 83](../../../../../../../backend/src/sro/application/knowledge/open_questions.py#L83): Docstring

> Everything the system knows it does not know.
>
> Worth a screen of its own: these are the places where the next confident
> answer would be a guess, and they are cheap to settle while somebody
> remembers the context.

## `AskAbout.raise_question`, [line 48](../../../../../../../backend/src/sro/application/knowledge/open_questions.py#L48): Comment

Code: `evidence=EvidenceLevel.ASSERTED,`

> Asserted, and deliberately the weakest level: a question is
> not evidence about the system, it is evidence that nobody
> has said yet.
