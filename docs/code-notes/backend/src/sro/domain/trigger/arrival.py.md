# Notes for `backend/src/sro/domain/trigger/arrival.py`

Comments and docstrings moved out of [`backend/src/sro/domain/trigger/arrival.py`](../../../../../../../backend/src/sro/domain/trigger/arrival.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/domain/trigger/arrival.py#L1): Docstring

> A page an operator lands on, as a rule their own browser evaluates.
>
> The wire that was missing. This system could recognise a job -- "create an
> equipment type, you've done this four times" -- and it could drive a browser
> through one, and nothing connected the two: a run began because somebody
> pressed a button, a console started it, or a schedule fired. An operator
> watching their own browser be driven through a login asked the obvious
> question, which was why it could not do that by itself.
>
> An arrival is the smallest honest answer. The operator is standing on the page
> where a job starts; they say "do this here"; the next time they land on that
> page, their browser starts it.
>
> **Evaluated in the browser, like a watch and for a narrower reason.** A watch
> is local because mail must not reach this side at all. An arrival could be
> evaluated here -- the page's url is already evidence -- and is not, because the
> thing being decided is "is this operator, right now, standing on that page",
> and the only process that knows is the one with the tab open. A server that
> tried would be asking the browser anyway.
>
> **A page, not a url.** `host/path`, lowercased, query and fragment dropped --
> the same shape `TaskCandidate.starts_on` already carries, so the rule an
> operator makes from an offer is the offer's own page and not a second spelling
> of it. A query string is one visit's parameters; a fragment is where they were
> inside the page. Neither says which page they are on, and both would make a
> rule that matched once and never again.

## module, [line 8](../../../../../../../backend/src/sro/domain/trigger/arrival.py#L8): Note on the line above

Code: `MAX_PAGE = 300`

> How long a page rule may be. A host and a path, not a url somebody pasted.
>
> The same argument `MAX_TERM` makes next door: a bound here is what makes "this
> is a page, not a payload" a refusal rather than a convention. Three hundred is
> generous for `host/path` and short enough that a session token glued onto the
> end of one does not fit.

## `Arrival`, [line 12](../../../../../../../backend/src/sro/domain/trigger/arrival.py#L12): Docstring

> The page whose arrival starts the job.

## `Arrival`, [line 13](../../../../../../../backend/src/sro/domain/trigger/arrival.py#L13): Note on the line above

Code: `page: str`

> `host/path`, as `page_of` renders it. Never a scheme, never a query.

## `page_of`, [line 31](../../../../../../../backend/src/sro/domain/trigger/arrival.py#L31): Docstring

> A url as the page it is: `host/path`, lowercased, nothing else.
>
> Here rather than in the extension, even though the extension is what
> evaluates the rule, because both sides have to agree on what "the same
> page" means and a rule with a copy in two languages drifts on one of them.
> `nudge.js` renders it identically; `test_the_command_vocabulary` holds that
> kind of pair together elsewhere in this codebase for the same reason.

## `Arrival.matches`, [line 27](../../../../../../../backend/src/sro/domain/trigger/arrival.py#L27): Docstring

> Whether the operator is standing on this page.
>
> Exact, not a prefix. A prefix rule on `host/` is every page on that
> host, which is the interruption this whole design refuses; and a
> deeper page is a different screen doing different work, whatever its
> url has in common with this one.

## `Arrival.__post_init__`, [line 25](../../../../../../../backend/src/sro/domain/trigger/arrival.py#L25): Comment

Code: `raise InvariantViolation("a page rule is lowercase; use `page_of` to make one")`

> Normalised by the caller rather than here, so a rule and the
> page it was made from are the same string in the store and in
> the browser. A dataclass that quietly rewrote its own field
> would make the two disagree on which of them is the rule.

## `page_of`, [line 33](../../../../../../../backend/src/sro/domain/trigger/arrival.py#L33): Comment

Code: `if parsed.scheme not in ("http", "https"):`

> http and https only. `chrome://settings` parses perfectly well and its
> "host" is `settings`, so without this a rule could be made about the
> browser's own pages -- which are not a system, carry no session, and are
> the one place an extension has no business driving anything.
