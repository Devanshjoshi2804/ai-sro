"""Sending a request this system composed, and reading what comes back.

A taught skill is replayed by the executor, with a run, a stage and a track
record behind it. A derived read has none of that: nobody demonstrated it, so
there is nothing to promote and nothing to verify against. What it has instead
is provenance -- the endpoint, the session and the filter dialect all come from
a demonstration that did happen -- and the rule that it may only ever read.

That rule is the whole safety story here and it is enforced by construction:
this sends GET, and there is no branch that sends anything else.
"""

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
    """Why there is no answer, where there is none."""


class AskTheSystem:
    def __init__(self, uow: UnitOfWork, http: HttpCaller, vault: CredentialVault) -> None:
        self._uow = uow
        self._http = http
        self._vault = vault

    async def execute(
        self, ctx: RequestContext, *, skill_id: SkillId, url: str, lead: str = ""
    ) -> Asked:
        """Send this read with the session the skill's own calls use."""
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
            # A redirect here is the identity provider taking over. Treated as
            # success it produced "the answer had no records in it", which
            # reads as "there are none" for a session that had simply expired.
            return Asked(None, url, "the system asked us to sign in again")

        answer = read_answer(response.text, url=url)
        if answer is None:
            return Asked(None, url, "the answer had no records in it")
        whole = await self._rest_of(url, sending, answer)
        return Asked(leading_with(whole, lead) if lead else whole, url)

    async def _rest_of(self, url: str, headers: dict[str, str], first: Answer) -> Answer:
        """Follow the paging, so "which ones" is answered with all of them."""
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
    """The header plans of the skill's own read.

    Borrowed rather than rebuilt: the session cookie, the site parameters and
    the anti-forgery header are what make a request authentic to this system,
    and a composed request without them is a request to a login page.
    """
    for step in steps:  # type: ignore[attr-defined]
        plan = getattr(step, "network_plan", None)
        if plan is not None and plan.method.upper() == "GET":
            return tuple(plan.headers)
    return ()
