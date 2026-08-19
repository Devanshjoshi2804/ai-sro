"""A run repairs the session it needs, once, and never repairs the skill.

The loop being replaced was done by hand: read the failing step, notice the
redirect to a login page, take a browser, sign in, observe what the application
sends, put it in the vault, run again. What matters in these tests is not that
it heals -- it is everything it refuses to heal.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest

from sro.application.connection.browsers import Browsers
from sro.application.connection.check_session import CheckSession
from sro.application.connection.connect_system import RefreshSession
from sro.application.connection.sign_in import EnsureSignedIn, SignIn
from sro.application.context import RequestContext
from sro.application.execution.self_heal import HealBudget, SelfHeal
from sro.application.knowledge.record_claim import RecordClaims
from sro.domain.connection.connection import Connection, ConnectionId
from sro.domain.execution.diagnosis import Remedy, diagnose
from sro.domain.execution.escalation import FailureKind
from tests import factories as f
from tests.unit.fakes import (
    FakeBrowserProvider,
    FakeClock,
    FakeCredentialVault,
    FakeEmbedder,
    FakeHttpCaller,
    FakeIdFactory,
    FakeSignInDriver,
    FakeUnitOfWork,
)

CTX = RequestContext(tenant_id=f.TENANT, principal_id=f.OPERATOR)


def test_a_login_page_is_the_one_failure_a_write_may_retry() -> None:
    """Proof the request never arrived, and the only status that gives it.

    Blue Yonder answers an expired session by redirecting to its identity
    provider, so the application never saw the call. A write may safely be sent
    again after the session is repaired.
    """
    found = diagnose(
        failure=FailureKind.ASSERTION_FAILED,
        status_code=302,
        redirected_off_host=True,
    )

    assert found.remedy is Remedy.REFRESH_SESSION
    assert found.safe_for_writes


@pytest.mark.parametrize("status", [500, 502, 409, 422, None])
def test_nothing_is_retried_when_the_outcome_is_unknown(status: int | None) -> None:
    """The failures that could have written half a task.

    A 500 may have committed. A 409 is the system disagreeing about facts. None
    of them are fixed by sending the same request again, and a warehouse task
    done twice is worse than one done never.
    """
    found = diagnose(
        failure=FailureKind.STATUS_MISMATCH, status_code=status, redirected_off_host=False
    )

    assert found.remedy is Remedy.NONE
    assert not found.safe_for_writes


def test_a_missing_minted_header_is_repaired_without_signing_in_again() -> None:
    """On a system that permits one session, a login costs the operator theirs.

    The token is reissued by the page, so it can be taken again without one.
    """
    found = diagnose(
        failure=FailureKind.CREDENTIAL_MISSING,
        status_code=None,
        redirected_off_host=False,
        missing_headers=("csrf-encrypt-token",),
    )

    assert found.remedy is Remedy.REFRESH_SESSION_CONTEXT
    # Nothing was sent: the step refused before it built the request.
    assert found.safe_for_writes


def test_an_accepted_session_with_a_rejected_request_is_a_token_not_a_login() -> None:
    found = diagnose(failure=None, status_code=403, redirected_off_host=False)

    assert found.remedy is Remedy.REFRESH_SESSION_CONTEXT


def test_a_control_that_moved_is_the_ladders_business_not_the_healers() -> None:
    """A remedy recovers what the target system owns. A control that moved is
    the skill drifting, and a rung that looks at the screen is the answer -- via
    the escalation table, which already governs it."""
    found = diagnose(
        failure=FailureKind.CONTROL_NOT_FOUND, status_code=None, redirected_off_host=False
    )

    assert found.remedy is Remedy.ESCALATE_MEDIUM


@pytest.mark.asyncio
async def test_one_repair_per_step_then_the_failure_stands() -> None:
    """A second identical failure means the diagnosis was wrong.

    What helps then is one clear failure for a person to read, not a log of six
    attempts at the same wrong idea.
    """
    budget = HealBudget()

    assert budget.take(0, Remedy.REFRESH_SESSION) is True
    assert budget.take(0, Remedy.REFRESH_SESSION) is False
    # A different step, and a different remedy on the same step, are each their
    # own attempt: they are different claims about what is wrong.
    assert budget.take(1, Remedy.REFRESH_SESSION) is True
    assert budget.take(0, Remedy.REFRESH_SESSION_CONTEXT) is True


@pytest.mark.asyncio
async def test_an_outage_is_never_answered_by_signing_in() -> None:
    """Signing in during an outage spends the credentials against a system that
    cannot answer, and throws away a session that may still be good."""
    uow, vault, browser, http = (
        FakeUnitOfWork(),
        FakeCredentialVault(),
        FakeBrowserProvider(),
        FakeHttpCaller(),
    )
    connection = Connection(
        id=ConnectionId("con_1"),
        tenant_id=f.TENANT,
        name="WMS",
        target_system="blue_yonder",
        base_url="https://wms.example.com/portal",
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    connection.authenticated(datetime(2026, 1, 2, tzinfo=UTC))
    async with uow:
        await uow.connections.add(connection)
        await uow.commit()
    await vault.store(connection.cookie_key, "SESSIONID=maybe-fine")
    http.unreachable = True

    sign_in = SignIn(
        uow, vault, browser, FakeSignInDriver(), RefreshSession(uow, vault, FakeClock())
    )
    check = CheckSession(uow, vault, http)
    healer = SelfHeal(
        uow,
        vault,
        browser,
        check,
        EnsureSignedIn(sign_in, check, uow),
        RecordClaims(uow, FakeClock(), FakeIdFactory(), FakeEmbedder()),
        RefreshSession(uow, vault, FakeClock()),
        Browsers(browser, uow, FakeClock(), FakeIdFactory()),
    )

    healed = await healer.attempt(
        CTX,
        target_system="blue_yonder",
        facility="SG",
        step_index=0,
        mutating=False,
        budget=HealBudget(),
        status_code=302,
        redirected_off_host=True,
    )

    # Reported rather than swallowed: nothing was signed in, and the step is
    # told why instead of being left with the assertion that failed.
    assert healed is not None and not healed.repaired
    assert await vault.get(connection.cookie_key) == "SESSIONID=maybe-fine"


@pytest.mark.asyncio
async def test_a_live_session_with_a_rejected_call_is_repaired_as_context() -> None:
    """What the live WMS taught the healer on its first outing.

    The portal accepted the cookies and the data API refused the call, so the
    session check said signed in, the remedy signed nothing in, and it reported
    success while the retry came back 302 all the same. A session that is alive
    while the call is refused is a token problem, not a login problem.
    """
    uow, vault, browser, http = (
        FakeUnitOfWork(),
        FakeCredentialVault(),
        FakeBrowserProvider(),
        FakeHttpCaller(),
    )
    connection = Connection(
        id=ConnectionId("con_1"),
        tenant_id=f.TENANT,
        name="WMS",
        target_system="blue_yonder",
        base_url="https://wms.example.com/portal",
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    connection.authenticated(datetime(2026, 1, 2, tzinfo=UTC))
    async with uow:
        await uow.connections.add(connection)
        await uow.commit()
    await vault.store(connection.cookie_key, "SESSIONID=alive")
    http.answer(status_code=200)  # the portal is happy; the API was not
    browser.headers = {
        "csrf-encrypt-token": "fresh",
        "referer": "https://wms.example.com/page?ctx=1",
    }

    sign_in = SignIn(
        uow, vault, browser, FakeSignInDriver(), RefreshSession(uow, vault, FakeClock())
    )
    check = CheckSession(uow, vault, http)
    healer = SelfHeal(
        uow,
        vault,
        browser,
        check,
        EnsureSignedIn(sign_in, check, uow),
        RecordClaims(uow, FakeClock(), FakeIdFactory(), FakeEmbedder()),
        RefreshSession(uow, vault, FakeClock()),
        Browsers(browser, uow, FakeClock(), FakeIdFactory()),
    )

    healed = await healer.attempt(
        CTX,
        target_system="blue_yonder",
        facility="SG",
        step_index=0,
        mutating=False,
        budget=HealBudget(),
        status_code=302,
        redirected_off_host=True,
        endpoint="GET /data/WM/wm/policies",
    )

    assert healed is not None
    assert await vault.get("acme/blue_yonder/SG/csrf-encrypt-token") == "fresh"
    assert await vault.get("acme/blue_yonder/SG/referer") == "https://wms.example.com/page?ctx=1"


@pytest.mark.asyncio
async def test_the_token_and_the_session_that_minted_it_are_taken_together() -> None:
    """The pairing bug, in the healer this time.

    A token minted in one browser and a cookie kept from another authenticate
    nothing. The first version took the token alone, reported success, and the
    retry was refused exactly as before.
    """
    uow, vault = FakeUnitOfWork(), FakeCredentialVault()
    browser, http = FakeBrowserProvider(), FakeHttpCaller()
    connection = Connection(
        id=ConnectionId("con_1"),
        tenant_id=f.TENANT,
        name="WMS",
        target_system="blue_yonder",
        base_url="https://wms.example.com/portal",
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    connection.authenticated(datetime(2026, 1, 2, tzinfo=UTC))
    async with uow:
        await uow.connections.add(connection)
        await uow.commit()
    await vault.store(connection.cookie_key, "SESSIONID=stale")
    await vault.store(
        connection.session_key,
        json.dumps(
            {
                "origin": connection.base_url,
                "cookies": [{"name": "SESSIONID", "value": "stale", "domain": "wms.example.com"}],
            }
        ),
    )
    http.answer(status_code=200)  # the portal is happy; the API was not
    browser.headers = {"csrf-encrypt-token": "fresh"}
    browser.cookies = (
        {"name": "SESSIONID", "value": "minted-with-it", "domain": "wms.example.com"},
    )

    sign_in = SignIn(
        uow, vault, browser, FakeSignInDriver(), RefreshSession(uow, vault, FakeClock())
    )
    check = CheckSession(uow, vault, http)
    healer = SelfHeal(
        uow,
        vault,
        browser,
        check,
        EnsureSignedIn(sign_in, check, uow),
        RecordClaims(uow, FakeClock(), FakeIdFactory(), FakeEmbedder()),
        RefreshSession(uow, vault, FakeClock()),
        Browsers(browser, uow, FakeClock(), FakeIdFactory()),
    )

    healed = await healer.attempt(
        CTX,
        target_system="blue_yonder",
        facility="SG",
        step_index=0,
        mutating=False,
        budget=HealBudget(),
        status_code=302,
        redirected_off_host=True,
        endpoint="GET /data/WM/wm/transportModes",
    )

    assert healed is not None
    # The browser started from the stored session rather than blank: a browser
    # sent to the application with nothing in it lands on a login page, and
    # everything read there belongs to nobody.
    assert browser.restored
    assert await vault.get("acme/blue_yonder/SG/csrf-encrypt-token") == "fresh"
    assert await vault.get(connection.cookie_key) == "SESSIONID=minted-with-it"


@pytest.mark.asyncio
async def test_a_provider_with_no_browser_says_so_instead_of_going_quiet() -> None:
    """What an operator was shown for a read that came back 302.

    The step said "assertion_failed", which describes the assertion and not the
    reason: the session was gone, and the healer could not renew it because the
    browser provider had nothing to give -- a self-hosted Steel whose Chrome had
    been orphaned on its own profile lock. Both facts are actionable; the one
    that was reported is not.
    """
    uow, vault, http = FakeUnitOfWork(), FakeCredentialVault(), FakeHttpCaller()
    browser = FakeBrowserProvider(available=False)
    connection = Connection(
        id=ConnectionId("con_1"),
        tenant_id=f.TENANT,
        name="WMS",
        target_system="blue_yonder",
        base_url="https://wms.example.com/portal",
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    connection.authenticated(datetime(2026, 1, 2, tzinfo=UTC))
    async with uow:
        await uow.connections.add(connection)
        await uow.commit()
    await vault.store(connection.cookie_key, "SESSIONID=alive")
    http.answer(status_code=200)  # the portal answers; the data call did not

    sign_in = SignIn(
        uow, vault, browser, FakeSignInDriver(), RefreshSession(uow, vault, FakeClock())
    )
    healer = SelfHeal(
        uow,
        vault,
        browser,
        CheckSession(uow, vault, http),
        EnsureSignedIn(sign_in, CheckSession(uow, vault, http), uow),
        RecordClaims(uow, FakeClock(), FakeIdFactory(), FakeEmbedder()),
        RefreshSession(uow, vault, FakeClock()),
        Browsers(browser, uow, FakeClock(), FakeIdFactory()),
    )

    healed = await healer.attempt(
        CTX,
        target_system="blue_yonder",
        facility="SG",
        step_index=0,
        mutating=False,
        budget=HealBudget(),
        status_code=302,
        redirected_off_host=True,
    )

    assert healed is not None and not healed.repaired
    assert "login page" in healed.because
    assert "could not take a browser" in healed.detail
