# Notes for `backend/src/sro/application/ports/vault.py`

Comments and docstrings moved out of [`backend/src/sro/application/ports/vault.py`](../../../../../../../backend/src/sro/application/ports/vault.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/ports/vault.py#L1): Docstring

> Where secrets live.
>
> Nothing in the evidence plane, the skill plane or a log ever holds a credential
> value. They hold a *key* into this, and the value is fetched at the moment it is
> needed. That is what makes a recording safe to keep and a skill safe to share
> between sites.

## `VaultUnavailable`, [line 14](../../../../../../../backend/src/sro/application/ports/vault.py#L14): Docstring

> No usable secret store. Not a ``DomainError``: the request was fine.
>
> Raised rather than falling back to plaintext. A vault that quietly degrades
> into a file of readable passwords is worse than one that refuses to start,
> because nothing downstream can tell the difference.

## `CredentialVault.store`, [line 7](../../../../../../../backend/src/sro/application/ports/vault.py#L7): Docstring

> Write a secret. Overwrites: rotation is an ordinary event.

## `CredentialVault.get`, [line 9](../../../../../../../backend/src/sro/application/ports/vault.py#L9): Docstring

> Read a secret. ``None`` when absent -- callers decide what that means.

## `CredentialVault.delete`, [line 11](../../../../../../../backend/src/sro/application/ports/vault.py#L11): Docstring

> Idempotent: deleting an absent key is success, not an error.
