# Notes for `backend/src/sro/application/execution/egress.py`

Comments and docstrings moved out of [`backend/src/sro/application/execution/egress.py`](../../../../../../../backend/src/sro/application/execution/egress.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/execution/egress.py#L1): Docstring

> What may leave the deployment, and the record of what did.
>
> Capture is storage and stays in the customer's infrastructure. Sending is a
> different decision, made per deployment, and this is the one place it happens
> for the vision rung. Two rules, in this order:
>
> 1. **Redact before sending, never after.** A screenshot taken while a password
>    field has focus is not sent at all; a text digest is stripped of anything a
>    credential field name identifies.
> 2. **Log what went, whether or not it worked.** A model call with no record of
>    what it saw is a hole in the audit trail exactly where an incident review
>    will look.

## module, [line 10](../../../../../../../backend/src/sro/application/execution/egress.py#L10): Note on the line above

Code: `_SECRET_ON_SCREEN = ("password", "passcode", "pin", "secret", "token", "otp", "mfa")`

> Words that, seen on a page, mean a credential is being entered. Matched on the
> digest rather than on the image, because we cannot read pixels here -- and when
> one appears the image is withheld rather than blurred.
>
> Matched as whole words. As substrings, "pin" is inside "shipping" and "picking",
> so a warehouse screen refused to be looked at for showing the word Shipping --
> and the rung that exists for screens nobody has demonstrated could not see any
> of them.
>
> A deliberate subset of ``SECRET_TOKENS`` rather than the whole of it: this
> refuses the entire screen, and "credential" or "ssn" appearing somewhere on a
> warehouse page is not reason enough to blind the rung. The check below keeps it
> a subset, so a word can be added there and considered here rather than the two
> drifting apart, which is how "passcode" came to be in one and not the other.
>
> A test keeps it a subset.

## `_words_on`, [line 13](../../../../../../../backend/src/sro/application/execution/egress.py#L13): Docstring

> The digest as separate lowercase words.
>
> Split on camel case as well as on punctuation, so ``passwordField`` still
> names a password while ``Shipping`` does not name a PIN.

## `EgressRefused`, [line 18](../../../../../../../backend/src/sro/application/execution/egress.py#L18): Docstring

> Nothing left the deployment, and the reason is worth recording.
>
> Refusing is a normal outcome: a deployment with egress switched off runs L1
> and L2 exactly as before, and a screen with a credential on it is never a
> screen worth a model's opinion.

## `prepare`, [line 27](../../../../../../../backend/src/sro/application/execution/egress.py#L27): Docstring

> The screen as it may be sent, or a refusal with its reason.

## `_strip`, [line 44](../../../../../../../backend/src/sro/application/execution/egress.py#L44): Docstring

> Drop any line naming a credential field.
>
> Line-wise because a digest is `label: value` pairs: removing the value alone
> would leave the label, and removing nothing would send the value. The field
> names that were dropped are returned, so the log says what went missing --
> a silent redaction is indistinguishable from a bug.
