import hashlib
from pathlib import Path

import httpx
from httpx import ASGITransport

from sro.config import get_settings
from sro.interface.http.app import create_app


async def test_health_says_which_page_code_this_process_loaded() -> None:
    page_code = Path(get_settings().page_code_path).read_bytes()  # noqa: ASYNC240 - a small local file, once
    expected = hashlib.sha256(page_code).hexdigest()
    transport = ASGITransport(app=create_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as http:
        said = (await http.get("/health")).json()

    assert said["page_code"] == expected
