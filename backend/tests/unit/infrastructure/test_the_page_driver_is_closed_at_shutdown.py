"""The page driver holds a CDP connection per Steel container and a Playwright
instance for as long as the process lives. Nothing closed either (S5 review
I6), so every shutdown left both to die with the event loop."""

from __future__ import annotations

import inspect

from sro.infrastructure.temporal import worker
from sro.interface.http import app


def test_the_api_closes_the_page_driver_when_it_stops() -> None:
    source = inspect.getsource(app.lifespan)
    assert "container.aclose_clients()" in source, source
    assert source.index("yield") < source.index("container.aclose_clients()"), source


def test_the_worker_closes_the_page_driver_when_it_stops() -> None:
    source = inspect.getsource(worker.run)
    assert "container.aclose_clients()" in source, source
    assert source.index("finally") < source.index("container.aclose_clients()"), source
