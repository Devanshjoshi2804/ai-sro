"""The vault side of "whose session is this".

`session_scope` names the system a call is going to. This is the rule for the
one credential that does not come from it: a header plan's own
`credential_ref`, which induction stamps with a single system for every step of
a skill because a skill had one.

Tested here rather than through a run because a run cannot reach it today --
`_check_runnable` refuses a device-less cross-system run, and a device run's
session comes from the browser. The rule is kept anyway: it is four lines, and
it is what stands between a deployment that holds both systems' credentials and
sending one system's cookie to the other.
"""

from __future__ import annotations

from sro.application.execution.headers import resolve_headers
from sro.domain.recording.sensitivity import Sensitivity
from sro.domain.skill.plan import HeaderPlan
from tests.unit.fakes import FakeCredentialVault

SCOPE = "acme"
COOKIE = HeaderPlan(
    name="cookie", sensitivity=Sensitivity.SESSION, credential_ref="blue_yonder/DC01/cookie"
)


async def _vault(**held: str) -> FakeCredentialVault:
    vault = FakeCredentialVault()
    for key, value in held.items():
        await vault.store(f"{SCOPE}/{key.replace('__', '/')}", value)
    return vault


async def test_the_calling_system_decides_which_stored_session_is_used() -> None:
    vault = await _vault(
        blue_yonder__DC01__cookie="wms=the-warehouse-session",
        sap__DC01__cookie="erp=the-finance-session",
    )

    resolved = await resolve_headers(
        (COOKIE,), values={}, vault=vault, scope=SCOPE, session_scope="sap/DC01"
    )

    # The plan says `blue_yonder`, because induction only ever knew one system.
    # The call is going to the ERP.
    assert resolved.headers == {"cookie": "erp=the-finance-session"}


async def test_a_session_it_does_not_hold_is_missing_rather_than_the_other_one() -> None:
    vault = await _vault(blue_yonder__DC01__cookie="wms=the-warehouse-session")

    resolved = await resolve_headers(
        (COOKIE,), values={}, vault=vault, scope=SCOPE, session_scope="sap/DC01"
    )

    # Falling back to the reference -- or to `<system>/cookie` for the system
    # the reference names -- would leak the same value by the other door.
    assert resolved.headers == {}
    assert resolved.missing == ("cookie",)


async def test_the_site_fallback_still_works_within_one_system() -> None:
    """A skill taught at one site stays usable at another the same login
    reaches; that is what the fallback is for, and it must not have been
    narrowed into uselessness."""
    vault = await _vault(blue_yonder__cookie="wms=the-warehouse-session")

    resolved = await resolve_headers(
        (COOKIE,), values={}, vault=vault, scope=SCOPE, session_scope="blue_yonder/SG"
    )

    assert resolved.headers == {"cookie": "wms=the-warehouse-session"}
