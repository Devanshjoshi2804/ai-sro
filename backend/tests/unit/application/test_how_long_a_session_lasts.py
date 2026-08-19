"""Nobody knows how long a WMS session lives, so the system watches.

Two hours or four is a guess, and both directions cost: too often signs the
operator out of a system that permits one session, too rarely means the first
thing anybody notices is a batch failing overnight. The credential says
nothing — three opaque cookies, no expiry — so the number is observed and kept
beside everything else known about that system.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from sro.application.connection.session_life import SAFETY, UNKNOWN_LIFE, Life, SessionLife
from sro.application.context import RequestContext
from sro.application.knowledge.record_claim import RecordClaims
from sro.domain.shared.identifiers import PrincipalId, TenantId
from tests.unit.fakes import FakeClock, FakeEmbedder, FakeIdFactory, FakeUnitOfWork

CTX = RequestContext(tenant_id=TenantId("acme"), principal_id=PrincipalId("clerk"))
NOON = datetime(2026, 8, 18, 12, tzinfo=UTC)


@pytest.fixture
def life() -> SessionLife:
    uow = FakeUnitOfWork()
    return SessionLife(uow, RecordClaims(uow, FakeClock(), FakeIdFactory(), FakeEmbedder()))


class TestWhatIsKnown:
    async def test_before_anything_is_observed_it_refreshes_often(self, life: SessionLife) -> None:
        """Being early costs one login. Being late costs the run."""
        known = await life.of(CTX, system="blue_yonder")

        assert known.observed is None
        assert known.refresh_after == UNKNOWN_LIFE * SAFETY

    async def test_a_session_that_died_teaches_how_long_they_last(self, life: SessionLife) -> None:
        await life.minted(CTX, system="blue_yonder", at=NOON)
        await life.worked(CTX, system="blue_yonder", at=NOON + timedelta(hours=4))
        await life.died(CTX, system="blue_yonder", at=NOON + timedelta(hours=5))

        known = await life.of(CTX, system="blue_yonder")

        # Four, not five: everything after the last call that worked is time
        # the session may already have been dead.
        assert known.observed == timedelta(hours=4)
        assert known.refresh_after == timedelta(hours=2)

    async def test_the_shortest_life_seen_is_the_one_kept(self, life: SessionLife) -> None:
        """A weekend where nothing was asked does not prove it survived one."""
        await life.minted(CTX, system="blue_yonder", at=NOON)
        await life.worked(CTX, system="blue_yonder", at=NOON + timedelta(hours=4))
        await life.died(CTX, system="blue_yonder", at=NOON + timedelta(hours=5))

        await life.minted(CTX, system="blue_yonder", at=NOON + timedelta(days=1))
        await life.worked(CTX, system="blue_yonder", at=NOON + timedelta(days=1, hours=1))
        await life.died(CTX, system="blue_yonder", at=NOON + timedelta(days=1, hours=2))

        assert (await life.of(CTX, system="blue_yonder")).observed == timedelta(hours=1)

    async def test_each_system_is_measured_on_its_own(self, life: SessionLife) -> None:
        await life.minted(CTX, system="blue_yonder", at=NOON)
        await life.worked(CTX, system="blue_yonder", at=NOON + timedelta(hours=8))
        await life.died(CTX, system="blue_yonder", at=NOON + timedelta(hours=9))

        assert (await life.of(CTX, system="another_wms")).observed is None

    async def test_a_death_with_nothing_recorded_before_it_teaches_nothing(
        self, life: SessionLife
    ) -> None:
        """No mint, no measurement. A made-up start would be a made-up number."""
        await life.died(CTX, system="blue_yonder", at=NOON)

        assert (await life.of(CTX, system="blue_yonder")).observed is None


class TestWhenToReplaceIt:
    def test_a_session_past_half_its_life_is_replaced_before_it_is_needed(self) -> None:
        known = Life(
            system="blue_yonder",
            observed=timedelta(hours=4),
            minted_at=NOON,
            last_good_at=NOON,
        )

        assert not known.worth_refreshing(NOON + timedelta(hours=1))
        assert known.worth_refreshing(NOON + timedelta(hours=2, minutes=1))

    def test_a_session_nobody_has_timed_is_left_to_the_short_default(self) -> None:
        known = Life(system="blue_yonder", observed=None, minted_at=NOON, last_good_at=NOON)

        assert known.worth_refreshing(NOON + timedelta(minutes=16))

    def test_without_a_start_there_is_nothing_to_measure_against(self) -> None:
        known = Life(
            system="blue_yonder", observed=timedelta(hours=4), minted_at=None, last_good_at=None
        )

        assert not known.worth_refreshing(NOON + timedelta(days=7))
