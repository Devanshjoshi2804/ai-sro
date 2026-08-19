"""Fetching all of something, when the system hands it over a page at a time.

"How many suppliers are there" is answerable from one page, because the
envelope says how many exist. "Which ones are they" is not: the operator asked
for the suppliers and got the first fifty, with the rest behind a page number
nobody in a warehouse should have to know about.

So a read that came back paged is followed to the end. The paging is the
system's own -- the parameters the demonstration used are the parameters this
walks, in the dialect that endpoint proved it speaks -- and it stops at a limit
rather than trusting a `total` it was told, because a collection that grows
while it is being read would otherwise never finish.
"""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlencode, urlsplit, urlunsplit

from sro.application.induction.sites import url_query_pairs

MOST_PAGES = 40
"""A ceiling on politeness, not on correctness. Forty pages of fifty is two
thousand records -- past that this is a report, not an answer, and hammering a
warehouse's API to render a table nobody will scroll is not a service."""

_OFFSET_KEYS = ("offset", "start", "skip")
_PAGE_KEYS = ("page", "pageno", "pagenumber")
_LIMIT_KEYS = ("limit", "pagesize", "size", "count", "max")


@dataclass(frozen=True, slots=True)
class Paging:
    """How this endpoint was seen to page, read off the request it made."""

    offset_key: str | None
    page_key: str | None
    limit: int

    first_page: int = 0
    """The page number the demonstrated call itself asked for.

    Counted from, rather than assumed to be zero. Against a one-based API the
    first "next" page was page one -- the page already in hand -- so every row
    on it was counted twice and the total was reported a page out.
    """

    @property
    def pages(self) -> bool:
        return self.offset_key is not None or self.page_key is not None


def how_it_pages(url: str) -> Paging:
    """The paging parameters this call carried, if any."""
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
    """The same call, asking for what comes after what has been read.

    ``None`` when this endpoint showed no way to ask -- and then one page is
    all there is to have, which the answer says rather than implies.
    """
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
