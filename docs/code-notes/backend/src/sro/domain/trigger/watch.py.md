# Notes for `backend/src/sro/domain/trigger/watch.py`

Comments and docstrings moved out of [`backend/src/sro/domain/trigger/watch.py`](../../../../../../../backend/src/sro/domain/trigger/watch.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/domain/trigger/watch.py#L1): Docstring

> A trigger the operator's own browser evaluates, against a mail it can see.
>
> This is not capture. ADR 008 keeps mail hosts out of observation and that stays
> exactly true: nothing here writes a page into the evidence plane. A watch is a
> rule the browser holds and applies locally, and the only things that ever leave
> the machine are the fact of a match and the handful of values the task needs.
>
> The distinction this module exists to make, because it is easy to collapse:
>
> A **term** is a comparison, and a comparison needs both sides. "Mails from this
> sender", "subject containing this phrase" -- the operator wrote that text by
> pointing at an example, and what is stored is their rule, not mined mail
> content. It sits in the control plane next to a schedule's cron expression and
> is no more sensitive than one. A matcher that knew only *where* to look could
> not tell one mail from another: it would match every mail that has a subject,
> which is all of them, and the first stage of an autonomous system would be a
> trigger that fires on everything.
>
> A **value** is a location and nothing else. The order number is different in
> every mail, so there is nothing to compare and nothing to store -- only where
> to find it. It is read at match time, passed as a parameter, and never written
> down.
>
> So ``Term`` carries text, ``ValueAt`` carries a ``ControlLocator``, and neither
> type has a field the other's data would fit in. That is the guard against mail
> bodies reaching storage, and it is structural rather than a rule somebody has
> to remember: ``TermField`` names the two headers an operator points at, there
> is no member for a body, and no amount of pointing at one yields a ``Term``
> that could hold it.

## module, [line 11](../../../../../../../backend/src/sro/domain/trigger/watch.py#L11): Note on the line above

Code: `QUESTION = "question"`

> The value name that makes a watch a question rather than a job.
>
> A location like every other value -- where in the mail the question is -- read
> at match time and never stored. The name is fixed here rather than chosen per
> trigger because two sides read it: the browser that reads the mail and the
> trigger that says it asks.

## module, [line 13](../../../../../../../backend/src/sro/domain/trigger/watch.py#L13): Note on the line above

Code: `MAX_TERM = 200`

> A sender and a subject phrase are short. Not a storage limit -- the second
> half of the guard above. A paragraph in a term is a pasted mail body whatever
> field it claims to be, and this is what makes that a refusal rather than a
> review comment nobody writes.

## module, [line 58](../../../../../../../backend/src/sro/domain/trigger/watch.py#L58): Note on the line above

Code: `MIN_WORD = 2`

> How short a word can be and still count. `PO` and `WM` are the vocabulary
> this warehouse actually uses; one letter is a list bullet.

## `Term`, [line 30](../../../../../../../backend/src/sro/domain/trigger/watch.py#L30): Docstring

> One half of "mails like this one" -- a header, and text to find in it.

## `_words`, [line 61](../../../../../../../backend/src/sro/domain/trigger/watch.py#L61): Docstring

> A header as the set of words in it, stemmed.
>
> Here and mirrored in `watch.js`, which is the side that evaluates it. One
> rule in two languages is the thing this codebase has been burned by --
> `shape_of` served a shape `recognise.js` could never match for weeks -- so
> the pair is held together by `test_the_mail_rules_a_browser_holds` and by
> the extension's own suite naming the same examples.

## `_stem`, [line 70](../../../../../../../backend/src/sro/domain/trigger/watch.py#L70): Docstring

> `shipped`, `ships` and `ship` as one word, and nothing cleverer.
>
> The doubled consonant is not a flourish: English doubles it before `-ed`,
> so `shipped` strips to `shipp`, and a rule written "Short ship" then failed
> on a mail saying "SHORT-SHIPPED" -- which is the exact case this whole
> change is about. Collapsed only after an ending was removed, so `pass` and
> `across` are left alone.

## `ValueAt`, [line 81](../../../../../../../backend/src/sro/domain/trigger/watch.py#L81): Docstring

> Where the task's parameter is read from, on a mail that matched.
>
> A location, never a value. ``ControlLocator`` is reused rather than
> reinvented because this is the same problem the skills already solved --
> find this control again tomorrow on a page that re-rendered -- and because
> it has no field a mail body would fit in.

## `ValueAt`, [line 82](../../../../../../../backend/src/sro/domain/trigger/watch.py#L82): Note on the line above

Code: `name: str`

> The skill parameter this fills.

## `Watch`, [line 92](../../../../../../../backend/src/sro/domain/trigger/watch.py#L92): Docstring

> A host, what makes a mail one of these, and where to read the values.

## `Watch`, [line 93](../../../../../../../backend/src/sro/domain/trigger/watch.py#L93): Note on the line above

Code: `host: str`

> The mail host this is evaluated on. Excluded from capture by
> ``ObservationPolicy`` and that is not a contradiction: a watch reads and
> forgets, it does not record.

## `Watch`, [line 99](../../../../../../../backend/src/sro/domain/trigger/watch.py#L99): Note on the line above

Code: `subject_at: ControlLocator | None = None`

> Where the two headers are on the client this operator actually uses.
>
> A term is a comparison and a comparison needs both sides. The text is the
> operator's; the other side is a header on a page, and there is no standard
> for where that is -- Gmail, Outlook Web and a corporate webmail render a
> mail three different ways, and none of them says which node is the sender.
> A browser handed only the text would have to guess a selector, which is a
> matcher that works on one client this quarter and silently stops.
>
> So the operator marks them, in the same act and by the same mechanism they
> mark the values: a ``ControlLocator``. Not a ``ValueAt`` -- a value is a
> skill parameter and is uploaded on a match, and the sender and subject are
> the two things this design is most careful never to send anywhere. These
> are read in the browser, compared in the browser, and forgotten there.

## `Term.matches`, [line 45](../../../../../../../backend/src/sro/domain/trigger/watch.py#L45): Docstring

> Whether this header says what the operator pointed at.
>
> Substring first, because a phrase somebody marked in their own mail is
> usually there verbatim in the next one, and an address is a substring
> by nature. Then WORDS, because the next one is written by a person:
>
>     term    "Short ship"
>     matches "Short ship on PO 4471"      -- the substring
>     matches "PO 4471 arrived short"      -- shipped, reordered
>     matches "SHORT-SHIPPED: PO 4471"     -- punctuation, a suffix
>
> Every word of the term has to appear, in any order, anywhere in the
> header. Narrowing is still the safe direction: adding a word to a term
> makes it stricter, never looser, and a term of one word matches exactly
> what a substring of that word did. What this drops is order,
> punctuation and case -- three things that vary between two people
> writing about the same thing, and none of which the operator was
> choosing when they pointed at a phrase.
>
> Stems, so `shipped`, `ships` and `ship` are one word. A trailing `s` or
> `ed` and nothing cleverer: a real stemmer matches `code` to `coded` and
> to `barcode`, and this is the direction where being wrong proposes
> something about somebody's payroll.

## `Term.nearly`, [line 51](../../../../../../../backend/src/sro/domain/trigger/watch.py#L51): Docstring

> Whether this header has SOME of the term's words but not all.
>
> Reported, never matched on. A rule that fires half-way is worse than
> one that does not fire; a rule that misses in silence is worse than
> both, because the operator believes their browser is watching for
> something and it is not. `watch.js` reports these and the panel says
> so, using the OPERATOR'S OWN WORDS -- the mail's text stays in the mail.

## `Watch.matches`, [line 119](../../../../../../../backend/src/sro/domain/trigger/watch.py#L119): Docstring

> Whether this mail is one of the ones the operator meant.
>
> Every term has to match. An "or" is two watches, which is also how an
> operator would say it -- and narrowing is the safe direction to be wrong
> in, because the cost of a miss is a mail nobody was offered help with
> and the cost of a false match is a proposal about somebody's payroll.
>
> The browser is what actually evaluates this. Keeping the rule here is
> what lets a server check a claimed match later without ever having been
> sent the mail.

## `Watch.nearly`, [line 125](../../../../../../../backend/src/sro/domain/trigger/watch.py#L125): Docstring

> The terms this mail has some of, when the watch did not match.
>
> Empty when it matched, empty when the mail has nothing to do with the
> rule, and empty for a sender term -- see below. What is left is the
> case worth saying out loud: the operator
> wrote "Short ship" and a mail arrived saying "shipment delayed", so the
> rule was about the right conversation and did not fire.
>
> The terms are the operator's own words. Nothing from the mail is in
> what comes back, which is what keeps this on the right side of ADR 008
> -- the browser can report a near miss without reporting a mail.

## `Watch.reads`, [line 137](../../../../../../../backend/src/sro/domain/trigger/watch.py#L137): Docstring

> The parameters a matching mail supplies.

## `Watch.nearly`, [line 130](../../../../../../../backend/src/sro/domain/trigger/watch.py#L130): Comment

Code: `return tuple(`

> Subjects only. A sender either is or is not the person, and every
> address on earth shares words with every other one -- `@acme.example`
> against `@northwind.example` has `example` in common, which is a
> near miss on nothing. A subject is where two people writing about the
> same thing write it differently, which is the whole of what this
> reports.
