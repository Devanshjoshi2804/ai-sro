from __future__ import annotations

import asyncio
import contextlib
import logging
from collections import Counter
from collections.abc import Collection
from dataclasses import replace
from datetime import datetime, timedelta

from sro.application.connection.refusals import CodeAsked, RefusedCredentials, fingerprint
from sro.application.connection.sign_in import tagged_logins
from sro.application.context import RequestContext
from sro.application.ports.browser import BrowserUnavailable
from sro.application.ports.locks import AccountBusy, AccountLocks
from sro.application.ports.page import PageDriver, PageGone, SessionRef
from sro.application.ports.pool import BrowserPool
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.system import Clock
from sro.application.ports.vault import CredentialVault
from sro.application.ports.vision import Screen
from sro.application.runtime.step import (
    Held,
    LaneContext,
    NeedsAPerson,
    StepLane,
    WaitingForAPerson,
)
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
from sro.domain.shared.identifiers import TenantId
from sro.domain.skill.signing_in import (
    a_sign_in_page,
    asks_for_a_code,
    recorded_login,
    sign_in_chain,
)
from sro.domain.skill.workflow import Workflow

logger = logging.getLogger(__name__)

K_CLOSE_S = 5.0
K_HEADERS_WAIT_S = 20.0
K_CODE_WAIT = timedelta(minutes=10)


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
        self,
        ctx: RequestContext,
        account: Account,
        start_url: str,
        *,
        holder: str,
        park: bool = True,
    ) -> Held:
        async with self._uow as uow:
            lease = await uow.browser_sessions.current_lease(ctx.tenant_id, account)
        if lease is not None:
            with contextlib.suppress(PageGone):
                held = await self._attach(ctx, lease, start_url, holder if park else None)
                if held is not None:
                    return held
        async with self._locks.hold(account):
            return await self._ready(ctx, account, start_url, holder=holder, park=park)

    async def reattach(
        self, ctx: RequestContext, lease_id: str, target_id: str, *, holder: str
    ) -> Held:
        async with self._uow as uow:
            lease = await uow.browser_sessions.get_lease(ctx.tenant_id, lease_id)
        if lease is None or not lease.live(self._clock.now()):
            raise PageGone(f"lease {lease_id} is no longer live")
        held = Held(replace(lease, holder=holder), target_id, await self._session(lease))
        await self._driver.url_of(held.session, target_id)
        return held

    async def open_tab(self, ctx: RequestContext, held: Held, url: str) -> Held:
        return replace(held, target_id=await self._driver.open_tab(held.session, url))

    async def opened_by(self, ctx: RequestContext, held: Held, *, deadline_s: float) -> Held:
        return replace(
            held, target_id=await self._driver.opened_by(held.session, held.target_id, deadline_s)
        )

    async def release(self, ctx: RequestContext, held: Held) -> None:
        with contextlib.suppress(PageGone):
            await self._driver.close_tab(held.session, held.target_id)

    async def signed_out(self, ctx: RequestContext, held: Held) -> bool:
        return a_sign_in_page(await self._driver.signals(held.session, held.target_id))

    async def screenshot(self, ctx: RequestContext, held: Held) -> Screen:
        return await self._driver.screenshot(held.session, held.target_id)

    async def beat(self, ctx: RequestContext, lease_id: str, *, holder: str | None) -> bool:
        async with self._uow as uow:
            kept = await uow.browser_sessions.beat(
                ctx.tenant_id, lease_id, now=self._clock.now(), holder=holder
            )
            await uow.commit()
        return kept

    async def prepare_to_expire(self, lease: Lease) -> bool:
        try:
            session = await self._session(lease)
        except (BrowserUnavailable, KeyError):
            return False
        if lease.state is LeaseState.READY:
            with contextlib.suppress(TimeoutError, PageGone, BrowserUnavailable):
                async with asyncio.timeout(self._close_s):
                    await self._save_state(lease, session)
        return True

    async def end_expired(self, lease: Lease) -> None:
        await self._close(lease)

    async def headers(
        self,
        ctx: RequestContext,
        held: Held,
        url: str,
        *,
        fresh: bool = False,
        needs: Collection[str] = (),
        wait_s: float = K_HEADERS_WAIT_S,
    ) -> dict[str, str]:
        since = 0
        if fresh:
            since = await self._driver.mark(held.session, held.target_id)
            await self._driver.goto(
                held.session,
                held.target_id,
                await self._driver.url_of(held.session, held.target_id),
            )
        said = await self._driver.headers_for(held.session, url, wait_s, since=since, needs=needs)
        cookie = await self._driver.cookies_for(held.session, url)
        return {"cookie": cookie, **said} if cookie else said

    async def reauth(
        self,
        ctx: RequestContext,
        held: Held,
        start_url: str,
        *,
        back_to: str | None = None,
        park: bool = True,
    ) -> None:
        async with self._locks.hold(held.lease.account):
            async with self._uow as uow:
                lease = await uow.browser_sessions.get_lease(ctx.tenant_id, held.lease.id)
            if lease is None or not lease.live(self._clock.now()):
                raise PageGone(f"lease {held.lease.id} is no longer live")
            if lease.state is LeaseState.WAITING:
                raise AccountBusy(
                    f"{lease.account.key} is waiting for a person until {lease.expires_at}"
                )
            held = replace(held, lease=replace(lease, holder=held.lease.holder))
            await self._driver.goto(held.session, held.target_id, start_url)
            if a_sign_in_page(await self._driver.signals(held.session, held.target_id)):
                try:
                    await self._sign_in(ctx, held, start_url, park=park)
                except NeedsAPerson as asked:
                    if park and asked.kind == "password":
                        await self._park(ctx, held.lease, "password")
                    raise
                await self._save_state(held.lease, held.session)
                await self._driver.forget_calls(held.session, held.target_id)
            if back_to is not None:
                await self._driver.goto(held.session, held.target_id, back_to)

    async def recover(
        self, ctx: RequestContext, lease_id: str, start_url: str, *, holder: str
    ) -> Held:
        async with self._uow as uow:
            lease = await uow.browser_sessions.get_lease(ctx.tenant_id, lease_id)
        if lease is None:
            raise PageGone(f"lease {lease_id} is not known")
        return await self.acquire(ctx, lease.account, start_url, holder=holder)

    async def resume(
        self,
        ctx: RequestContext,
        lease_id: str,
        target_id: str,
        start_url: str,
        *,
        holder: str,
        main: bool = True,
    ) -> Held:
        async with self._uow as uow:
            lease = await uow.browser_sessions.get_lease(ctx.tenant_id, lease_id)
        if lease is None or lease.state is not LeaseState.WAITING or lease.waits_for != "code":
            raise PageGone(f"lease {lease_id} is not waiting for a one-time code")
        async with self._locks.hold(lease.account):
            if not lease.live(self._clock.now()):
                return await self._ready(ctx, lease.account, start_url, holder=holder, park=True)
            held = Held(lease, target_id, await self._session(lease))
            signals = await self._driver.signals(held.session, target_id)
            if asks_for_a_code(signals):
                raise WaitingForAPerson(
                    f"{lease.account.origin} still asks for a one-time code", held=held
                )
            if a_sign_in_page(signals):
                raise NeedsAPerson(
                    f"{lease.account.origin} asks for a password now, not a code",
                    kind="password",
                )
            now = self._clock.now()
            until = now + K_LEASE_TTL
            if not await self._settle(ctx, lease, LeaseState.READY, until=until, now=now):
                raise PageGone(f"lease {lease_id} was lost while it waited for a person")
            if main:
                await self._driver.goto(held.session, target_id, start_url)
            await self._save_state(lease, held.session)
            await CodeAsked(self._vault).clear(lease.account.vault_key("password"))
            await self._driver.forget_calls(held.session, target_id)
            if not await self.beat(ctx, lease_id, holder=holder):
                raise PageGone(f"lease {lease_id} was lost while it waited for a person")
        return replace(
            held, lease=replace(lease, state=LeaseState.READY, holder=holder, expires_at=until)
        )

    async def unpark(self, ctx: RequestContext, lease_id: str, waits_for: str) -> None:
        async with self._uow as uow:
            lease = await uow.browser_sessions.get_lease(ctx.tenant_id, lease_id)
        if lease is None or lease.state is not LeaseState.WAITING:
            return
        async with self._locks.hold(lease.account):
            now = self._clock.now()
            async with self._uow as uow:
                lease = await uow.browser_sessions.get_lease(ctx.tenant_id, lease_id)
                if (
                    lease is not None
                    and lease.state is LeaseState.WAITING
                    and lease.waits_for == waits_for
                ):
                    ended = await uow.browser_sessions.settle(
                        ctx.tenant_id,
                        lease_id,
                        state=LeaseState.WAITING,
                        until=now,
                        now=now,
                        waits_for=waits_for,
                    ) and await uow.browser_sessions.expire(ctx.tenant_id, lease_id, now=now)
                    await uow.commit()
                    if ended:
                        await self._close(lease)

    async def _attach(
        self, ctx: RequestContext, lease: Lease, start_url: str, holder: str | None
    ) -> Held | None:
        if lease.state is not LeaseState.READY or not lease.live(self._clock.now()):
            return None
        return await self._beaten(ctx, await self._tab(lease, start_url), holder)

    async def _beaten(self, ctx: RequestContext, held: Held, holder: str | None) -> Held | None:
        kept = False
        try:
            kept = await self.beat(ctx, held.lease.id, holder=holder)
        finally:
            if not kept:
                await self.release(ctx, held)
        if not kept:
            return None
        return held if holder is None else replace(held, lease=replace(held.lease, holder=holder))

    async def _recover(
        self, ctx: RequestContext, lease: Lease, start_url: str, holder: str | None
    ) -> Held | None:
        try:
            return await self._attach(ctx, lease, start_url, holder)
        except PageGone:
            if lease.context_id not in await self._pool.contexts(lease.container_url):
                return None
        return await self._beaten(ctx, await self._tab(lease, start_url), holder)

    async def _ready(
        self, ctx: RequestContext, account: Account, start_url: str, *, holder: str, park: bool
    ) -> Held:
        now = self._clock.now()
        async with self._uow as uow:
            old = await uow.browser_sessions.current_lease(ctx.tenant_id, account)
            taken = old is not None and await uow.browser_sessions.expire(
                ctx.tenant_id, old.id, now=now
            )
            await uow.commit()
        if old is not None and not taken:
            if old.state is LeaseState.WAITING and old.context_id in await self._pool.contexts(
                old.container_url
            ):
                raise AccountBusy(f"{account.key} is waiting for a person until {old.expires_at}")
            held = await self._recover(ctx, old, start_url, holder if park else None)
            if held is not None:
                return held
            await self._settle(ctx, old, LeaseState.BROKEN)
        if old is not None:
            await self._close(old)
        async with self._uow as uow:
            busy = Counter(await uow.browser_sessions.busy_containers(now=now))
            pinned = await uow.browser_sessions.pinned_container(ctx.tenant_id, account)
        container, steel_id, context_id = await self._pool.open(
            ctx.tenant_id.value, busy, pinned=pinned
        )
        fresh = Lease(
            new_lease_id(),
            account,
            container,
            steel_id,
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
        await self._reclaim(container)
        try:
            held = await self._signed_in(ctx, lease, start_url, park=park)
        except WaitingForAPerson:
            raise
        except (NeedsAPerson, asyncio.CancelledError, TimeoutError):
            kept = False
            try:
                kept = await self._settle(ctx, lease, LeaseState.READY)
            finally:
                if not kept:
                    await self._close(lease)
            raise
        except BaseException:
            try:
                await self._settle(ctx, lease, LeaseState.BROKEN)
            finally:
                await self._close(lease)
            raise
        settled = False
        try:
            settled = await self._settle(ctx, lease, LeaseState.READY)
        finally:
            if not settled:
                await self.release(ctx, held)
        if not settled:
            raise PageGone(f"lease {lease.id} was lost while it was signing in")
        return replace(held, lease=replace(lease, state=LeaseState.READY))

    async def _signed_in(
        self, ctx: RequestContext, lease: Lease, start_url: str, *, park: bool
    ) -> Held:
        session = await self._session(lease)
        state = await self._vault.get(lease.account.vault_key("state"))
        if state:
            await self._driver.restore_state(session, state)
        held = Held(lease, await self._driver.open_tab(session, start_url), session)
        try:
            if a_sign_in_page(await self._driver.signals(session, held.target_id)):
                await self._sign_in(ctx, held, start_url, park=park)
            await self._save_state(held.lease, held.session)
            await self._driver.forget_calls(session, held.target_id)
        except WaitingForAPerson:
            raise
        except BaseException:
            with contextlib.suppress(PageGone):
                await self._driver.close_tab(session, held.target_id)
            raise
        return held

    async def _recorded(
        self, ctx: RequestContext, start_url: str
    ) -> tuple[Account, Workflow, dict[str, Gesture]]:
        tagged, seen = await tagged_logins(self._uow, ctx.tenant_id)
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

    async def _sign_in(
        self, ctx: RequestContext, held: Held, start_url: str, *, park: bool
    ) -> None:
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
        asked = CodeAsked(self._vault)
        since = await asked.since(key)
        if not park and since is not None and self._clock.now() - since < K_CODE_WAIT:
            raise NeedsAPerson(f"{account.origin} asks for a one-time code", kind="code")
        await self._driver.forget_headers_before(
            held.session, await self._driver.mark(held.session, held.target_id)
        )
        if asks_for_a_code(await self._driver.signals(held.session, held.target_id)):
            await self._wait_for_a_person(ctx, held, park=park)
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
            await self._wait_for_a_person(ctx, held, park=park)
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
        await asked.clear(key)

    async def _wait_for_a_person(self, ctx: RequestContext, held: Held, *, park: bool) -> None:
        await CodeAsked(self._vault).ask(
            held.lease.account.vault_key("password"), at=self._clock.now()
        )
        if not park:
            raise NeedsAPerson(f"{held.lease.account.origin} asks for a one-time code", kind="code")
        until = await self._park(ctx, held.lease, "code")
        waiting = replace(held.lease, state=LeaseState.WAITING, expires_at=until, waits_for="code")
        raise WaitingForAPerson(
            f"{held.lease.account.origin} asks for a one-time code",
            held=replace(held, lease=waiting),
        )

    async def _park(self, ctx: RequestContext, lease: Lease, waits_for: str) -> datetime:
        until = self._clock.now() + K_CODE_WAIT
        async with self._uow as uow:
            moved = await uow.browser_sessions.settle(
                ctx.tenant_id,
                lease.id,
                state=LeaseState.WAITING,
                until=until,
                waits_for=waits_for,
                holder=lease.holder,
            )
            await uow.commit()
        if not moved:
            raise PageGone(f"lease {lease.id} was lost while it was signing in")
        return until

    async def _save_state(self, lease: Lease, session: SessionRef) -> None:
        state = await self._driver.storage_state(session)
        size = len(state.encode())
        if size > K_VAULT_VALUE_BYTES:
            logger.warning(
                "%s: the signed-in state is %d bytes, over the vault's %d; not saved",
                lease.account.key,
                size,
                K_VAULT_VALUE_BYTES,
            )
            return
        await self._vault.store(lease.account.vault_key("state"), state)

    async def _settle(
        self,
        ctx: RequestContext,
        lease: Lease,
        state: LeaseState,
        *,
        until: datetime | None = None,
        now: datetime | None = None,
    ) -> bool:
        async with self._uow as uow:
            moved = await uow.browser_sessions.settle(
                ctx.tenant_id, lease.id, state=state, until=until, now=now
            )
            await uow.commit()
        return moved

    async def _tab(self, lease: Lease, start_url: str) -> Held:
        session = await self._session(lease)
        return Held(lease, await self._driver.open_tab(session, start_url), session)

    async def _session(self, lease: Lease) -> SessionRef:
        return SessionRef(lease.context_id, await self._pool.cdp_url(lease.container_url))

    async def _reclaim(self, container_url: str) -> None:
        try:
            async with asyncio.timeout(self._close_s):
                listed = await self._pool.contexts(container_url)
                async with self._uow as uow:
                    retired = await uow.browser_sessions.retired_contexts(container_url, listed)
                for context_id in retired:
                    await self._pool.close(container_url, context_id)
        except (TimeoutError, BrowserUnavailable) as why:
            logger.warning("contexts on %s were not reclaimed: %r", container_url, why)

    async def _close(self, lease: Lease) -> None:
        try:
            async with asyncio.timeout(self._close_s):
                await self._driver.forget(await self._session(lease))
                await self._pool.close(lease.container_url, lease.context_id)
        except (TimeoutError, BrowserUnavailable, PageGone) as why:
            logger.warning(
                "context %s of lease %s was not closed: %r", lease.context_id, lease.id, why
            )
        except KeyError as why:
            logger.warning(
                "container %s of lease %s is no longer configured: %r",
                lease.container_url,
                lease.id,
                why,
            )
            async with self._uow as uow:
                await uow.browser_sessions.settle(
                    TenantId(lease.account.tenant), lease.id, state=LeaseState.BROKEN
                )
                await uow.commit()
