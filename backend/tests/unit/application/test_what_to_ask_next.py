"""The chips under a result were three sentences hard-coded in the browser.

One of them — "which X are used for parcel" — was written for a transport-mode
demo and then offered under every result in the system, including entities
where nothing could answer it. A suggestion the system cannot act on
advertises a capability that does not exist.
"""

from __future__ import annotations

import pytest

from sro.application.context import RequestContext
from sro.application.intent.next_steps import SuggestNext
from sro.domain.shared.identifiers import PrincipalId, TenantId
from tests import factories as f
from tests.unit.fakes import FakeUnitOfWork

CTX = RequestContext(tenant_id=TenantId("acme"), principal_id=PrincipalId("clerk"))


@pytest.fixture
async def uow() -> FakeUnitOfWork:
    unit = FakeUnitOfWork()
    await unit.skills.add(
        f.skill(
            name="Create supplier",
            objective_key=f.objective(
                target_system="blue_yonder", entity_type="supplier", objective_type="create"
            ),
        )
    )
    return unit


class TestEarningASuggestion:
    async def test_a_column_with_a_few_values_becomes_a_filter(self, uow: FakeUnitOfWork) -> None:
        """The values came out of the answer it is offered under, so the
        narrowing path can compose exactly this request."""
        offered = await SuggestNext(uow, None).after(
            CTX,
            system="blue_yonder",
            entity="supplier",
            values={"countryName": ("CAN", "USA")},
            rows=239,
        )

        assert any("countryName CAN" in text for text in offered)

    async def test_a_taught_skill_for_this_entity_is_offered_by_name(
        self, uow: FakeUnitOfWork
    ) -> None:
        offered = await SuggestNext(uow, None).after(
            CTX,
            system="blue_yonder",
            entity="supplier",
            values={"countryName": ("CAN", "USA")},
            rows=239,
        )

        assert "create a supplier" in offered

    async def test_a_skill_for_another_entity_is_not_offered(self, uow: FakeUnitOfWork) -> None:
        """ "Create a supplier" under a list of waves is a chip that leads
        somewhere nobody asked to go."""
        offered = await SuggestNext(uow, None).after(
            CTX,
            system="blue_yonder",
            entity="wave",
            values={"status": ("OPEN", "CLOSED")},
            rows=12,
        )

        assert not any("supplier" in text for text in offered)

    async def test_an_identifier_is_never_offered_as_a_filter(self, uow: FakeUnitOfWork) -> None:
        """A column with a different value in every record is a needle, and
        offering one from somebody's own haystack is not a suggestion."""
        offered = await SuggestNext(uow, None).after(
            CTX,
            system="blue_yonder",
            entity="supplier",
            values={"supplierNumber": ("A", "B", "C")},
            rows=3,
        )

        assert not any("supplierNumber" in text for text in offered)

    async def test_nothing_is_offered_when_nothing_is_earned(self, uow: FakeUnitOfWork) -> None:
        """No skills for this entity, no categorical columns — so no chips.
        Silence is better than a suggestion that goes nowhere."""
        assert (
            await SuggestNext(uow, None).after(
                CTX, system="other_wms", entity="pallet", values={}, rows=0
            )
            == ()
        )
