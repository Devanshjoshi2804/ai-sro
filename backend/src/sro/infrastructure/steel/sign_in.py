"""Sign a hosted browser in by filling the system's own login page.

Written against the shape of a login rather than against one vendor's markup:
a page with a password box wants a password, a page with only a text box wants
an identifier, and an identity provider that asks for them on separate pages is
the same loop run twice. That covers Keycloak, Azure B2C and the ordinary
single-form login without a per-system script.

What it will not do is a second factor. A code sent to a phone has no answer in
the vault, and pretending otherwise would leave an operator watching a browser
time out. Those systems are told plainly to connect by hand.
"""

from __future__ import annotations

import logging
from typing import Final
from urllib.parse import urlsplit

from playwright.async_api import Page, async_playwright

from sro.application.ports.sign_in import SignInDriver, SignInFailed, SignInResult

logger = logging.getLogger(__name__)

_PASSWORD: Final = "input[type=password]:not([disabled])"  # noqa: S105 -- a CSS selector
_IDENTIFIER: Final = (
    "input[type=email]:not([disabled]), "
    "input[type=text]:not([disabled]), "
    "input[type=tel]:not([disabled])"
)
_SUBMIT: Final = (
    "button[type=submit]:not([disabled]), "
    "input[type=submit]:not([disabled]), "
    "button#next, button#continue"
)
_MFA: Final = (
    "input[autocomplete='one-time-code'], "
    "input[name*='otp' i], input[name*='mfa' i], input[id*='verification' i]"
)

_ROUNDS: Final = 6
"""Identifier page, password page, consent, and slack. A login that has not
finished in six is stuck, and looping harder on a stuck login only delays
telling somebody."""


class PlaywrightSignIn(SignInDriver):
    async def sign_in(
        self,
        *,
        debugger_url: str,
        url: str,
        username: str,
        password: str,
        choose: tuple[str, ...] = (),
        timeout_s: float = 90.0,
    ) -> SignInResult:
        steps: list[str] = []
        host = urlsplit(url).hostname or ""
        async with async_playwright() as driver:
            browser = await driver.chromium.connect_over_cdp(debugger_url)
            context = browser.contexts[0] if browser.contexts else await browser.new_context()
            page = context.pages[0] if context.pages else await context.new_page()
            try:
                await page.goto(url, wait_until="domcontentloaded")
                steps.append("opened the system")
                for _ in range(_ROUNDS):
                    await _settle(page)
                    if await _visible(page, _MFA):
                        raise SignInFailed(
                            "this system asks for a second factor, which no stored credential "
                            "can answer. Connect it by hand and the session will be kept."
                        )
                    if await _filled(page, _PASSWORD, password):
                        steps.append("entered the password")
                    elif await _filled(page, _IDENTIFIER, username):
                        steps.append("entered the username")
                    elif _on(page.url, host):
                        break
                    else:
                        # No field, not home: an account picker or a consent
                        # screen. Azure B2C opens by asking which tenant the
                        # operator belongs to, and that page has links rather
                        # than inputs -- the driver filled nothing, found no
                        # submit button, and stopped one click from the login
                        # form every time.
                        if await _chose(page, choose):
                            steps.append("chose how to sign in")
                            continue
                        if not await _submit(page):
                            break
                        steps.append("continued")
                        continue
                    await _submit(page)
                await _settle(page)
                landed = page.url
            finally:
                await browser.close()

        if not _on(landed, host):
            raise SignInFailed(
                f"the login did not finish -- the browser is still at {urlsplit(landed).hostname}. "
                "Connect this system by hand once and the session will be kept from there."
            )
        return SignInResult(landed_at=landed, steps=tuple(steps))


def _on(url: str, host: str) -> bool:
    return (urlsplit(url).hostname or "") == host


async def _settle(page: Page) -> None:
    """Give the page the moment it needs, without making it a deadline.

    Identity providers redirect through several documents, some of which never
    go quiet -- so a timeout here is normal and means "carry on", not "failed".
    """
    try:
        await page.wait_for_load_state("networkidle", timeout=8000)
    except Exception:
        await page.wait_for_timeout(1500)


async def _visible(page: Page, selector: str) -> bool:
    element = await page.query_selector(selector)
    return bool(element and await element.is_visible())


async def _filled(page: Page, selector: str, value: str) -> bool:
    """Fill the first visible match, and say whether there was one.

    Fills only an empty box: an identity provider that carries the username
    across its own pages would otherwise have it typed twice.
    """
    for element in await page.query_selector_all(selector):
        if not await element.is_visible() or await element.input_value():
            continue
        await element.fill(value)
        return True
    return False


async def _submit(page: Page) -> bool:
    """Press the button, or the key that stands in for it."""
    for element in await page.query_selector_all(_SUBMIT):
        if await element.is_visible():
            await element.click()
            return True
    if await _visible(page, _PASSWORD) or await _visible(page, _IDENTIFIER):
        await page.keyboard.press("Enter")
        return True
    return False


async def _chose(page: Page, choose: tuple[str, ...]) -> bool:
    """Click the identity provider a demonstration showed us choosing.

    Matched on the text somebody was recorded clicking rather than on anything
    this code believes about tenants: "Local WMS users (bf56-001-eus2) (SSO)"
    means nothing to anyone who has not seen this deployment.
    """
    for wanted in choose:
        if not wanted.strip():
            continue
        for element in await page.query_selector_all("a, button, [role=link], [role=button]"):
            try:
                if not await element.is_visible():
                    continue
                text = ((await element.inner_text()) or "").strip()
            except Exception:
                # A chooser redraws itself as it is read. Not the option.
                logger.debug("an option would not describe itself", exc_info=True)
                continue
            if (text and text[:80] in wanted) or wanted[:80] in text:
                await element.click()
                return True
    return False
