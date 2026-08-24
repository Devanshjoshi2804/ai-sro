"""The real recorded base, read. Fixtures would prove only that fixtures parse."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import pytest

from sro.domain.knowledge.entry import EntryKind, EvidenceLevel
from sro.infrastructure.knowledge.catalogue import read_catalogue

# The tree was restructured and this guard was not, so it pointed at a
# directory that no longer exists and skipped every test in the file --
# quietly, which is the only way a skip is worse than a failure.
ROOT = Path(__file__).resolve().parents[3].parent / "knowledge-base"

pytestmark = pytest.mark.skipif(
    not (ROOT / "index" / "app-map.json").is_file(),
    reason="the recorded knowledge base is not checked out here",
)


@pytest.fixture(scope="module")
def claims() -> tuple:
    return read_catalogue(ROOT, system="blue_yonder")


def test_every_kind_of_thing_the_base_records_is_read(claims: tuple) -> None:
    kinds = Counter(claim.kind for claim in claims)

    assert kinds[EntryKind.SCREEN] > 300, "316 screens were captured"
    assert kinds[EntryKind.ENDPOINT] > 500, "551 endpoints were catalogued"
    assert kinds[EntryKind.FIELD] > 200
    assert kinds[EntryKind.FORM] > 50
    assert kinds[EntryKind.FLOW] > 10, "the full-cascade flows (not the terse lifecycle ones)"
    assert kinds[EntryKind.STATUS] > 100
    assert kinds[EntryKind.QUIRK] > 10


def test_a_flow_with_a_colliding_resource_name_still_gets_its_own_claim(
    claims: tuple,
) -> None:
    """A duplicate-name rejection flow and the ordinary create both name the
    same resource. `spec` is what tells them apart; `resource` alone would
    have silently dropped one at ingest."""
    flows = [claim for claim in claims if claim.kind is EntryKind.FLOW]
    resources = {claim.body["resource"] for claim in flows}

    colliding = [r for r in resources if sum(1 for c in flows if c.body["resource"] == r) > 1]
    assert colliding, "the base has more than one flow for the same resource"


def test_claims_keep_the_evidence_level_they_were_recorded_at(claims: tuple) -> None:
    """Flattening everything to "we know this" is what the base's own audit
    caught. Help-text fields are asserted; a re-run probe battery is not."""
    by_kind = {kind: set() for kind in EntryKind}
    for claim in claims:
        by_kind[claim.kind].add(claim.evidence)

    assert by_kind[EntryKind.FIELD] == {EvidenceLevel.ASSERTED}
    assert EvidenceLevel.REPRODUCED in by_kind[EntryKind.STATUS]
    assert EvidenceLevel.ROUND_TRIP in by_kind[EntryKind.QUIRK]


def test_a_falsified_claim_is_kept_and_marked(claims: tuple) -> None:
    """ "We believed this and it was wrong" is the most useful row in the base."""
    quirks = [claim for claim in claims if claim.kind is EntryKind.QUIRK]
    falsified = [claim for claim in quirks if claim.body.get("falsified")]

    assert falsified, "the base records claims its own re-testing knocked down"


def test_the_verifier_can_tell_the_two_404s_apart(claims: tuple) -> None:
    """ROUTE-MISSING means the endpoint never existed; RECORD-MISSING means it
    exists and the record is gone. Only the second proves a delete worked."""
    kinds = {
        claim.body.get("kind")
        for claim in claims
        if claim.kind is EntryKind.STATUS and claim.body.get("status") == 404
    }

    assert {"ROUTE-MISSING", "RECORD-MISSING"} <= kinds


def test_no_two_claims_of_a_kind_share_a_key(claims: tuple) -> None:
    """Two entries with one key are one claim believed twice, which supersession
    handles — but inside a single read it means the reader is losing records."""
    seen = Counter((claim.kind, claim.key) for claim in claims)

    assert [key for key, count in seen.items() if count > 1] == []
