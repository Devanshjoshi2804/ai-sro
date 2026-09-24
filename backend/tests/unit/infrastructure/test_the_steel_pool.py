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


def _pool(**clients: _Client) -> SteelPool:
    urls = {name.replace("_", "-"): client for name, client in clients.items()}
    return SteelPool(
        cast("dict[str, SteelClient]", {f"http://{url}:3000": c for url, c in urls.items()}),
        per_container=1,
    )


async def test_a_session_goes_to_the_first_container_with_room() -> None:
    pool = _pool(steel=_Client("one"), steel_2=_Client("two"))

    assert await pool.open({"http://steel:3000": 1}) == ("http://steel-2:3000", "two-1")


async def test_a_full_pool_says_so_rather_than_sharing_a_browser() -> None:
    pool = _pool(steel=_Client("one"))

    with pytest.raises(PoolFull):
        await pool.open({"http://steel:3000": 1})
