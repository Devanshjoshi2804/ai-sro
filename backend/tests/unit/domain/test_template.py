"""Templates.

The one thing worth proving here is that recorded JSON bodies -- which are made
of braces -- do not produce phantom parameters. That is the entire reason the
placeholder syntax is ``$name`` rather than ``{name}``.
"""

from __future__ import annotations

import pytest

from sro.domain.shared.errors import InvariantViolation
from sro.domain.shared.identifiers import RecordingId, SkillId, TenantId
from sro.domain.shared.objective import Direction, ObjectiveKey
from sro.domain.skill.template import Template


class TestTemplate:
    def test_json_braces_are_not_mistaken_for_parameters(self) -> None:
        body = Template('{"shipmentId": "12345", "lines": [{"qty": 3}]}')

        assert body.placeholders == frozenset()
        assert body.is_literal

    def test_placeholders_are_found_in_both_syntaxes(self) -> None:
        assert Template("/api/orders/$order_id/lines/${line_no}").placeholders == {
            "order_id",
            "line_no",
        }

    def test_rendering_refuses_to_leave_a_hole(self) -> None:
        # A half-substituted URL on a POST is not a recoverable outcome.
        with pytest.raises(KeyError):
            Template("/api/orders/$order_id").render({})


class TestIdentifiers:
    def test_ids_of_different_kinds_never_compare_equal(self) -> None:
        # mypy also rejects this comparison, which is the same guarantee one
        # layer earlier. The runtime check stands for callers that lose types.
        assert SkillId("x") != RecordingId("x")  # type: ignore[comparison-overlap]

    def test_blank_ids_are_rejected(self) -> None:
        with pytest.raises(InvariantViolation):
            TenantId("   ")


class TestObjectiveKey:
    def test_equality_is_structural_which_is_what_pairs_two_runs(self) -> None:
        assert ObjectiveKey(
            objective_type="release_wave",
            target_system="blue_yonder",
            entity_type="shipment",
            facility="DC01",
            direction=Direction.OUTBOUND,
        ) == ObjectiveKey(
            objective_type="release_wave",
            target_system="blue_yonder",
            entity_type="shipment",
            facility="DC01",
            direction=Direction.OUTBOUND,
        )

    def test_the_same_task_at_a_different_facility_is_a_different_objective(self) -> None:
        from tests import factories as f

        assert f.objective() != f.objective(facility="DC02")

    def test_slug_is_stable_and_readable(self) -> None:
        from tests import factories as f

        assert f.objective().slug() == "blue_yonder/DC01/shipment/outbound/resolve_short_ship"
