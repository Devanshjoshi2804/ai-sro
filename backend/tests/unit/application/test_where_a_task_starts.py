"""The page a task starts on, remembered.

A nudge -- "you have done this here before, shall I do it?" -- fires when the
operator lands where a task starts, so the candidate has to know where that is.
It is the first page seen in the first episode, host and path only: the query
string is where a warehouse system puts session ids and timestamps, and a page
that is never the same page twice is a page nothing can ever recognise.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sro.application.observation.segment import Observed, segment
from sro.domain.shared.identifiers import BatchId

AT = datetime(2026, 9, 3, 10, 0, tzinfo=UTC)
BATCH = BatchId("bat_one")


def _gesture(seconds: int, url: str) -> Observed:
    return Observed(
        at=AT + timedelta(seconds=seconds),
        kind="gesture",
        host="wms.example",
        batch_id=BATCH,
        url=url,
    )


def _call(seconds: int) -> Observed:
    return Observed(
        at=AT + timedelta(seconds=seconds),
        kind="request",
        host="wms.example",
        batch_id=BATCH,
        method="POST",
        url="https://wms.example/api/suppliers",
        mutating=True,
    )


def test_an_episode_starts_on_the_first_page_it_saw_without_its_query() -> None:
    [piece] = segment([_gesture(0, "https://wms.example/ui/suppliers/new?sid=abc&t=1"), _call(3)])

    assert piece.episode.starts_on == "wms.example/ui/suppliers/new"


def test_an_episode_with_no_url_starts_nowhere() -> None:
    """An older extension sent gestures without a URL. Nowhere is the honest
    answer, and a candidate that starts nowhere never nudges."""
    [piece] = segment([_gesture(0, ""), _call(3)])

    assert piece.episode.starts_on == ""
