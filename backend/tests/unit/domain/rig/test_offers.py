"""`counsel_over`'s rules, and `clamped`'s, ported from
`new_agent_arch/tests/test_offers.py` without the store: every row is built
by hand as an `OfferRow` rather than read back from a SQLite `offers` table,
so what a repository's query would have selected -- the window's cut to
`K_WINDOW`, the tenant/device/`k > 0` filter, the `ORDER BY at DESC, id DESC`
tiebreak, the `off_` + hex id `record_offer` mints -- is the caller's
concern now, left for plan 3. Every assertion here lands on a `Counsel`
field, `as_json()`, or `clamped`'s string; never on a store.
"""

from datetime import UTC, datetime, timedelta

import pytest

from sro.domain.skill.offers import (
    K_OFFER_AFTER,
    K_QUIET_HOURS,
    Counsel,
    OfferRow,
    clamped,
    counsel_over,
    fate_of,
)


def _when(hour: int, day: int = 6) -> datetime:
    return datetime(2026, 9, day, hour, tzinfo=UTC)


def _at(hour: int, day: int = 6) -> str:
    return _when(hour, day=day).isoformat()


def test_a_fate_the_protocol_does_not_have_is_refused_and_named() -> None:
    """The last belt behind the route's own check, and it says which word it
    would not take -- a caller told only "bad fate" has to guess."""
    with pytest.raises(ValueError, match="ignored"):
        fate_of("ignored")


def test_a_job_nobody_has_answered_is_offered_at_the_default() -> None:
    advice = counsel_over([], [], now=_when(23))
    assert advice == Counsel(K_OFFER_AFTER, None)
    assert advice.as_json() == {
        "offer_after": K_OFFER_AFTER,
        "later": False,
        "quiet_until": None,
    }


def test_three_refusals_running_rest_the_job_for_a_day_on_that_browser() -> None:
    rows = [
        OfferRow(2, "dismissed", _at(12)),
        OfferRow(2, "did_it", _at(11)),
        OfferRow(2, "dismissed", _at(10)),
    ]
    resting = counsel_over(rows, rows[:3], now=_when(13))
    assert resting.quiet_until == (_when(12) + timedelta(hours=K_QUIET_HOURS)).isoformat()
    assert counsel_over(rows, rows[:2], now=_when(13)).quiet_until is None, "two is not enough"
    assert counsel_over(rows, [], now=_when(13)).quiet_until is None, "no browser, no rest"
    assert counsel_over(rows, rows[:3], now=_when(12, day=7)).quiet_until is None, "the day passed"


def test_an_offer_the_operator_did_not_refuse_breaks_the_run() -> None:
    expired_breaks = [
        OfferRow(2, "dismissed", _at(13)),
        OfferRow(2, "expired", _at(12)),
        OfferRow(2, "dismissed", _at(11)),
        OfferRow(2, "dismissed", _at(10)),
    ]
    assert counsel_over(expired_breaks, expired_breaks[:3], now=_when(14)).quiet_until is None

    accepted_breaks = [
        OfferRow(2, "dismissed", _at(16)),
        OfferRow(2, "dismissed", _at(15)),
        OfferRow(2, "accepted", _at(14)),
        *expired_breaks,
    ]
    assert counsel_over(accepted_breaks, accepted_breaks[:3], now=_when(17)).quiet_until is None


def test_an_arrival_nudge_is_not_evidence_either_way() -> None:
    """Arrival nudges are recorded at k = 0 -- "you have been here before",
    nothing typed -- and are neither kind of evidence. `counsel_over` does
    not know that itself: the repository's `k > 0` is what keeps them out,
    left for plan 3 (see the rig's original, listed there). Handed k = 0
    rows anyway, it reads them like any other -- three refused running still
    rests the job."""
    rows = [OfferRow(0, "dismissed", _at(h)) for h in (12, 11, 10)]
    advice = counsel_over(rows, rows, now=_when(13))
    assert advice.quiet_until is not None, "counsel_over trusts the rows it is given"


def test_offers_that_keep_diverging_move_the_job_past_where_they_diverged() -> None:
    two_diverged = [OfferRow(2, "diverged", _at(11)), OfferRow(2, "diverged", _at(10))]
    assert counsel_over(two_diverged, [], now=_when(23)).offer_after == K_OFFER_AFTER, (
        "two offers are not enough to read"
    )

    # Every browser's offers count towards the threshold.
    three_diverged = [OfferRow(3, "diverged", _at(13)), *two_diverged]
    later = counsel_over(three_diverged, [], now=_when(23))
    assert later.offer_after == 4, "one past the deepest k that diverged"
    assert later.as_json()["later"] is True

    # Half or more: three diverged of six still moves it ...
    six_total = [
        OfferRow(4, "accepted", _at(16)),
        OfferRow(4, "accepted", _at(15)),
        OfferRow(4, "accepted", _at(14)),
        *three_diverged,
    ]
    assert counsel_over(six_total, [], now=_when(23)).offer_after == 4

    # ... and three of seven does not.
    seven_total = [OfferRow(4, "accepted", _at(17)), *six_total]
    assert counsel_over(seven_total, [], now=_when(23)).offer_after == K_OFFER_AFTER


def test_only_the_newest_ten_offers_are_read() -> None:
    """The window is the caller's `SELECT ... LIMIT K_WINDOW`, left for plan
    3 (see the rig's original, listed there). `counsel_over` reads whatever
    window it is handed: cutting a longer one down to the newest `K_WINDOW`
    is the repository's job, not this function's -- handed all thirteen
    rows uncut, the three oldest still count towards the threshold."""
    newest_ten = [OfferRow(3, "accepted", _at(h)) for h in range(12, 6, -1)] + [
        OfferRow(3, "diverged", _at(h)) for h in range(6, 2, -1)
    ]
    oldest_three = [OfferRow(2, "diverged", _at(h)) for h in range(2, -1, -1)]
    assert counsel_over(newest_ten, [], now=_when(23)).offer_after == K_OFFER_AFTER, (
        "four of ten diverged is not half"
    )
    assert counsel_over(newest_ten + oldest_three, [], now=_when(23)).offer_after == 4, (
        "uncut, the three older diverged tip seven of thirteen past half"
    )


def test_offers_in_the_same_second_are_read_in_the_order_they_arrived() -> None:
    """All six offers tie on `at`; which three of them are "the newest
    three" turns on the repository's `ORDER BY at DESC, id DESC` -- arrival
    order, left for plan 3 (see the rig's original, listed there).
    `counsel_over` does not break the tie itself: it trusts the list it is
    given, in the order it is given, so whether the accepted offer landed
    among the newest three or not decides the answer."""
    at = _at(10)
    with_accepted = [
        OfferRow(2, "accepted", at),
        OfferRow(2, "dismissed", at),
        OfferRow(2, "dismissed", at),
    ]
    without_accepted = [OfferRow(2, "dismissed", at) for _ in range(3)]
    assert counsel_over(with_accepted, with_accepted, now=_when(11)).quiet_until is None, (
        "the accepted offer, wherever the tie put it, breaks the run"
    )
    assert counsel_over(without_accepted, without_accepted, now=_when(11)).quiet_until is not None


def test_a_browser_clock_ahead_of_the_rig_is_pulled_back_to_now() -> None:
    now = _when(10)
    assert clamped("2099-01-01T00:00:00Z", now) == now.isoformat()
    # Naive -- no offset written -- is read as the rig's own clock, UTC.
    assert clamped("2026-09-06T09:00:00", now) == _when(9).isoformat()
    # Behind now, the browser's own reading is kept.
    assert clamped("2026-09-06T08:00:00+00:00", now) == _when(8).isoformat()
