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


async def resolve_headers(
    plans: tuple[HeaderPlan, ...],
    *,
    values: dict[str, str],
    vault: CredentialVault,
    scope: str,
    session_scope: str,
    bearer: str | None = None,
    browser_session: bool = False,
) -> ResolvedHeaders:
    headers: dict[str, str] = {}
    missing: list[str] = []

    if bearer:
        _put(headers, "Authorization", f"Bearer {bearer}")

    for plan in plans:
        if plan.managed and plan.name.lower() == "referer":
            live = await vault.get(f"{scope}/{session_scope}/referer")
            if live:
                _put(headers, "referer", live)
            continue

        if plan.managed or plan.sensitivity is Sensitivity.TRANSPORT:
            continue

        if plan.credential_ref is not None:
            if browser_session:
                continue
            if bearer and plan.name.lower() == "cookie":
                continue
            ref = plan.credential_ref
            if _system_of(ref) != _system_of(session_scope):
                ref = f"{session_scope}/{plan.name.lower()}"
            secret = await vault.get(f"{scope}/{ref}")
            if secret is None:
                secret = await vault.get(f"{scope}/{_system_of(ref)}/cookie")
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


def client_headers(plans: tuple[HeaderPlan, ...], url: str) -> dict[str, str]:
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
    for existing in list(headers):
        if existing.lower() == name.lower():
            del headers[existing]
    headers[name] = value
