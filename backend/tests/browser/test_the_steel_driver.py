from __future__ import annotations

import pytest

from sro.application.ports.page import SessionRef
from sro.config import get_settings
from sro.infrastructure.steel.driver import SteelDriver
from tests.browser.steel_rig import Rig, cdp_url, cdp_url_2, rig  # noqa: F401

pytestmark = pytest.mark.browser


async def test_a_tab_is_found_again_by_its_target_id_after_a_restart(
    rig: Rig,  # noqa: F811
    cdp_url: str,  # noqa: F811
) -> None:
    session = SessionRef("local", cdp_url)
    first = SteelDriver(get_settings().page_code_path)
    target = await first.open_tab(session, rig.url("/public"))
    await first.forget(session)

    again = SteelDriver(get_settings().page_code_path)

    assert (await again.url_of(session, target)).endswith("/public")


async def test_the_page_code_is_in_every_new_document(
    rig: Rig,  # noqa: F811
    cdp_url: str,  # noqa: F811
) -> None:
    session = SessionRef("local", cdp_url)
    driver = SteelDriver(get_settings().page_code_path)
    target = await driver.open_tab(session, rig.url("/public"))

    assert await driver.evaluate(session, target, "typeof globalThis.sroPage") == "object"


async def test_saved_state_signs_a_fresh_browser_in(
    rig: Rig,  # noqa: F811
    cdp_url: str,  # noqa: F811
    cdp_url_2: str,  # noqa: F811
) -> None:
    driver = SteelDriver(get_settings().page_code_path)
    one = SessionRef("one", cdp_url)
    target = await driver.open_tab(one, rig.url("/"))
    await rig.sign_in_in(driver, one, target)
    state = await driver.storage_state(one)

    two = SessionRef("two", cdp_url_2)
    await driver.restore_state(two, state)
    landed = await driver.open_tab(two, rig.url("/app"))

    assert (await driver.url_of(two, landed)).endswith("/app")
