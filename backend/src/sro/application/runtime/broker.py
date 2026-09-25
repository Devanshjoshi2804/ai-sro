from __future__ import annotations

import asyncio
import contextlib
import logging
from collections import Counter
from dataclasses import replace

from sro.application.connection.refusals import RefusedCredentials, fingerprint
from sro.application.connection.sign_in import tagged_logins
from sro.application.context import RequestContext
from sro.application.ports.browser import BrowserUnavailable
from sro.application.ports.locks import AccountBusy, AccountLocks
from sro.application.ports.page import PageDriver, PageGone, SessionRef
from sro.application.ports.pool import BrowserPool
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.system import Clock
from sro.application.ports.vault import CredentialVault
from sro.application.runtime.step import Held, LaneContext, NeedsAPerson, StepLane
from sro.domain.execution.account import (
    K_LEASE_TTL,
    K_VAULT_VALUE_BYTES,
    Account,
    Lease,
    LeaseState,
    new_lease_id,
)
from sro.domain.observation.gesture import Gesture
from sro.domain.shared.errors import InvariantViolation
from sro.domain.shared.hosts import origin_of
from sro.domain.skill.signing_in import (
    a_sign_in_page,
    asks_for_a_code,
    recorded_login,
    sign_in_chain,
)
from sro.domain.skill.workflow import Workflow

logger = logging.getLogger(__name__)

K_CLOSE_S = 5.0


class SessionBroker:
    def __init__(
        self,
        uow: UnitOfWork,
        pool: BrowserPool,
        driver: PageDriver,
        locks: AccountLocks,
        vault: CredentialVault,
        clock: Clock,
        *,
        ui: StepLane,
        close_s: float = K_CLOSE_S,
    ) -> None:
        self._uow, self._pool, self._driver = uow, pool, driver
        self._locks, self._vault, self._clock, self._ui = locks, vault, clock, ui
        self._close_s = close_s

    async def account_for(self, ctx: RequestContext, start_url: str) -> Account:
        account, _, _ = await self._recorded(ctx, start_url)
        return account

    async def acquire(
        self, ctx: RequestContext, account: Account, start_url: str, *, holder: str
    ) -> Held:
        async with self._uow as uow:
            lease = await uow.browser_sessions.current_lease(ctx.tenant_id, account)
        if lease is not None and await self._attachable(ctx, lease, holder):
            return await self._tab(lease, start_url)
        async with self._locks.hold(account):
            return await self._ready(ctx, account, start_url, holder=holder)

    async def reattach(self, ctx: RequestContext, lease_id: str, target_id: str) -> Held:
        async with self._uow as uow:
            lease = await uow.browser_sessions.get_lease(ctx.tenant_id, lease_id)
        if lease is None or not lease.live(self._clock.now()):
            raise PageGone(f"lease {lease_id} is no longer live")
        held = Held(lease, target_id, await self._session(lease))
        await self._driver.url_of(held.session, target_id)
        return held

    async def release(self, ctx: RequestContext, held: Held) -> None:
        with contextlib.suppress(PageGone):
            await self._driver.close_tab(held.session, held.target_id)

    async def beat(self, ctx: RequestContext, lease_id: str, *, holder: str) -> bool:
        async with self._uow as uow:
            kept = await uow.browser_sessions.beat(
                ctx.tenant_id, lease_id, now=self._clock.now(), holder=holder
            )
            await uow.commit()
        return kept

    async def _attachable(self, ctx: RequestContext, lease: Lease, holder: str) -> bool:
        return (
            lease.state is LeaseState.READY
            and lease.live(self._clock.now())
            and await self.beat(ctx, lease.id, holder=holder)
        )

    async def _ready(
        self, ctx: RequestContext, account: Account, start_url: str, *, holder: str
    ) -> Held:
        now = self._clock.now()
        async with self._uow as uow:
            repo = uow.browser_sessions
            old = await repo.current_lease(ctx.tenant_id, account)
            taken = old is not None and await repo.expire(ctx.tenant_id, old.id, now=now)
            busy = Counter(await repo.busy_containers(ctx.tenant_id, now=now))
            pinned = await repo.pinned_container(ctx.tenant_id, account)
            await uow.commit()
        if old is not None and not taken:
            if await self._attachable(ctx, old, holder):
                return await self._tab(old, start_url)
            raise AccountBusy(f"{account.key} is held by lease {old.id} until {old.expires_at}")
        if old is not None:
            await self._close(old)
        container, context_id = await self._pool.open(ctx.tenant_id.value, busy, pinned=pinned)
        fresh = Lease(
            new_lease_id(),
            account,
            container,
            context_id,
            context_id,
            holder,
            now,
            now + K_LEASE_TTL,
            LeaseState.SIGNING_IN,
        )
        async with self._uow as uow:
            lease = await uow.browser_sessions.lease(ctx.tenant_id, fresh)
            await uow.commit()
        if lease.id != fresh.id:
            await self._close(fresh)
            raise AccountBusy(f"{account.key} was leased as {lease.id} by another holder")
        try:
            held = await self._signed_in(ctx, lease, start_url)
        except BaseException:
            await self._settle(ctx, lease, LeaseState.BROKEN)
            await self._close(lease)
            raise
        if not await self._settle(ctx, lease, LeaseState.READY):
            raise PageGone(f"lease {lease.id} was lost while it was signing in")
        return replace(held, lease=replace(lease, state=LeaseState.READY))

    async def _signed_in(self, ctx: RequestContext, lease: Lease, start_url: str) -> Held:
        session = await self._session(lease)
        state = await self._vault.get(lease.account.vault_key("state"))
        if state:
            await self._driver.restore_state(session, state)
        held = Held(lease, await self._driver.open_tab(session, start_url), session)
        try:
            if a_sign_in_page(await self._driver.signals(session, held.target_id)):
                await self._sign_in(ctx, held, start_url)
            await self._save_state(held)
        except BaseException:
            with contextlib.suppress(PageGone):
                await self._driver.close_tab(session, held.target_id)
            raise
        return held

    async def _recorded(
        self, ctx: RequestContext, start_url: str
    ) -> tuple[Account, Workflow, dict[str, Gesture]]:
        tagged, seen = await tagged_logins(self._uow, ctx)
        login = recorded_login(start_url, tagged, seen)
        job = next((one for one in tagged if login is not None and one.id == login.job_id), None)
        if login is None or job is None:
            raise NeedsAPerson(
                f"no recorded sign-in lands on {origin_of(start_url)}; "
                "sign in once with the extension watching",
            )
        try:
            account = Account.of(ctx.tenant_id.value, login.origin, login.username or "")
        except InvariantViolation:
            raise NeedsAPerson(
                f"the recorded sign-in at {login.origin} has no username; "
                "record the sign-in again with the username typed",
                kind="value",
            ) from None
        return account, job, seen

    async def _sign_in(self, ctx: RequestContext, held: Held, start_url: str) -> None:
        account = held.lease.account
        recorded, job, seen = await self._recorded(ctx, start_url)
        if recorded != account:
            raise NeedsAPerson(
                f"the recorded sign-in at {recorded.origin} is not {account.username}'s; "
                f"record {account.username} signing in",
            )
        key = account.vault_key("password")
        password = await self._vault.get(key)
        refused = RefusedCredentials(self._vault)
        if not password or await refused.standing(key, password) is not None:
            raise NeedsAPerson(
                f"no usable password is stored for {account.username} at {account.origin}",
                kind="password",
            )
        if asks_for_a_code(await self._driver.signals(held.session, held.target_id)):
            raise NeedsAPerson(f"{account.origin} asks for a one-time code")
        lane = LaneContext.for_sign_in(ctx, job, seen, held, secret=password)
        for step in sign_in_chain(job, seen):
            result = await self._ui.execute(step, {}, lane)
            if result.verdict == "failed":
                raise NeedsAPerson(
                    f"signing in to {account.origin} stopped at '{step.says}': {result.reason}",
                )
            if not await self.beat(ctx, held.lease.id, holder=held.lease.holder):
                raise PageGone(f"lease {held.lease.id} was lost while it was signing in")
        after = await self._driver.signals(held.session, held.target_id)
        if asks_for_a_code(after):
            raise NeedsAPerson(f"{account.origin} asks for a one-time code")
        if a_sign_in_page(after):
            await refused.refuse(
                key,
                at=self._clock.now(),
                reason="the sign-in form came back after the password was submitted",
                fingerprint=fingerprint(key, password),
            )
            raise NeedsAPerson(
                f"the password for {account.username} at {account.origin} was refused; "
                "store a new one",
                kind="password",
            )
        await self._driver.goto(held.session, held.target_id, start_url)

    async def _save_state(self, held: Held) -> None:
        state = await self._driver.storage_state(held.session)
        size = len(state.encode())
        if size > K_VAULT_VALUE_BYTES:
            logger.warning(
                "%s: the signed-in state is %d bytes, over the vault's %d; not saved",
                held.lease.account.key,
                size,
                K_VAULT_VALUE_BYTES,
            )
            return
        await self._vault.store(held.lease.account.vault_key("state"), state)

    async def _settle(self, ctx: RequestContext, lease: Lease, state: LeaseState) -> bool:
        async with self._uow as uow:
            moved = await uow.browser_sessions.settle(ctx.tenant_id, lease.id, state=state)
            await uow.commit()
        return moved

    async def _tab(self, lease: Lease, start_url: str) -> Held:
        session = await self._session(lease)
        return Held(lease, await self._driver.open_tab(session, start_url), session)

    async def _session(self, lease: Lease) -> SessionRef:
        return SessionRef(lease.context_id, await self._pool.cdp_url(lease.container_url))

    async def _close(self, lease: Lease) -> None:
        try:
            async with asyncio.timeout(self._close_s):
                await self._driver.forget(await self._session(lease))
                await self._pool.close(lease.container_url, lease.context_id)
        except (TimeoutError, BrowserUnavailable, PageGone) as why:
            logger.warning(
                "context %s of lease %s was not closed: %r", lease.context_id, lease.id, why
            )
