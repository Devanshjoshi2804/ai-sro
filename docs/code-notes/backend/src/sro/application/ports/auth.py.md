# Notes for `backend/src/sro/application/ports/auth.py`

Comments and docstrings moved out of [`backend/src/sro/application/ports/auth.py`](../../../../../../../backend/src/sro/application/ports/auth.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/ports/auth.py#L1): Docstring

> Who is asking.
>
> Until now the answer came from a header the caller wrote themselves, which
> means the tenant boundary this system is built around was decoration: anybody
> who could reach the port could read another customer's recordings and send
> writes into their WMS under any name they liked.
>
> The port is narrow because the surface that decides identity should be small
> enough to read in one sitting. One thing turns a credential into a caller, and
> one thing mints credentials, and they live behind this file.

## `Caller`, [line 12](../../../../../../../backend/src/sro/application/ports/auth.py#L12): Note on the line above

Code: `principal_id: PrincipalId`

> The human or service the credential was issued to. This is what a write
> records as its authorisation -- never a name supplied in the request, which
> is a signature nobody checked.

## `CredentialRejected`, [line 15](../../../../../../../backend/src/sro/application/ports/auth.py#L15): Docstring

> Not a valid credential: absent, expired, tampered with, or signed by a
> key this deployment does not hold. The reason is never narrowed for the
> caller, because the difference is only useful to somebody guessing.

## `Unconfigured`, [line 18](../../../../../../../backend/src/sro/application/ports/auth.py#L18): Docstring

> This deployment cannot verify anybody. Distinct from a rejection: the
> fault is ours, the answer is 503, and it must never be read as permission.

## `Credentials.verify`, [line 22](../../../../../../../backend/src/sro/application/ports/auth.py#L22): Docstring

> The caller this credential belongs to, or raise.

## `Credentials.issue`, [line 24](../../../../../../../backend/src/sro/application/ports/auth.py#L24): Docstring

> A credential for this caller. Used by the CLI that onboards someone,
> and by nothing that a request can reach.
