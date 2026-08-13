"""Skill aggregate: the invariants that stop an unrunnable skill from existing."""

from __future__ import annotations

import pytest

from sro.domain.shared.errors import InvariantViolation
from sro.domain.skill.parameter import Parameter, ParameterKind
from sro.domain.skill.promotion import PromotionStage
from sro.domain.skill.skill import SkillStep, SkillVersion
from sro.domain.skill.template import Template
from tests import factories as f


class TestSkillStep:
    def test_a_step_with_no_plan_at_all_is_rejected(self) -> None:
        with pytest.raises(InvariantViolation, match="no way to perform it"):
            SkillStep(index=0, intent="do the thing")

    def test_either_plan_alone_is_enough(self) -> None:
        assert SkillStep(index=0, intent="click", ui_plan=f.ui_plan())
        assert SkillStep(index=0, intent="call", network_plan=f.network_plan())

    def test_placeholders_are_collected_from_both_plans_and_assertions(self) -> None:
        step = f.step(
            network_plan=f.network_plan(url=Template("https://wms.test/${shipment_id}")),
            ui_plan=f.ui_plan(value=Template("${reason_code}")),
        )

        assert step.placeholders == {"shipment_id", "reason_code"}


class TestVersionInvariants:
    def test_a_template_hole_with_no_declared_parameter_is_rejected(self) -> None:
        # The whole point of validating here: at induction the recordings that
        # would explain the missing parameter are still to hand. At execution
        # time they are not, and the failure is a half-built URL on a POST.
        with pytest.raises(InvariantViolation, match="undeclared parameters: shipment_id"):
            SkillVersion(
                version=1,
                steps=(f.step(),),
                parameters=(),
                provenance=f.provenance(),
            )

    def test_step_indices_must_be_contiguous_from_zero(self) -> None:
        with pytest.raises(InvariantViolation, match=r"0\.\.n-1"):
            SkillVersion(
                version=1,
                steps=(f.step(0), f.step(2)),
                parameters=(f.parameter(),),
                provenance=f.provenance(),
            )

    def test_duplicate_parameter_names_are_rejected(self) -> None:
        with pytest.raises(InvariantViolation, match="unique"):
            SkillVersion(
                version=1,
                steps=(f.step(),),
                parameters=(f.parameter(), f.parameter()),
                provenance=f.provenance(),
            )

    def test_a_derived_parameter_cannot_be_used_before_it_is_produced(self) -> None:
        # Session ids and server-generated LPNs are derived. Using one at step 0
        # when step 1 produces it means nothing can ever populate it.
        derived = Parameter(
            name="shipment_id",
            kind=ParameterKind.DERIVED,
            source_step_index=1,
            source_pointer="/data/id",
        )

        with pytest.raises(InvariantViolation, match="used at step 0"):
            SkillVersion(
                version=1,
                steps=(f.step(0), f.step(1, network_plan=None)),
                parameters=(derived,),
                provenance=f.provenance(),
            )

    def test_derived_parameters_are_excluded_from_inputs(self) -> None:
        version = f.skill_version()

        assert [p.name for p in version.inputs] == ["shipment_id"]

    def test_provenance_is_mandatory(self) -> None:
        with pytest.raises(InvariantViolation, match="cite the recordings"):
            f.provenance(recording_ids=())


class TestVersioning:
    def test_versions_are_append_only_and_sequential(self) -> None:
        skill = f.skill(versions=2)

        assert [v.version for v in skill.versions] == [1, 2]
        assert skill.latest.version == 2

        with pytest.raises(InvariantViolation, match="expected v3"):
            skill.add_version(f.skill_version(version=5))

    def test_a_new_version_always_starts_unpromoted(self) -> None:
        skill = f.skill(versions=0)

        with pytest.raises(InvariantViolation, match="starts at RECORDED"):
            skill.add_version(f.skill_version(stage=PromotionStage.SHADOW))

    def test_promoting_a_new_version_does_not_touch_the_reviewed_one(self) -> None:
        skill = f.skill(versions=1)
        skill.versions[0].promote(PromotionStage.SHADOW, f.at(700), f.OPERATOR)
        skill.add_version(f.skill_version(version=2))

        assert skill.version(1).stage is PromotionStage.SHADOW
        assert skill.version(2).stage is PromotionStage.RECORDED
