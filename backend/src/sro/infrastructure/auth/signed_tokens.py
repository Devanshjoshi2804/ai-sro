"""Credentials this deployment signs itself.

A JWT-shaped token with an HMAC over it: header, claims, signature, all
base64url, so anything that reads JWTs can read these. Written against the
standard library rather than a JWT package on purpose -- the whole of it is
sixty lines that can be audited in one sitting, and the alternative is a
dependency whose defaults decide who gets in.

What it is not: an identity provider. There are no passwords here, no refresh
flow and no revocation list. A token is minted for an operator by somebody with
shell access, it expires, and a compromised one is dealt with by rotating the
signing key. That is the honest shape for a system whose customers will bring
their own SSO -- and it is the difference between a boundary and a decoration.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time

from sro.application.ports.auth import Caller, CredentialRejected, Credentials, Unconfigured
from sro.domain.shared.identifiers import PrincipalId, TenantId

ALGORITHM = "HS256"
_HEADER: dict[str, object] = {"alg": ALGORITHM, "typ": "JWT"}


class SignedTokens(Credentials):
    def __init__(self, secret: str) -> None:
        # Not a default, not a generated-per-boot value: a deployment that
        # signs with a key nobody wrote down accepts nothing after a restart,
        # and one that signs with a default accepts everybody's tokens.
        self._secret = secret.encode() if secret else b""

    def issue(self, caller: Caller, *, lasting_hours: float = 24 * 30) -> str:
        now = int(time.time())
        claims: dict[str, object] = {
            "sub": caller.principal_id.value,
            "ten": caller.tenant_id.value,
            "iat": now,
            "exp": now + int(lasting_hours * 3600),
        }
        signing_input = f"{_encode(_HEADER)}.{_encode(claims)}"
        return f"{signing_input}.{_b64(self._sign(signing_input))}"

    def verify(self, presented: str) -> Caller:
        if not self._secret:
            raise Unconfigured(
                "SRO_AUTH_SECRET is not set, so no credential can be checked. "
                "Generate one with `make auth-secret`."
            )

        parts = presented.strip().removeprefix("Bearer ").strip().split(".")
        if len(parts) != 3:
            raise CredentialRejected("not a credential this system issued")
        header_part, claims_part, signature = parts

        # Compared in constant time, and before anything in the token is read:
        # a signature checked after the claims are trusted is not a check.
        expected = self._sign(f"{header_part}.{claims_part}")
        if not hmac.compare_digest(_b64(expected), signature):
            raise CredentialRejected("this credential was not signed by us")

        try:
            claims = json.loads(_debase(claims_part))
        except (ValueError, TypeError) as exc:
            raise CredentialRejected("this credential is malformed") from exc

        if not isinstance(claims, dict):
            raise CredentialRejected("this credential is malformed")
        expires = claims.get("exp")
        if not isinstance(expires, int) or expires <= time.time():
            raise CredentialRejected("this credential has expired")

        tenant, principal = claims.get("ten"), claims.get("sub")
        if not isinstance(tenant, str) or not isinstance(principal, str):
            raise CredentialRejected("this credential names no caller")
        return Caller(tenant_id=TenantId(tenant), principal_id=PrincipalId(principal))

    def _sign(self, signing_input: str) -> bytes:
        return hmac.new(self._secret, signing_input.encode(), hashlib.sha256).digest()


def _encode(payload: dict[str, object]) -> str:
    return _b64(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode())


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _debase(part: str) -> bytes:
    return base64.urlsafe_b64decode(part + "=" * (-len(part) % 4))
