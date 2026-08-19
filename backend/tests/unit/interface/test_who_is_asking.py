"""The tenant boundary, checked rather than claimed.

Every use case reads its tenant from the request context, so for as long as
that context came from a header the caller typed, the isolation this system is
built around could be crossed by typing a different value -- and a write into
somebody's warehouse could be attributed to a name nobody verified.
"""

from __future__ import annotations

import time

import pytest

from sro.application.ports.auth import Caller, CredentialRejected, Unconfigured
from sro.domain.shared.identifiers import PrincipalId, TenantId
from sro.infrastructure.auth.signed_tokens import SignedTokens

SECRET = "the-key-this-deployment-signs-with"  # noqa: S105 -- not a credential
CALLER = Caller(tenant_id=TenantId("acme"), principal_id=PrincipalId("devansh.j"))


def test_a_credential_names_the_caller_it_was_issued_to() -> None:
    tokens = SignedTokens(SECRET)

    assert tokens.verify(tokens.issue(CALLER, lasting_hours=1)) == CALLER


def test_the_bearer_prefix_is_accepted_because_that_is_how_it_arrives() -> None:
    tokens = SignedTokens(SECRET)

    assert tokens.verify(f"Bearer {tokens.issue(CALLER, lasting_hours=1)}") == CALLER


def test_a_token_signed_by_somebody_else_is_refused() -> None:
    """The whole point: another deployment's key does not open this one."""
    theirs = SignedTokens("a-different-deployments-key").issue(CALLER, lasting_hours=1)

    with pytest.raises(CredentialRejected):
        SignedTokens(SECRET).verify(theirs)


def test_changing_the_tenant_in_a_token_invalidates_it() -> None:
    """The attack this exists to stop: same token, somebody else's data."""
    tokens = SignedTokens(SECRET)
    header, _mine, signature = tokens.issue(CALLER, lasting_hours=1).split(".")
    other = tokens.issue(
        Caller(tenant_id=TenantId("rival"), principal_id=PrincipalId("devansh.j")),
        lasting_hours=1,
    ).split(".")[1]

    with pytest.raises(CredentialRejected):
        tokens.verify(f"{header}.{other}.{signature}")


def test_an_expired_credential_is_refused() -> None:
    tokens = SignedTokens(SECRET)

    expired = tokens.issue(CALLER, lasting_hours=-1)

    with pytest.raises(CredentialRejected):
        tokens.verify(expired)


def test_a_credential_that_never_expires_cannot_be_issued() -> None:
    """Every token carries an expiry, so a leaked one stops working."""
    claims = SignedTokens(SECRET).issue(CALLER, lasting_hours=1).split(".")[1]

    import base64
    import json

    decoded = json.loads(base64.urlsafe_b64decode(claims + "=" * (-len(claims) % 4)))
    assert decoded["exp"] > time.time()


def test_nonsense_is_refused_rather_than_crashing() -> None:
    tokens = SignedTokens(SECRET)

    for presented in ("", "hello", "a.b", "a.b.c", "Bearer ..."):
        with pytest.raises(CredentialRejected):
            tokens.verify(presented)


def test_without_a_signing_key_nothing_is_accepted() -> None:
    """Not even a token this process just minted: a deployment that cannot
    check credentials must refuse, and 503 is not a way in."""
    with pytest.raises(Unconfigured):
        SignedTokens("").verify(SignedTokens(SECRET).issue(CALLER, lasting_hours=1))
