import pytest

from sro.domain.shared.prices import PRICES, is_priced, price


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


def test_a_preview_model_is_priced_like_what_it_previews() -> None:
    """A pass on a preview name recorded cost_usd 0.0 with unpriced=True: honest
    and useless. The run that proved this architecture works billed $1.12 and
    every row said free."""
    for preview, real in (
        ("gemini-3.1-pro-preview", "gemini-3.1-pro"),
        ("gemini-3-flash-preview", "gemini-3-flash"),
        ("gemini-3.8-flash-preview", "gemini-3.8-flash"),
    ):
        assert is_priced(preview), preview
        assert price(preview, 40_000, 30_000) == price(real, 40_000, 30_000)

    # And the long-prompt doubling follows the preview too, or a 200K+ pass on
    # the preview name would be priced at half the real rate.
    assert price("gemini-3.1-pro-preview", 250_000, 1_000) == price(
        "gemini-3.1-pro", 250_000, 1_000
    )
