from __future__ import annotations

import asyncio
import logging
from collections.abc import Set as AbstractSet
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Final
from urllib.parse import urlsplit

from playwright.async_api import Error as PlaywrightError
from playwright.async_api import Page, async_playwright

from sro.application.ports.sign_in import (
    CredentialsRefused,
    SignInDriver,
    SignInFailed,
    SignInResult,
)

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

_OFFERS: Final = "a, button, [role=link], [role=button], input[type=submit]"

_ROUNDS: Final = 6

_QUIET_S: Final = 8.0

_PROBE_S: Final = 1.0

_STILL: Final = 5

_SHOWN: Final = 240


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
        try:
            async with async_playwright() as driver:
                browser = await driver.chromium.connect_over_cdp(
                    debugger_url, timeout=max(1.0, timeout_s * 1000)
                )
                context = browser.contexts[0] if browser.contexts else await browser.new_context()
                page = context.pages[0] if context.pages else await context.new_page()
                try:
                    return await _drive(
                        page,
                        url=url,
                        username=username,
                        password=password,
                        choose=choose,
                        timeout_s=timeout_s,
                    )
                finally:
                    await browser.close()
        except PlaywrightError as why:
            raise SignInFailed(
                f"the browser could not be driven: {_brief(why, (username, password))}"
            ) from None


class _Round(Enum):
    LANDED = auto()
    ACTED = auto()
    WAITING = auto()
    REFUSED = auto()


@dataclass(slots=True)
class _Login:
    host: str
    username: str
    password: str
    choose: tuple[str, ...]
    deadline: float
    steps: list[str] = field(default_factory=list)
    taken: set[str] = field(default_factory=set)
    typed: bool = False

    @property
    def secrets(self) -> tuple[str, ...]:
        return (self.username, self.password)


async def _drive(
    page: Page,
    *,
    url: str,
    username: str,
    password: str,
    choose: tuple[str, ...],
    timeout_s: float,
) -> SignInResult:
    try:
        return await _walk(
            page,
            url=url,
            username=username,
            password=password,
            choose=choose,
            timeout_s=timeout_s,
        )
    except PlaywrightError as why:
        raise SignInFailed(
            f"the browser could not be driven: {_brief(why, (username, password))}"
        ) from None


async def _walk(
    page: Page,
    *,
    url: str,
    username: str,
    password: str,
    choose: tuple[str, ...],
    timeout_s: float,
) -> SignInResult:
    clock = asyncio.get_running_loop()
    login = _Login(
        host=urlsplit(url).hostname or "",
        username=username,
        password=password,
        choose=choose,
        deadline=clock.time() + timeout_s,
    )
    moves = [0]

    def moved(frame: object) -> None:
        if frame == page.main_frame:
            moves[0] += 1

    page.on("framenavigated", moved)
    await page.goto(url, wait_until="domcontentloaded", timeout=_ms(login.deadline))
    login.steps.append("opened the system")
    acted = still = 0
    seen: tuple[str, int] | None = None
    trouble = ""
    while clock.time() < login.deadline:
        await _settle(page, login.deadline)
        if acted >= _ROUNDS:
            break
        try:
            did = await _round(page, login)
        except PlaywrightError as why:
            if page.is_closed():
                raise
            trouble = _brief(why, login.secrets)
            logger.debug("the page moved while it was being read: %s", trouble)
            seen, still = None, 0
            await asyncio.sleep(_PROBE_S)
            continue
        if did is _Round.LANDED:
            break
        if did is _Round.REFUSED:
            raise CredentialsRefused(
                f"the credentials were refused -- {urlsplit(page.url).hostname} showed its "
                f"sign-in form again after they were submitted, saying: "
                f"{await _shown(page, login) or 'nothing readable'}. They were submitted once "
                "and not retried. Check the stored username and password."
            )
        if did is _Round.ACTED:
            acted += 1
            seen, still = None, 0
            continue
        here = (page.url, moves[0])
        still = still + 1 if here == seen else 0
        seen = here
        if still >= _STILL:
            raise SignInFailed(
                f"the login stopped at {urlsplit(page.url).hostname}, which shows: "
                f"{await _shown(page, login) or 'nothing readable'} and offered: "
                f"{await _on_offer(page, login.secrets) or 'nothing clickable'}. "
                f"It did: {', '.join(login.steps)}. Connect this system by hand once and "
                "the session will be kept from there."
            )
        await asyncio.sleep(_PROBE_S)

    landed = page.url
    if not _on(landed, login.host):
        offered = await _on_offer(page, login.secrets)
        raise SignInFailed(
            f"the login did not finish -- the browser is still at "
            f"{urlsplit(landed).hostname}, which offered: {offered or 'nothing clickable'}. "
            f"It did: {', '.join(login.steps)}."
            + (f" The last thing the page did was fail with: {trouble}." if trouble else "")
            + " Connect this system by hand once and the session will be kept from there."
        )
    return SignInResult(landed_at=landed, steps=tuple(login.steps))


async def _round(page: Page, login: _Login) -> _Round:
    if await _visible(page, _MFA):
        raise SignInFailed(
            "this system asks for a second factor, which no stored credential "
            "can answer. Connect it by hand and the session will be kept."
        )

    if login.typed:
        if await _empty(page, _PASSWORD, login.deadline):
            return _Round.REFUSED
        if _on(page.url, login.host):
            return _Round.LANDED
        if await _visible(page, _PASSWORD):
            return _Round.WAITING
        if not await _submit(page, login.deadline):
            return _Round.WAITING
        login.steps.append("continued")
        return _Round.ACTED

    if picked := await _chose(page, login.choose, login.deadline, login.taken):
        login.taken.add(picked)
        login.steps.append("chose how to sign in")
        return _Round.ACTED

    named = await _filled(page, _IDENTIFIER, login.username, login.deadline)
    secret = await _filled(page, _PASSWORD, login.password, login.deadline)
    if named:
        login.steps.append("entered the username")
    if secret:
        login.steps.append("entered the password")
        login.typed = True

    if not named and not secret:
        if _on(page.url, login.host):
            return _Round.LANDED
        if not await _submit(page, login.deadline):
            return _Round.WAITING
        login.steps.append("continued")
        return _Round.ACTED
    await _submit(page, login.deadline)
    return _Round.ACTED


def _on(url: str, host: str) -> bool:
    return (urlsplit(url).hostname or "") == host


def _ms(deadline: float) -> float:
    return max(1.0, (deadline - asyncio.get_running_loop().time()) * 1000)


def _brief(error: BaseException, secrets: tuple[str, ...]) -> str:
    first = _redacted(str(error).split("\n", 1)[0], secrets)
    return f"{type(error).__name__}: {first[:200]}"


def _redacted(text: str, secrets: tuple[str, ...]) -> str:
    for secret in secrets:
        if secret:
            text = text.replace(secret, "[redacted]")
    return text


async def _settle(page: Page, deadline: float) -> None:
    try:
        await page.wait_for_load_state("networkidle", timeout=min(_QUIET_S * 1000, _ms(deadline)))
    except Exception:
        await asyncio.sleep(min(_PROBE_S, _ms(deadline) / 1000))


async def _visible(page: Page, selector: str) -> bool:
    element = await page.query_selector(selector)
    return bool(element and await element.is_visible())


async def _empty(page: Page, selector: str, deadline: float) -> bool:
    for element in await page.query_selector_all(selector):
        if await element.is_visible() and not await element.input_value(timeout=_ms(deadline)):
            return True
    return False


async def _filled(page: Page, selector: str, value: str, deadline: float) -> bool:
    for element in await page.query_selector_all(selector):
        if not await element.is_visible() or await element.input_value(timeout=_ms(deadline)):
            continue
        await element.fill(value, timeout=_ms(deadline))
        return True
    return False


async def _submit(page: Page, deadline: float) -> bool:
    for element in await page.query_selector_all(_SUBMIT):
        if await element.is_visible():
            await element.click(timeout=_ms(deadline))
            return True
    if await _visible(page, _PASSWORD) or await _visible(page, _IDENTIFIER):
        await page.keyboard.press("Enter")
        return True
    return False


async def _chose(
    page: Page, choose: tuple[str, ...], deadline: float, taken: AbstractSet[str] = frozenset()
) -> str | None:
    for wanted in choose:
        if not wanted.strip() or wanted in taken:
            continue
        for element in await page.query_selector_all("a, button, [role=link], [role=button]"):
            try:
                if not await element.is_visible():
                    continue
                text = ((await element.inner_text()) or "").strip()
            except Exception as why:
                logger.debug("an option would not describe itself: %s", _brief(why, ()))
                continue
            if (text and text[:80] in wanted) or wanted[:80] in text:
                await element.click(timeout=_ms(deadline))
                return wanted
    return None


async def _shown(page: Page, login: _Login) -> str:
    try:
        text = await page.inner_text("body", timeout=_ms(login.deadline))
    except PlaywrightError as why:
        logger.debug("the page would not say what it shows: %s", _brief(why, login.secrets))
        return ""
    return " ".join(_redacted(text, login.secrets).split())[:_SHOWN]


async def _on_offer(page: Page, secrets: tuple[str, ...]) -> str:
    seen: list[str] = []
    try:
        elements = await page.query_selector_all(_OFFERS)
    except PlaywrightError as why:
        logger.debug("the page moved while its options were read: %s", _brief(why, ()))
        return ""
    for element in elements:
        try:
            if not await element.is_visible():
                continue
            said = (await element.inner_text()) or (await element.get_attribute("value")) or ""
            text = " ".join(_redacted(said, secrets).split())[:60]
        except Exception as why:  # pragma: no cover - the page is redrawing
            logger.debug("an option would not describe itself: %s", _brief(why, ()))
            continue
        if text and text not in seen:
            seen.append(text)
    return "; ".join(seen[:8])
