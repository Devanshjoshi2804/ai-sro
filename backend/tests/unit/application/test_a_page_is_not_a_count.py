"""“How many suppliers are there?” — 50. There were 330,140.

Fifty was the page size. The number was right there in the envelope beside the
records, and the run reported the length of the list it happened to receive, so
the operator was given a confident wrong number about their own warehouse —
which is the one output this system is arranged to never produce.
"""

from __future__ import annotations

import json

from sro.application.execution.answer import read_answer

LISTING = "https://wms.test/data/WM/wm/suppliers?siteId=SG&limit=50&offset=0"


def _page(rows: int, **envelope: object) -> str:
    return json.dumps({"data": [{"supplierNumber": f"S{n}"} for n in range(rows)], **envelope})


def test_the_size_of_the_whole_set_is_the_answer_not_the_page() -> None:
    answer = read_answer(_page(50, total=330140), url=LISTING)

    assert answer is not None
    assert answer.rows == 50
    assert answer.counted == 330140
    assert "330140 suppliers" in answer.sentence("suppliers")


def test_a_full_page_with_no_total_refuses_to_give_a_number() -> None:
    """The honest answer to a page is "at least this many"."""
    answer = read_answer(_page(50), url=LISTING)

    assert answer is not None
    assert answer.counted is None
    assert answer.partial
    said = answer.sentence("suppliers")
    assert said.startswith("At least 50 suppliers")
    assert "did not say how many" in said


def test_a_short_page_is_the_whole_answer() -> None:
    """Fewer records than were asked for means there are no more."""
    answer = read_answer(_page(23), url=LISTING)

    assert answer is not None
    assert answer.counted == 23
    assert not answer.partial
    assert answer.sentence("transport modes").startswith("There are 23 transport modes")


def test_a_number_we_put_in_the_request_is_not_a_total() -> None:
    """`limit=50` echoed back as `50` says the server heard us, nothing more."""
    answer = read_answer(_page(50, limit=50, offset=0), url=LISTING)

    assert answer is not None
    assert answer.total is None
    assert answer.counted is None


def test_two_candidate_totals_are_no_total_at_all() -> None:
    """Acting on whichever came first is the wrong-answer failure with extra
    steps. The system says it cannot say."""
    answer = read_answer(_page(50, total=330140, filtered=91), url=LISTING)

    assert answer is not None
    assert answer.total is None
    assert answer.counted is None


def test_an_unpaged_read_still_answers_plainly() -> None:
    """Nothing in the request mentions paging, so the list is the answer."""
    answer = read_answer(_page(16), url="https://wms.test/data/WM/wm/transportModes?siteId=SG")

    assert answer is not None
    assert answer.counted == 16


def test_nothing_found_is_a_count_of_zero_not_a_shrug() -> None:
    answer = read_answer(json.dumps({"data": []}), url=LISTING)

    assert answer is not None
    assert answer.counted == 0
    assert answer.sentence("suppliers") == "Nothing matched — no suppliers came back."
