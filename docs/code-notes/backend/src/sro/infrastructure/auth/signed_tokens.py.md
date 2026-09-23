# Notes for `backend/src/sro/infrastructure/auth/signed_tokens.py`

Comments and docstrings moved out of [`backend/src/sro/infrastructure/auth/signed_tokens.py`](../../../../../../../backend/src/sro/infrastructure/auth/signed_tokens.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/infrastructure/auth/signed_tokens.py#L1): Docstring

> Credentials this deployment signs itself.
>
> A JWT-shaped token with an HMAC over it: header, claims, signature, all
> base64url, so anything that reads JWTs can read these. Written against the
> standard library rather than a JWT package on purpose -- the whole of it is
> sixty lines that can be audited in one sitting, and the alternative is a
> dependency whose defaults decide who gets in.
>
> What it is not: an identity provider. There are no passwords here, no refresh
> flow and no revocation list. A token is minted for an operator by somebody with
> shell access, it expires, and a compromised one is dealt with by rotating the
> signing key. That is the honest shape for a system whose customers will bring
> their own SSO -- and it is the difference between a boundary and a decoration.

## `SignedTokens.__init__`, [line 18](../../../../../../../backend/src/sro/infrastructure/auth/signed_tokens.py#L18): Comment

Code: `self._secret = secret.encode() if secret else b""`

> Not a default, not a generated-per-boot value: a deployment that
> signs with a key nobody wrote down accepts nothing after a restart,
> and one that signs with a default accepts everybody's tokens.

## `SignedTokens.verify`, [line 43](../../../../../../../backend/src/sro/infrastructure/auth/signed_tokens.py#L43): Comment

Code: `expected = self._sign(f"{header_part}.{claims_part}")`

> Compared in constant time, and before anything in the token is read:
> a signature checked after the claims are trusted is not a check.
