"""Whose browser a session id belongs to, and what that stops.

Before there was an answer, a session id was a bare string. One tenant could
list the deployment's browsers, name one, and watch it, drive it, or empty its
cookies into their own vault -- and the audit trail named the thief. The
repository layer had filtered by tenant since the beginning; the browser pool
never had.
"""

from __future__ import annotations

import pytest

from sro.application.connection.browsers import Browsers
from sro.application.context import RequestContext
from sro.application.ports.browser import BrowserUnavailable
from sro.domain.shared.errors import Conflict, NotFound
from sro.domain.shared.identifiers import BrowserSessionId, PrincipalId, TenantId
from tests import factories as f
from tests.unit.fakes import FakeBrowserProvider, FakeClock, FakeIdFactory, FakeUnitOfWork

MINE = RequestContext(tenant_id=f.TENANT, principal_id=f.OPERATOR)
THEIRS = RequestContext(tenant_id=TenantId("rival"), principal_id=PrincipalId("somebody-else"))


def _browsers(uow: FakeUnitOfWork, browser: FakeBrowserProvider) -> Browsers:
    return Browsers(browser, uow, FakeClock(), FakeIdFactory())


async def test_a_browser_i_opened_is_mine() -> None:
    uow, provider = FakeUnitOfWork(), FakeBrowserProvider()
    browsers = _browsers(uow, provider)

    opened = await browsers.open(MINE)

    assert [session.id for session in await browsers.mine(MINE)] == [opened.id]
    assert await browsers.session(MINE, opened.id) is not None


async def test_another_tenant_cannot_see_it() -> None:
    uow, provider = FakeUnitOfWork(), FakeBrowserProvider()
    browsers = _browsers(uow, provider)
    await browsers.open(MINE)

    assert await browsers.mine(THEIRS) == ()


async def test_another_tenant_naming_it_is_told_it_does_not_exist() -> None:
    """The same answer as an id that never existed. A distinct refusal would
    tell a caller which ids are real, which is most of what they need."""
    uow, provider = FakeUnitOfWork(), FakeBrowserProvider()
    browsers = _browsers(uow, provider)
    opened = await browsers.open(MINE)

    with pytest.raises(NotFound):
        await browsers.session(THEIRS, opened.id)


async def test_a_live_session_nobody_claimed_belongs_to_nobody() -> None:
    """A browser the provider has but this system did not open -- left over from
    before the claim existed, or from a restart. It is not anybody's."""
    uow, provider = FakeUnitOfWork(), FakeBrowserProvider()
    stray = await provider.open()

    assert await _browsers(uow, provider).mine(MINE) == ()
    assert stray.id not in {s.id for s in await _browsers(uow, provider).mine(THEIRS)}


async def test_a_claim_on_a_session_the_provider_forgot_is_not_a_browser() -> None:
    uow, provider = FakeUnitOfWork(), FakeBrowserProvider()
    browsers = _browsers(uow, provider)
    opened = await browsers.open(MINE)
    await provider.close(opened.id)

    assert await browsers.mine(MINE) == ()


async def test_one_browser_may_not_be_handed_to_two_tenants() -> None:
    """The primary key is the security property. If the provider ever recycles
    an id, the second claim fails rather than transferring the first."""
    uow = FakeUnitOfWork()
    await uow.browser_sessions.claim(
        f.TENANT, BrowserSessionId("sess-1"), f.OPERATOR, FakeClock().now()
    )

    with pytest.raises(Conflict):
        await uow.browser_sessions.claim(
            TenantId("rival"), BrowserSessionId("sess-1"), PrincipalId("x"), FakeClock().now()
        )


async def test_a_second_browser_borrows_this_tenant_s_own() -> None:
    """One browser behind the provider, so asking for a second does not produce
    one. Borrowing is right; borrowing across tenants was not."""
    uow, provider = FakeUnitOfWork(), _OneBrowser()
    browsers = _browsers(uow, provider)
    first = await browsers.open(MINE)

    again = await browsers.open(MINE)

    assert again.id == first.id


async def test_it_will_not_borrow_a_browser_belonging_to_someone_else() -> None:
    uow, provider = FakeUnitOfWork(), _OneBrowser()
    browsers = _browsers(uow, provider)
    await browsers.open(MINE)

    with pytest.raises(BrowserUnavailable):
        await browsers.open(THEIRS)


async def test_it_will_not_borrow_one_somebody_is_demonstrating_in() -> None:
    uow, provider = FakeUnitOfWork(), _OneBrowser()
    browsers = _browsers(uow, provider)
    theirs = await browsers.open(MINE)
    recording = f.recording()
    recording.attach_browser_session(theirs.id)
    await uow.recordings.add(recording)

    with pytest.raises(BrowserUnavailable):
        await browsers.open(MINE)


async def test_an_attached_browser_is_owned_like_any_other() -> None:
    """It used to be the literal id "attached" for every tenant and every
    recording, so they all collided on one string."""
    uow, provider = FakeUnitOfWork(), FakeBrowserProvider()
    browsers = _browsers(uow, provider)

    attached = await browsers.attach(MINE, "ws://localhost:9222/devtools/browser/x")

    assert str(attached.id).startswith("attached_")
    assert attached.debugger_url == "ws://localhost:9222/devtools/browser/x"
    assert str(attached.id) in uow.browser_sessions.rows


async def test_releasing_gives_back_the_browser_and_the_claim() -> None:
    uow, provider = FakeUnitOfWork(), FakeBrowserProvider()
    browsers = _browsers(uow, provider)
    opened = await browsers.open(MINE)

    await browsers.release(opened.id)

    assert opened.id in provider.closed
    assert uow.browser_sessions.rows == {}


class _OneBrowser(FakeBrowserProvider):
    """Refuses a second session, as a self-hosted provider does."""

    async def open(self, *, start_url: str | None = None) -> object:  # type: ignore[override]
        if [held for held in self.opened if held not in self.closed]:
            raise BrowserUnavailable("this deployment has one browser and it is in use")
        return await super().open(start_url=start_url)


async def test_taking_one_says_whether_it_was_borrowed() -> None:
    """The healer closed whatever it took. A borrowed browser belongs to
    whoever signed into it, so closing it logs a warehouse operator out."""
    uow, provider = FakeUnitOfWork(), _OneBrowser()
    browsers = _browsers(uow, provider)

    opened, borrowed_first = await browsers.take(MINE)
    again, borrowed_second = await browsers.take(MINE)

    assert not borrowed_first
    assert borrowed_second and again.id == opened.id
