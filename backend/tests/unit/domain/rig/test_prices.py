import pytest

from sro.domain.shared.prices import PRICES, price


def test_a_price_is_dollars_per_million_tokens() -> None:
    """Gemini 3.8 Flash: $0.75 in, $3.75 out, introductory to 2026-12-31."""
    assert PRICES["gemini-3.8-flash"] == (0.75, 3.75)

    assert price("gemini-3.8-flash", 1_000_000, 0) == pytest.approx(0.75)
    assert price("gemini-3.8-flash", 0, 1_000_000) == pytest.approx(3.75)
    assert price("gemini-3.8-flash", 1000, 200) == pytest.approx(0.00075 + 0.00075)


def test_an_unknown_model_costs_nothing_and_does_not_raise() -> None:
    """A rig must not fall over because a price list is stale."""
    assert price("gemini-9-imaginary", 1000, 1000) == 0.0


def test_a_long_prompt_doubles_gemini_3_1_pro_rates() -> None:
    """Above 200K input tokens the standard rate no longer applies."""
    under = price("gemini-3.1-pro", 200_000, 0)
    over = price("gemini-3.1-pro", 200_001, 0)

    assert under == pytest.approx(200_000 * 2.00 / 1_000_000)
    assert over == pytest.approx(200_001 * 4.00 / 1_000_000)
