"""Turn a header plan back into headers that can be sent.

The plan says where each value comes from; this resolves those sources. A header
whose source cannot be resolved stops the step -- sending the call without it
would produce a 401 or, worse, a call that succeeds as somebody else.
"""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlsplit

from sro.application.ports.vault import CredentialVault
from sro.domain.recording.sensitivity import Sensitivity
from sro.domain.skill.plan import HeaderPlan


def _system_of(credential_ref: str) -> str:
    return credential_ref.split("/", 1)[0]


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
    bearer: str | None = None,
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

    # A credential built to be held, where one exists. The cookies below are a
    # human's browser session: they work, and they expire on the identity
    # provider's schedule rather than on anything this system controls. An
    # offline token outlives the session that created it, so where there is one
    # it is what authenticates the call.
    if bearer:
        _put(headers, "Authorization", f"Bearer {bearer}")

    for plan in plans:
        if plan.managed and plan.name.lower() == "referer":
            # The page the application makes its calls from, when the session
            # recorded one. Blue Yonder's filter reads a per-session
            # `libraryContext` out of the Referer and redirects to the login
            # page without it -- so the executor sent a live cookie, a live
            # token, and still got a 302, which is indistinguishable from being
            # signed out. The origin remains the fallback.
            live = await vault.get(f"{scope}/{session_scope}/referer")
            if live:
                _put(headers, "referer", live)
            continue

        if plan.managed or plan.sensitivity is Sensitivity.TRANSPORT:
            continue  # the HTTP client owns these

        if plan.credential_ref is not None:
            if bearer and plan.name.lower() == "cookie":
                # Both would be sent otherwise, and a stale session cookie
                # beside a good token is how a call gets refused for the reason
                # that was just fixed.
                continue
            secret = await vault.get(f"{scope}/{plan.credential_ref}")
            if secret is None:
                # A skill names `<system>/<site>/cookie`; a login is to a
                # system. Falling back keeps a skill taught at one site usable
                # at another the same connection reaches.
                secret = await vault.get(f"{scope}/{_system_of(plan.credential_ref)}/cookie")
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


_ORIGIN_HEADERS = ("referer", "origin")


def client_headers(plans: tuple[HeaderPlan, ...], url: str) -> dict[str, str]:
    """Client-managed headers, set for *this* request rather than replayed.

    `Referer` and `Origin` are recorded as client-managed because the captured
    values describe the page a demonstration happened on, and replaying those is
    misleading. Omitting them altogether turned out to be worse: Blue Yonder's
    auth filter answers a same-origin API call with no `Referer` by redirecting
    to the login page, so every replayed read came back 302 with a live session
    in hand. A browser would have sent one; the executor sends the one that is
    true of the call it is actually making.
    """
    parts = urlsplit(url)
    if not parts.scheme or not parts.netloc:
        return {}
    origin = f"{parts.scheme}://{parts.netloc}"
    observed = {plan.name.lower() for plan in plans if plan.managed}

    headers: dict[str, str] = {}
    if "referer" in observed:
        headers["referer"] = f"{origin}/"
    if "origin" in observed:
        headers["origin"] = origin
    return headers


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
