"""A trimmed answer is a shorter answer, not a different kind of thing."""

from __future__ import annotations

import json

from sro.domain.lookup.answer import K_ANSWER_CHARS, K_ANSWER_ROWS, as_seen, trimmed


def _many(rows: int) -> str:
    """A warehouse collection: many records, forty fields each."""
    record = {f"field{n}": "x" * 40 for n in range(40)}
    return json.dumps({"@type": "ResponseBodyWrapper", "data": [record] * rows})


def test_a_body_of_records_is_cut_by_record_and_still_parses() -> None:
    """Measured on the deployment 2026-09-21: fifty customer types of forty
    fields each went past 64KB, the cut landed mid-object, and the panel --
    which reads `data` to count and tabulate -- fell back to 240 characters of
    raw JSON. That answers nothing and never reaches the row the question was
    about."""
    body = _many(500)
    assert len(body) > K_ANSWER_CHARS

    kept, cut = trimmed(body)

    assert cut is True
    assert kept is not None
    said = json.loads(kept)
    assert len(said["data"]) == K_ANSWER_ROWS
    assert said["@type"] == "ResponseBodyWrapper", "the envelope went with the rows"


def test_an_answer_that_fits_is_left_exactly_alone() -> None:
    body = _many(2)

    assert trimmed(body) == (body, False)


def test_a_body_that_is_not_records_is_cut_the_way_it_always_was() -> None:
    """A page of HTML, one object, a picture. There is nothing structural to
    preserve, and a character cut is the honest answer."""
    page = "<html>" + ("x" * K_ANSWER_CHARS) + "</html>"

    kept, cut = trimmed(page)

    assert cut is True
    assert kept == page[:K_ANSWER_CHARS]


def test_a_short_list_of_very_fat_records_is_not_pretended_to_fit() -> None:
    """Fewer records than the row cap, and still too big: the rows cannot be
    dropped without lying about how many there are, so the character cut
    stands and `truncated` says so."""
    body = json.dumps({"data": [{"huge": "x" * K_ANSWER_CHARS}]})

    kept, cut = trimmed(body)

    assert cut is True
    assert kept is not None and len(kept) == K_ANSWER_CHARS


def test_nothing_to_trim_is_nothing() -> None:
    assert trimmed(None) == (None, False)


def test_the_shape_every_surface_draws_from() -> None:
    """One shaping, used by the wire and by the conversation. Two would be two
    answers to the same question."""
    seen = as_seen(
        system="WM",
        target="/data/WM/wm/customerTypes",
        ok=True,
        detail="",
        answer={"status": 200, "body": '{"data":[{"customerType":"KKYT"}]}'},
    )

    assert seen["status"] == 200
    assert seen["truncated"] is False
    assert "KKYT" in str(seen["body"])


def test_a_picture_is_not_carried() -> None:
    """Hundreds of kilobytes of base64 per screen, and what it MEANS is a
    model's question rather than a field on this shape."""
    seen = as_seen(
        system="WM",
        target="#wm.config/...",
        ok=True,
        detail="",
        answer={"image_base64": "iVBORw0KGgo=", "width": 1280, "height": 800},
    )

    assert seen["body"] is None
    assert "image_base64" not in seen
