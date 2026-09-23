from __future__ import annotations

import json
from dataclasses import dataclass
from urllib.parse import urlencode, urlsplit, urlunsplit

from sro.application.context import RequestContext
from sro.application.execution.headers import client_headers, resolve_headers
from sro.application.induction.sites import (
    as_a_filter,
    url_query_pairs,
    without_filter,
)
from sro.application.ports.http import HttpCaller, TargetUnreachable
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.vault import CredentialVault
from sro.domain.shared.errors import DomainError
from sro.domain.shared.identifiers import SkillId
from sro.domain.skill.lookup import Options
from sro.domain.skill.parameter import Parameter
from sro.domain.skill.plan import NetworkPlan
from sro.domain.skill.skill import SkillVersion
from sro.domain.skill.template import Template

MOST_ROWS = 50


@dataclass(frozen=True, slots=True)
class Choice:
    value: str
    label: str


class NoSuchParameter(DomainError):
    code = "no_such_parameter"


class ListChoices:
    def __init__(self, uow: UnitOfWork, http: HttpCaller, vault: CredentialVault) -> None:
        self._uow = uow
        self._http = http
        self._vault = vault

    async def execute(
        self,
        ctx: RequestContext,
        *,
        skill_id: SkillId,
        parameter: str,
        version: int | None = None,
        like: str = "",
    ) -> tuple[Choice, ...]:
        async with self._uow as uow:
            skill = await uow.skills.get(ctx.tenant_id, skill_id)
        chosen = skill.version(version) if version else skill.latest
        options = _options_of(chosen, parameter)

        plan = _fetch_plan(options, like)
        scope = str(ctx.tenant_id)
        session_scope = f"{skill.objective_key.target_system}/{skill.objective_key.facility}"
        url = plan.url.render({})
        resolved = await resolve_headers(
            plan.headers, values={}, vault=self._vault, scope=scope, session_scope=session_scope
        )
        if resolved.missing:
            raise DomainError(
                "the system is not connected, so its "
                f"{parameter} list cannot be fetched: no {', '.join(resolved.missing)}"
            )
        try:
            response = await self._http.send(
                "GET", url, headers={**client_headers(plan.headers, url), **resolved.headers}
            )
        except TargetUnreachable as error:
            raise DomainError(
                f"the system did not answer with its {parameter} list: {error}"
            ) from error

        return _as_choices(options, response.text)


def _options_of(version: SkillVersion, name: str) -> Options:
    parameter: Parameter | None = next((p for p in version.parameters if p.name == name), None)
    if parameter is None or parameter.options is None:
        raise NoSuchParameter(
            f"{name} is not a field with a list behind it; whoever runs this types it"
        )
    return parameter.options


def _fetch_plan(options: Options, like: str) -> NetworkPlan:
    return NetworkPlan(method="GET", url=_searched(options, like), headers=options.headers)


def _searched(options: Options, like: str) -> Template:
    if not like or options.search is None:
        return Template(_showing(without_filter(options.url), MOST_ROWS))
    searched = as_a_filter(options.url, column=options.search, placeholder=like)
    return Template(_showing(searched or options.url, MOST_ROWS))


def _showing(url: str, rows: int) -> str:
    parts = urlsplit(url)
    pairs = [(key, value) for key, value in url_query_pairs(url) if key.lower() != "limit"]
    if any(key.lower() == "limit" for key, _ in url_query_pairs(url)):
        pairs.append(("limit", str(rows)))
    return urlunsplit(
        (parts.scheme, parts.netloc, parts.path, urlencode(pairs, safe="${}"), parts.fragment)
    )


def _as_choices(options: Options, text: str | None) -> tuple[Choice, ...]:
    try:
        document = json.loads(text or "")
    except ValueError:
        return ()
    data = document.get("data") if isinstance(document, dict) else document
    records = [r for r in data if isinstance(r, dict)] if isinstance(data, list) else []

    choices: list[Choice] = []
    for record in records[:MOST_ROWS]:
        value = record.get(options.value)
        if value is None or not str(value).strip():
            continue
        shown = [
            str(record.get(field, "")).strip()
            for field in options.label
            if record.get(field) is not None
        ]
        choices.append(Choice(value=str(value), label=" — ".join(part for part in shown if part)))
    return tuple(choices)
