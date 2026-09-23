# Notes for `backend/src/sro/application/induction/sites.py`

Comments and docstrings moved out of [`backend/src/sro/application/induction/sites.py`](../../../../../../../backend/src/sro/application/induction/sites.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/induction/sites.py#L1): Docstring

> Addresses of values inside a step, and substitution at those addresses.
>
> Addressing rather than string-replacing is what stops a quantity of ``3`` being
> substituted where a page number happens to share the value.

## module, [line 75](../../../../../../../backend/src/sro/application/induction/sites.py#L75): Note on the line above

Code: `_RECENT_MILLIS = range(1_600_000_000_000, 4_000_000_000_000)`

> 2020 to 2096, in milliseconds. What a cache-buster's value looks like.

## module, [line 163](../../../../../../../backend/src/sro/application/induction/sites.py#L163): Note on the line above

Code: `_IN_PATH = str.maketrans({c: f"%{ord(c):02X}" for c in "/?#"})`

> What a value cannot carry into a path segment without ending it.
>
> Only these three, because a path segment is stored the way the demonstration
> sent it -- `url_path_segments` never unquotes -- so the text in one is already
> percent-encoded and everything else in it has to be left exactly alone.
> Encoding the `%` of an `ATTN%20ALI` again gives `ATTN%2520ALI`, the
> double-encoding `choices._searched` already carries a warning about. These
> three are safe to touch anyway: an already-encoded segment spells them `%2F`,
> `%3F` and `%23`, never bare, since a bare `/` would have made it two segments
> in the recording.

## module, [line 165](../../../../../../../backend/src/sro/application/induction/sites.py#L165): Note on the line above

Code: `_IN_QUERY = str.maketrans({c: f"%{ord(c):02X}" for c in "%&=+;#"})`

> What a value cannot carry into a query parameter without ending it.
>
> More than the path's set, and that asymmetry is the point: a query value is
> held *decoded* -- `url_query_pairs` reads it through `parse_qsl` -- so a `%`
> here is a percent sign somebody typed and encoding it is restoring what the
> demonstration itself put on the wire, not doubling it. The set is
> form-urlencoding's own delimiters, because that is the syntax this value is
> read back out of; `+` and `;` are in it because a reader that means "space"
> by one and "separator" by the other is a reader we do not control.

## `TextBodySite`, [line 27](../../../../../../../backend/src/sro/application/induction/sites.py#L27): Docstring

> Whole body, when it is not JSON and differs between runs.

## `HeaderSite`, [line 31](../../../../../../../backend/src/sro/application/induction/sites.py#L31): Docstring

> A request header whose value varied between runs.
>
> Only headers the domain calls replayable reach here. A trace id differs on
> every run and a cookie differs on every session; treating those as varying
> inputs would turn session noise into parameters the operator is asked for.

## `ActionValueSite`, [line 36](../../../../../../../backend/src/sro/application/induction/sites.py#L36): Docstring

> Text the human typed, or the option they selected.

## `parse_json`, [line 66](../../../../../../../backend/src/sro/application/induction/sites.py#L66): Docstring

> Parse as JSON, or ``None`` for form-encoded and plain-text bodies.

## `without_clocks`, [line 78](../../../../../../../backend/src/sro/application/induction/sites.py#L78): Docstring

> The same address, minus the parameters that only mean "now".
>
> Ext JS appends `_dc=<epoch millis>` to defeat caching and jQuery's `_` does
> the same. Replaying yesterday's "now" is at best meaningless; dropping the
> whole query instead is worse, because a site-scoped collection needs its
> site parameter and answers nothing without it.

## `as_a_filter`, [line 88](../../../../../../../backend/src/sro/application/induction/sites.py#L88): Docstring

> The same query, asking the server for one column instead of the other.
>
> The demonstration searched for what its operator was looking for -- ten rows
> where the name contained an "h" -- and replaying that searches for their
> record, not this one. But it also proves how this system is asked: the
> filter's own shape, in its own vocabulary, with a real 200 behind it.
>
> So the query is kept and its terms are replaced: same parameter, same
> dialect, this run's value. ``None`` when nothing here looks like a filter,
> because inventing one for an API that never showed us one is a guess.

## `without_filter`, [line 121](../../../../../../../backend/src/sro/application/induction/sites.py#L121): Docstring

> The same address with nobody's search on it.
>
> A dropdown opening for the first time should show what is there, not what
> the operator who taught the task was looking for that afternoon.

## `filter_terms_of`, [line 131](../../../../../../../backend/src/sro/application/induction/sites.py#L131): Docstring

> Every filter term this address carries, across its query parameters.

## `_filter_terms`, [line 135](../../../../../../../backend/src/sro/application/induction/sites.py#L135): Docstring

> The filter this query parameter carried, or ``None`` if it is not one.
>
> An empty list is a filter -- an empty one. The distinction matters: it says
> this endpoint accepts a filter here, which is the difference between
> composing a narrower request and inventing a parameter.

## `substitute_url`, [line 145](../../../../../../../backend/src/sro/application/induction/sites.py#L145): Docstring

> Rebuild a URL with placeholders at the given sites.
>
> Scheme and host are never parameterised: which host a system lives on is a
> deployment fact, not a per-run value.

## `render_url`, [line 168](../../../../../../../backend/src/sro/application/induction/sites.py#L168): Docstring

> Substitute values into a URL template, encoded for the slot each lands in.
>
> A value is text, and text in a URL is structure: `X&limit=9999` supplied
> for a search term used to render `?name=X&limit=9999&limit=25`, asking the
> server a question nobody demonstrated. Same defect as the JSON body's, and
> the same answer -- encode rather than refuse, so an operator searching for
> `Smith & Sons` still gets to.
>
> Split at the first `?` so each half encodes in its own syntax, and rendered
> with the same `Template` both halves came from rather than a second
> substitution syntax written here. Nothing outside a placeholder is touched,
> so a template renders byte-for-byte as it did before wherever the values
> going into it carry none of these characters.

## `as_a_filter`, [line 98](../../../../../../../backend/src/sro/application/induction/sites.py#L98): Comment

Code: `if key.lower() not in {"offset", "start", "page"}:`

> Offsets belong to the page somebody was looking at, not to a
> search for one record.

## `as_a_filter`, [line 102](../../../../../../../backend/src/sro/application/induction/sites.py#L102): Comment

Code: `term = terms[0] if terms else shape`

> An empty list is a filter slot: the endpoint takes this parameter and
> was sent nothing in it. What a term looks like then has to come from
> somewhere this system has been seen filling one in -- never from a
> shape invented here.

## `as_a_filter`, [line 100](../../../../../../../backend/src/sro/application/induction/sites.py#L100): Comment

Code: `continue`

> An empty slot and no proven shape to fill it with. Composing the
> request without the filter would ask for everything, which is a
> different question from the one that was asked.

## `substitute_url`, [line 158](../../../../../../../backend/src/sro/application/induction/sites.py#L158): Comment

Code: `return urlunsplit(`

> safe="${}" keeps placeholders readable instead of percent-encoded, because
> a human reviews these templates.

## `substitute_body`, [line 195](../../../../../../../backend/src/sro/application/induction/sites.py#L195): Comment

Code: `markers: dict[str, str] = {}`

> A field whose absent form is not itself a JSON string -- `null` for a
> number the form nulls -- must send that form unrendered: a quoted
> `"null"` is a string, and a form expecting a number rejects it. Such a
> leaf gets a `\x00pointer\x00` sentinel instead of its placeholder here,
> so the later unquoting step can find exactly this leaf and nothing else
> -- a `\x00` byte is not something a form control lets an operator type,
> and `json.dumps` always escapes one to `\u0000`, so the marker's quoted
> form can only occur in the output where this function itself put it.
> Doing this with the placeholder text directly, `${name}`, would unquote
> any other field whose own value happened to read that.
>
> Keyed on the site rather than the parameter's name, because which leaves
> lose their quotes is a fact about those leaves: one parameter can fill a
> body number here and a URL segment there, and the name says nothing about
> which is which.
