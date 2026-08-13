"""Turn a header plan back into headers that can be sent.

The plan says where each value comes from; this resolves those sources. A header
whose source cannot be resolved stops the step -- sending the call without it
would produce a 401 or, worse, a call that succeeds as somebody else.
"""

from __future__ import annotations

from dataclasses import dataclass

from sro.application.ports.vault import CredentialVault
from sro.domain.recording.sensitivity import Sensitivity
from sro.domain.skill.plan import HeaderPlan


@dataclass(frozen=True, slots=True)
class ResolvedHeaders:
    headers: dict[str, str]
    missing: tuple[str, ...]
    """Names whose value could not be produced. Non-empty means: do not send."""


async def resolve_headers(
    plans: tuple[HeaderPlan, ...],
    *,
    values: dict[str, str],
    vault: CredentialVault,
    scope: str,
    session_scope: str,
) -> ResolvedHeaders:
    """``scope`` is the tenant whose session is used, prefixed onto every key.

    A skill's credential reference names a system and a site -- `blue_yonder/SG/
    cookie` -- and deliberately not a tenant, because the same skill is meant to
    be usable by whoever owns a login to that system. The tenant is supplied
    here, at the moment of resolution, so a run can only ever reach its own.
    ``session_scope`` is where minted headers live: `<system>/<facility>`.

    "Minted" is aspirational for headers whose algorithm is the target system's
    secret. Blue Yonder's `CSRF-ENCRYPT-TOKEN` is issued at login and cannot be
    computed here, so what the executor does is fetch the live one belonging to
    the connected session. That is the same trust boundary as the cookie, and it
    keeps the value out of the skill.
    """
    headers: dict[str, str] = {}
    missing: list[str] = []

    for plan in plans:
        if plan.managed or plan.sensitivity is Sensitivity.TRANSPORT:
            continue  # the HTTP client owns these

        if plan.credential_ref is not None:
            secret = await vault.get(f"{scope}/{plan.credential_ref}")
            if secret is None:
                missing.append(plan.name)
            else:
                _put(headers, plan.name, secret)
            continue

        if plan.mint:
            live = await vault.get(f"{scope}/{session_scope}/{plan.name.lower()}")
            if live is None:
                missing.append(plan.name)
            else:
                _put(headers, plan.name, live)
            continue

        if plan.value is not None:
            _put(headers, plan.name, plan.value.render(values))

    return ResolvedHeaders(headers=headers, missing=tuple(dict.fromkeys(missing)))


def _put(headers: dict[str, str], name: str, value: str) -> None:
    """Last spelling wins, case-insensitively.

    A capture holds both `Content-Type` and `content-type` because CDP reports
    the request twice over; sending both is at best redundant and at worst two
    conflicting values of one header.
    """
    for existing in list(headers):
        if existing.lower() == name.lower():
            del headers[existing]
    headers[name] = value
