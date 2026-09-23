# Notes for `backend/src/sro/application/connection/refusals.py`

Why the code in [`backend/src/sro/application/connection/refusals.py`](../../../../../../../backend/src/sro/application/connection/refusals.py) is the way it is. Each note names the code it explains (function or class, then the line in the current file).

## module, [line 1](../../../../../../../backend/src/sro/application/connection/refusals.py#L1): Docstring

> A password the system refused, remembered so nothing types it again.
>
> Submitting credentials once per attempt does not stop a lockout when
> attempts repeat: the session keeper signs in every pass, and a run's rescue
> rungs plan the password step again after the form came back. Each repeat
> spends the account's lockout budget, unattended.
>
> The refusal is kept against the credential itself -- its vault key, which is
> per tenant, login origin and field -- not against a connection. Measured on
> the deployed tenant (greyorange, QA box, 2026-09-23): the `connections`
> table is empty there and sign-in happens by running the mined login job,
> whose password step reads `<tenant>/<login origin>/password`. A latch on the
> connection would guard a path production does not take.

## module, [line 10](../../../../../../../backend/src/sro/application/connection/refusals.py#L10): Note on the line above

Code: `MARK = "#refused"`

> The refusal lives in the vault beside the secret, under the secret's own key
> plus this suffix. The vault is the one store both processes (API and worker)
> share that is already keyed exactly this way, and it puts the latch next to
> the thing whose lifecycle it follows. `#` never occurs in a key
> `secret_key_of` builds, so no real secret can be mistaken for a mark.

## `fingerprint`, [line 16](../../../../../../../backend/src/sro/application/connection/refusals.py#L16): Function

> The first 12 hex of sha256 over the vault key and the value. It binds a
> failed count and a refusal to the password they were about (task 10, fix
> rounds 1 and 2), is the run's in-run mark for a handed-out value, and is
> stored in the vault beside the password -- the same trust boundary.

## `RefusedCredentials.standing`, [line 35](../../../../../../../backend/src/sro/application/connection/refusals.py#L35): Docstring

> The standing refusal for this key, or None. A mark that cannot be parsed
> still counts as a refusal: the safe reading of a latch nobody can read is
> "latched". Given the current value, a refusal recorded with another
> value's fingerprint does not stand (task 10 fix round 2): a refusal
> written just after the operator stored a new password is about the old
> one, so the store/refuse race cannot refuse a password nobody submitted.
> A refusal without a fingerprint (older records) stands for any value.

## module, [line 11](../../../../../../../backend/src/sro/application/connection/refusals.py#L11): Constant

Code: `FAILED = "#failed"`

> The failed-attempt count, kept next to `#refused` under the secret's own key
> (audit wave 1, task 10, 2026-09-24). A count per run let every run spend one
> bad submit without limit on a system with no recorded sign-in job. The
> record holds a decimal count and a truncated keyed-hash fingerprint of the
> password it counted, in the same vault as the password itself.

## `FailedAttempts`, [line 52](../../../../../../../backend/src/sro/application/connection/refusals.py#L52): Class

> Failed sign-in attempts for one vault key, across runs, recorded as
> `"<count> <fingerprint>"`. The fingerprint is `fingerprint(key, value)` of
> the password it counted (task 10 fix round): a count read
> for another password -- or an old record with none -- starts again from
> zero, so a run that read the count, lost a race with the operator storing a
> new password and wrote its count back cannot bring the NEW password closer
> to a latch. `add` is still read, increment, write: two runs failing on the
> same password at the same moment can lose one increment, making the latch
> one attempt late.

## `ForgetsRefusalOnWrite`, [line 66](../../../../../../../backend/src/sro/application/connection/refusals.py#L66): Class

> The vault, wrapped so that writing a key lifts any refusal against it and
> clears its failed-attempt count (`#failed`, task 10). Writing or deleting a
> mark itself touches nothing else.
>
> New credentials are the one thing that can fix a refusal, and they arrive
> through several doors -- `PUT /v1/secrets` (which the panel's keep-secret box
> calls), the connection's credentials endpoint, anything added later. Doing
> it here, once, in the vault every one of them writes through, is what keeps
> a door from being forgotten. Installed in `build_container`.
>
> It costs two extra deletes per write, including the session cookies a
> refresh stores. Deleting a missing key is a no-op in the file vault and a
> handled NotFound in Secret Manager.
