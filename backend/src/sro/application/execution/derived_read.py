from __future__ import annotations

from dataclasses import dataclass

from sro.application.context import RequestContext
from sro.application.execution.answer import Answer, leading_with, merge, read_answer
from sro.application.execution.headers import client_headers, resolve_headers
from sro.application.execution.paging import MOST_PAGES, how_it_pages, next_page
from sro.application.ports.http import HttpCaller, TargetUnreachable
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.vault import CredentialVault
from sro.domain.shared.identifiers import SkillId
from sro.domain.skill.plan import HeaderPlan


@dataclass(frozen=True, slots=True)
class Asked:
    answer: Answer | None
    url: str
    detail: str = ""


class AskTheSystem:
    def __init__(self, uow: UnitOfWork, http: HttpCaller, vault: CredentialVault) -> None:
        self._uow = uow
        self._http = http
        self._vault = vault

    async def execute(
        self, ctx: RequestContext, *, skill_id: SkillId, url: str, lead: str = ""
    ) -> Asked:
        async with self._uow as uow:
            skill = await uow.skills.get(ctx.tenant_id, skill_id)
        key = skill.objective_key
        headers = _headers_of(skill.latest.steps)

        resolved = await resolve_headers(
            headers,
            values={},
            vault=self._vault,
            scope=str(ctx.tenant_id),
            session_scope=f"{key.target_system}/{key.facility}",
        )
        if resolved.missing:
            return Asked(
                None, url, f"the system is not connected: no {', '.join(resolved.missing)}"
            )

        sending = {**client_headers(headers, url), **resolved.headers}
        try:
            response = await self._http.send("GET", url, headers=sending)
        except TargetUnreachable as error:
            return Asked(None, url, f"the system did not answer: {error}")

        if response.status_code >= 400:
            return Asked(None, url, f"the system answered {response.status_code}")
        if 300 <= response.status_code < 400:
            return Asked(None, url, "the system asked us to sign in again")

        answer = read_answer(response.text, url=url)
        if answer is None:
            return Asked(None, url, "the answer had no records in it")
        whole = await self._rest_of(url, sending, answer)
        return Asked(leading_with(whole, lead) if lead else whole, url)

    async def _rest_of(self, url: str, headers: dict[str, str], first: Answer) -> Answer:
        paging = how_it_pages(url)
        if not paging.pages or first.rows < paging.limit:
            return first

        pages = [first]
        so_far = first.rows
        for page in range(MOST_PAGES):
            following = next_page(url, paging, so_far=so_far, page=page)
            if following is None:
                break
            try:
                response = await self._http.send("GET", following, headers=headers)
            except TargetUnreachable:
                break
            answer = read_answer(response.text, url=following)
            if answer is None or answer.rows == 0:
                break
            pages.append(answer)
            so_far += answer.rows
            if answer.rows < paging.limit:
                break
        return merge(tuple(pages)) or first


def _headers_of(steps: object) -> tuple[HeaderPlan, ...]:
    for step in steps:  # type: ignore[attr-defined]
        plan = getattr(step, "network_plan", None)
        if plan is not None and plan.method.upper() == "GET":
            return tuple(plan.headers)
    return ()
