# Notes for `backend/src/sro/domain/recording/redaction.py`

Comments and docstrings moved out of [`backend/src/sro/domain/recording/redaction.py`](../../../../../../../backend/src/sro/domain/recording/redaction.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/domain/recording/redaction.py#L1): Docstring

> Credential removal, at every point of capture.
>
> Everything a demonstration does is evidence and is kept verbatim -- with one
> exception. A password is not evidence of what happened; it is a key to the
> customer's system, and keeping it would turn the evidence store into a
> credential store with none of the handling that implies.
>
> So credentials are removed here, before a body is ever written, rather than
> filtered on the way out. Matched by field name, because a name is a decision the
> target system already made; guessing from values would redact real business
> data. What is kept is the field name, so a reviewer sees what was removed.
>
> Domain rather than ``infrastructure.steel``, where this lived while Steel was
> the only thing that captured a body. It is not: the observation ingest path
> takes bodies straight from an operator's own browser, and the layering rule --
> application never imports an adapter -- meant the one body redactor in the
> codebase was unreachable from the one path that was storing bodies unredacted.
> Stdlib only, so the move is a relocation and not a rewrite.

## module, [line 71](../../../../../../../backend/src/sro/domain/recording/redaction.py#L71): Note on the line above

Code: `_XML_FIELD = re.compile(r"<([A-Za-z_][\w.:-]*)([^>]*)>([^<]*)</\1>")`

> Leaf elements only -- the ones with a value in them rather than more
> elements. Matching containers as well would have the outermost match eat the
> whole document and never reach the field inside it.

## `redact_body`, [line 11](../../../../../../../backend/src/sro/domain/recording/redaction.py#L11): Docstring

> Return the body with credential values removed, and what removed them.
>
> Two rules, and a value goes if EITHER fires. The name rule below is the
> secondary one and has to be: a field name is chosen by whoever wrote the
> vendor's API, an open vocabulary guessed at forever. The shape rule needs
> no name, so it runs last and over whatever the parsers produced -- reaching
> a credential in a field nobody thought to list, and through a body no
> parser here fitted at all.
>
> A shape is reported as `«shape: jwt»` rather than as a field name, because
> "we removed this because it looked like a JWT" is a different fact from
> "we removed this because it was called password". The marker left in the
> text is the same either way, so nothing downstream learns a second
> convention.

## `_redact_xml`, [line 75](../../../../../../../backend/src/sro/domain/recording/redaction.py#L75): Docstring

> Elements and attributes whose name says credential.
>
> SOAP is not a museum piece in this trade -- a WMS that speaks it puts the
> password in ``<Password>`` -- and nothing here looked at XML at all, so
> those bodies were stored exactly as sent.
>
> Textual rather than parsed on purpose: a captured body may be truncated or
> malformed, and a parser that refuses it would redact nothing at all.

## `_redact_multipart`, [line 100](../../../../../../../backend/src/sro/domain/recording/redaction.py#L100): Docstring

> A part whose ``name=`` says credential loses its content.
>
> Boundary-agnostic: the boundary is whatever the first line says it is, and
> a body whose parts cannot be told apart is left alone rather than mangled.

## `redact_body`, [line 11](../../../../../../../backend/src/sro/domain/recording/redaction.py#L11): Comment

Code: `def redact_body(text: str, *, content_type: str | None) -> tuple[str, tuple[str, ...]]:`

> ^ Re-exported deliberately: capture.py imports the marker from here, and
> there is one marker for every path that writes it.

## `_redact_named`, [line 24](../../../../../../../backend/src/sro/domain/recording/redaction.py#L24): Comment

Code: `return _redact_xml(text)`

> Before the form heuristic below, which is "has an = and one line" --
> true of every one-line XML document with an attribute in it.

## `_redact_json.walk`, [line 45](../../../../../../../backend/src/sro/domain/recording/redaction.py#L45): Comment

Code: `removed.append(str(key))`

> Whatever shape it is. This used to require a scalar, so
> ``{"password": ["hunter2"]}`` was written to the evidence
> store verbatim and reported as nothing removed -- and a
> list is exactly what an HTML form with a repeated field
> produces.

## `_redact_json`, [line 55](../../../../../../../backend/src/sro/domain/recording/redaction.py#L55): Comment

Code: `return (json.dumps(cleaned_document, ensure_ascii=False) if removed else text), tuple(`

> ``ensure_ascii=False`` because the default escapes the marker this very
> function just wrote to ``\u00abredacted\u00bb``, along with any the
> browser had already put in the same body -- and then a reviewer grepping
> the evidence store for «redacted» finds neither. Measured over the 395
> stored batches: 15 bodies came back with escaped markers.
