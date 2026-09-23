from __future__ import annotations

import logging
import struct

from playwright.async_api import Frame, Page, async_playwright

from sro.application.ports.ui import ResolvedLocator, UiOutcome, UiUnavailable
from sro.application.ports.vision import Screen
from sro.domain.recording.events import ActionKind
from sro.domain.skill.locator import LocatorStrategy

logger = logging.getLogger(__name__)

_TEXT_DIGEST = r"""(page) => {
    const seen = [];
    document.querySelectorAll('input, select, textarea, button, a, .x-grid-cell, label')
        .forEach((el) => {
            const rect = el.getBoundingClientRect();
            if (rect.width < 2 || rect.height < 2) return;
            const label = (el.getAttribute('aria-label') || el.getAttribute('placeholder')
                || el.textContent || el.name || '').trim().slice(0, 80);
            // Normalised 0-1000, because that is the space the vision model
            // answers in. Mixing pixels here and 0-1000 there made a model
            // repeat a digest coordinate verbatim and land a quarter of the way
            // up the page.
            // In the page's space, not this frame's. The screen the model is
            // shown is the whole page; a control inside an iframe that starts
            // 90px down was described as if the iframe were the screen, so
            // every hint it gave was that much too high.
            const nx = Math.round((rect.x + rect.width / 2 + page.dx) / page.width * 1000);
            const ny = Math.round((rect.y + rect.height / 2 + page.dy) / page.height * 1000);
            if (label) seen.push(`${label}: ${nx},${ny}`);
        });
    return seen.slice(0, 200).join('\n');
}"""

_TYPE_DELAY_MS = 60


class PlaywrightUiDriver:
    def __init__(self, debugger_url: str) -> None:
        self._debugger_url = debugger_url

    def for_session(self, debugger_url: str) -> PlaywrightUiDriver:
        return PlaywrightUiDriver(debugger_url)

    async def current_url(self) -> str | None:
        if not self._debugger_url:
            return None
        async with self._page() as page:
            return page.url

    async def perform(
        self,
        *,
        action: ActionKind,
        locators: tuple[ResolvedLocator, ...],
        value: str | None = None,
    ) -> UiOutcome:
        if not self._debugger_url:
            raise UiUnavailable("no browser is attached; set SRO_UI_DEBUGGER_URL")

        async with self._page() as page:
            frame = await _visible_screen(page)
            for locator in locators:
                selector, count = await _resolve(frame, locator)
                if selector is None:
                    continue
                try:
                    await _act(page, frame, selector, action=action, value=value)
                except Exception as error:
                    logger.debug("locator %s resolved but failed", locator.query, exc_info=True)
                    return UiOutcome(
                        performed=False,
                        matched_by=locator.strategy,
                        candidates=count,
                        detail=f"found the control but could not {action}: {error}",
                    )
                await page.wait_for_timeout(1200)
                return UiOutcome(performed=True, matched_by=locator.strategy, candidates=count)

        tried = ", ".join(f"{loc.strategy}={loc.query}" for loc in locators) or "nothing"
        return UiOutcome(performed=False, detail=f"no control matched: {tried}")

    async def capture(self) -> Screen:
        if not self._debugger_url:
            raise UiUnavailable("no browser is attached; set SRO_UI_DEBUGGER_URL")

        async with self._page() as page:
            frame = await _visible_screen(page)
            image = await page.screenshot(type="png")
            width, height = await _screen_size(page, image)
            try:
                offset = await _offset_of(frame, page)
                digest = await frame.evaluate(
                    _TEXT_DIGEST,
                    {"dx": offset[0], "dy": offset[1], "width": width, "height": height},
                )
            except Exception:
                logger.debug("the visible frame would not describe itself", exc_info=True)
                digest = ""
            return Screen(
                image=image,
                mime_type="image/png",
                width=width,
                height=height,
                text_digest=str(digest)[:8000],
            )

    async def perform_at(
        self, *, action: ActionKind, x: int, y: int, value: str | None = None
    ) -> UiOutcome:
        if not self._debugger_url:
            raise UiUnavailable("no browser is attached; set SRO_UI_DEBUGGER_URL")

        async with self._page() as page:
            try:
                await page.mouse.move(x, y)
                match action:
                    case ActionKind.CLICK:
                        await page.mouse.click(x, y)
                    case ActionKind.TYPE:
                        await page.mouse.click(x, y)
                        await page.keyboard.type(value or "", delay=_TYPE_DELAY_MS)
                    case ActionKind.PRESS:
                        await page.keyboard.press(value or "Enter")
                    case ActionKind.SCROLL:
                        await page.mouse.wheel(0, int(value or 400))
                    case ActionKind.HOVER:
                        pass
                    case _:
                        return UiOutcome(
                            performed=False, detail=f"{action} cannot be performed at a point"
                        )
            except Exception as error:
                return UiOutcome(
                    performed=False, detail=f"could not {action} at ({x},{y}): {error}"
                )
            await page.wait_for_timeout(1200)
            return UiOutcome(performed=True, candidates=1)

    def _page(self) -> _AttachedPage:
        return _AttachedPage(self._debugger_url)


class _AttachedPage:
    def __init__(self, debugger_url: str) -> None:
        self._debugger_url = debugger_url

    def for_session(self, debugger_url: str) -> PlaywrightUiDriver:
        return PlaywrightUiDriver(debugger_url)

    async def __aenter__(self) -> Page:
        self._playwright = await async_playwright().start()
        try:
            self._browser = await self._playwright.chromium.connect_over_cdp(self._debugger_url)
        except Exception as error:
            await self._playwright.stop()
            raise UiUnavailable(f"could not attach to {self._debugger_url}: {error}") from error

        contexts = self._browser.contexts
        pages = [page for context in contexts for page in context.pages]
        if not pages:
            raise UiUnavailable("the attached browser has no page open")
        return pages[0]

    async def __aexit__(self, *exc: object) -> None:
        await self._browser.close()
        await self._playwright.stop()


async def _offset_of(frame: Frame, page: Page) -> tuple[float, float]:
    if frame == page.main_frame:
        return (0.0, 0.0)
    try:
        element = await frame.frame_element()
        box = await element.bounding_box()
    except Exception:
        logger.debug("a frame would not say where it is", exc_info=True)
        return (0.0, 0.0)
    return (float(box["x"]), float(box["y"])) if box else (0.0, 0.0)


async def _screen_size(page: Page, image: bytes) -> tuple[int, int]:
    try:
        measured = await page.evaluate(
            "() => ({ width: window.innerWidth, height: window.innerHeight })"
        )
        if measured and int(measured["width"]) > 0 and int(measured["height"]) > 0:
            return int(measured["width"]), int(measured["height"])
    except Exception:
        logger.debug("the page would not say how big it is", exc_info=True)

    marker = image.find(b"IHDR")
    if marker != -1:
        width, height = struct.unpack(">II", image[marker + 4 : marker + 12])
        if width and height:
            ratio = await _device_pixel_ratio(page)
            return int(width / ratio), int(height / ratio)
    return 1280, 800


async def _device_pixel_ratio(page: Page) -> float:
    try:
        ratio = float(await page.evaluate("() => window.devicePixelRatio"))
    except Exception:
        logger.debug("the page would not say its pixel ratio", exc_info=True)
        return 1.0
    return ratio if ratio > 0 else 1.0


async def _visible_screen(page: Page) -> Frame:
    best: tuple[Frame, int] | None = None
    for frame in page.frames:
        try:
            visible = await frame.evaluate(
                "document.visibilityState === 'visible' && document.body.offsetHeight > 100"
            )
            weight = await frame.evaluate("document.querySelectorAll('.x-panel, form').length")
        except Exception:
            logger.debug("frame %s did not answer", frame.url[:80], exc_info=True)
            continue
        if visible and weight and (best is None or weight > best[1]):
            best = (frame, int(weight))
    return best[0] if best else page.main_frame


async def _resolve(frame: Frame, locator: ResolvedLocator) -> tuple[str | None, int]:
    match locator.strategy:
        case LocatorStrategy.COMPONENT:
            return await _resolve_component(frame, locator)
        case LocatorStrategy.TEST_ID:
            selector = f'[data-testid="{locator.query}"]'
        case LocatorStrategy.ROLE_AND_NAME:
            role, _, name = locator.query.partition("|")
            selector = f'[role="{role}"][aria-label="{name}"]'
        case LocatorStrategy.TEXT:
            selector = f"text={locator.query}"
        case LocatorStrategy.CSS_PATH:
            selector = locator.query

    count = await frame.locator(selector).count()
    if not count:
        return None, 0
    return selector, count


async def _resolve_component(frame: Frame, locator: ResolvedLocator) -> tuple[str | None, int]:
    result = await frame.evaluate(
        """(query) => {
            if (!window.Ext || !Ext.ComponentQuery) return null;
            const all = Ext.ComponentQuery.query(query);
            const visible = all.filter((c) => c.isVisible && c.isVisible(true));
            const chosen = visible[0];
            if (!chosen) return {count: all.length, id: null};
            const el = chosen.inputEl || chosen.btnEl || chosen.el;
            const dom = el && el.dom ? el.dom : null;
            if (dom && !dom.id) dom.id = 'sro-' + Math.random().toString(36).slice(2);
            return {count: visible.length, id: dom ? dom.id : null};
        }""",
        locator.query,
    )
    if not result or not result.get("id"):
        return None, 0
    return f"#{result['id']}", int(result.get("count") or 1)


async def _act(
    page: Page,
    frame: Frame,
    selector: str,
    *,
    action: ActionKind,
    value: str | None,
) -> None:
    element = frame.locator(selector).first
    match action:
        case ActionKind.CLICK:
            await element.click(timeout=8000)
        case ActionKind.TYPE:
            await element.click(timeout=8000)
            await element.fill("")
            await page.keyboard.type(value or "", delay=_TYPE_DELAY_MS)
        case ActionKind.SELECT:
            await element.select_option(value or "", timeout=8000)
        case ActionKind.PRESS:
            await element.press(value or "Enter", timeout=8000)
        case ActionKind.HOVER:
            await element.hover(timeout=8000)
        case _:
            raise ValueError(f"{action} cannot be performed by this driver")
