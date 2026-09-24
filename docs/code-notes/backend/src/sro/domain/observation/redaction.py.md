# Notes for `backend/src/sro/domain/observation/redaction.py`

Comments and docstrings moved out of [`backend/src/sro/domain/observation/redaction.py`](../../../../../../../backend/src/sro/domain/observation/redaction.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/domain/observation/redaction.py#L1): Docstring

> The credential vocabulary and the rules that act on it.
>
> Ported out of the rig's `new_agent_arch/src/rig/wire.py`, which applied them to
> every request on its way to the store. They live in the domain because both
> belts need them and only one direction of import is allowed: `trim.body_keys`
> applies the same three rules -- name, shape and the recursive walk -- to every
> body that reaches a prompt, and the domain may not import `sro.application`, so
> `sro.application.capture.rig_wire` imports them back from here instead. The
> rules themselves are unchanged, and the wire's boundary behaviour with them.
>
> Three rules, in the order they run. The NAME rule (`is_secret_name`) reads a
> field's name against `SECRET_WORDS`, whole words only. The SHAPE rule
> (`redact_shapes`) reads the value itself, because a field name is chosen by
> whoever wrote the vendor's API and that vocabulary can never be finished. The
> WALK (`redact_data`) applies the name rule at every depth, because
> `{"auth": {"password": ...}}` is the same credential one level down.
>
> Not to be confused with `sro.domain.recording.sensitivity`, the generated
> vocabulary the recorder and the Steel capture path share. This is the rig's own
> hand-copy of the extension's `new-chrome-extension/src/content/sensitivity.module.js`,
> kept for as long as the rig's evidence is read by these functions;
> `tests/unit/domain/rig/test_trim.py` is what says the two copies of the
> extension's rule still agree with the extension.

## `shapes_in`, [line 143](../../../../../../../backend/src/sro/domain/observation/redaction.py#L143): Docstring

> Which credential shapes appear in this text, in the order first seen.
>
> Kept apart from the redaction so a body can record *why* it lost something.
> "This went because it looked like a JWT" is a different fact from "this
> went because it was called password", and a reviewer wants to tell them
> apart -- while the marker left behind is the same either way, so nothing
> downstream has to learn a second convention.

## `redact_shapes`, [line 154](../../../../../../../backend/src/sro/domain/observation/redaction.py#L154): Docstring

> The same text with every credential-shaped run replaced.
>
> A substitution rather than a verdict on the whole value: a shape can sit
> inside a larger string -- a bearer scheme in free text, a PEM block in a
> log line -- and every byte that did not match is left exactly as it
> arrived. Text with no credential in it comes back identical, which is what
> lets this run over a URL that must not be re-encoded.

## `_words_of`, [line 160](../../../../../../../backend/src/sro/domain/observation/redaction.py#L160): Docstring

> camelCase, snake_case and "Shipping Date" alike, split into words.
>
> The acronym rule is `([A-Z]{2,})([A-Z][a-z])` and deliberately not
> `([A-Z]+)([A-Z][a-z])`: the wider one splits the lone `N` off
> `pickNPassAutoDropLocation` and leaves `Pass` bare, blanking a real
> warehouse field ("Pick N Pass"). Two-or-more needs three capitals in a row
> before it cuts, so `SAMLResponse` splits into saml/response -- which is what
> makes the word `saml` worth having -- and `NPass` stays whole. Measured over
> 3,270 distinct field, header and query-parameter names from the real acme
> store plus knowledge-base/http/exchanges: it changes none of them.

## `is_secret_name`, [line 166](../../../../../../../backend/src/sro/domain/observation/redaction.py#L166): Docstring

> Whether a field called this holds a credential.
>
> Whole words, not substrings, which is the extension's rule and matters:
> `"pin" in name` flags a real field in this tenant's captured data called
> "Shipping Date Escalation". The joined form is checked too, so `apiKey`
> and `api_key` both match `apikey`.

## `_redact_query`, [line 186](../../../../../../../backend/src/sro/domain/observation/redaction.py#L186): Docstring

> An `a=b&c=d` string with every credential-named value replaced.
>
> Spliced by hand rather than round-tripped through parse_qsl + urlencode,
> which is the extension's rule and its stated reason: re-encoding touches
> every pair rather than the one that matched -- it collapses a repeated key,
> turns a literal space into `+`, and percent-encodes the marker itself, so
> grepping stored evidence for the «redacted» every other path writes finds
> nothing. Splicing leaves every untouched byte exactly as the browser sent
> it. A pair with no `=` is given one, as the extension does: the name alone
> is what matched.

## `redact_url`, [line 199](../../../../../../../backend/src/sro/domain/observation/redaction.py#L199): Docstring

> A URL with credential-named query and fragment values replaced.
>
> `?token=...` is as much a credential as the header form, and a URL is
> stored on every event there is -- a navigation, a request, and the frame a
> gesture happened in. The fragment is checked too when it is shaped like a
> query string: `#access_token=...` is how an OAuth implicit flow hands a
> token back, and the audit found one on disk.
>
> A relative URL is redacted too, unlike the extension's copy. The extension
> leaves one alone because it cannot RESOLVE it -- the service worker has no
> page to resolve against -- and that reasoning is about resolution, which
> nothing here does: the query and fragment are spliced by raw string
> position and need no scheme or host. Skipping them cost the whole corpus:
> every one of the 611 distinct URLs in the captured knowledge base is
> relative, so the guard that was meant to be conservative excluded 100% of
> real evidence from URL redaction. Zero of them redact today, so closing it
> costs nothing and covers the shape all real traffic has.
>
> An unparseable URL is still left alone rather than guessed at.

## `redact_data`, [line 231](../../../../../../../backend/src/sro/domain/observation/redaction.py#L231): Docstring

> The same rule at every depth, through dicts and lists alike.
>
> The flat version of this guarded the top level of a JSON object and
> nothing else, so `{"auth": {"password": ...}}` walked straight past it.

## `_redact_multipart`, [line 276](../../../../../../../backend/src/sro/domain/observation/redaction.py#L276): Docstring

> A part names its field on one line and carries the value on another, so
> the pair scanner never sees the two together and cannot act on the name.

## `_redact_named`, [line 294](../../../../../../../backend/src/sro/domain/observation/redaction.py#L294): Docstring

> One body, whatever shape it is, with every credential-named value gone.
>
> Mirrors the extension's redactBody: JSON walked recursively (arrays and
> bare strings included), XML and SOAP, multipart, form-urlencoded --
> including when the mime type is absent and the text is merely shaped like
> a form -- and, when no parser fits, a scan for `name=value` pairs rather
> than storing the text unread.
>
> Where a parser was chosen and the document did not parse, the body is
> replaced wholesale. An unparsed body that might hold a credential is the
> failure; a body replaced entirely is legible and safe.

## `redact_body`, [line 310](../../../../../../../backend/src/sro/domain/observation/redaction.py#L310): Docstring

> The name rule above, then the shape rule over whatever it produced.
>
> Last and over the whole body, whatever parser ran: a shape needs no field
> name, so it reaches a credential in a value the name rule had no name to
> judge -- including through a body no parser fitted and through one replaced
> by UNINSPECTABLE, where the name rule gave up entirely.

## module, [line 7](../../../../../../../backend/src/sro/domain/observation/redaction.py#L7): Comment

Code: `SECRET_HEADERS = frozenset(`

> Mirrors SECRET_HEADERS and SECRET_HEADER_HINTS in the extension's
> new-chrome-extension/src/content/sensitivity.module.js. Note this rule is
> deliberately not the field rule: a header matches on an exact lowered name OR
> on a substring hint, because `x-acme-session-key` has to match on `sess`.
> trim.is_secret_name() matches whole words precisely because the opposite is
> true of body fields -- see the ten real shipping fields a substring rule
> blanks. These live here rather than in the wire module that applies them to
> every stored request, because the domain may not import the application layer
> and `body_keys` below needs the same vocabulary: one copy, imported the one
> direction the layering allows.

## module, [line 39](../../../../../../../backend/src/sro/domain/observation/redaction.py#L39): Comment

Code: `SECRET_WORDS = frozenset(`

> Mirrors SECRET_WORDS and isSecretName in the same extension module. Here for
> the reason the header rule above is: the wire models apply it to everything
> that reaches the store and `body_keys` applies it again to everything that
> reaches a prompt, and only one of those two may import the other.

## module, [line 115](../../../../../../../backend/src/sro/domain/observation/redaction.py#L115): Comment

Code: `UNINSPECTABLE = "«whole body: could not be parsed to redact»"`

> Stored in place of a body this process could not parse to redact. The
> extension writes the same sentence in redacted_fields for the same reason.

## module, [line 117](../../../../../../../backend/src/sro/domain/observation/redaction.py#L117): Comment

Code: `SECRET_SHAPES: tuple[tuple[str, str], ...] = (`

> Mirrors SECRET_SHAPE and SECRET_SHAPE_ANY_CASE in the same extension module,
> which are generated from `sensitivity.SECRET_SHAPES`. The value rule beside
> the name rules, and it exists because the name rule cannot be finished: a
> field name is chosen by whoever wrote the vendor's API, an open vocabulary
> guessed at forever, and the round before this one found 57 of 85 realistic
> credential names unmatched and then blanked three real warehouse fields
> closing the gap. A shape is not open in that way -- a JWT is a JWT in any
> field, and a warehouse dock code is never a PEM block.
>
> Measured over 47,969 distinct real values from the acme store plus
> knowledge-base/http/exchanges -- the VALUES, which nothing here had ever
> measured, only the names: every pattern below matches zero of them.
> `new_agent_arch/tests/test_corpus.py` is that measurement as a test. It ran
> in the rig, against the rig's own corpus, before any of this was ported; it
> is not in this repository and nothing here re-measures it.
>
> High-entropy detection is deliberately absent, on the same corpus: a Shannon
> threshold of 4.5 bits over runs of 20+ token characters blanks 791 real
> values, 4.0 blanks 14,419, 3.5 blanks 21,250 -- and 5.0 blanks nothing at
> all. There is no threshold between useless and destructive.

## module, [line 118](../../../../../../../backend/src/sro/domain/observation/redaction.py#L118): Comment

Code: `("jwt", r"eyJ[A-Za-z0-9_-]{10,}(?:\.[A-Za-z0-9_-]*){2,4}"),`

> Two to four dots, not exactly two. A signed JWT has three segments; an
> encrypted one (JWE compact serialisation) has five, and the real Okta
> authorization code in this deployment's evidence store is a JWE with
> segment lengths [124, 342, 16, 1035, 22]. The three-segment rule matched
> its first three and left 1,059 characters of ciphertext under a marker
> saying the token was gone -- worse than no match, because that marker is
> what a reader greps for to call the store clean.

## module, [line 124](../../../../../../../backend/src/sro/domain/observation/redaction.py#L124): Comment

Code: `(`

> The whole block and not just the BEGIN line, or the substitution would
> replace the header and leave the key material under a marker claiming it
> had been removed. The END clause is optional so a truncated capture still
> loses its opening line.

## module, [line 133](../../../../../../../backend/src/sro/domain/observation/redaction.py#L133): Comment

Code: `("bearer", r"\bbearer\s+[A-Za-z0-9._~+/-]{20,}"),`

> A scheme name plus a blob, and so case-blind -- kept apart from the set
> above because `AKIA`, `AIza` and `eyJ` are case-SENSITIVE prefixes that a
> blind match would widen over the lowercase identifiers this corpus is
> full of.

## module, [line 171](../../../../../../../backend/src/sro/domain/observation/redaction.py#L171): Comment

Code: `OAUTH_COMPANIONS = frozenset(`

> An OAuth authorization code is a credential; a warehouse `code` is not.
> `code` cannot join SECRET_WORDS -- that rule matches whole words, and this
> tenant's captured traffic carries 138 distinct field names ending in one
> (areaCode, locationCode, pickZoneCode, verificationCode...). So the rule is
> narrowed twice: the parameter must be named *exactly* `code`, not merely
> contain the word, and the same query or fragment must carry another OAuth
> parameter beside it -- which is what tells a callback hop from an ordinary
> call. Measured over 23,751 URLs in that capture: no `code` parameter and no
> `state` parameter appear at all, and the three query names containing "code"
> (areaCode, operationCode, barCodeTemplateId) are untouched by an exact match.
> This costs no live evidence and closes the last row of the audit's table.

## `redact_url`, [line 212](../../../../../../../backend/src/sro/domain/observation/redaction.py#L212): Comment

Code: `return redact_shapes(head if hash_at == -1 else f"{head}#{_redact_fragment(fragment)}")`

> The shape pass runs over the whole rebuilt URL rather than only the
> query, because a token can sit in a path segment where there is no
> parameter name to judge it by. It substitutes, so a URL carrying no
> credential comes back byte-identical -- the property the hand-splicing
> above exists to keep.

## module, [line 224](../../../../../../../backend/src/sro/domain/observation/redaction.py#L224): Comment

Code: `_PAIR = re.compile(r"([A-Za-z_][\w.-]*)(\s*[=:]\s*)([^\s&;,]*)")`

> Any `name=value` or `name: value` pair, wherever it sits in an otherwise
> unstructured body. The parsers above each want a whole well-formed document;
> this wants only a field name next to a field value, which is all a
> name-based rule needs to act -- and is what catches a graphql mutation.

## `_redact_json`, [line 253](../../../../../../../backend/src/sro/domain/observation/redaction.py#L253): Comment

Code: `return UNINSPECTABLE`

> Not the document it claimed to be: truncated, or never JSON at all.
> Replaced whole rather than stored unexamined -- see redact_body.

## `_redact_json`, [line 255](../../../../../../../backend/src/sro/domain/observation/redaction.py#L255): Comment

Code: `return json.dumps(_redact_pairs(document), ensure_ascii=False)`

> A bare JSON string is a document too, and `"password=hunter2"` is
> what one looks like when it carries a credential.

## `_redact_json`, [line 257](../../../../../../../backend/src/sro/domain/observation/redaction.py#L257): Comment

Code: `return text if cleaned == document else json.dumps(cleaned, ensure_ascii=False)`

> ensure_ascii=False for the same reason the query string is spliced rather
> than re-encoded: the default writes the marker as \u00abredacted\u00bb,
> and then grepping stored evidence for «redacted» finds nothing. The
> extension's JSON.stringify writes it literally; so does this.
>
> Unchanged means unchanged: the original bytes, not a reserialisation.

## `_redact_fragment`, [line 215](../../../../../../../backend/src/sro/domain/observation/redaction.py#L215): Docstring

> The same fragment rule as `recording/sensitivity.py`'s `_redact_fragment`: a
> hash router's own query (`#/done?code=...`) is judged as a query. See there.
