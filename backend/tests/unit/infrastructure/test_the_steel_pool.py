from typing import cast

import pytest

from sro.application.ports.pool import PoolFull
from sro.infrastructure.steel.client import SteelClient
from sro.infrastructure.steel.pool import SteelPool


class _Client:
    def __init__(self, name: str) -> None:
        self.name = name
        self.opened = 0

    async def open(self) -> object:
        self.opened += 1
        return type("S", (), {"id": f"{self.name}-{self.opened}"})()


def _pool(
    containers_by_tenant: dict[str, tuple[str, ...]] | None = None,
    fallback: tuple[str, ...] = (),
    per_container: int = 1,
    **clients: _Client,
) -> SteelPool:
    urls = {name.replace("_", "-"): client for name, client in clients.items()}
    return SteelPool(
        cast("dict[str, SteelClient]", {f"http://{url}:3000": c for url, c in urls.items()}),
        containers_by_tenant=containers_by_tenant,
        fallback=fallback,
        per_container=per_container,
    )


async def test_a_session_goes_to_the_least_loaded_container_of_its_tenant() -> None:
    pool = _pool(per_container=5, steel=_Client("one"), steel_2=_Client("two"))

    assert await pool.open("greyorange", {"http://steel:3000": 3, "http://steel-2:3000": 1}) == (
        "http://steel-2:3000",
        "two-1",
    )


async def test_a_full_tenant_says_so_rather_than_sharing_a_browser() -> None:
    pool = _pool(per_container=1, steel=_Client("one"))

    with pytest.raises(PoolFull):
        await pool.open("greyorange", {"http://steel:3000": 1})


async def test_two_tenants_never_receive_the_same_container() -> None:
    pool = _pool(
        per_container=1,
        containers_by_tenant={
            "acme": ("http://steel:3000",),
            "beta": ("http://steel-2:3000",),
        },
        steel=_Client("one"),
        steel_2=_Client("two"),
    )

    acme_url, _ = await pool.open("acme", {})
    beta_url, _ = await pool.open("beta", {})

    assert acme_url == "http://steel:3000"
    assert beta_url == "http://steel-2:3000"
    assert acme_url != beta_url


async def test_a_tenant_never_overflows_into_another_tenants_container() -> None:
    pool = _pool(
        per_container=1,
        containers_by_tenant={"acme": ("http://steel:3000",)},
        steel=_Client("one"),
        steel_2=_Client("two"),
    )

    await pool.open("acme", {})

    with pytest.raises(PoolFull):
        await pool.open("acme", {"http://steel:3000": 1})


async def test_a_pinned_account_stays_on_its_container_while_it_is_the_tenants() -> None:
    pool = _pool(
        per_container=5,
        containers_by_tenant={"acme": ("http://steel:3000", "http://steel-2:3000")},
        steel=_Client("one"),
        steel_2=_Client("two"),
        steel_3=_Client("three"),
    )
    busy = {"http://steel:3000": 3, "http://steel-2:3000": 1}

    pinned, _ = await pool.open("acme", busy, pinned="http://steel:3000")
    elsewhere, _ = await pool.open("acme", busy, pinned="http://steel-3:3000")

    assert pinned == "http://steel:3000"
    assert elsewhere == "http://steel-2:3000"
