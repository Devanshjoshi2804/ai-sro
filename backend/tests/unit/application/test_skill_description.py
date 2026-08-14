"""A skill says what it does, because that is how it will be found."""

from __future__ import annotations

import pytest

from sro.application.induction.describe import compose
from sro.domain.shared.errors import InvariantViolation
from sro.domain.skill.parameter import ParameterKind
from sro.domain.skill.template import Template
from tests import factories as f

ADJUST = f.network_plan(
    method="PUT",
    url=Template("https://wms.test/data/WM/wm/inventory/adjust?siteId=SG"),
    body=Template('{"quantity": "${quantity}"}'),
)


async def test_the_description_names_the_task_and_the_call_it_writes_with() -> None:
    described = compose(
        f.objective(objective_type="adjust", entity_type="inventory", facility="SG"),
        (f.step(0, network_plan=ADJUST),),
        (f.parameter(name="lpn"), f.parameter(name="quantity")),
    )

    assert described.summary.startswith("Adjust inventory at SG on blue_yonder.")
    assert "PUT /data/WM/wm/inventory/adjust" in described.summary
    assert "Needs lpn, quantity." in described.when_to_use


async def test_a_read_only_skill_says_so_rather_than_naming_no_write() -> None:
    described = compose(
        f.objective(objective_type="view", entity_type="inventory"),
        (f.step(0, network_plan=f.network_plan(method="GET")),),
        (),
    )

    assert "reading only." in described.summary


async def test_the_operators_own_words_are_quoted_rather_than_paraphrased() -> None:
    described = compose(
        f.objective(),
        (f.step(0, narration="that leaves the count queued for approval"),),
        (),
    )

    assert '"that leaves the count queued for approval"' in described.summary


async def test_a_step_needing_a_human_is_part_of_knowing_when_to_use_it() -> None:
    described = compose(
        f.objective(),
        (f.step(0, requires_human=True, branch_hint="If the count does not match, raise it"),),
        (),
    )

    assert "One step needs a human." in described.when_to_use
    assert "Not covered: If the count does not match" in described.when_to_use


async def test_a_version_cannot_be_left_undescribed() -> None:
    version = f.skill_version()

    with pytest.raises(InvariantViolation):
        version.describe(summary="   ", when_to_use="anything")


async def test_rewording_changes_what_finds_it_and_nothing_else() -> None:
    version = f.skill_version()
    before = version.steps

    version.describe(summary="Cycle count correction", when_to_use="After a physical count")

    assert version.summary == "Cycle count correction"
    assert version.steps is before
    assert version.parameters[0].kind is ParameterKind.INPUT
