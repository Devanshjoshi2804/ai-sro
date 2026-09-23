from __future__ import annotations

import json
from dataclasses import dataclass, field

from sro.application.connection.browsers import Browsers
from sro.application.connection.check_session import CheckSession, SessionHealth
from sro.application.connection.connect_system import RefreshSession
from sro.application.connection.sign_in import EnsureSignedIn
from sro.application.context import RequestContext
from sro.application.knowledge.record_claim import Claim, RecordClaims
from sro.application.ports.browser import BrowserProvider, BrowserUnavailable
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.vault import CredentialVault
from sro.domain.connection.connection import Connection, ConnectionStatus
from sro.domain.execution.diagnosis import Diagnosis, Remedy, diagnose
from sro.domain.knowledge.entry import EntryKind, EvidenceLevel


@dataclass(frozen=True, slots=True)
class Healed:
    remedy: Remedy
    because: str
    detail: str

    repaired: bool = True


@dataclass
class HealBudget:
    spent: set[tuple[int, Remedy]] = field(default_factory=set)

    def take(self, step_index: int, remedy: Remedy) -> bool:
        if (step_index, remedy) in self.spent:
            return False
        self.spent.add((step_index, remedy))
        return True


class SelfHeal:
    def __init__(
        self,
        uow: UnitOfWork,
        vault: CredentialVault,
        browser: BrowserProvider,
        check: CheckSession,
        ensure: EnsureSignedIn,
        record: RecordClaims,
        refresh: RefreshSession,
        browsers: Browsers,
    ) -> None:
        self._uow = uow
        self._vault = vault
        self._browser = browser
        self._check = check
        self._ensure = ensure
        self._record = record
        self._refresh = refresh
        self._browsers = browsers

    async def attempt(
        self,
        ctx: RequestContext,
        *,
        target_system: str,
        facility: str,
        step_index: int,
        mutating: bool,
        budget: HealBudget,
        failure: object = None,
        status_code: int | None = None,
        redirected_off_host: bool = False,
        missing_headers: tuple[str, ...] = (),
        endpoint: str | None = None,
    ) -> Healed | None:
        finding: Diagnosis = diagnose(
            failure=failure,  # type: ignore[arg-type]
            status_code=status_code,
            redirected_off_host=redirected_off_host,
            missing_headers=missing_headers,
        )
        if finding.remedy is Remedy.NONE or finding.remedy is Remedy.ESCALATE_MEDIUM:
            return None
        if mutating and not finding.safe_for_writes:
            return None
        if not budget.take(step_index, finding.remedy):
            return None

        try:
            detail = await self._apply(ctx, finding.remedy, target_system, facility)
        except BrowserUnavailable as exc:
            return Healed(
                remedy=finding.remedy,
                because=finding.because,
                detail=f"could not take a browser to repair it: {exc}",
                repaired=False,
            )
        if detail is None:
            if finding.remedy is Remedy.REFRESH_SESSION:
                await self._mark_expired(ctx, target_system, finding.because)
            return Healed(
                remedy=finding.remedy,
                because=finding.because,
                detail="nothing here repaired it",
                repaired=False,
            )

        await self._learn(ctx, target_system, finding, endpoint, missing_headers)
        return Healed(remedy=finding.remedy, because=finding.because, detail=detail)

    async def _mark_expired(self, ctx: RequestContext, target_system: str, because: str) -> None:
        async with self._uow as uow:
            connection = await uow.connections.find_by_system(ctx.tenant_id, target_system)
            if connection is None or connection.status is ConnectionStatus.EXPIRED:
                return
            connection.rejected(because)
            await uow.connections.save(connection)
            await uow.commit()

    async def _apply(
        self, ctx: RequestContext, remedy: Remedy, target_system: str, facility: str
    ) -> str | None:
        if remedy is Remedy.REFRESH_SESSION:
            health = await self._check.for_system(ctx, target_system=target_system)
            if health is not None and health.health is SessionHealth.UNREACHABLE:
                return None
            if health is not None and health.health is SessionHealth.SIGNED_IN:
                return await self._refresh_context(ctx, target_system, facility)
            if not await self._ensure.execute(ctx, target_system=target_system):
                return None
            return f"signed {target_system} in again and kept the session it produced"

        return await self._refresh_context(ctx, target_system, facility)

    async def _refresh_context(
        self, ctx: RequestContext, target_system: str, facility: str
    ) -> str | None:
        async with self._uow as uow:
            connection = await uow.connections.find_by_system(ctx.tenant_id, target_system)
        if connection is None:
            return None

        session, borrowed = await self._browsers.take(ctx)
        try:
            if not borrowed:
                await self._browser.restore(session.id, await self._load(ctx, connection))
            headers = await self._browser.session_headers(session.id, connection.base_url)
            cookies = list(await self._browser.session_cookies(session.id))
        finally:
            if not borrowed:
                await self._browsers.release(session.id)

        if not headers:
            return None
        for name, value in headers.items():
            await self._vault.store(f"{ctx.tenant_id}/{target_system}/{facility}/{name}", value)
        await self._refresh.execute(ctx, cookies=cookies, trusted=True)
        return "took a fresh " + ", ".join(sorted(headers)) + " and the session that minted it"

    async def _load(self, ctx: RequestContext, connection: Connection) -> list[dict[str, object]]:
        stored = await self._vault.get(connection.session_key)
        if not stored:
            return []
        payload = json.loads(stored)
        cookies: list[dict[str, object]] = payload.get("cookies", [])
        return cookies

    async def _learn(
        self,
        ctx: RequestContext,
        target_system: str,
        finding: Diagnosis,
        endpoint: str | None,
        missing_headers: tuple[str, ...],
    ) -> None:
        if endpoint is None:
            return
        await self._record.execute(
            ctx,
            (
                Claim(
                    system=target_system,
                    kind=EntryKind.QUIRK,
                    key=f"{endpoint} {finding.remedy.value}",
                    title=f"{endpoint} needed the session repaired: {finding.remedy.value}",
                    body={
                        "endpoint": endpoint,
                        "remedy": finding.remedy.value,
                        "because": finding.because,
                        "headers": list(missing_headers),
                    },
                    source="self-heal",
                    evidence=EvidenceLevel.OBSERVED,
                ),
            ),
        )
