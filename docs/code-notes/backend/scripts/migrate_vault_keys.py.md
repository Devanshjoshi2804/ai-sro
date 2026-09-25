# Notes for `backend/scripts/migrate_vault_keys.py`

Comments and docstrings moved out of [`backend/scripts/migrate_vault_keys.py`](../../../../backend/scripts/migrate_vault_keys.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../backend/scripts/migrate_vault_keys.py#L1): Docstring

> The one-shot QA vault key migration.
>
> S1 changed vault keys from `{tenant}/{credential origin}/password` to
> `{tenant}/{credential origin}/{encoded username}/password`, built by
> `Account.vault_key`. QA's passwords were stored under the old key, recorded
> before S1, and the new scheme has no fallback to it — a sign-in job that used
> to find its password finds nothing until this runs.
>
> `make migrate-vault-keys` (dry-run), then `--apply` on QA. `--delete-old` is
> a separate, later run: the user makes it only after QA-1 passes, never on
> the same pass as the copy.

## `_jobs_and_gestures`, [line 25](../../../../backend/scripts/migrate_vault_keys.py#L25): Note on the function

> Same shape as `sro.application.connection.sign_in._recorded`: every
> `signs_in` job's cited gestures, widened to the gestures in the sitting
> around them (`K_SITTING_GAP_S`), because `signs_in_to` and `recorded_login`
> both read past the cited set to find where a session lands. One query per
> tenant's whole set of sign-in jobs rather than one per job — QA has few
> tenants and few sign-in jobs, and a per-job round trip buys nothing a batch
> doesn't already give it.
>
> Only jobs decided true move; an undecided job (`signs_in` NULL) is never
> taken for a sign-in job. The count of undecided jobs is printed per tenant
> so the operator knows to wait for a mining sweep and run the script again.

## `_migrate_job`, [line 48](../../../../backend/scripts/migrate_vault_keys.py#L48): Note on the function

> The new key is never hand-assembled: `Account.of(...).vault_key("password")`
> is the one function S1 built for this, and a key built any other way is a
> key the runtime's own reader would not recognise. `recorded.origin` already
> passed through `origin_of` once (inside `signs_in_to`/`recorded_login`), and
> `Account.of` runs it through `origin_of` again — verified idempotent — so
> this never double-encodes the origin.
>
> Read-before-write on the new key is what makes a second run a no-op: a key
> already there is left alone rather than overwritten, so an operator's own
> `PUT /v1/secrets` write after the first migration is never clobbered by a
> second `--apply`.
>
> `--delete-old` only ever removes a key this same call confirmed still holds
> the value that made it to (or already sits at) the new key — never a delete
> with no corresponding copy on record.

## `main`, [line 123](../../../../backend/scripts/migrate_vault_keys.py#L123): Note on the function

> `--dry-run` wins over `--apply` if both are given, because the flag that
> guarantees nothing is written should never lose a race with the one that
> writes. The default with neither flag given is the same dry run.
