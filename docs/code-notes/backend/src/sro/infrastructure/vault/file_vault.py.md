# Notes for `backend/src/sro/infrastructure/vault/file_vault.py`

Comments and docstrings moved out of [`backend/src/sro/infrastructure/vault/file_vault.py`](../../../../../../../backend/src/sro/infrastructure/vault/file_vault.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/infrastructure/vault/file_vault.py#L1): Docstring

> Encrypted file vault.
>
> The development and single-node deployment story, behind the same port a real
> secret manager will use. Two properties it does not compromise on:
>
> - **No key, no vault.** Without ``SRO_VAULT_KEY`` it refuses to start rather than
>   writing plaintext. A store that silently degrades is worse than one that
>   stops, because nothing downstream can tell.
> - **The file is unreadable without the key**, so a backup, a stray copy or a
>   laptop does not leak the customer's WMS login.
>
> Swapping this for Vault or a cloud secret manager is one adapter.

## `FileCredentialVault._write`, [line 59](../../../../../../../backend/src/sro/infrastructure/vault/file_vault.py#L59): Comment

Code: `temporary = self._path.with_suffix(".tmp")`

> Written via a temp file in the same directory so a crash mid-write
> cannot leave a half-file that decrypts to nothing.
