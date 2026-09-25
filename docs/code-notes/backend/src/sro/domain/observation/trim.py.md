# Notes for `backend/src/sro/domain/observation/trim.py`

Comments and docstrings moved out of [`backend/src/sro/domain/observation/trim.py`](../../../../../../../backend/src/sro/domain/observation/trim.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/domain/observation/trim.py#L1): Docstring

> A2 — what one gesture looks like to the model that reads it.
>
> Token discipline, because A3 runs once per gesture and a day is thousands of
> them. css_path and xpath are excluded on purpose: long, meaningless to a model,
> and the two locators that break. The runner still reads them from the stored row.
>
> Ported from `new_agent_arch/src/rig/trim.py`. `body_keys` below is the
> prompt-side belt: the wire's `Request` already redacted a body on its way to the
> store, and this runs the same rules again on the way to the model. Those rules
> are `sro.domain.observation.redaction`, which came out of the rig's wire module
> with this file and was split back out of it -- one address for the credential
> vocabulary, imported by both belts.

## `thin`, [line 15](../../../../../../../backend/src/sro/domain/observation/trim.py#L15): Docstring

> True when nothing here would tell a model what the control is.
>
> A targetless gesture (a scroll) is thin by definition -- there is no
> control to name.

## `path_shape`, [line 29](../../../../../../../backend/src/sro/domain/observation/trim.py#L29): Docstring

> /data/WM/wm/addresses/1183 -> /data/WM/wm/addresses/*

## `looks_like_an_id`, [line 34](../../../../../../../backend/src/sro/domain/observation/trim.py#L34): Docstring

> Digits are what make a segment an id, not hyphens and length.
>
> The rule this replaced starred any long hyphenated segment, which erased
> ordinary route words -- /api/order-status became /api/* -- and still missed
> short numeric slugs like sku-123456.

## `body_keys`, [line 52](../../../../../../../backend/src/sro/domain/observation/trim.py#L52): Docstring

> Keys and short values. Never the prose, never the whole payload.
>
> The prompt-side belt. The wire's `Request` already redacted this text on its
> way to the store, and this runs again on the way to the model: two belts,
> neither relying on the other. Every one of the four ways out of here is
> redacted, which was the defect -- one of them was, and a form body with no
> mime type, a SOAP login, a JSON array and a bare JSON string took the other
> three.

## `is_secret`, [line 91](../../../../../../../backend/src/sro/domain/observation/trim.py#L91): Docstring

> Whether this gesture's value is a credential.
>
> Belt-and-braces: the wire parser already drops a credential value at parse
> time, but that validator does not re-run if a nested Target is mutated
> after the fact. A credential reaching a prompt is not a thing to hold by
> inheritance alone. A scroll has no target at all, so this falls back to
> gesture.action.secret alone.

## `body_keys`, [line 54](../../../../../../../backend/src/sro/domain/observation/trim.py#L54): Comment

Code: `if body is not None and body.redacted_fields:`

> "There was no body" and "there was a body and we declined to keep it"
> are different facts, and returning None for both told the model the
> first when the truth was the second. The extension names the failure
> in its own comment -- a suppressed body "reads to a reviewer as a body
> that was checked and found clean" -- and redacted_fields is where it
> says which: «not captured», «dropped: larger than the tenant's
> max_body_bytes». One key and one line, because this goes in a prompt.

## `body_keys`, [line 60](../../../../../../../backend/src/sro/domain/observation/trim.py#L60): Comment

Code: `return {"_": (redact_body(body.text, body.mime_type) or "")[:VALUE_CHARS]}`

> Unparseable, or parsed to something that has no keys at all: an
> array, a bare string. There is nothing to name, so the text goes in
> whole -- through the same rule the store's copy went through, which
> covers the shapes json.loads never sees.

## `body_keys`, [line 62](../../../../../../../backend/src/sro/domain/observation/trim.py#L62): Comment

Code: `fields: dict[object, object] = parsed`

> The name is kept and the value is not: that a login carried a password is
> worth reading, what the password was is not. redact_data recurses, because
> {"auth": {"password": ...}} is the same credential one level down and the
> flat version of this rule let it through.

## `_call`, [line 85](../../../../../../../backend/src/sro/domain/observation/trim.py#L85): Comment

Code: `"blocked": call.blocked_reason,`

> Carried for the same reason failure_reason is. A request the browser's
> own policy blocked has no status and no failure, so without this it
> arrives as `status: null, failed: null` -- indistinguishable from a
> call still in flight or one that vanished.
