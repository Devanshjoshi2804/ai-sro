"""Issue a credential for an operator. Shell access only, on purpose.

Lives beside the composition root rather than under `interface`, because it
binds to an adapter by name and `interface` may not: a router reaching an
adapter directly is how a deployment ends up unable to swap one.

There is no self-service sign-up and no password store: somebody who can run
this on the box hands a token to somebody who needs one, and it expires. That
is the right amount of identity for a system whose customers will bring their
own SSO, and it is enough to make the tenant boundary real.

    python -m sro.cli.mint acme devansh.j --days 30
"""

from __future__ import annotations

import argparse
import sys

from sro.application.ports.auth import Caller, Unconfigured
from sro.config import get_settings
from sro.domain.shared.identifiers import PrincipalId, TenantId
from sro.infrastructure.auth.signed_tokens import SignedTokens


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Issue an AI-SRO credential.")
    parser.add_argument("tenant", help="the tenant this credential can see, e.g. acme")
    parser.add_argument("principal", help="who it is for, e.g. devansh.j")
    parser.add_argument("--days", type=float, default=30.0)
    args = parser.parse_args(argv)

    secret = get_settings().auth_secret
    if not secret:
        print(
            "SRO_AUTH_SECRET is not set, so nothing can be signed. "
            "Generate one with `make auth-secret` and put it in the environment.",
            file=sys.stderr,
        )
        return 2

    token = SignedTokens(secret).issue(
        Caller(tenant_id=TenantId(args.tenant), principal_id=PrincipalId(args.principal)),
        lasting_hours=args.days * 24,
    )
    # The token itself on stdout and nothing else, so it can be piped without
    # a human having to cut a banner off it.
    print(token)
    return 0


if __name__ == "__main__":  # pragma: no cover - entry point
    try:
        raise SystemExit(main())
    except Unconfigured as exc:  # pragma: no cover - defensive
        print(str(exc), file=sys.stderr)
        raise SystemExit(2) from exc
