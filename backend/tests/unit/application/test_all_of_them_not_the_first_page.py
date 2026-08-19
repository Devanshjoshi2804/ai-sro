"""“Which suppliers do we have?” is not a question about the first fifty.

The count was fixed first: the envelope says how many exist. What stayed broken
was the list beside it — 238 found, 25 carried back — which is a table an
operator cannot use for a question they asked in full.
"""

from __future__ import annotations

import json

from sro.application.execution.answer import merge, read_answer
from sro.application.execution.paging import how_it_pages, next_page

LISTING = "https://wms.test/data/WM/wm/suppliers?query=%5B%5D&offset=0&limit=50&siteId=SG"


def _page(rows: int, start: int = 0, total: int | None = 238) -> str:
    body: dict[str, object] = {
        "data": [
            {"supplierNumber": f"S{n + start}", "addressName": f"NAME {n + start}"}
            for n in range(rows)
        ]
    }
    if total is not None:
        body["total"] = total
    return json.dumps(body)


class TestHowItPages:
    def test_the_paging_is_read_off_the_call_the_demonstration_made(self) -> None:
        paging = how_it_pages(LISTING)

        assert paging.offset_key == "offset"
        assert paging.limit == 50

    def test_the_next_page_asks_for_what_has_not_been_read(self) -> None:
        paging = how_it_pages(LISTING)

        assert "offset=50" in (next_page(LISTING, paging, so_far=50, page=0) or "")
        assert "limit=50" in (next_page(LISTING, paging, so_far=50, page=0) or "")

    def test_an_endpoint_that_showed_no_paging_cannot_be_paged(self) -> None:
        """Inventing `?page=2` for an API that never showed us one is a guess."""
        plain = "https://wms.test/data/WM/wm/transportModes?siteId=SG"

        assert next_page(plain, how_it_pages(plain), so_far=16, page=0) is None

    def test_a_page_numbered_api_is_walked_by_page(self) -> None:
        numbered = "https://wms.test/things?page=1&pageSize=20"

        following = next_page(numbered, how_it_pages(numbered), so_far=20, page=1)

        assert "page=2" in (following or "")


class TestMerging:
    def test_every_page_is_one_answer(self) -> None:
        pages = (
            read_answer(_page(50, start=0), url=LISTING),
            read_answer(_page(50, start=50), url=LISTING),
            read_answer(_page(38, start=100), url=LISTING),
        )

        whole = merge(tuple(p for p in pages if p))

        assert whole is not None
        assert whole.rows == 138
        assert len(whole.sample) == 138
        # The count still comes from the system, not from how much we read.
        assert whole.counted == 238

    def test_reading_to_the_end_is_not_a_partial_answer(self) -> None:
        """A full first page says "at least 50" on its own. Followed to the end
        it is simply the answer."""
        first = read_answer(_page(50, total=None), url=LISTING)
        assert first is not None and first.partial

        whole = merge((first, read_answer(_page(12, start=50, total=None), url=LISTING)))  # type: ignore[arg-type]

        assert whole is not None
        assert not whole.partial
        assert whole.counted == 62
