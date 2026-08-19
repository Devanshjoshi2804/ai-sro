"""Parameter naming.

The name is the first thing a supervisor reads on a skill, so a wrong one is a
review problem rather than a cosmetic one.
"""

from __future__ import annotations

import pytest

from sro.application.induction.naming import deduplicate, snake_case, suggest_name
from sro.application.induction.sites import (
    ActionValueSite,
    JsonBodySite,
    UrlPathSite,
    UrlQuerySite,
)

URL = "https://wms.test/api/waves/W-1001/release"


class TestPathSegments:
    def test_an_id_is_named_after_the_segment_before_it(self) -> None:
        # Segment 2 of the *path* is the wave id. Counting segments from the
        # whole URL instead names it after the host.
        assert suggest_name(UrlPathSite(2), url=URL) == "wave_id"

    def test_a_leading_segment_falls_back_to_its_position(self) -> None:
        assert suggest_name(UrlPathSite(0), url=URL) == "path_0"

    def test_a_relative_url_names_the_same_way(self) -> None:
        assert suggest_name(UrlPathSite(2), url="/api/orders/12345") == "order_id"


class TestOtherSites:
    @pytest.mark.parametrize(
        ("pointer", "expected"),
        [("/shipmentId", "shipment_id"), ("/lines/0/sku", "sku"), ("", "body_value")],
    )
    def test_body_pointers_use_the_last_named_token(self, pointer: str, expected: str) -> None:
        assert suggest_name(JsonBodySite(pointer), url=URL) == expected

    def test_query_keys_are_used_verbatim_in_snake_case(self) -> None:
        assert suggest_name(UrlQuerySite("orderNumber"), url=URL) == "order_number"

    def test_a_typed_value_is_named_after_its_field_label(self) -> None:
        assert suggest_name(ActionValueSite(), url=URL, field_label="Wave ID") == "wave_id"


def test_snake_case_handles_the_shapes_wms_payloads_actually_use() -> None:
    assert snake_case("shipmentId") == "shipment_id"
    assert snake_case("Order Number") == "order_number"
    assert snake_case("123") == "value_123"


def test_a_collision_suffixes_rather_than_merges() -> None:
    assert deduplicate("wave_id", {"wave_id"}) == "wave_id_2"


def test_a_name_that_is_not_plain_ascii_is_one_word() -> None:
    """``[a-z0-9]+`` split "zürich" into "z" and "rich", so a facility or a
    supplier whose name carries an accent was matched on fragments of itself --
    and "rich" is a word that turns up elsewhere."""
    from sro.application.intent.match import words

    assert "zürich" in words("the Zürich facility")
    assert "rich" not in words("the Zürich facility")
