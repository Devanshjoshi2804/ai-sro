from __future__ import annotations

import logging
from collections.abc import Set as AbstractSet
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
                taken: set[str] = set()
                for _ in range(_ROUNDS):
                    await _settle(page)
                    if await _visible(page, _MFA):
                        raise SignInFailed(
                            "this system asks for a second factor, which no stored credential "
                            "can answer. Connect it by hand and the session will be kept."
                        )

                    if picked := await _chose(page, choose, taken):
                        taken.add(picked)
                        steps.append("chose how to sign in")
                        continue

                    named = await _filled(page, _IDENTIFIER, username)
                    secret = await _filled(page, _PASSWORD, password)
                    if named:
                        steps.append("entered the username")
                    if secret:
                        steps.append("entered the password")

                    if not named and not secret:
                        if _on(page.url, host):
                            break
                        if not await _submit(page):
                            break
                        steps.append("continued")
                        continue
                    await _submit(page)
                await _settle(page)
                landed = page.url
                offered = await _on_offer(page)
            finally:
                await browser.close()

        if not _on(landed, host):
            raise SignInFailed(
                f"the login did not finish -- the browser is still at "
                f"{urlsplit(landed).hostname}, which offered: {offered or 'nothing clickable'}. "
                f"It did: {', '.join(steps)}. Connect this system by hand once and the "
                "session will be kept from there."
            )
        return SignInResult(landed_at=landed, steps=tuple(steps))


def _on(url: str, host: str) -> bool:
    return (urlsplit(url).hostname or "") == host


async def _settle(page: Page) -> None:
    try:
        await page.wait_for_load_state("networkidle", timeout=8000)
    except Exception:
        await page.wait_for_timeout(1500)


async def _visible(page: Page, selector: str) -> bool:
    element = await page.query_selector(selector)
    return bool(element and await element.is_visible())


async def _filled(page: Page, selector: str, value: str) -> bool:
    for element in await page.query_selector_all(selector):
        if not await element.is_visible() or await element.input_value():
            continue
        await element.fill(value)
        return True
    return False


async def _submit(page: Page) -> bool:
    for element in await page.query_selector_all(_SUBMIT):
        if await element.is_visible():
            await element.click()
            return True
    if await _visible(page, _PASSWORD) or await _visible(page, _IDENTIFIER):
        await page.keyboard.press("Enter")
        return True
    return False


async def _chose(
    page: Page, choose: tuple[str, ...], taken: AbstractSet[str] = frozenset()
) -> str | None:
    for wanted in choose:
        if not wanted.strip() or wanted in taken:
            continue
        for element in await page.query_selector_all("a, button, [role=link], [role=button]"):
            try:
                if not await element.is_visible():
                    continue
                text = ((await element.inner_text()) or "").strip()
            except Exception:
                logger.debug("an option would not describe itself", exc_info=True)
                continue
            if (text and text[:80] in wanted) or wanted[:80] in text:
                await element.click()
                return wanted
    return None


async def _on_offer(page: Page) -> str:
    seen: list[str] = []
    for element in await page.query_selector_all(
        "a, button, [role=link], [role=button], input[type=submit]"
    ):
        try:
            if not await element.is_visible():
                continue
            text = " ".join(
                (
                    (await element.inner_text()) or (await element.get_attribute("value")) or ""
                ).split()
            )[:60]
        except Exception:  # pragma: no cover - the page is redrawing
            logger.debug("an option would not describe itself", exc_info=True)
            continue
        if text and text not in seen:
            seen.append(text)
    return "; ".join(seen[:8])
