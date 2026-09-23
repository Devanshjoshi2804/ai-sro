# Notes for `backend/src/sro/infrastructure/vault/secret_manager.py`

Comments and docstrings moved out of [`backend/src/sro/infrastructure/vault/secret_manager.py`](../../../../../../../backend/src/sro/infrastructure/vault/secret_manager.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/infrastructure/vault/secret_manager.py#L1): Docstring

> The deployed vault: Google Secret Manager, behind the same port.
>
> `file_vault` is the laptop and the single node, and says so in its own first
> line: *swapping this for a cloud secret manager is one adapter*. This is that
> adapter, written before the deploy rather than during it, so the first time
> this runs against a real project is not also the first time anybody finds out
> what its ids may contain.
>
> **Nothing above this line changes.** `CredentialVault` is three methods, and
> the run path, the planner and the route that stores one know only those three.
> What is here is the translation and the failure modes.
>
> **Ids are not keys.** A vault key is `tenant/system/field` -- the shape
> `Connection.credential_key` has always used and `domain/execution/secrets`
> builds -- and Secret Manager ids allow only letters, digits, `_` and `-`, up
> to 255 characters. So the key is mapped, and the mapping is collision-proof
> rather than merely tidy: a plain substitution would put `a/b` and `a-b` in the
> same secret, which is one tenant reading another tenant's password.
>
> **A missing secret is `None` and a broken project is an exception.** The port
> says callers decide what absence means, and they do: a step that finds no
> password refuses by name and says which key it wanted. Losing the network,
> being denied by IAM, or naming a project that does not exist are not absence
> -- they are `VaultUnavailable`, which is what the port promises instead of a
> quiet fallback to plaintext.
>
> **The client is synchronous.** Every call here runs in a worker thread, so a
> run parked on a password does not stop the event loop that is driving
> somebody's browser.

## module, [line 11](../../../../../../../backend/src/sro/infrastructure/vault/secret_manager.py#L11): Note on the line above

Code: `MAX_ID = 255`

> Secret Manager's own limit on a secret id.

## module, [line 15](../../../../../../../backend/src/sro/infrastructure/vault/secret_manager.py#L15): Note on the line above

Code: `_DIGEST = 12`

> How much of the key's hash rides along. Enough that two keys colliding is
> not a thing that happens; short enough to leave the readable part readable.

## `secret_id_for`, [line 18](../../../../../../../backend/src/sro/infrastructure/vault/secret_manager.py#L18): Docstring

> A vault key as a Secret Manager id: readable, and never ambiguous.
>
> `new/keycloak.example/password` becomes
> `new_keycloak-example_password__a1b2c3d4e5f6`.
>
> The suffix is not decoration. Substitution alone is lossy -- `a/b` and
> `a-b` both flatten to `a-b` -- and two tenants whose ids differ only where
> the substitution bites would share one secret, which is one of them reading
> the other's password. The digest is of the ORIGINAL key, so the mapping is
> one-way, deterministic across processes, and injective in practice.
>
> Truncated from the front of the readable part rather than the back, because
> the tail of these keys is the field and the head is the tenant: a truncated
> id that keeps `…/password` and loses which tenant it belongs to is the one
> shape that would be worse than unreadable.

## `_Secrets`, [line 25](../../../../../../../backend/src/sro/infrastructure/vault/secret_manager.py#L25): Docstring

> The three calls this adapter makes, named so a test can stand in.
>
> Not the client's whole surface: a fake that had to implement everything
> `SecretManagerServiceClient` offers would be a fake nobody writes, and the
> three below are the whole of what a vault is.

## `SecretManagerVault`, [line 32](../../../../../../../backend/src/sro/infrastructure/vault/secret_manager.py#L32): Docstring

> One Google project's secrets, as the vault this system already has.

## `_real_client`, [line 95](../../../../../../../backend/src/sro/infrastructure/vault/secret_manager.py#L95): Docstring

> The Google client, imported only when a deployment asks for it.
>
> At module scope this import would make `google-cloud-secret-manager` a
> dependency of running the test suite on a laptop, which is the opposite of
> what the optional extra is for. The message names the extra, because "no
> module named google.cloud" is a sentence nobody can act on at three in the
> morning.

## `SecretManagerVault.store`, [line 42](../../../../../../../backend/src/sro/infrastructure/vault/secret_manager.py#L42): Docstring

> Write a secret, creating it the first time.
>
> Two calls, because Secret Manager separates the container from its
> versions: `create_secret` once, then a version per write. A key that
> already exists takes the second call alone -- `AlreadyExists` is the
> ordinary path here, not an error, since rotation is what this method is
> for.

## `SecretManagerVault._store`, [line 49](../../../../../../../backend/src/sro/infrastructure/vault/secret_manager.py#L49): Comment

Code: `with contextlib.suppress(exceptions.AlreadyExists):`

> `AlreadyExists` is the ordinary path, not an error: rotation is
> what `store` is for, and the container outlives every version in
> it.

## `SecretManagerVault._store`, [line 54](../../../../../../../backend/src/sro/infrastructure/vault/secret_manager.py#L54): Comment

Code: `"secret": {"replication": {"automatic": {}}},`

> Replicated wherever the project says. A vault that
> pinned a region here would be a vault that stops
> working in the deployment that pins a different one.

## `SecretManagerVault._get`, [line 74](../../../../../../../backend/src/sro/infrastructure/vault/secret_manager.py#L74): Comment

Code: `return None`

> Absence, which the port says callers decide the meaning of. A
> step that types a password decides it means "nobody stored one"
> and refuses by name.

## `SecretManagerVault._get`, [line 76](../../../../../../../backend/src/sro/infrastructure/vault/secret_manager.py#L76): Comment

Code: `raise VaultUnavailable(f"the secret store could not be read: {refused}") from refused`

> Everything else is the store being unusable -- denied by IAM, a
> project that does not exist, no network. Not absence: answering
> `None` here would tell a run that nobody had stored a password
> when the truth is that nobody could ask.

## `SecretManagerVault._delete`, [line 90](../../../../../../../backend/src/sro/infrastructure/vault/secret_manager.py#L90): Comment

Code: `return`

> Idempotent, as the port requires: deleting an absent key is
> success and not an error.

## `_real_client`, [line 99](../../../../../../../backend/src/sro/infrastructure/vault/secret_manager.py#L99): Comment

Code: `raise VaultUnavailable(`

> Building the client is where credentials are resolved, and a machine
> with none raises `DefaultCredentialsError` -- which is not a
> `VaultUnavailable`, so it came out of `build_container` and took the
> whole API down at import. Found by running it rather than by reading
> it: a deployment with `SRO_VAULT_PROJECT` set and no application
> credentials would not have started at all, and the message would have
> named Google's documentation rather than this setting.
>
> Now it is the vault refusing, which `_build_vault` already knows how
> to hold: the API starts, reading recordings and reviewing skills work
> as they always did, and the refusal arrives at the one step that
> actually needs a secret.
