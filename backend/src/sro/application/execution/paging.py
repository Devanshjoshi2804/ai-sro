from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlencode, urlsplit, urlunsplit

from sro.application.induction.sites import url_query_pairs

MOST_PAGES = 40

_OFFSET_KEYS = ("offset", "start", "skip")
_PAGE_KEYS = ("page", "pageno", "pagenumber")
_LIMIT_KEYS = ("limit", "pagesize", "size", "count", "max")


@dataclass(frozen=True, slots=True)
class Paging:
    offset_key: str | None
    page_key: str | None
    limit: int

    first_page: int = 0

    @property
    def pages(self) -> bool:
        return self.offset_key is not None or self.page_key is not None


def how_it_pages(url: str) -> Paging:
    query = {key.lower(): value for key, value in url_query_pairs(url)}
    original = {key.lower(): key for key, _ in url_query_pairs(url)}

    limit = next(
        (int(query[key]) for key in _LIMIT_KEYS if key in query and query[key].isdigit()),
        0,
    )
    offset_key = next((original[key] for key in _OFFSET_KEYS if key in query), None)
    page_key = next((original[key] for key in _PAGE_KEYS if key in query), None)
    first = next(
        (int(query[key]) for key in _PAGE_KEYS if key in query and query[key].isdigit()),
        0,
    )
    return Paging(offset_key=offset_key, page_key=page_key, limit=limit, first_page=first)


def next_page(url: str, paging: Paging, *, so_far: int, page: int) -> str | None:
    if not paging.pages or paging.limit <= 0:
        return None

    parts = urlsplit(url)
    pairs = [
        (
            key,
            str(so_far)
            if paging.offset_key and key == paging.offset_key
            else str(paging.first_page + page + 1)
            if paging.page_key and key == paging.page_key
            else value,
        )
        for key, value in url_query_pairs(url)
    ]
    return urlunsplit(
        (parts.scheme, parts.netloc, parts.path, urlencode(pairs, safe="${}"), parts.fragment)
    )
