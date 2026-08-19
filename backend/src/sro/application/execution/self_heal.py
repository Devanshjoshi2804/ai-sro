"""Repair the session a run needs, once, and write down what was learned.

The loop this replaces was done by hand: read the failing step, notice the
redirect to a login page, take a browser, sign in, observe what the application
sends, put it in the vault, run it again. Every part of that is mechanical, and
none of it needed the person it took.

What makes it safe to automate is what it is *not* allowed to touch. A remedy
recovers something the target system owns -- a session, a token, the page the
application calls from. It never edits a step, a parameter or an assertion:
those are evidence from a demonstration, and evidence is changed by
demonstrating again. So the worst a wrong diagnosis can do is waste one retry.

Once per step, and once per run for the same remedy, because a system that
signs you out twice in a minute is telling you something a third login will not
fix.

And it is not silent. Every heal is recorded on the step it repaired, and what
it proved -- that this endpoint needs this header, that this system rotates its
session -- goes to the knowledge store, so the next run reads it instead of
rediscovering it. That is the difference between a retry and a brain.
"""

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
from sro.domain.connection.connection import Connection
from sro.domain.execution.diagnosis import Diagnosis, Remedy, diagnose
from sro.domain.knowledge.entry import EntryKind, EvidenceLevel


@dataclass(frozen=True, slots=True)
class Healed:
    remedy: Remedy
    because: str
    detail: str
    """What was actually done, for the step's record. Names no value."""

    repaired: bool = True
    """False when the symptom was diagnosed and the repair did not happen.

    Worth returning rather than swallowing: a read that came back 302 was
    reported to the operator as "assertion_failed", which describes the
    assertion and not the reason -- the session was gone, and the healer could
    not take a browser to renew it because the provider had none to give. Both
    of those are things a person can act on; "assertion_failed" is not.
    """


@dataclass
class HealBudget:
    """One attempt per step, one per remedy per run.

    Not a rate limit. A second identical failure after a successful repair means
    the diagnosis was wrong, and the useful thing then is a person reading one
    clear failure rather than a log of six.
    """

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
        """Repair what the symptom points at, or return None and leave it alone."""
        finding: Diagnosis = diagnose(
            failure=failure,  # type: ignore[arg-type]
            status_code=status_code,
            redirected_off_host=redirected_off_host,
            missing_headers=missing_headers,
        )
        if finding.remedy is Remedy.NONE or finding.remedy is Remedy.ESCALATE_MEDIUM:
            # Escalation is the run's decision, not a repair: it changes which
            # rung performs the task, and the table that governs it already
            # exists.
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
            return Healed(
                remedy=finding.remedy,
                because=finding.because,
                detail="nothing here repaired it",
                repaired=False,
            )

        await self._learn(ctx, target_system, finding, endpoint, missing_headers)
        return Healed(remedy=finding.remedy, because=finding.because, detail=detail)

    async def _apply(
        self, ctx: RequestContext, remedy: Remedy, target_system: str, facility: str
    ) -> str | None:
        if remedy is Remedy.REFRESH_SESSION:
            health = await self._check.for_system(ctx, target_system=target_system)
            if health is not None and health.health is SessionHealth.UNREACHABLE:
                # An outage is not a session problem, and signing in during one
                # spends the credentials against a system that cannot answer.
                return None
            if health is not None and health.health is SessionHealth.SIGNED_IN:
                # The session is alive and the call was still turned away, so
                # what expired is what the executor carries beside it -- the
                # token the page mints, the context in the Referer. Signing in
                # again would do nothing at best and, on a system that permits
                # one session, take the operator's browser down at worst.
                #
                # Found by watching this fire against the live WMS: the healer
                # reported success and the retry came back 302 all the same.
                return await self._refresh_context(ctx, target_system, facility)
            if not await self._ensure.execute(ctx, target_system=target_system):
                return None
            return f"signed {target_system} in again and kept the session it produced"

        return await self._refresh_context(ctx, target_system, facility)

    async def _refresh_context(
        self, ctx: RequestContext, target_system: str, facility: str
    ) -> str | None:
        """Take what the application sends beside its cookies, without a login.

        Deliberately not a sign-in: on a system that permits one session at a
        time, signing in again to fix a token would sign the operator's own
        browser out. If the session itself is gone this returns nothing and the
        step fails honestly.
        """
        async with self._uow as uow:
            connection = await uow.connections.find_by_system(ctx.tenant_id, target_system)
        if connection is None:
            return None

        # A provider with no browser to give is not "no repair available": it
        # is the reason, and it is reported rather than swallowed.
        session, borrowed = await self._browsers.take(ctx)
        try:
            if not borrowed:
                # A borrowed browser is somebody's own, already signed in.
                # Restoring stored cookies over the top of it replaces a live
                # session with an older one.
                await self._browser.restore(session.id, await self._load(ctx, connection))
            headers = await self._browser.session_headers(session.id, connection.base_url)
            # Both, from this browser, in this order. A token minted in one
            # session and a cookie kept from another authenticate nothing: the
            # first attempt at this took the token alone, reported success, and
            # the retry was refused exactly as before.
            cookies = list(await self._browser.session_cookies(session.id))
        finally:
            # Never one we did not open: it belongs to whoever signed into it,
            # and closing it logs a warehouse operator out mid-shift.
            if not borrowed:
                await self._browsers.release(session.id)

        if not headers:
            return None
        for name, value in headers.items():
            await self._vault.store(f"{ctx.tenant_id}/{target_system}/{facility}/{name}", value)
        await self._refresh.execute(ctx, cookies=cookies, trusted=True)
        return "took a fresh " + ", ".join(sorted(headers)) + " and the session that minted it"

    async def _load(self, ctx: RequestContext, connection: Connection) -> list[dict[str, object]]:
        """The stored session, so the browser starts where the operator left it.

        A blank browser sent to the application lands on a login page and mints
        nothing worth having.
        """
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
        """What the repair proved about the system, for the next run to read.

        Observed rather than reproduced: one repair shows the system behaves
        this way once. A second run that heals the same way is what makes it a
        habit, and the store's own supersession rules handle that.
        """
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
